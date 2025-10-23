"""Main entry point for the server."""

import asyncio
import os
import uuid
import uvicorn

from dotenv import load_dotenv

# from app.plugins import AskarStorage
from app.plugins.storage import StorageManager
from app.tasks import TaskManager

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))

APP_PORT = int(os.getenv("APP_PORT", "8000"))
APP_WORKERS = int(os.getenv("APP_WORKERS", "4"))


async def startup_tasks():
    """Run startup tasks before server starts."""
    # Provision databases (synchronously - must complete before server starts)
    from app.plugins import AskarStorage
    await AskarStorage().provision()
    await StorageManager().provision(recreate=False)
    
    # Run startup tasks
    await TaskManager(str(uuid.uuid4())).set_policies()
    # await TaskManager(str(uuid.uuid4())).sync_records()


if __name__ == "__main__":
    # Run startup tasks and wait for completion
    print("Running startup tasks...")
    asyncio.run(startup_tasks())
    print("Startup tasks completed. Starting server...")
    
    # Start server
    uvicorn.run("app:app", host="0.0.0.0", port=APP_PORT, reload=False)
