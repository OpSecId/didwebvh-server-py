"""Tests for StorageManager."""

import pytest


@pytest.mark.asyncio
async def test_storage_provision(storage_manager):
    """Test that StorageManager provisions correctly."""
    # storage_manager fixture already provisions the database
    assert storage_manager.db_type in ['sqlite', 'postgres']


@pytest.mark.asyncio
async def test_create_log_entry(storage_manager):
    """Test creating a log entry."""
    log_entry = storage_manager.create_log_entry(
        scid="test-scid-123",
        did="did:webvh:example.com:test:123",
        domain="example.com",
        namespace="test",
        identifier="123",
        logs=[{"versionId": "1", "state": {"id": "did:webvh:example.com:test:123"}}]
    )
    
    assert log_entry.scid == "test-scid-123"
    assert log_entry.did == "did:webvh:example.com:test:123"
    assert log_entry.deactivated is False


@pytest.mark.asyncio
async def test_get_log_entry(storage_manager):
    """Test retrieving a log entry."""
    # Create
    storage_manager.create_log_entry(
        scid="test-scid-456",
        did="did:webvh:example.com:test:456",
        domain="example.com",
        namespace="test",
        identifier="456",
        logs=[{"versionId": "1"}]
    )
    
    # Retrieve
    log_entry = storage_manager.get_log_entry("test-scid-456")
    assert log_entry is not None
    assert log_entry.scid == "test-scid-456"


@pytest.mark.asyncio
async def test_update_log_entry(storage_manager):
    """Test updating a log entry."""
    # Create
    storage_manager.create_log_entry(
        scid="test-scid-789",
        did="did:webvh:example.com:test:789",
        domain="example.com",
        namespace="test",
        identifier="789",
        logs=[{"versionId": "1"}]
    )
    
    # Update
    updated = storage_manager.update_log_entry(
        "test-scid-789",
        logs=[{"versionId": "1"}, {"versionId": "2"}],
        deactivated=True
    )
    
    assert updated is not None
    assert len(updated.logs) == 2
    assert updated.deactivated is True


@pytest.mark.asyncio
async def test_delete_log_entry(storage_manager):
    """Test deleting a log entry."""
    # Create
    storage_manager.create_log_entry(
        scid="test-scid-delete",
        did="did:webvh:example.com:test:delete",
        domain="example.com",
        namespace="test",
        identifier="delete",
        logs=[{"versionId": "1"}]
    )
    
    # Delete
    success = storage_manager.delete_log_entry("test-scid-delete")
    assert success is True
    
    # Verify deletion
    log_entry = storage_manager.get_log_entry("test-scid-delete")
    assert log_entry is None


@pytest.mark.asyncio
async def test_create_resource(storage_manager):
    """Test creating a resource."""
    resource = storage_manager.create_resource(
        resource_id="res-123",
        scid="test-scid-123",
        did="did:webvh:example.com:test:123",
        resource_type="anonCredsSchema",
        resource_name="TestSchema",
        content={"attrNames": ["name", "age"]},
        metadata={"version": "1.0"}
    )
    
    assert resource.resource_id == "res-123"
    assert resource.resource_type == "anonCredsSchema"


@pytest.mark.asyncio
async def test_get_resources_filtered(storage_manager):
    """Test filtering resources."""
    # Create multiple resources
    storage_manager.create_resource(
        resource_id="res-1",
        scid="scid-1",
        did="did:webvh:example.com:test:1",
        resource_type="anonCredsSchema",
        resource_name="Schema1",
        content={},
        metadata={}
    )
    
    storage_manager.create_resource(
        resource_id="res-2",
        scid="scid-1",
        did="did:webvh:example.com:test:1",
        resource_type="anonCredsCredDef",
        resource_name="CredDef1",
        content={},
        metadata={}
    )
    
    # Filter by scid
    resources = storage_manager.get_resources(filters={"scid": "scid-1"})
    assert len(resources) == 2
    
    # Filter by resource_type
    schemas = storage_manager.get_resources(filters={"resource_type": "anonCredsSchema"})
    assert len(schemas) == 1
    assert schemas[0].resource_type == "anonCredsSchema"


@pytest.mark.asyncio
async def test_create_task(storage_manager):
    """Test creating a task."""
    task = storage_manager.create_task(
        task_id="task-123",
        task_type="load_test",
        status="started",
        progress={"completed": 0}
    )
    
    assert task.task_id == "task-123"
    assert task.status == "started"


@pytest.mark.asyncio
async def test_policy_upsert(storage_manager):
    """Test creating and updating policies."""
    # Create
    policy = storage_manager.create_or_update_policy(
        "active",
        {
            "version": "1.0",
            "witness": True,
            "portability": False
        }
    )
    
    assert policy.version == "1.0"
    assert policy.witness is True
    
    # Update
    updated = storage_manager.create_or_update_policy(
        "active",
        {
            "version": "2.0",
            "witness": False
        }
    )
    
    assert updated.version == "2.0"
    assert updated.witness is False


@pytest.mark.asyncio
async def test_provision_recreate(storage_manager):
    """Test that provision with recreate drops all data."""
    # Create some data
    storage_manager.create_log_entry(
        scid="to-be-deleted",
        did="did:webvh:example.com:test:deleted",
        domain="example.com",
        namespace="test",
        identifier="deleted",
        logs=[{"versionId": "1"}]
    )
    
    # Verify it exists
    entry = storage_manager.get_log_entry("to-be-deleted")
    assert entry is not None
    
    # Reprovision with recreate
    await storage_manager.provision(recreate=True)
    
    # Verify data is gone
    entry = storage_manager.get_log_entry("to-be-deleted")
    assert entry is None

