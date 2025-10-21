"""Explorer routes for DIDs and resources UI."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.plugins import AskarStorage, DidWebVH

from config import templates, settings

router = APIRouter(tags=["Explorer"])
askar = AskarStorage()
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
    tags = {
        "scid": scid or None,
        "namespace": namespace or None,
        "identifier": identifier or None,
        "domain": domain or None,
    }
    if status == "active":
        tags["deactivated"] = "False"
    elif status == "deactivated":
        tags["deactivated"] = "True"

    tags = {k: v for k, v in tags.items() if v is not None}
    
    # Note: has_resources filter would need to be applied post-fetch
    # as it's not a tag in the database
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Get total count for pagination
    total = await askar.count_category_entries("didRecord", tags)
    total_pages = (total + limit - 1) // limit  # Ceiling division
    
    # Get paginated results
    entries = await askar.get_category_entries("didRecord", tags, limit=limit, offset=offset)
    results = [entry.value_json for entry in entries]
    
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
    tags = {
        "scid": scid or None,
        "resource_id": resource_id or None,
        "resource_type": resource_type or None,
    }
    tags = {k: v for k, v in tags.items() if v is not None}
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Get total count for pagination
    total = await askar.count_category_entries("resourceRecord", tags)
    total_pages = (total + limit - 1) // limit  # Ceiling division
    
    # Get paginated results
    entries = await askar.get_category_entries("resourceRecord", tags, limit=limit, offset=offset)
    
    CONTEXT = {
        "results": [entry.value_json for entry in entries],
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
