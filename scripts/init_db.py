"""
init_db.py — CLI script to initialize SQLite database schemas.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import load_settings, get_database_url
from backend.storage.repository import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("init_db")

def main():
    logger.info("Initializing database...")
    try:
        settings = load_settings()
        db_url = get_database_url(settings)
        logger.info(f"Target Database URL: {db_url}")
        
        init_db(db_url)
        logger.info("Database schemas and indexes created successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
