"""
Route helpers — shared utilities for all route blueprints.

Provides common functions for DB URL resolution, JSON responses,
and request filter parsing (DRY extraction from dashboard_routes.py).
"""

import logging
from typing import Optional, Tuple

from flask import jsonify, request, session

from backend.config import load_settings, get_database_url

logger = logging.getLogger("youtube_collector")


def ok(data, status=200):
    """Return a JSON success response."""
    return jsonify(data), status


def err(message, status=500):
    """Return a JSON error response."""
    return jsonify({"error": message}), status


def get_db_url() -> str:
    """Resolve the database URL from settings."""
    return get_database_url(load_settings())


def get_owned_project(project_id: str):
    """Return a project only when it belongs to the logged-in user."""
    from backend.storage.projects_repo import get_project

    project = get_project(project_id, get_db_url())
    if not project or project.get("owner_user_id") != session.get("user_id"):
        return None
    return project


def get_owned_video(video_id: str):
    """Return a video only when its project belongs to the logged-in user."""
    from backend.storage.repository import get_video

    video = get_video(video_id, get_db_url())
    if not video or not get_owned_project(video.get("project_id")):
        return None
    return video


def parse_type_filter(type_filter: Optional[str]) -> Optional[bool]:
    """Convert a 'type' query param into an is_baseline boolean.

    Returns True for 'baseline', False for 'new', None otherwise.
    """
    if type_filter == "baseline":
        return True
    elif type_filter == "new":
        return False
    return None


def parse_common_filters() -> Tuple[Optional[str], Optional[str], Optional[bool]]:
    """Extract project_id, video_id, and is_baseline from the current request.

    Returns (project_id, video_id, is_baseline).
    """
    project_id = request.args.get("project_id")
    video_id = request.args.get("video_id")
    is_baseline = parse_type_filter(request.args.get("type"))
    return project_id, video_id, is_baseline
