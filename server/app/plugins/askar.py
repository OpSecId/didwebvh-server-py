"""Askar plugin for storing and verifying data."""

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import canonicaljson
from aries_askar import Key, Store
from aries_askar.bindings import LocalKeyHandle
from aries_askar.error import AskarError
from fastapi import HTTPException
from multiformats import multibase

from config import settings


class AskarStorage:
    """Askar storage plugin."""

    def __init__(self):
        """Initialize the Askar storage plugin."""
        self.db = settings.ASKAR_DB
        self.key = Store.generate_raw_key(hashlib.md5(settings.DOMAIN.encode()).hexdigest())

    async def provision(self, recreate=False):
        """Provision the Askar storage."""
        await Store.provision(self.db, "raw", self.key, recreate=recreate)
        try:
            await self.store("registry", "witness", [])
        except:
            pass

    async def open(self):
        """Open the Askar storage."""
        return await Store.open(self.db, "raw", self.key)

    async def fetch(self, category, data_key):
        """Fetch data from the store."""
        store = await self.open()
        try:
            async with store.session() as session:
                data = await session.fetch(category, data_key)
            return json.loads(data.value)
        except Exception:
            return None

    async def store(self, category, data_key, data):
        """Store data in the store."""
        store = await self.open()
        try:
            async with store.session() as session:
                await session.insert(category, data_key, json.dumps(data))
        except Exception:
            raise HTTPException(status_code=404, detail="Couldn't store record.")

    async def update(self, category, data_key, data):
        """Update data in the store."""
        store = await self.open()
        try:
            async with store.session() as session:
                await session.replace(category, data_key, json.dumps(data))
        except Exception:
            raise HTTPException(status_code=404, detail="Couldn't update record.")

    async def append(self, category, data_key, data):
        """Append data in the store."""
        try:
            stored_data = await self.fetch(category, data_key)
            stored_data.append(data)
            await self.update(category, data_key, stored_data)
        except Exception:
            raise HTTPException(status_code=404, detail="Couldn't update record.")


class AskarVerifier:
    """Askar verifier plugin."""

    def __init__(self):
        """Initialize the Askar verifier plugin."""
        self.type = "DataIntegrityProof"
        self.purpose = "assertionMethod"
        self.cryptosuite = "eddsa-jcs-2022"
        self.proof_ttl = settings.PROOF_TTL

    def create_proof_config(self, did):
        """Create a proof configuration."""
        expires = str(
            (
                datetime.now(timezone.utc) + timedelta(minutes=self.proof_ttl)
            ).isoformat("T", "seconds")
        )
        return {
            "type": self.type,
            "cryptosuite": self.cryptosuite,
            "proofPurpose": self.purpose,
            "expires": expires,
            "domain": settings.DOMAIN,
            "challenge": self.create_challenge(did + expires),
        }

    def create_challenge(self, value):
        """Create a challenge."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, settings.SECRET_KEY + value))

    def validate_challenge(self, proof, did):
        """Validate the challenge."""
        if proof.get("domain") != settings.DOMAIN:
            raise HTTPException(status_code=400, detail='Wrong domain')
        if proof.get("challenge") != self.create_challenge(did + proof["expires"]):
            raise HTTPException(status_code=400, detail='Wrong challenge')

    def validate_proof(self, proof):
        """Validate the proof."""
        if datetime.fromisoformat(proof["expires"]) < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail='Proof expired.')
        if proof["type"] != self.type:
            raise HTTPException(status_code=400, detail=f"Expected {self.type} proof type.")
        if proof["cryptosuite"] != self.cryptosuite:
            raise HTTPException(status_code=400, detail=f"Expected {self.cryptosuite} cryptosuite.")
        if proof["proofPurpose"] != self.purpose:
            raise HTTPException(status_code=400, detail=f"Expected {self.purpose} proof purpose.")

    def verify_proof(self, document, proof):
        """Verify the proof."""
        self.validate_proof(proof)

        multikey = proof["verificationMethod"].split("#")[-1]

        key = Key(LocalKeyHandle()).from_public_bytes(
            alg="ed25519", public=bytes(bytearray(multibase.decode(multikey))[2:])
        )

        proof_options = proof.copy()
        signature = multibase.decode(proof_options.pop("proofValue"))

        hash_data = (
            sha256(canonicaljson.encode_canonical_json(proof_options)).digest()
            + sha256(canonicaljson.encode_canonical_json(document)).digest()
        )
        try:
            if not key.verify_signature(message=hash_data, signature=signature):
                raise HTTPException(status_code=400, detail="Signature was forged or corrupt.")
            return True
        except Exception:
            raise HTTPException(status_code=400, detail="Error verifying proof.")
