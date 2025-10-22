"""Tests for DidControllerRecord and new simplified API."""

import pytest
from app.plugins import DidWebVH


@pytest.mark.asyncio
async def test_create_did_controller(storage_manager):
    """Test creating a DID controller with simplified API."""
    # Use DidWebVH to generate proper test log entries
    webvh = DidWebVH()
    logs = webvh.new_test_entry_logs(identifier="testalias")
    witness_file = [{"versionId": logs[0]["versionId"], "proof": {}}]
    
    # Create DID controller - API automatically extracts all data
    controller = storage_manager.create_did_controller(
        logs=logs,
        witness_file=witness_file
    )
    
    # Verify extraction happened correctly
    assert controller.scid is not None
    assert controller.did.startswith("did:webvh:")
    assert controller.alias == "testalias"
    assert controller.deactivated is False
    assert controller.logs == logs
    assert controller.witness_file == witness_file


@pytest.mark.asyncio
async def test_get_did_controller_by_alias(storage_manager):
    """Test getting DID controller by namespace and alias."""
    webvh = DidWebVH()
    logs = webvh.new_test_entry_logs(identifier="myalias")
    
    controller = storage_manager.create_did_controller(logs=logs)
    
    # Retrieve by namespace and alias
    retrieved = storage_manager.get_did_controller_by_alias(controller.namespace, controller.alias)
    
    assert retrieved is not None
    assert retrieved.scid == controller.scid
    assert retrieved.alias == controller.alias


@pytest.mark.asyncio
async def test_update_did_controller(storage_manager):
    """Test updating a DID controller - automatic re-extraction."""
    webvh = DidWebVH()
    logs = webvh.new_test_entry_logs(identifier="updatealias", count=1)
    
    controller = storage_manager.create_did_controller(logs=logs)
    initial_log_count = len(controller.logs)
    
    # Add more log entries
    more_logs = webvh.new_test_entry_logs(identifier="updatealias", count=3)
    
    # Update - method automatically re-extracts state
    updated = storage_manager.update_did_controller(
        scid=controller.scid,
        logs=more_logs
    )
    
    assert updated is not None
    assert len(updated.logs) > initial_log_count
    assert updated.scid == controller.scid


@pytest.mark.asyncio
async def test_create_resource_with_fk(storage_manager):
    """Test creating a resource with FK relationship to DID controller."""
    # Create parent DID first
    webvh = DidWebVH()
    logs = webvh.new_test_entry_logs(identifier="resalias")
    controller = storage_manager.create_did_controller(logs=logs)
    
    # Create resource with FK to controller
    attested_resource = {
        "id": f"{controller.did}/resources/schema-123.json",
        "metadata": {
            "resourceId": "schema-123",
            "resourceType": "anonCredsSchema",
            "resourceName": "TestSchema"
        },
        "content": {"attrNames": ["name", "age"]},
        "proof": {
            "verificationMethod": f"{controller.did}#key-1",
            "proofValue": "z123456"
        }
    }
    
    resource = storage_manager.create_resource(controller.scid, attested_resource)
    
    assert resource.resource_id == "schema-123"
    assert resource.scid == controller.scid  # FK relationship
    assert resource.resource_type == "anonCredsSchema"


@pytest.mark.asyncio
async def test_get_resources_by_scid(storage_manager):
    """Test querying resources by SCID."""
    # Create DID
    webvh = DidWebVH()
    logs = webvh.new_test_entry_logs(identifier="queryalias")
    controller = storage_manager.create_did_controller(logs=logs)
    
    # Create multiple resources
    for i in range(3):
        attested_resource = {
            "id": f"{controller.did}/resources/resource-{i}.json",
            "metadata": {
                "resourceId": f"resource-{i}",
                "resourceType": "anonCredsSchema",
                "resourceName": f"Schema{i}"
            },
            "content": {},
            "proof": {
                "verificationMethod": f"{controller.did}#key-1"
            }
        }
        storage_manager.create_resource(controller.scid, attested_resource)
    
    # Query by scid
    resources = storage_manager.get_resources(filters={"scid": controller.scid})
    
    assert len(resources) == 3
    assert all(r.scid == controller.scid for r in resources)


