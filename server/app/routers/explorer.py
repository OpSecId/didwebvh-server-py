"""Explorer routes for DIDs and resources UI."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.plugins import AskarStorage, DidWebVH
from app.plugins.storage import StorageManager
from app.db.models import DidControllerRecord
from app.db.explorer_models import ExplorerResourceRecord
from app.utilities import beautify_date, resource_details, resource_id_to_url
from app.avatar_generator import generate_avatar

from config import templates, settings

router = APIRouter(tags=["Explorer"])
askar = AskarStorage()
storage = StorageManager()
webvh = DidWebVH()


@router.get("/")
async def explorer_index(request: Request):
    """Landing page for the explorer UI."""
    CONTEXT = {"branding": settings.BRANDING}
    return templates.TemplateResponse(request=request, name="pages/index.jinja", context=CONTEXT)


@router.get("/dids")
async def explorer_did_table(
    request: Request,
    namespace: str = None,
    status: str = None,
    identifier: str = None,
    scid: str = None,
    domain: str = None,
    has_resources: str = None,
    page: int = 1,
    limit: int = 50,
):
    """DID table with pagination."""
    # Build filters for StorageManager query
    filters = {}
    if scid:
        filters["scid"] = scid
    if namespace:
        filters["namespace"] = namespace
    if identifier:
        filters["alias"] = identifier  # Note: identifier maps to alias column
    if domain:
        filters["domain"] = domain
    if status == "active":
        filters["deactivated"] = False
    elif status == "deactivated":
        filters["deactivated"] = True
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Get total count for pagination
    total = storage.count_did_controllers(filters)
    total_pages = (total + limit - 1) // limit  # Ceiling division
    
    # Get paginated results from DidControllerRecord
    did_controllers = storage.get_did_controllers(filters, limit=limit, offset=offset)
    
    # Format results for explorer UI (compute fields on-the-fly)
    results = []
    for controller in did_controllers:
        # Get resources for this DID
        did_resources = storage.get_resources(filters={"scid": controller.scid})
        formatted_resources = [
            {
                "type": r.resource_type,
                "digest": r.resource_id,
                "details": {}  # Can be enhanced with resource_details() later
            }
            for r in did_resources
        ]
        
        # Generate links
        links = {
            "resolver": f"{settings.UNIRESOLVER_URL}/#{controller.did}",
            "log_file": f"https://{controller.domain}/{controller.namespace}/{controller.alias}/did.jsonl",
            "witness_file": f"https://{controller.domain}/{controller.namespace}/{controller.alias}/did-witness.json",
            "resource_query": f"https://{settings.DOMAIN}/explorer/resources?scid={controller.scid}",
            "whois_presentation": f"https://{controller.domain}/{controller.namespace}/{controller.alias}/whois.vp",
        }
        
        results.append({
            # Basic info
            "did": controller.did,
            "scid": controller.scid,
            "domain": controller.domain,
            "namespace": controller.namespace,
            "identifier": controller.alias,
            "created": beautify_date(controller.logs[0].get("versionTime")) if controller.logs else "",
            "updated": beautify_date(controller.logs[-1].get("versionTime")) if controller.logs else "",
            "deactivated": str(controller.deactivated),
            
            # Computed explorer fields
            "avatar": generate_avatar(controller.scid),
            "active": not controller.deactivated,
            "witnesses": controller.parameters.get("witness", {}).get("witnesses", []) if controller.parameters else [],
            "watchers": controller.parameters.get("watchers", []) if controller.parameters else [],
            "resources": formatted_resources,
            "links": links,
            "parameters": controller.parameters,
            "version_id": controller.logs[-1].get("versionId") if controller.logs else "",
            "version_time": controller.logs[-1].get("versionTime") if controller.logs else "",
            
            # Raw data (for detail views)
            "logs": controller.logs,
            "witness_file": controller.witness_file,
            "whois_presentation": controller.whois_presentation,
        })
    
    # Apply has_resources filter (post-fetch since it's not a tag)
    if has_resources == "yes":
        results = [r for r in results if r.get("resources") and len(r.get("resources", [])) > 0]
    elif has_resources == "no":
        results = [r for r in results if not r.get("resources") or len(r.get("resources", [])) == 0]
    
    CONTEXT = {
        "results": results,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None,
        }
    }

    if request.headers.get("Accept") == "application/json":
        return JSONResponse(status_code=200, content=CONTEXT)
    CONTEXT["branding"] = settings.BRANDING
    return templates.TemplateResponse(request=request, name="pages/did_list.jinja", context=CONTEXT)


@router.get("/resources")
async def explorer_resource_table(
    request: Request,
    scid: str = None,
    resource_id: str = None,
    resource_type: str = None,
    page: int = 1,
    limit: int = 50,
):
    """Resource table with pagination."""
    # Build filters for StorageManager query
    filters = {}
    if scid:
        filters["scid"] = scid
    if resource_id:
        filters["resource_id"] = resource_id
    if resource_type:
        filters["resource_type"] = resource_type
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Get total count for pagination
    total = storage.count_resources(filters)
    total_pages = (total + limit - 1) // limit  # Ceiling division
    
    # Get paginated results from AttestedResourceRecord
    resource_records = storage.get_resources(filters, limit=limit, offset=offset)
    
    # Format results for explorer UI (compute on-the-fly)
    formatted_results = []
    for r in resource_records:
        formatted_results.append({
            # Basic info
            "did": r.did,
            "scid": r.scid,
            "resource_id": r.resource_id,
            "resource_type": r.resource_type,
            "resource_name": r.resource_name,  # Add resource_name field
            
            # Computed fields
            "attested_resource": r.attested_resource,
            "details": resource_details(r.attested_resource),
            "url": resource_id_to_url(r.attested_resource.get("id")),
            "author": {
                "avatar": generate_avatar(r.scid),
                "scid": r.scid,
                "domain": r.did.split(":")[3] if len(r.did.split(":")) >= 4 else "",
                "namespace": r.did.split(":")[4] if len(r.did.split(":")) >= 5 else "",
                "alias": r.did.split(":")[5] if len(r.did.split(":")) >= 6 else "",
            }
        })
    
    CONTEXT = {
        "results": formatted_results,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None,
        }
    }

    if request.headers.get("Accept") == "application/json":
        return JSONResponse(status_code=200, content=CONTEXT)

    CONTEXT["branding"] = settings.BRANDING
    return templates.TemplateResponse(
        request=request, name="pages/resource_list.jinja", context=CONTEXT
    )


@router.get("/credentials")
async def explorer_credential_table(
    request: Request,
    scid: str = None,
    issuer_did: str = None,
    subject_id: str = None,
    credential_type: str = None,
    namespace: str = None,
    alias: str = None,
    revoked: bool = None,
    page: int = 1,
    limit: int = 50,
):
    """Credential table with pagination."""
    # Build filters for StorageManager query
    filters = {}
    if scid:
        filters["scid"] = scid
    if issuer_did:
        filters["issuer_did"] = issuer_did
    if subject_id:
        filters["subject_id"] = subject_id
    if namespace:
        filters["namespace"] = namespace
    if alias:
        filters["alias"] = alias
    if revoked is not None:
        filters["revoked"] = revoked
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Get total count for pagination
    total = storage.count_credentials(filters)
    total_pages = (total + limit - 1) // limit  # Ceiling division
    
    # Get paginated results from VerifiableCredentialRecord
    credential_records = storage.get_credentials(filters, limit=limit, offset=offset)
    
    # Format results for explorer UI (compute on-the-fly)
    formatted_results = []
    for c in credential_records:
        vc = c.verifiable_credential
        
        # Extract credential types
        cred_types = vc.get("type", [])
        if isinstance(cred_types, str):
            cred_types = [cred_types]
        # Filter out "VerifiableCredential" to show only specific types
        specific_types = [t for t in cred_types if t != "VerifiableCredential"]
        
        # Extract subject info
        subject = vc.get("credentialSubject", {})
        if isinstance(subject, list):
            subject = subject[0] if subject else {}
        
        formatted_results.append({
            # Basic info
            "credential_id": c.credential_id,
            "issuer_did": c.issuer_did,
            "subject_id": c.subject_id or "N/A",
            "scid": c.scid,
            
            # Credential details
            "credential_type": specific_types[0] if specific_types else "VerifiableCredential",
            "all_types": cred_types,
            "revoked": c.revoked,
            "status": "Revoked" if c.revoked else "Active",
            
            # Validity
            "valid_from": beautify_date(c.valid_from) if c.valid_from else "N/A",
            "valid_until": beautify_date(c.valid_until) if c.valid_until else "N/A",
            
            # Full credential
            "verifiable_credential": vc,
            
            # Timestamps
            "created": beautify_date(c.created),
            "updated": beautify_date(c.updated),
        })
    
    CONTEXT = {
        "results": formatted_results,
        "query_params": {
            "scid": scid,
            "issuer_did": issuer_did,
            "subject_id": subject_id,
            "credential_type": credential_type,
            "namespace": namespace,
            "alias": alias,
            "revoked": revoked,
        },
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None,
        }
    }

    if request.headers.get("Accept") == "application/json":
        return JSONResponse(status_code=200, content=CONTEXT)

    CONTEXT["branding"] = settings.BRANDING
    return templates.TemplateResponse(
        request=request, name="pages/credential_list.jinja", context=CONTEXT
    )
