"""
config.py — Load settings and environment variables.
"""

import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv, set_key

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

# --- Settings cache (avoids re-reading YAML on every request) ---
_settings_cache: dict = {}
_settings_mtime: float = 0.0


def load_settings() -> dict:
    """Loads settings.yaml from the config/ folder.

    Results are cached in-memory and only refreshed when the file's mtime
    changes, so repeated calls from dashboard endpoints or the scheduler
    loop don't hit disk on every invocation.
    """
    global _settings_cache, _settings_mtime
    settings_path = PROJECT_ROOT / "config" / "settings.yaml"
    if not settings_path.exists():
        print(f"[ERROR] settings.yaml not found: {settings_path}")
        sys.exit(1)

    try:
        mtime = settings_path.stat().st_mtime
    except OSError:
        mtime = 0.0

    if _settings_cache and mtime == _settings_mtime:
        return _settings_cache

    with open(settings_path, "r", encoding="utf-8") as f:
        _settings_cache = yaml.safe_load(f)
    _settings_mtime = mtime
    return _settings_cache

def update_settings(new_settings_dict: dict):
    """Updates specific fields in settings.yaml based on a partial dictionary."""
    global _settings_cache, _settings_mtime
    settings_path = PROJECT_ROOT / "config" / "settings.yaml"
    
    current_settings = load_settings()
    
    # Deep update (simplified for our specific needs)
    if "youtube" in new_settings_dict:
        if "youtube" not in current_settings: current_settings["youtube"] = {}
        current_settings["youtube"].update(new_settings_dict["youtube"])
        
    if "scheduler" in new_settings_dict:
        if "scheduler" not in current_settings: current_settings["scheduler"] = {}
        current_settings["scheduler"].update(new_settings_dict["scheduler"])

    with open(settings_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(current_settings, f, default_flow_style=False, sort_keys=False)
        
    _settings_cache = current_settings
    try:
        _settings_mtime = settings_path.stat().st_mtime
    except OSError:
        pass

def update_env_var(key: str, value: str):
    """Updates or adds an environment variable in the .env file."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        env_path.touch()
    set_key(str(env_path), key, value)
    os.environ[key] = value # Update active process env



def get_database_url(settings: dict) -> str:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        db_url = settings.get("storage", {}).get("database_url", "sqlite:///data/youtube_monitor.db")
    return db_url
