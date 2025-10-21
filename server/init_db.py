"""Initialize the database."""

import asyncio
import logging
import sys
from app.plugins.storage import StorageManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database(recreate: bool = False):
    """
    Initialize database tables.
    
    Args:
        recreate: If True, drop all tables before creating them
    """
    logger.info("Initializing SQLAlchemy database...")
    storage = StorageManager()
    await storage.provision(recreate=recreate)
    logger.info("Database initialized successfully!")


if __name__ == "__main__":
    # Check for --recreate flag
    recreate = "--recreate" in sys.argv
    
    if recreate:
        response = input("⚠️  This will DROP ALL TABLES. Are you sure? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
    
    asyncio.run(init_database(recreate=recreate))

