"""
db.py — Database connection and context manager helper.
"""

import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DEFAULT_DB_REL_PATH = "data/youtube_monitor.db"

def get_db_path(database_url: str = None) -> Path:
    """
    Parses SQLite file path from database_url or falls back to default.
    Example: sqlite:///data/youtube_monitor.db -> data/youtube_monitor.db
    """
    if not database_url:
        database_url = os.getenv("DATABASE_URL", "")

    db_path_str = DEFAULT_DB_REL_PATH
    if database_url and database_url.startswith("sqlite:///"):
        db_path_str = database_url[len("sqlite:///"):]

    project_root = Path(__file__).resolve().parent.parent.parent
    full_path = project_root / db_path_str
    
    full_path.parent.mkdir(parents=True, exist_ok=True)
    return full_path

@contextmanager
def get_db_connection(database_url: str = None):
    """
    Context manager to obtain a sqlite3 connection.
    Enforces row factory to return sqlite3.Row dict-like objects.
    """
    db_url_str = database_url or os.getenv("DATABASE_URL", "")
    if ":memory:" in db_url_str:
        conn = sqlite3.connect(":memory:")
    else:
        db_path = get_db_path(database_url)
        conn = sqlite3.connect(str(db_path))
        
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    try:
        yield conn
    finally:
        conn.close()
