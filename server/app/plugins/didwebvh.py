"""DID Web Verifiable History (DID WebVH) plugin."""

from fastapi import HTTPException
from config import settings
from datetime import datetime
from multiformats import multibase, multihash
# from app.models.did_log import LogParameters
from app.utilities import digest_multibase
import canonicaljson
import json


class DidWebVH:
    """DID Web Verifiable History (DID WebVH) plugin."""

    def __init__(self):
        """Initialize the DID WebVH plugin."""
        self.prefix = settings.DID_WEBVH_PREFIX
        self.method_version = f"{self.prefix}0.4"
        self.did_string_base = self.prefix + r"{SCID}:" + settings.DOMAIN

    # def _init_parameters(self, update_key, next_key=None, ttl=100):
    #     # https://identity.foundation/trustdidweb/#generate-scid
    #     parameters = LogParameters(
    #         method=self.method_version, scid=r"{SCID}", updateKeys=[update_key]
    #     )
    #     return parameters

    def _init_state(self, did_doc):
        return json.loads(json.dumps(did_doc).replace("did:web:", self.prefix + r"{SCID}:"))

    def _generate_scid(self, log_entry):
        # https://identity.foundation/trustdidweb/#generate-scid
        jcs = canonicaljson.encode_canonical_json(log_entry)
        multihashed = multihash.digest(jcs, "sha2-256")
        encoded = multibase.encode(multihashed, "base58btc")[1:]
        return encoded

    def _generate_entry_hash(self, log_entry):
        # https://identity.foundation/trustdidweb/#generate-entry-hash
        jcs = canonicaljson.encode_canonical_json(log_entry)
        multihashed = multihash.digest(jcs, "sha2-256")
        encoded = multibase.encode(multihashed, "base58btc")[1:]
        return encoded

    def create_initial_did_doc(self, did_string):
        """Create an initial DID document."""
        did_doc = {"@context": [], "id": did_string}
        return did_doc

    # def create(self, did_doc, update_key):
    #     """Create a new DID WebVH log."""
    #     # https://identity.foundation/trustdidweb/#create-register
    #     log_entry = InitialLogEntry(
    #         versionId=r"{SCID}",
    #         versionTime=str(datetime.now().isoformat("T", "seconds")),
    #         parameters=self._init_parameters(update_key=update_key),
    #         state=self._init_state(did_doc),
    #     ).model_dump()
    #     scid = self._generate_scid(log_entry)
    #     log_entry = json.loads(json.dumps(log_entry).replace("{SCID}", scid))
    #     log_entry_hash = self._generate_entry_hash(log_entry)
    #     log_entry["versionId"] = f"1-{log_entry_hash}"
    #     return log_entry

    def verify_resource(self, secured_resource):
        """Verify resource."""
        proof = secured_resource.pop("proof")
        proof = proof if isinstance(proof, dict) else [proof]
        if (
            not proof.get("verificationMethod")
            or not proof.get("proofValue")
            or proof.get("type") != "DataIntegrityProof"
            or proof.get("cryptosuite") == "eddsa-jcs-2022"
            or proof.get("proofPurpose") == "assertionMethod"
        ):
            raise HTTPException(status_code=400, detail="Invalid proof options.")

    def validate_resource(self, resource):
        """Validate resource."""
        proof = resource.pop("proof")
        verification_method = proof.get("verificationMethod")
        did = verification_method.split("#")[0]

        provided_id = resource.get("id")

        content = resource.get("content")
        content_digest = digest_multibase(content)

        metadata = resource.get("metadata")

        if settings.DOMAIN != did.split(":")[3]:
            raise HTTPException(status_code=400, detail="Invalid resource id.")

        if did != provided_id.split("/")[0]:
            raise HTTPException(status_code=400, detail="Invalid resource id.")

        if content_digest != provided_id.split("/")[-1].split(".")[0]:
            raise HTTPException(status_code=400, detail="Invalid resource id.")

        if not metadata.get("resourceId") or content_digest != metadata.get("resourceId"):
            raise HTTPException(status_code=400, detail="Invalid resource id.")

        if not metadata.get("resourceType"):
            raise HTTPException(status_code=400, detail="Missing resource type.")

    def compare_resource(self, old_resource, new_resource):
        """Compare resource."""
        if old_resource.get("id") != new_resource.get("id"):
            raise HTTPException(status_code=400, detail="Invalid resource id.")
        if digest_multibase(old_resource.get("content")) != digest_multibase(
            new_resource.get("content")
        ):
            raise HTTPException(status_code=400, detail="Invalid resource content.")
        if digest_multibase(old_resource.get("metadata").get("resourceType")) != digest_multibase(
            new_resource.get("metadata").get("resourceType")
        ):
            raise HTTPException(status_code=400, detail="Invalid resource type.")
        if digest_multibase(
            old_resource.get("proof").get("verificationMethod").split("#")[0]
        ) != digest_multibase(new_resource.get("proof").get("verificationMethod").split("#")[0]):
            raise HTTPException(status_code=400, detail="Invalid verification method.")

    def resource_store_id(self, resource):
        """Generate resource id for storage."""
        resource_id = resource.get("id")
        did = resource_id.split("/")[0]
        namespace = did.split(":")[4]
        identifier = did.split(":")[5]
        content_digest = resource_id.split("/")[-1]
        return f"{namespace}:{identifier}:{content_digest}"
