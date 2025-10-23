"""Credential management endpoints."""

import copy
import logging

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from app.models.web_schemas import CredentialUpload
from app.plugins.storage import StorageManager as SQLStorage
from app.db.models import DidControllerRecord

router = APIRouter(tags=["Verifiable Credentials"])
logger = logging.getLogger(__name__)

sql_storage = SQLStorage()


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
    
    # Check credential type/format
    credential_type = verifiable_credential.get("type")
    if isinstance(credential_type, list):
        if "EnvelopedVerifiableCredential" in credential_type:
            credential_format = "EnvelopedVerifiableCredential"
        elif "VerifiableCredential" in credential_type:
            credential_format = "VerifiableCredential"
        else:
            credential_format = "Unknown"
    else:
        credential_format = credential_type if credential_type else "Unknown"
    
    logger.info(f"Credential format: {credential_format}")
    
    # Validate format is recognized
    if credential_format == "Unknown":
        logger.error(f"Unrecognized credential type: {credential_type}")
        raise HTTPException(
            status_code=400, 
            detail="Credential type must be 'VerifiableCredential' or 'EnvelopedVerifiableCredential'"
        )

    # Check for credentialId in options
    # For EnvelopedVCs, we need to preserve the data URL and use options.credentialId as the lookup key
    options = vars(request_body).get("options")
    custom_credential_id = None
    if options and hasattr(options, "credentialId") and options.credentialId:
        logger.info(f"Using custom credentialId from options: {options.credentialId}")
        custom_credential_id = options.credentialId
        
        # Only override ID for non-enveloped credentials
        if credential_format != "EnvelopedVerifiableCredential":
            verifiable_credential["id"] = custom_credential_id
    
    # Ensure credential has an ID
    if not verifiable_credential.get("id"):
        logger.error("Credential missing ID field")
        raise HTTPException(status_code=400, detail="Credential must have an 'id' field")

    # Store credential in SQL database (uses scid from FK relationship)
    # Mark as format-verified (we validated the format above)
    try:
        sql_storage.create_credential(
            did_controller.scid, 
            verifiable_credential, 
            custom_id=custom_credential_id,
            verified=True,  # Format validation passed
            verification_method="format-validation"
        )
        stored_id = custom_credential_id if custom_credential_id else verifiable_credential['id']
        logger.info(f"Credential {stored_id} stored successfully")
    except IntegrityError as e:
        # Duplicate credential ID (UNIQUE constraint violation)
        stored_id = custom_credential_id if custom_credential_id else verifiable_credential.get('id', 'unknown')
        logger.warning(f"Credential {stored_id} already exists")
        raise HTTPException(
            status_code=409, 
            detail=f"Credential with ID '{stored_id}' already exists. Use PUT to update or choose a different credentialId."
        )
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


@router.put("/{namespace}/{identifier}/credentials/{credential_id}")
async def update_credential(
    credential_id: str,
    request_body: CredentialUpload,
    did_controller: DidControllerRecord = Depends(get_did_controller_dependency)
):
    """Update an existing credential."""
    logger.info(f"=== Updating credential {credential_id} ===")

    # Get existing credential from SQL database
    existing_credential = sql_storage.get_credential(credential_id)
    if not existing_credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    # Verify the credential belongs to this DID controller
    if existing_credential.scid != did_controller.scid:
        raise HTTPException(status_code=403, detail="Credential does not belong to this DID")

    # Extract and validate new credential
    verifiable_credential = vars(request_body)["verifiableCredential"].model_dump()
    logger.debug(f"New credential ID: {verifiable_credential.get('id', 'unknown')}")
    
    # Ensure the credential ID matches
    if verifiable_credential.get('id') != credential_id:
        raise HTTPException(status_code=400, detail="Credential ID in body must match URL parameter")
    
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
        verifier.verify_resource_proof(copy.deepcopy(verifiable_credential))
        logger.debug("Credential proof verified successfully")
    except Exception as e:
        logger.error(f"Credential proof verification failed: {e}")
        raise HTTPException(status_code=400, detail=f"Credential proof verification failed: {str(e)}")

    # Update credential in SQL database
    try:
        updated_credential = sql_storage.update_credential(verifiable_credential)
        if not updated_credential:
            raise HTTPException(status_code=404, detail="Credential not found for update")
        logger.info(f"Credential {credential_id} updated successfully")
    except ValueError as e:
        logger.error(f"Invalid credential data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update credential: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update credential: {str(e)}")

    return JSONResponse(status_code=200, content=verifiable_credential)
