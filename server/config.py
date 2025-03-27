"""App configuration."""

import logging
import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Settings(BaseSettings):
    """App settings."""

    PROJECT_TITLE: str = "DID WebVH Server"
    PROJECT_VERSION: str = "v0"

    SECRET_KEY: str = os.environ.get("SECRET_KEY", "s3cret")
    WEBVH_VERSION: str = os.environ.get("WEBVH_VERSION", "0.4")

    DOMAIN: str = os.environ.get("DOMAIN", "localhost")
    DID_WEB_PREFIX: str = "did:web:"
    DID_WEBVH_PREFIX: str = "did:webvh:"
    DID_WEB_BASE: str = f"{DID_WEB_PREFIX}{DOMAIN}"
    
    WITNESS_KEY: str = os.environ.get("WITNESS_REGISTRY", None)
    WITNESS_REGISTRY: str = os.environ.get("WITNESS_REGISTRY", None)
    
    if not WITNESS_KEY and not WITNESS_REGISTRY:
        pass
    
    if WITNESS_KEY and WITNESS_REGISTRY:
        pass
    
    PROOF_TTL: int = os.environ.get("PROOF_TTL", 10) # Minutes

    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "didwebvh-server")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_SERVER_NAME: str = os.getenv("POSTGRES_SERVER_NAME", "")
    POSTGRES_SERVER_PORT: str = os.getenv("POSTGRES_SERVER_PORT", "")

    ASKAR_DB: str = "sqlite://app.db"
    if POSTGRES_USER and POSTGRES_PASSWORD and POSTGRES_SERVER_NAME and POSTGRES_SERVER_PORT:
        logging.info(f"Using postgres storage: {POSTGRES_SERVER_NAME}:{POSTGRES_SERVER_PORT}")
        ASKAR_DB: str = f"postgres://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER_NAME}:{POSTGRES_SERVER_PORT}/{POSTGRES_DB}"
    else:
        logging.info("Using SQLite database")

    SCID_PLACEHOLDER: str = "{SCID}"


settings = Settings()
