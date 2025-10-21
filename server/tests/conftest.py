"""Pytest fixtures for tests."""

import asyncio
import pytest
from app.plugins.storage import StorageManager
from app.plugins import AskarStorage


@pytest.fixture(scope="function")
async def storage_manager():
    """
    Provide a clean StorageManager instance for each test.
    
    Similar to how Askar tests provision with recreate=True.
    """
    storage = StorageManager()
    await storage.provision(recreate=True)
    yield storage


@pytest.fixture(scope="function")
async def askar_storage():
    """
    Provide a clean AskarStorage instance for each test.
    
    Maintains compatibility with existing Askar tests.
    """
    askar = AskarStorage()
    await askar.provision(recreate=True)
    yield askar


@pytest.fixture(scope="function")
async def dual_storage():
    """
    Provide both StorageManager and AskarStorage for migration tests.
    
    Useful for testing data migration between storage backends.
    """
    storage = StorageManager()
    askar = AskarStorage()
    
    # Provision both with clean slate
    await asyncio.gather(
        storage.provision(recreate=True),
        askar.provision(recreate=True)
    )
    
    yield {"storage": storage, "askar": askar}
