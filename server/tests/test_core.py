from app.routers.identifiers import request_did, read_did, read_did_log, create_didwebvh
from app.plugins import AskarStorage, AskarVerifier, DidWebVH
from app.models.web_schemas import RegisterInitialLogEntry
from app.models.did_log import LogEntry
from datetime import datetime, timezone
from tests.fixtures import (
    TEST_DOMAIN,
    TEST_DID_NAMESPACE,
    TEST_DID_IDENTIFIER,
    TEST_DID,
    TEST_DID_DOCUMENT,
    TEST_AUTHORISED_KEY,
    TEST_PROOF_OPTIONS,
)
import json
import pytest
import asyncio
from tests.signer import sign

askar = AskarStorage()
asyncio.run(askar.provision(recreate=True))

verifier = AskarVerifier()
didwebvh = DidWebVH()


@pytest.mark.asyncio
async def test_storage():
    category = "test"
    key = "01"
    data = {"value": None}
    value_1 = "value_1"
    value_2 = "value_2"

    data["value"] = value_1
    await askar.store(category, key, data)
    fetched_data = await askar.fetch(category, key)
    assert fetched_data["value"] == value_1

    data["value"] = value_2
    await askar.update(category, key, data)
    fetched_data = await askar.fetch(category, key)
    assert fetched_data["value"] == value_2


@pytest.mark.asyncio
async def test_request_did():
    did_request = await request_did(TEST_DID_NAMESPACE, TEST_DID_IDENTIFIER)
    did_request = json.loads(did_request.body.decode())
    assert did_request.get("didDocument").get("id") == TEST_DID
    assert did_request.get("proofOptions").get("type") == TEST_PROOF_OPTIONS["type"]
    assert (
        did_request.get("proofOptions").get("cryptosuite")
        == TEST_PROOF_OPTIONS["cryptosuite"]
    )
    assert (
        did_request.get("proofOptions").get("proofPurpose")
        == TEST_PROOF_OPTIONS["proofPurpose"]
    )
    assert did_request.get("proofOptions").get("domain") == TEST_DOMAIN
    assert did_request.get("proofOptions").get("challenge")
    assert datetime.fromisoformat(
        did_request.get("proofOptions").get("expires")
    ) > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_register_did():
    await askar.store("didDocument", TEST_DID, TEST_DID_DOCUMENT)
    await askar.store("authorizedKey", TEST_DID, TEST_AUTHORISED_KEY)


@pytest.mark.asyncio
async def test_resolve_did():
    did_doc = await read_did(TEST_DID_NAMESPACE, TEST_DID_IDENTIFIER)
    did_doc = json.loads(did_doc.body.decode())
    assert did_doc == TEST_DID_DOCUMENT
    assert did_doc.get("id") == TEST_DID


@pytest.mark.asyncio
async def test_verify_di_proof():
    document = await askar.fetch("didDocument", TEST_DID)
    signed_document = sign(document)
    proof = signed_document.pop("proof")
    assert verifier.verify_proof(signed_document, proof)


@pytest.mark.asyncio
async def test_create_log_entry():
    initial_log_entry = didwebvh.create(TEST_DID_DOCUMENT, TEST_AUTHORISED_KEY)
    assert initial_log_entry.get("versionId")
    assert initial_log_entry.get("versionTime")
    assert initial_log_entry.get("parameters")
    assert initial_log_entry.get("state")


@pytest.mark.asyncio
async def test_register_log_entry():
    log_entry = didwebvh.create(TEST_DID_DOCUMENT, TEST_AUTHORISED_KEY)
    assert log_entry.get("versionId")
    assert log_entry.get("versionTime")
    assert log_entry.get("parameters")
    assert log_entry.get("state")
    signed_log_entry = sign(log_entry)
    signed_log_entry["proof"] = [signed_log_entry["proof"]]
    log_request = RegisterInitialLogEntry.model_validate({"logEntry": signed_log_entry})
    response = await create_didwebvh(
        TEST_DID_NAMESPACE, TEST_DID_IDENTIFIER, log_request
    )
    log_entry = response.body.decode()
    LogEntry.model_validate(json.loads(log_entry))


@pytest.mark.asyncio
async def test_resolve_did_log():
    did_logs = await read_did_log(TEST_DID_NAMESPACE, TEST_DID_IDENTIFIER)
    did_logs = json.loads(did_logs.body.decode())
