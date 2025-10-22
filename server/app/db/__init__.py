"""Database package.

IMPORTANT: Database engine and session management is now handled by StorageManager.
All database operations should use StorageManager instead of importing from this module.

Example:
    from app.plugins.storage import StorageManager
    
    storage = StorageManager()
    storage.provision()  # Initialize database
    did_controller = storage.get_did_controller(namespace, identifier)
    
For FastAPI dependencies:
    from app.plugins.storage import StorageManager
    from sqlalchemy.orm import Session
    from fastapi import Depends
    
    @router.get("/items")
    async def get_items(db: Session = Depends(StorageManager().get_db)):
        ...
"""

from .base import Base
from .models import (
    DidControllerRecord,
    AttestedResourceRecord,
    VerifiableCredentialRecord,
    AdminBackgroundTask,
    ServerPolicy,
    KnownWitnessRegistry,
    TestLogEntry,
    TestResource,
)

__all__ = [
    "Base",
    "DidControllerRecord",
    "AttestedResourceRecord",
    "VerifiableCredentialRecord",
    "AdminBackgroundTask",
    "ServerPolicy",
    "KnownWitnessRegistry",
    "TestLogEntry",
    "TestResource",
]
