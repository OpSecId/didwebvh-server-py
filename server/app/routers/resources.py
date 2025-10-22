"""Ressource management endpoints."""

import copy
import logging

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.models.web_schemas import ResourceUpload
from app.plugins import AskarVerifier, AskarStorage, DidWebVH
from app.plugins.storage import StorageManager as SQLStorage
from app.db.models import DidControllerRecord
from app.utilities import first_proof, sync_resource, get_client_id, resource_details

from config import settings

router = APIRouter(tags=["Attested Resources"])
logger = logging.getLogger(__name__)

webvh = DidWebVH()
storage = AskarStorage()
sql_storage = SQLStorage()
verifier = AskarVerifier()

# Dependency to get DID controller from path parameters
async def get_did_controller_dependency(
    namespace: str,
    identifier: str
) -> DidControllerRecord:
    """Get DID controller from database, raise 404 if not found."""
    did_controller = sql_storage.get_did_controller_by_alias(namespace, identifier)
    if not did_controller:
        raise HTTPException(status_code=404, detail="DID not found. Create the DID first.")
    return did_controller


@router.post("/{namespace}/{identifier}/resources")
async def upload_attested_resource(
    request_body: ResourceUpload,
    did_controller: DidControllerRecord = Depends(get_did_controller_dependency)
):
    """Upload an attested resource."""
    logger.info(f"=== Uploading resource for {did_controller.namespace}/{did_controller.alias} ===")
    
    secured_resource = vars(request_body)["attestedResource"].model_dump()
    logger.debug(f"Secured resource: {secured_resource.get('metadata', {}).get('resourceId', 'unknown')}")
    
    resource = copy.deepcopy(secured_resource)
    proofs = resource.pop("proof")
    proofs = proofs if isinstance(proofs, list) else [proofs]
    logger.debug(f"Number of proofs: {len(proofs)}")

    # Check if endorsement policy is set for attested resources
    logger.debug(f"Endorsement policy enabled: {settings.WEBVH_ENDORSEMENT}")
    if settings.WEBVH_ENDORSEMENT:
        try:
            assert len(proofs) == 2
            witness_proof = next(
                (proof for proof in proofs if proof["verificationMethod"].startswith("did:key:")),
                None,
            )
            # Get registry from SQL storage
            registry_record = sql_storage.get_registry("knownWitnesses")
            witness_registry = registry_record.registry_data if registry_record else {}
            witness_id = witness_proof.get("verificationMethod").split("#")[0]
            assert witness_registry.get(witness_id, None)
            assert verifier.verify_proof(resource, witness_proof, witness_id.split(":")[-1])
        except AssertionError as e:
            logger.error(f"Endorsement validation failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid endorsement witness proof.")

    secured_resource["proof"] = next(
        (proof for proof in proofs if proof["verificationMethod"].startswith("did:webvh:")), None
    )

    author_id = secured_resource["proof"].get("verificationMethod").split("#")[0]
    logger.debug(f"Author ID: {author_id}")
    if (
        len(author_id.split(":")) != 6
        or author_id.split(":")[4] != did_controller.namespace
        or author_id.split(":")[5] != did_controller.alias
    ):
        logger.error(f"Author ID mismatch: {author_id} vs {did_controller.namespace}/{did_controller.alias}")
        raise HTTPException(status_code=400, detail="Invalid author id value.")

    # This will ensure the verification method is registered on the server
    # and that the proof is valid
    logger.debug("Verifying resource proof...")
    try:
        verifier.verify_resource_proof(copy.deepcopy(secured_resource))
        logger.debug("Resource proof verified successfully")
    except Exception as e:
        logger.error(f"Resource proof verification failed: {e}")
        raise

    # This will ensure that the resource is properly assigned to it's issuer
    # and double check the digested path
    logger.debug("Validating resource...")
    try:
        webvh.validate_resource(copy.deepcopy(secured_resource))
        logger.debug("Resource validated successfully")
    except Exception as e:
        logger.error(f"Resource validation failed: {e}")
        raise

    resource_record, tags = sync_resource(secured_resource)
    store_id = webvh.resource_store_id(copy.deepcopy(secured_resource))

    # Store resource in SQL database (uses scid from FK relationship)
    sql_storage.create_resource(did_controller.scid, secured_resource)

    return JSONResponse(status_code=201, content=secured_resource)


@router.put("/{namespace}/{identifier}/resources/{resource_id}")
async def update_attested_resource(
    resource_id: str,
    request_body: ResourceUpload,
    did_controller: DidControllerRecord = Depends(get_did_controller_dependency)
):
    """Update an attested resource."""
    secured_resource = vars(request_body)["attestedResource"].model_dump()
    secured_resource["proof"] = first_proof(secured_resource["proof"])

    # This will ensure the verification method is registered
    # on the server and that the proof is valid
    verifier.verify_resource_proof(copy.deepcopy(secured_resource))

    # This will ensure that the resource is properly assigned
    # to it's issuer and double check the digested path
    webvh.validate_resource(copy.deepcopy(secured_resource))

    store_id = webvh.resource_store_id(copy.deepcopy(secured_resource))
    resource_id = secured_resource.get("metadata").get("resourceId")

    # Get existing resource from SQL database
    existing_resource = sql_storage.get_resource(resource_id)
    if not existing_resource:
        raise HTTPException(status_code=404, detail="Couldn't find resource.")

    webvh.compare_resource(existing_resource.attested_resource, copy.deepcopy(secured_resource))

    resource_record, tags = sync_resource(secured_resource)

    # Update resource in SQL database (extracts resource_id from attested_resource)
    sql_storage.update_resource(secured_resource)
    return JSONResponse(status_code=200, content=secured_resource)


@router.get("/{namespace}/{identifier}/resources/{resource_id}")
async def get_resource(
    resource_id: str,
    did_controller: DidControllerRecord = Depends(get_did_controller_dependency)
):
    """Fetch existing resource."""

    # Get resource from SQL database
    resource_record = sql_storage.get_resource(resource_id)
    if not resource_record:
        raise HTTPException(status_code=404, detail="Couldn't find resource.")

    return JSONResponse(status_code=200, content=resource_record.attested_resource)
