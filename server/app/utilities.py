"""Utility functions for the DID Web server."""

from fastapi import HTTPException

from app.models.did_document import DidDocument
from app.plugins import AskarStorage, AskarVerifier
from config import settings
import requests
import json


def to_did_web(namespace: str, identifier: str):
    """Convert namespace and identifier to a DID Web identifier."""
    return f"{settings.DID_WEB_BASE}:{namespace}:{identifier}"


async def location_available(did: str):
    """Check if a location is available."""
    if await AskarStorage().fetch("didDocument", did):
        raise HTTPException(status_code=409, detail="Identifier unavailable.")


async def did_document_exists(did: str):
    """Check if a DID document exists."""
    if not await AskarStorage().fetch("didDocument", did):
        raise HTTPException(status_code=404, detail="Ressource not found.")


async def valid_did_registration(did_document):
    """Validate a DID document registration."""
    did_document
    proofs = did_document.pop("proof")
    try:
        # assert (
        #     did_document["id"] == f"{settings.DID_WEB_BASE}:{namespace}:{identifier}"
        # ), "Id mismatch between DID Document and requested endpoint."
        assert len(did_document["verificationMethod"]) >= 1, (
            "DID Document must contain at least 1 verificationMethod."
        )
        assert isinstance(proofs, list) and len(proofs) == 2, (
            "Insufficient proofs, must contain a client and an endorser proof."
        )
    except AssertionError as msg:
        raise HTTPException(status_code=400, detail=str(msg))

    endorser_proof = find_proof(proofs, f"{settings.DID_WEB_BASE}#key-01")
    endorser_key = settings.ENDORSER_MULTIKEY
    AskarVerifier(endorser_key).verify_proof(did_document, endorser_proof)

    client_proof = find_proof(proofs, did_document["verificationMethod"][0]["id"])
    client_key = find_key(did_document, client_proof["verificationMethod"])
    AskarVerifier(client_key).verify_proof(did_document, client_proof)

    return did_document


async def identifier_available(identifier: str):
    """Check if an identifier is available."""
    if await AskarStorage().fetch("didDocument", identifier):
        raise HTTPException(status_code=409, detail="Identifier unavailable.")


def derive_did(namespace, identifier):
    """Derive a DID from a namespace and identifier."""
    return f"{settings.DID_WEB_BASE}:{namespace}:{identifier}"


def create_did_doc(did, multikey, kid="key-01"):
    """Create a DID document."""
    return DidDocument(
        id=did,
        verificationMethod=[
            {
                "id": kid,
                "type": "Multikey",
                "controller": did,
                "publicKeyMultibase": multikey,
            }
        ],
        authentication=[kid],
        assertionMethod=[kid],
        service=[],
    ).model_dump()


def find_key(did_doc, kid):
    """Find a key in a DID document."""
    return next(
        (vm["publicKeyMultibase"] for vm in did_doc["verificationMethod"] if vm["id"] == kid),
        None,
    )


def find_proof(proof_set, kid):
    """Find a proof in a proof set."""
    return next(
        (proof for proof in proof_set if proof["verificationMethod"] == kid),
        None,
    )


async def find_known_witness_proof(proof_set):
    """Find a known witness proof."""
    witnesses = await AskarStorage().fetch('registry', 'witness')
    return next(
        (
            proof
            for proof in proof_set
            if proof["verificationMethod"].split('#')[0] in witnesses
        ),
        None,
    )

async def find_controller_proof(proof_set):
    """Find the controller proof."""
    witnesses = await AskarStorage().fetch('registry', 'witness')
    return next(
        (
            proof
            for proof in proof_set
            if proof["verificationMethod"].split('#')[0] not in witnesses
        ),
        None,
    )

async def cache_witness_registry():
    """Cache the witness registry."""
    r = requests.get(settings.WITNESS_REGISTRY)
    witnesses = list(r.json()['registry'])
    await AskarStorage().update("registry", "witness", witnesses)
    return witnesses

async def validate_new_log_entry_proof(new_log_entry, did):
    """Assert new log entry proof is valid."""
    
    proof = new_log_entry.pop("proof", None)
    proof = proof if isinstance(proof, list) else [proof]
    if len(proof) != 1:
        raise HTTPException(status_code=400, detail="Expecting singular proof from controller.")
    
    proof = proof[0]
    update_key = proof["verificationMethod"].split("#")[-1]
    if update_key not in await AskarStorage().fetch("updateKeys", did):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    AskarVerifier().verify_proof(new_log_entry, proof)
    
    return proof

async def webvh_state_to_web(did_document):
    """Transform a webvh log state into a did web document."""
    did = did_document['id']
    did_prefix = ':'.join(did.split(':')[:3])
    did_document = json.loads(json.dumps(did_document).replace(did_prefix, 'did:web'))
    did_document["alsoKnownAs"] = [did]
    return did_document
    
