from fastapi import FastAPI, APIRouter, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routers import identifiers, resources
from app.contexts import AttestedResourceCtx
import json
from config import settings

app = FastAPI(title=settings.PROJECT_TITLE, version=settings.PROJECT_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter()


@api_router.get("/server/status", tags=["Server"], include_in_schema=False)
async def server_status():
    """Server status endpoint."""
    return JSONResponse(status_code=200, content={"status": "ok"})


@api_router.get("/attested-resource/v1", tags=["Context"], include_in_schema=False)
async def get_attested_resource_ctx():
    """Attested Resource Context."""
    ctx = json.dumps(AttestedResourceCtx, indent=2)
    return Response(ctx, media_type="application/ld+json")


api_router.include_router(identifiers.router)
api_router.include_router(resources.router)

app.include_router(api_router)
