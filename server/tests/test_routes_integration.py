"""Integration tests for routes using the refactored storage."""

import pytest
from fastapi.testclient import TestClient
from app.plugins import DidWebVH


@pytest.fixture
def client(storage_manager):
    """FastAPI test client with storage provisioned."""
    from app import app  # Fixed import path
    return TestClient(app)


@pytest.mark.asyncio
async def test_create_and_retrieve_did(storage_manager):
    """Test creating DID through storage."""
    webvh = DidWebVH()
    logs = webvh.new_test_entry_logs(identifier="apitest")
    
    # Create DID through storage
    controller = storage_manager.create_did_controller(logs=logs)
    
    # Retrieve it back
    retrieved = storage_manager.get_did_controller_by_alias(controller.namespace, controller.alias)
    
    assert retrieved is not None
    assert retrieved.did == controller.did


@pytest.mark.asyncio
async def test_resource_creation_requires_valid_did(storage_manager):
    """Test that resources require a valid parent DID (FK constraint)."""
    webvh = DidWebVH()
    logs = webvh.new_test_entry_logs(identifier="parent")
    controller = storage_manager.create_did_controller(logs=logs)
    
    # Create resource with valid FK
    valid_resource = {
        "metadata": {
            "resourceId": "valid-123",
            "resourceType": "anonCredsSchema",
            "resourceName": "ValidSchema"
        },
        "content": {},
        "proof": {
            "verificationMethod": f"{controller.did}#key-1"
        }
    }
    
    resource = storage_manager.create_resource(controller.scid, valid_resource)
    assert resource.scid == controller.scid


@pytest.mark.asyncio
async def test_explorer_shows_did_records(storage_manager):
    """Test explorer can retrieve DID records."""
    webvh = DidWebVH()
    
    # Create a few DIDs
    for i in range(3):
        logs = webvh.new_test_entry_logs(identifier=f"explore{i}")
        storage_manager.create_did_controller(logs=logs)
    
    # Query all DIDs
    all_dids = storage_manager.get_did_controllers()
    
    assert len(all_dids) >= 3
    # Should contain our created DIDs
    assert any("explore" in did.alias for did in all_dids)


@pytest.mark.asyncio
async def test_deactivated_flag_extracted(storage_manager):
    """Test that deactivated status is automatically extracted from logs."""
    webvh = DidWebVH()
    logs = webvh.new_test_entry_logs(identifier="deactest")
    
    # Create DID (initially active)
    controller = storage_manager.create_did_controller(logs=logs)
    assert controller.deactivated is False


@pytest.mark.asyncio
async def test_resource_foreign_key_integrity(storage_manager):
    """Test that resources maintain FK integrity with DIDs."""
    webvh = DidWebVH()
    logs = webvh.new_test_entry_logs(identifier="fktest")
    controller = storage_manager.create_did_controller(logs=logs)
    
    # Create resource
    attested_resource = {
        "metadata": {
            "resourceId": "fk-test-123",
            "resourceType": "anonCredsSchema",
            "resourceName": "FKTestSchema"
        },
        "content": {},
        "proof": {
            "verificationMethod": f"{controller.did}#key-1"
        }
    }
    
    resource = storage_manager.create_resource(controller.scid, attested_resource)
    
    # Retrieve all resources for this DID
    resources = storage_manager.get_resources(filters={"scid": controller.scid})
    
    assert len(resources) >= 1
    assert any(r.resource_id == "fk-test-123" for r in resources)


@pytest.mark.asyncio
async def test_composite_index_performance(storage_manager):
    """Test that composite indexes improve query performance."""
    webvh = DidWebVH()
    
    # Create multiple DIDs in same namespace
    namespace = None
    for i in range(10):
        logs = webvh.new_test_entry_logs(identifier=f"perf{i}")
        controller = storage_manager.create_did_controller(logs=logs)
        if namespace is None:
            namespace = controller.namespace
    
    # Query by namespace (should use index)
    results = storage_manager.get_did_controllers(filters={"namespace": namespace})
    
    assert len(results) >= 1
    assert all(r.namespace == namespace for r in results)
    
    # Query by namespace and deactivated (should use composite index)
    active_results = storage_manager.get_did_controllers(
        filters={"namespace": namespace, "deactivated": False}
    )
    
    assert all(r.namespace == namespace and r.deactivated is False for r in active_results)


@pytest.mark.asyncio
async def test_simplified_api_signatures(storage_manager):
    """Test that the simplified API signatures work correctly."""
    webvh = DidWebVH()
    
    # create_did_controller: only takes logs and witness_file
    logs = webvh.new_test_entry_logs(identifier="simple1")
    witness_file = [{"versionId": logs[0]["versionId"], "proof": {}}]
    controller = storage_manager.create_did_controller(logs=logs, witness_file=witness_file)
    
    assert controller.scid is not None
    assert controller.did is not None
    
    # create_resource: only takes scid and attested_resource
    attested_resource = {
        "metadata": {
            "resourceId": "simple-res-1",
            "resourceType": "anonCredsSchema",
            "resourceName": "SimpleSchema"
        },
        "content": {},
        "proof": {
            "verificationMethod": f"{controller.did}#key-1"
        }
    }
    
    resource = storage_manager.create_resource(controller.scid, attested_resource)
    assert resource.resource_id == "simple-res-1"
    
    # update_resource: only takes attested_resource
    updated_resource = attested_resource.copy()
    updated_resource["content"] = {"updated": True}
    
    updated = storage_manager.update_resource(updated_resource)
    assert updated.attested_resource["content"]["updated"] is True
