"""
video_registry.py — Handles video registration, parsing, and retrieval.
"""

import logging
from typing import List, Dict, Any, Optional
from backend.youtube.video_utils import parse_video_id
from backend.storage import repository

logger = logging.getLogger("youtube_collector")

DEFAULT_PROJECT_ID = "default_politik"


def register_video(url_or_id: str, project_id: str = DEFAULT_PROJECT_ID,
                   database_url: Optional[str] = None) -> Optional[str]:
    """
    Parses video ID from URL or ID, saves it in SQLite registry, and returns the ID.
    If already exists, registers it without duplicate errors.
    """
    video_id = parse_video_id(url_or_id)
    if not video_id:
        logger.error(f"Cannot register video: invalid URL or ID format: '{url_or_id}'")
        return None

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        # project_id and database_url are distinct args — pass by keyword so the
        # configured database (not the project id) lands in database_url.
        repository.add_video(video_id, video_url, project_id, database_url=database_url)
        logger.info(f"Registered video {video_id} in registry.")
        return video_id
    except Exception as e:
        logger.error(f"Database error registering video {url_or_id}: {e}")
        return None

def get_video_details(video_id: str, database_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    return repository.get_video(video_id, database_url)

def get_monitored_videos(database_url: Optional[str] = None) -> List[Dict[str, Any]]:
    return repository.get_active_videos(database_url)
