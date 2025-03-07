"""This module contains dependencies used by the FastAPI application."""

from fastapi import HTTPException
from config import settings
import logging

from app.plugins import AskarStorage

logger = logging.getLogger(__name__)


async def identifier_available(namespace: str = None, identifier: str = None):
    """Check if a DID identifier is available."""
    
    if not namespace or not identifier:
        raise HTTPException(status_code=400, detail="Missing namespace or identifier query.")
    
    did = f"{settings.DID_WEB_BASE}:{namespace}:{identifier}"
    
    if await AskarStorage().fetch("didDocument", did):
        raise HTTPException(status_code=409, detail="Identifier unavailable.")
    
    return did


async def identifier_exists(namespace: str = None, identifier: str = None):
    """Check if a DID identifier is available."""
    
    if not namespace or not identifier:
        raise HTTPException(status_code=400, detail="Missing namespace or identifier query.")
    
    did = f"{settings.DID_WEB_BASE}:{namespace}:{identifier}"
    
    if not await AskarStorage().fetch("didDocument", did):
        raise HTTPException(status_code=404, detail="Not found.")
    
    return did


# async def identifier_available(did: str):
#     """Check if a DID identifier is available."""
#     print('hello')
#     # if await AskarStorage().fetch("didDocument", did):
#     #     raise HTTPException(status_code=409, detail="Identifier unavailable.")


async def did_document_exists(did: str):
    """Check if a DID document exists."""
    if not await AskarStorage().fetch("didDocument", did):
        raise HTTPException(status_code=404, detail="Resource not found.")