@pytest.mark.asyncio
async def test_update_whois_presentation(storage_manager):
    """Test updating WHOIS presentation."""
    # Create DID
    webvh = DidWebVH()
    logs = webvh.new_test_entry_logs(identifier="whoisalias")
    controller = storage_manager.create_did_controller(logs=logs)
    
    assert controller.whois_presentation is None
    
    # Update with WHOIS presentation
    whois_vp = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiablePresentation"],
        "holder": controller.did,
        "verifiableCredential": []
    }
    
    updated = storage_manager.update_did_controller(
        scid=controller.scid,
        whois_presentation=whois_vp
    )
    
    assert updated.whois_presentation == whois_vp
    # Verify logs weren't affected
    assert updated.logs == logs


@pytest.mark.asyncio
async def test_query_by_namespace_and_deactivated(storage_manager):
    """Test composite index query: namespace + deactivated."""
    webvh = DidWebVH()
    
    # Create DIDs in same namespace
    for i in range(3):
        logs = webvh.new_test_entry_logs(identifier=f"alias{i}")
        storage_manager.create_did_controller(logs=logs)
    
    # Get the namespace from one of them
    first = storage_manager.get_did_controller_by_alias("test-namespace", "alias0") or \
           storage_manager.get_did_controllers(limit=1)[0]
    
    # Query active DIDs in namespace (uses composite index)
    active_dids = storage_manager.get_did_controllers(
        filters={"namespace": first.namespace, "deactivated": False}
    )
    
    assert all(c.namespace == first.namespace and c.deactivated is False for c in active_dids)


@pytest.mark.asyncio
async def test_update_resource(storage_manager):
    """Test updating a resource."""
    # Create DID
    webvh = DidWebVH()
    logs = webvh.new_test_entry_logs(identifier="updresalias")
    controller = storage_manager.create_did_controller(logs=logs)
    
    # Create resource
    original_resource = {
        "id": f"{controller.did}/resources/schema-update.json",
        "metadata": {
            "resourceId": "schema-update",
            "resourceType": "anonCredsSchema",
            "resourceName": "OriginalSchema"
        },
        "content": {"version": "1.0"},
        "proof": {
            "verificationMethod": f"{controller.did}#key-1"
        }
    }
    
    resource = storage_manager.create_resource(controller.scid, original_resource)
    assert resource.attested_resource["content"]["version"] == "1.0"
    
    # Update resource
    updated_resource = {
        "id": f"{controller.did}/resources/schema-update.json",
        "metadata": {
            "resourceId": "schema-update",
            "resourceType": "anonCredsSchema",
            "resourceName": "UpdatedSchema"
        },
        "content": {"version": "2.0"},
        "proof": {
            "verificationMethod": f"{controller.did}#key-1"
        }
    }
    
    updated = storage_manager.update_resource(updated_resource)
    
    assert updated is not None
    assert updated.attested_resource["content"]["version"] == "2.0"
    assert updated.attested_resource["metadata"]["resourceName"] == "UpdatedSchema"


@pytest.mark.asyncio
async def test_count_and_pagination(storage_manager):
    """Test counting and pagination."""
    webvh = DidWebVH()
    
    # Create 10 DIDs
    for i in range(10):
        logs = webvh.new_test_entry_logs(identifier=f"pag{i}")
        storage_manager.create_did_controller(logs=logs)
    
    # Count all
    total = storage_manager.count_did_controllers()
    assert total == 10
    
    # Get with pagination
    page1 = storage_manager.get_did_controllers(limit=5, offset=0)
    page2 = storage_manager.get_did_controllers(limit=5, offset=5)
    
    assert len(page1) == 5
    assert len(page2) == 5
    assert page1[0].scid != page2[0].scid  # Different records
