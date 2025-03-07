"""Identifier endpoints for DIDWeb and DIDWebVH."""

import json
import copy

from fastapi import APIRouter, HTTPException, Response, Depends
from fastapi.responses import JSONResponse

from app.dependencies import identifier_available, identifier_exists
from app.utilities import find_known_witness_proof, find_controller_proof, validate_new_log_entry_proof, cache_witness_registry, webvh_state_to_web
from app.models.did_document import DidDocument
from app.models.web_schemas import RegisterDID, RegisterInitialLogEntry, UpdateLogEntry
from app.plugins import AskarStorage, AskarVerifier, DidWebVH
from config import settings

router = APIRouter(tags=["Identifiers"])


@router.get("/")
async def request_did(namespace: str = None, identifier: str = None):
    """Request a DID document and proof options for a given namespace and identifier."""
    
    # Has the client provided a namespace and an identifier?
    if not namespace or not identifier:
        raise HTTPException(status_code=400, detail="Missing namespace or identifier query.")
    
    # Is the requested DID available?
    did = f"{settings.DID_WEB_BASE}:{namespace}:{identifier}"
    if await AskarStorage().fetch("didDocument", did):
        raise HTTPException(status_code=409, detail="Identifier unavailable.")
    
    # Return proof options and basic did document
    return JSONResponse(
        status_code=200,
        content={
            "didDocument": DidDocument(id=did).model_dump(),
            "proofOptions": AskarVerifier().create_proof_config(did),
        },
    )


@router.post("/")
async def register_did(request_body: RegisterDID):
    """Register a DID document and proof set."""
    did_document = request_body.model_dump()["didDocument"]
    
    askar = AskarStorage()
    
    # Is the requested DID available?
    did = did_document["id"]
    if await askar.fetch('didDocument', did):
        raise HTTPException(status_code=409, detail="Identifier unavailable.")

    # Is there a proof set with a controller and a known witness signature?
    proof_set = did_document.pop("proof", None)
    
    # Look for a known witness verification method and update cache if none is found
    witness_proof = await find_known_witness_proof(proof_set)
    if not witness_proof:
        cache_witness_registry()
        witness_proof = await find_known_witness_proof(proof_set)
        
    controller_proof = find_controller_proof(proof_set)

    if not controller_proof or not witness_proof:
        raise HTTPException(status_code=400, detail="Missing proof.")
    
    # Are the proofs valid?
    verifier = AskarVerifier()
    
    # Witness
    verifier.validate_challenge(witness_proof, did)
    verifier.validate_proof(witness_proof)
    verifier.verify_proof(did_document, witness_proof)
    
    # Controller
    verifier.validate_challenge(controller_proof, did)
    verifier.validate_proof(controller_proof)
    verifier.verify_proof(did_document, controller_proof)
    
    # Get initial update key
    update_key = controller_proof["verificationMethod"].split("#")[-1]

    # Store did document and update key
    await askar.store("updateKeys", did, [update_key])
    await askar.store("didDocument", did, did_document)
    
    return JSONResponse(status_code=201, content=did_document)


@router.get("/{namespace}/{identifier}")
async def get_log_state(namespace: str, identifier: str):
    """Get the current state of the log for a given namespace and identifier."""
    askar = AskarStorage()
    
    # Does the requested did exists?
    did = f"{settings.DID_WEB_BASE}:{namespace}:{identifier}"
    if not await askar.fetch("didDocument", did):
        raise HTTPException(status_code=404, detail="Not found.")
    
    # Is there already a did log entry?
    log_entries = await askar.fetch("logEntries", did)
    if log_entries:
        return JSONResponse(status_code=200, content={})
        
    # Create an initial log entry to sign
    update_key = await askar.fetch("updateKeys", did)
    did_document = await askar.fetch("didDocument", did)
    initial_log_entry = DidWebVH().create(did_document, update_key)
    return JSONResponse(status_code=200, content={"logEntry": initial_log_entry})
    

@router.post("/{namespace}/{identifier}")
async def add_log_entry(namespace: str, identifier: str, request_body: RegisterInitialLogEntry):
    """Add a new log entry for a given namespace and identifier."""
    askar = AskarStorage()
    
    # Does the requested did exists?
    did = f"{settings.DID_WEB_BASE}:{namespace}:{identifier}"
    if not await askar.fetch("didDocument", did):
        raise HTTPException(status_code=404, detail="Not found.")
    
    # Is the proof valid and from an authorized update key?
    new_log_entry = request_body.model_dump()["logEntry"]
    new_log_entry['proof'] = validate_new_log_entry_proof(
        new_log_entry,
        did
    )

    # Is this a creation, update or deactivation
    log_entries = await askar.fetch("logEntries", did)
    parameters = new_log_entry['parameters']
    tags = {}
    if log_entries:
        # If there are already log entries present, we process the request as an update
        # TODO parameter validation
        # Witness check
        # Pre rotation check
        # Deactivation check
        if parameters.get('method'):
            tags['method'] = parameters['method']
        if parameters.get('deactivated') is True:
            tags['deactivated'] = True
        await askar.append("logEntries", did, new_log_entry)
    
    else:
        tags['scid'] = parameters['scid']
        tags['method'] = parameters['method']
        # If there are no log entries present, we process the request as a creation
        # TODO parameter validation
        await askar.store("logEntries", did, [new_log_entry])
        
    # Update the parallel did web document
    did_document = webvh_state_to_web(copy.deepcopy(new_log_entry["state"]))
    await askar.update("didDocument", did, did_document)
    
    return JSONResponse(status_code=201, content=new_log_entry)


@router.get("/{namespace}/{identifier}/did.json", include_in_schema=False)
async def read_did(did: str = Depends(identifier_exists)):
    """See https://identity.foundation/didwebvh/next/#read-resolve."""
    did_doc = await AskarStorage().fetch("didDocument", did)
    if did_doc:
        return Response(json.dumps(did_doc), media_type="application/did+ld+json")
    raise HTTPException(status_code=404, detail="Not Found")


@router.get("/{namespace}/{identifier}/did.jsonl", include_in_schema=False)
async def read_did_log(did: str = Depends(identifier_exists)):
    """See https://identity.foundation/didwebvh/next/#read-resolve."""
    log_entries = await AskarStorage().fetch("logEntries", did)
    if log_entries:
        log_entries = "\n".join([json.dumps(log_entry) for log_entry in log_entries])+'\n'
        return Response(log_entries, media_type="text/jsonl")
    raise HTTPException(status_code=404, detail="Not Found")
