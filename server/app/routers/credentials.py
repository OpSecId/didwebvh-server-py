"""Credential management endpoints."""

import copy
import logging

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.models.web_schemas import CredentialUpload
from app.plugins import AskarVerifier, AskarStorage
from app.plugins.storage import StorageManager as SQLStorage
from app.db.models import DidControllerRecord

router = APIRouter(tags=["Verifiable Credentials"])
logger = logging.getLogger(__name__)

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


@router.post("/{namespace}/{identifier}/credentials")
async def publish_credential(
    request_body: CredentialUpload,
    did_controller: DidControllerRecord = Depends(get_did_controller_dependency)
):
    """Publish a verifiable credential."""
    logger.info(f"=== Publishing credential for {did_controller.namespace}/{did_controller.alias} ===")
    
    verifiable_credential = vars(request_body)["verifiableCredential"].model_dump()
    logger.debug(f"Credential ID: {verifiable_credential.get('id', 'unknown')}")
    
    credential = copy.deepcopy(verifiable_credential)
    proofs = credential.pop("proof")
    proofs = proofs if isinstance(proofs, list) else [proofs]
    logger.debug(f"Number of proofs: {len(proofs)}")

    # Extract the issuer proof (from did:webvh:)
    verifiable_credential["proof"] = next(
        (proof for proof in proofs if proof["verificationMethod"].startswith("did:webvh:")), None
    )

    if not verifiable_credential["proof"]:
        logger.error("No valid proof found for credential")
        raise HTTPException(status_code=400, detail="Credential must have a proof from the issuer DID")

    # Verify issuer matches the DID controller
    issuer = verifiable_credential.get("issuer")
    if isinstance(issuer, dict):
        issuer_did = issuer.get("id")
    else:
        issuer_did = issuer
    
    logger.debug(f"Issuer DID: {issuer_did}")
    if issuer_did != did_controller.did:
        logger.error(f"Issuer mismatch: {issuer_did} vs {did_controller.did}")
        raise HTTPException(status_code=400, detail="Issuer DID must match the controller DID")

    # Verify the credential proof
    logger.debug("Verifying credential proof...")
    try:
        # Use verifier to check the proof
        verifier.verify_resource_proof(copy.deepcopy(verifiable_credential))
        logger.debug("Credential proof verified successfully")
    except Exception as e:
        logger.error(f"Credential proof verification failed: {e}")
        raise HTTPException(status_code=400, detail=f"Credential proof verification failed: {str(e)}")

    # Ensure credential has an ID
    if not verifiable_credential.get("id"):
        logger.error("Credential missing ID field")
        raise HTTPException(status_code=400, detail="Credential must have an 'id' field")

    # Store credential in SQL database (uses scid from FK relationship)
    try:
        sql_storage.create_credential(did_controller.scid, verifiable_credential)
        logger.info(f"Credential {verifiable_credential['id']} stored successfully")
    except Exception as e:
        logger.error(f"Failed to store credential: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store credential: {str(e)}")

    return JSONResponse(status_code=201, content=verifiable_credential)


@router.get("/{namespace}/{identifier}/credentials/{credential_id}")
async def get_credential(
    credential_id: str,
    did_controller: DidControllerRecord = Depends(get_did_controller_dependency)
):
    """Fetch an existing credential."""
    logger.info(f"=== Fetching credential {credential_id} ===")

    # Get credential from SQL database
    credential_record = sql_storage.get_credential(credential_id)
    if not credential_record:
        raise HTTPException(status_code=404, detail="Credential not found")

    # Verify the credential belongs to this DID controller
    if credential_record.scid != did_controller.scid:
        raise HTTPException(status_code=403, detail="Credential does not belong to this DID")

    return JSONResponse(status_code=200, content=credential_record.verifiable_credential)


@router.get("/{namespace}/{identifier}/credentials")
async def list_credentials(
    did_controller: DidControllerRecord = Depends(get_did_controller_dependency),
    revoked: bool = None,
    limit: int = 50,
    offset: int = 0
):
    """List all credentials issued by this DID controller."""
    logger.info(f"=== Listing credentials for {did_controller.namespace}/{did_controller.alias} ===")

    filters = {"scid": did_controller.scid}
    if revoked is not None:
        filters["revoked"] = revoked

    credentials = sql_storage.get_credentials(filters=filters, limit=limit, offset=offset)
    total = sql_storage.count_credentials(filters=filters)

    return JSONResponse(
        status_code=200,
        content={
            "credentials": [c.verifiable_credential for c in credentials],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    )


@router.post("/{namespace}/{identifier}/credentials/{credential_id}/revoke")
async def revoke_credential(
    credential_id: str,
    did_controller: DidControllerRecord = Depends(get_did_controller_dependency)
):
    """Revoke a credential."""
    logger.info(f"=== Revoking credential {credential_id} ===")

    # Get credential from SQL database
    credential_record = sql_storage.get_credential(credential_id)
    if not credential_record:
        raise HTTPException(status_code=404, detail="Credential not found")

    # Verify the credential belongs to this DID controller
    if credential_record.scid != did_controller.scid:
        raise HTTPException(status_code=403, detail="Credential does not belong to this DID")

    # Revoke the credential
    success = sql_storage.revoke_credential(credential_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to revoke credential")

    logger.info(f"Credential {credential_id} revoked successfully")
    return JSONResponse(status_code=200, content={"message": "Credential revoked successfully"})
