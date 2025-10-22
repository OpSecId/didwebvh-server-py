"""This module contains dependencies used by the FastAPI application."""

from fastapi import HTTPException

from app.plugins.storage import StorageManager


def identifier_available(namespace: str, alias: str):
    """Check if a DID identifier is available."""
    storage = StorageManager()
    if storage.get_did_controller_by_alias(namespace, alias):
        raise HTTPException(status_code=409, detail="Identifier unavailable.")


def did_controller_exists(namespace: str, alias: str):
    """Check if a DID controller exists."""
    storage = StorageManager()
    if not storage.get_did_controller_by_alias(namespace, alias):
        raise HTTPException(status_code=404, detail="DID not found.")
