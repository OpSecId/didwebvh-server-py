"""Identifier endpoints for DIDWeb and DIDWebVH."""

import json
import logging

from fastapi import APIRouter, HTTPException, Response, Depends, Depends
from fastapi.responses import JSONResponse, RedirectResponse

from config import settings

logger = logging.getLogger(__name__)

from app.models.web_schemas import NewLogEntry, WhoisUpdate
from app.plugins import AskarStorage, AskarVerifier, DidWebVH, PolicyError
from app.plugins.storage import StorageManager
from app.db.models import DidControllerRecord
from app.db.models import DidControllerRecord
from app.utilities import (
    get_client_id,
    first_proof,
    find_verification_method,
    timestamp,
    sync_did_info,
)

router = APIRouter(tags=["Identifiers"])
askar = AskarStorage()
storage = StorageManager()
verifier = AskarVerifier()
webvh = DidWebVH()

# Dependency to get DID controller from path parameters
async def get_did_controller_dependency(
    namespace: str,
    identifier: str
) -> DidControllerRecord:
    """Get DID controller from database, raise 404 if not found."""
    did_controller = storage.get_did_controller_by_alias(namespace, identifier)
    if not did_controller:
        raise HTTPException(status_code=404, detail="Not Found")
    return did_controller


@router.get("/")
async def request_did(
    namespace: str = None,
    ns: str = None,
    identifier: str = None,
    alias: str = None,
):
    """Request a DID document and proof options for a given namespace and identifier.
    
    Query parameters:
        namespace or ns: The DID namespace (use one, not both)
        identifier or alias: The DID identifier/alias (use one, not both)
    """

    # Check if both namespace and ns are provided
    if namespace and ns:
        raise HTTPException(status_code=400, detail="Provide either 'namespace' or 'ns', not both.")
    
    # Check if both identifier and alias are provided
    if identifier and alias:
        raise HTTPException(status_code=400, detail="Provide either 'identifier' or 'alias', not both.")
    
    # Use whichever is provided
    namespace = namespace or ns
    identifier = identifier or alias

    if not namespace and not identifier:
        return RedirectResponse(url="/explorer", status_code=302)

    if not namespace or not identifier:
        raise HTTPException(status_code=400, detail="Missing namespace/ns and identifier/alias query parameters.")

    # Check if identifier already exists in database
    if storage.get_did_controller_by_alias(namespace, identifier):
        raise HTTPException(status_code=409, detail="Identifier unavailable.")

    if namespace in settings.RESERVED_NAMESPACES:
        raise HTTPException(status_code=400, detail=f"Unavailable namespace: {namespace}.")

    return JSONResponse(
        status_code=200,
        content={
            "versionId": webvh.scid_placeholder,
            "versionTime": timestamp(),
            "parameters": webvh.parameters(),
            "state": {
                "@context": ["https://www.w3.org/ns/did/v1"],
                "id": webvh.placeholder_id(namespace, identifier),
            },
            "proof": webvh.proof_options(),
        },
    )


@router.post("/{namespace}/{identifier}")
async def new_log_entry(
    namespace: str,
    identifier: str,
    request_body: NewLogEntry,
):
    """Create a new log entry for a given namespace and identifier."""

    log_entry = request_body.model_dump().get("logEntry")
    witness_signature = request_body.model_dump().get("witnessSignature")

    # Get existing DID controller if it exists
    did_controller = storage.get_did_controller_by_alias(namespace, identifier)
    
    prev_log_entries = did_controller.logs if did_controller else []
    prev_witness_file = did_controller.witness_file if did_controller else None

    # Get policy and registry (still from Askar for now)
    webvh = DidWebVH(
        active_policy=await askar.fetch("policy", "active"),
        active_registry=(await askar.fetch("registry", "knownWitnesses")).get("registry"),
    )

    # Create DID
    if not prev_log_entries:
        try:
            log_entries, witness_file = await webvh.validate_did_request(log_entry, witness_signature)
        except PolicyError as err:
            raise HTTPException(status_code=400, detail=f"Policy infraction: {err}")

        # Create DID controller in database (extracts all data from logs)
        controller = storage.create_did_controller(log_entries, witness_file)
        logger.info(f"Created DID controller: {controller.scid} ({controller.namespace}/{controller.alias})")

        return JSONResponse(status_code=201, content=log_entries[-1])

    # Update DID
    try:
        log_entries, witness_file = await webvh.update_did(
            log_entry=log_entry,
            log_entries=prev_log_entries,
            witness_signature=witness_signature,
            prev_witness_file=prev_witness_file,
        )

        # Update DID controller in database (re-extracts state from logs)
        storage.update_did_controller(did_controller.scid, log_entries, witness_file)
        
    except PolicyError as err:
        raise HTTPException(status_code=400, detail=f"Policy infraction: {err}")

    # Deactivate DID
    if log_entries[-1].get("parameters").get("deactivated"):
        try:
            webvh.deactivate_did()
        except PolicyError as err:
            raise HTTPException(status_code=400, detail=f"Policy infraction: {err}")

    return JSONResponse(status_code=200, content=log_entries[-1])


