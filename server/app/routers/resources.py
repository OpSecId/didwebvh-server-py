from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Union
from app.models.web_schemas import ResourceUpload, ResourceTemplate
from app.models.resource import AttestedResource
from app.models.anoncreds import SecuredSchema, SecuredCredDef
from app.plugins import AskarVerifier, AskarStorage, DidWebVH
from app.utilities import digest_multibase, is_webvh_did, first_proof
from config import settings
import copy
import json

# router = APIRouter(tags=["LinkedResources"])
router = APIRouter()

SUPPORTED_RESSOURCE_TYPES = [
    'AnonCredsSchema',
    'AnonCredsCredDef',
]

@router.get("/{namespace}/{identifier}/resources/{resource_id}", tags=["Resources"])
async def get_resource(namespace: str, identifier: str, resource_id: str):
    
    storage = AskarStorage()
    store_id = f'{namespace}:{identifier}:{resource_id}'
    resource = await storage.fetch(
        'resource', 
        store_id
    )
    
    if not resource:
        raise HTTPException(status_code=404, detail="Couldn't find resource.")
    
    return JSONResponse(status_code=200, content=resource)
        

@router.post("/resources", tags=["LinkedResources"])
async def upload_linked_resource(request_body: ResourceUpload):
    secured_resource = vars(request_body)['securedResource'].model_dump()
    secured_resource['proof'] = first_proof(secured_resource['proof'])
    
    options = vars(request_body)['options'].model_dump()
    # try:
    verifier = AskarVerifier()
    # This will ensure the verification method is registered on the server and that the proof is valid
    await verifier.verify_resource_proof(copy.deepcopy(secured_resource))
    
    webvh = DidWebVH()
    # This will ensure that the resource is properly assigned to it's issuer and double check the digested path
    webvh.validate_resource(copy.deepcopy(secured_resource))
    
    storage = AskarStorage()
    store_id = webvh.resource_store_id(copy.deepcopy(secured_resource))
    await storage.store(
        'resource',
        store_id,
        secured_resource,
        secured_resource.get('metadata')
    )
    return JSONResponse(status_code=201, content=secured_resource)
    # except:
    #     raise HTTPException(status_code=400, detail="Unable to store resource.")

@router.put("/{namespace}/{identifier}/resources/{resource_id}", tags=["Resources"])
async def update_resource(namespace: str, identifier: str, resource_id: str, request_body: ResourceUpload):
    secured_resource = vars(request_body)['securedResource'].model_dump()
    secured_resource['proof'] = first_proof(secured_resource['proof'])
    
    options = vars(request_body)['options'].model_dump()
    
    verifier = AskarVerifier()
    # This will ensure the verification method is registered on the server and that the proof is valid
    await verifier.verify_resource_proof(copy.deepcopy(secured_resource))
    
    webvh = DidWebVH()
    # This will ensure that the resource is properly assigned to it's issuer and double check the digested path
    webvh.validate_resource(copy.deepcopy(secured_resource))
    
    storage = AskarStorage()
    store_id = webvh.resource_store_id(copy.deepcopy(secured_resource))
    resource = await storage.fetch('resource', store_id)
    
    if not resource:
        raise HTTPException(status_code=404, detail="Couldn't find resource.")
    
    webvh.compare_resource(copy.deepcopy(resource),  copy.deepcopy(secured_resource))

    storage = AskarStorage()
    store_id = f'{namespace}:{identifier}:{resource_id}'
    await storage.update(
        'resource',
        store_id,
        secured_resource,
        secured_resource.get('resourceMetadata')
    )
    return JSONResponse(status_code=200, content=secured_resource)
