"""
routes/videos.py — Video CRUD routes.

Handles: GET /api/videos, POST /api/videos,
POST /api/videos/<id>/toggle, DELETE /api/videos/<id>.
"""

import re
import logging
from flask import Blueprint, request

from backend.storage.repository import get_all_videos, add_video, toggle_video_monitoring, delete_video
from backend.routes import ok, err, get_db_url, get_owned_project, get_owned_video

logger = logging.getLogger("youtube_collector")

videos_bp = Blueprint("videos", __name__, url_prefix="/api")


@videos_bp.route("/videos", methods=["GET"])
def get_videos():
    try:
        from flask import session
        user_id = session.get("user_id")
        return ok({"videos": get_all_videos(get_db_url(), owner_user_id=user_id)})
    except Exception as e:
        logger.error(f"Videos list error: {e}")
        return err(str(e))


@videos_bp.route("/videos", methods=["POST"])
def post_video():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    if not url:
        return err("URL YouTube tidak boleh kosong", 400)

    # Extract YouTube video ID
    # Matches: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/embed/ID, etc.
    match = re.search(r'(?:v=|youtu\.be\/|embed\/)([^&?\/]+)', url)
    if not match:
        return err("Format URL YouTube tidak valid", 400)

    video_id = match.group(1)
    project_id = data.get("project_id", "").strip()
    if not project_id:
        return err("Project ID harus dipilih", 400)

    try:
        if not get_owned_project(project_id):
            return err("Project not found", 404)
            
        video = add_video(video_id, url, project_id, get_db_url())
        if not video:
            return ok({"success": False, "error": "Video mungkin sudah ada atau gagal ditambahkan"}, 409)
        return ok({"success": True, "video": video})
    except Exception as e:
        logger.error(f"Add video error: {e}")
        return err(str(e))


@videos_bp.route("/videos/<video_id>/toggle", methods=["POST", "PUT"])
def toggle_video(video_id):
    try:
        if not get_owned_video(video_id):
            return err("Video tidak ditemukan", 404)
            
        video = toggle_video_monitoring(video_id, get_db_url())
        if not video:
            return err("Video tidak ditemukan", 404)
        return ok({"success": True, "video": video})
    except Exception as e:
        logger.error(f"Toggle video error: {e}")
        return err(str(e))


@videos_bp.route("/videos/<video_id>", methods=["DELETE"])
def remove_video(video_id):
    try:
        if not get_owned_video(video_id):
            return err("Video tidak ditemukan", 404)
            
        success = delete_video(video_id, get_db_url())
        if not success:
            return err("Video tidak ditemukan", 404)
        return ok({"success": True})
    except Exception as e:
        logger.error(f"Delete video error: {e}")
        return err(str(e))
