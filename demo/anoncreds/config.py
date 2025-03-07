import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from cachelib.file import FileSystemCache

load_dotenv()
Path("session").mkdir(parents=True, exist_ok=True)

class Config(object):
    
    APP_TITLE = 'AnonCreds + WebVH'
    
    SECRET_KEY = os.getenv('SECRET_KEY', 'unsecured')
    
    DOMAIN = os.getenv('DOMAIN', 'localhost')
    ENDPOINT = f"http://{DOMAIN}" if DOMAIN == 'localhost:5000' else f"https://{DOMAIN}"
    
    ASKAR_DB = os.getenv('ASKAR_DB', 'sqlite://session/app.db')
    
    SESSION_TYPE = 'cachelib'
    SESSION_SERIALIZATION_FORMAT = 'json'
    SESSION_CACHELIB = FileSystemCache(threshold=500, cache_dir="session")
    SESSION_COOKIE_NAME  = 'AnonCreds'
    SESSION_COOKIE_SAMESITE = 'Strict'
    SESSION_COOKIE_HTTPONLY = 'True'
    
    AGENT_ADMIN_API_KEY = os.getenv('AGENT_ADMIN_API_KEY', '')
    AGENT_ADMIN_ENDPOINT = os.getenv('AGENT_ADMIN_ENDPOINT', 'https://api.issuer.test-suite.app')
    AGENT_WITNESS_SEED = os.getenv('AGENT_WITNESS_SEED', '00000000000000000000000000000000')
    
    DIDWEBVH_SERVER = os.getenv('DIDWEBVH_SERVER', 'https://id.test-suite.app')
    DIDWEBVH_WITNESS_KEY = os.getenv('DIDWEBVH_WITNESS_KEY', 'z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i')
    
    DEMO = {
        "name": "WebVH AnonCreds Demo",
        "version": "1.0",
        "issuer": "WebVH AnonCreds Demo",
        "size": 100,
        "preview": {
            "email": "jane.doe@example.com",
            "date": "20250102"
        },
        "request": {
            "attributes": ["email"],
            "predicate": ["date", ">=", 20250101]
        }
    }
        