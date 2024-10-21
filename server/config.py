from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv
import logging

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Settings(BaseSettings):
    PROJECT_TITLE: str = "TDW Server"
    PROJECT_VERSION: str = "v0"

    SECRET_KEY: str = os.environ["SECRET_KEY"]

    DOMAIN: str = os.environ["DOMAIN"]
    DID_WEB_BASE: str = f"did:web:{DOMAIN}"
    ENDORSER_MULTIKEY: str = os.environ["ENDORSER_MULTIKEY"]

    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_SERVER_NAME: str = os.getenv("POSTGRES_SERVER_NAME", "")
    POSTGRES_SERVER_PORT: str = os.getenv("POSTGRES_SERVER_PORT", "")

    ASKAR_DB: str = "sqlite://app.db"
    if (
        POSTGRES_USER
        and POSTGRES_PASSWORD
        and POSTGRES_SERVER_NAME
        and POSTGRES_SERVER_PORT
    ):
        logging.info(
            f"Using postgres storage: {POSTGRES_SERVER_NAME}:{POSTGRES_SERVER_PORT}"
        )
        ASKAR_DB: str = f"postgres://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER_NAME}:{POSTGRES_SERVER_PORT}/tdw-server"
    else:
        logging.info("Using SQLite database")

    SCID_PLACEHOLDER: str = "{SCID}"


settings = Settings()