@router.get("/{namespace}/{identifier}/did.json")
async def read_did(did_controller: DidControllerRecord = Depends(get_did_controller_dependency)):
    """See https://identity.foundation/didwebvh/next/#publishing-a-parallel-didweb-did."""
    document_state = webvh.get_document_state(did_controller.logs)
    did_document = json.dumps(document_state.to_did_web())
    return Response(did_document, media_type="application/did+ld+json")


@router.get("/{namespace}/{identifier}/did.jsonl")
async def read_did_log(did_controller: DidControllerRecord = Depends(get_did_controller_dependency)):
    """See https://identity.foundation/didwebvh/next/#the-did-log-file."""
    log_entries = "\n".join([json.dumps(log_entry) for log_entry in did_controller.logs]) + "\n"
    return Response(log_entries, media_type="text/jsonl")


@router.get("/{namespace}/{identifier}/did-witness.json")
async def read_witness_file(did_controller: DidControllerRecord = Depends(get_did_controller_dependency)):
    """See https://identity.foundation/didwebvh/next/#the-witness-proofs-file."""
    if not did_controller.witness_file:
        raise HTTPException(status_code=404, detail="Not Found")

    return JSONResponse(status_code=200, content=did_controller.witness_file)


@router.get("/{namespace}/{identifier}/whois.vp")
async def read_whois(did_controller: DidControllerRecord = Depends(get_did_controller_dependency)):
    """See https://identity.foundation/didwebvh/v1.0/#whois-linkedvp-service."""
    if not did_controller.whois_presentation:
        raise HTTPException(status_code=404, detail="Not Found")

    return Response(json.dumps(did_controller.whois_presentation), media_type="application/vp")


@router.post("/{namespace}/{identifier}/whois")
async def update_whois(
    request_body: WhoisUpdate,
    did_controller: DidControllerRecord = Depends(get_did_controller_dependency)
):
    """
    Update WHOIS with a Verifiable Presentation.
    
    Supports both:
    - VerifiablePresentation (with Data Integrity proof)
    - EnvelopedVerifiablePresentation (VC-JOSE VP-JWT)
    
    See https://didwebvh.info/latest/whois/
    """
    doc_state = webvh.get_document_state(did_controller.logs)
    whois_vp = request_body.model_dump().get("verifiablePresentation")
    
    # Check if this is an EnvelopedVerifiablePresentation
    if whois_vp.get("type") == "EnvelopedVerifiablePresentation":
        # EnvelopedVP - the presentation is in a JWT data URL
        logger.info(f"Received EnvelopedVerifiablePresentation for {did_controller.did}")
        
        # TODO: Verify the VP-JWT signature
        # For now, just store it
        logger.warning(f"EnvelopedVP signature verification not yet implemented")
        
        # Store the EnvelopedVP
        storage.update_did_controller(
            scid=did_controller.scid,
            whois_presentation=whois_vp
        )
        
        return JSONResponse(status_code=200, content={"Message": "Whois EnvelopedVP updated."})
    
    # Standard VerifiablePresentation with Data Integrity proof
    whois_vp_copy = whois_vp.copy()
    proof = first_proof(whois_vp_copy.pop("proof"))

    if proof.get("verificationMethod").split("#")[0] != doc_state.document.get("id"):
        return JSONResponse(status_code=400, content={"Reason": "Invalid holder."})

    multikey = find_verification_method(doc_state.document, proof.get("verificationMethod"))

    if not multikey:
        return JSONResponse(status_code=400, content={"Reason": "Invalid verification method."})

    verifier.purpose = "authentication"
    if not verifier.verify_proof(whois_vp_copy, proof, multikey):
        return JSONResponse(status_code=400, content={"Reason": "Verification failed."})

    # Update DID controller with new WHOIS presentation
    storage.update_did_controller(
        scid=did_controller.scid,
        whois_presentation=whois_vp
    )

    return JSONResponse(status_code=200, content={"Message": "Whois VP updated."})
