"""
routes/dashboard.py — Dashboard metrics & analytics routes.

Handles: /api/health, /api/dashboard/summary, distributions, timeline,
realtime, representative-comments, interpretation, /api/settings/ollama-status.
"""

import logging
from flask import Blueprint, request

from backend.storage.db import get_db_connection
from backend.storage.repository import sample_inference_rows
from backend.dashboard_helpers import (
    fetch_summary, fetch_distributions, fetch_timeline,
    fetch_interpretation, fetch_realtime_metrics,
)
from backend.routes import (
    ok, err, get_db_url, parse_common_filters, get_owned_project, get_owned_video,
)

from datetime import datetime, timezone

logger = logging.getLogger("youtube_collector")

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api")


def _filters_are_owned(project_id, video_id) -> bool:
    return not (
        (project_id and not get_owned_project(project_id))
        or (video_id and not get_owned_video(video_id))
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@dashboard_bp.route("/health", methods=["GET"])
def health():
    try:
        with get_db_connection(get_db_url()) as conn:
            conn.execute("SELECT 1;")
        return ok({"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()})
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return ok({"status": "unhealthy", "error": str(e)}, 503)


# ---------------------------------------------------------------------------
# Dashboard Data
# ---------------------------------------------------------------------------

@dashboard_bp.route("/dashboard/summary", methods=["GET"])
def dashboard_summary():
    project_id, video_id, is_baseline = parse_common_filters()
    if not _filters_are_owned(project_id, video_id):
        return err("Data not found", 404)
    from flask import session
    try:
        return ok(fetch_summary(get_db_url(), project_id=project_id, video_id=video_id, is_baseline=is_baseline, owner_user_id=session.get("user_id")))
    except Exception as e:
        logger.error(f"Dashboard summary error: {e}")
        return err(str(e))


@dashboard_bp.route("/dashboard/distributions", methods=["GET"])
def dashboard_distributions():
    project_id, video_id, is_baseline = parse_common_filters()
    if not _filters_are_owned(project_id, video_id):
        return err("Data not found", 404)
    from flask import session
    try:
        return ok(fetch_distributions(get_db_url(), project_id=project_id, video_id=video_id, is_baseline=is_baseline, owner_user_id=session.get("user_id")))
    except Exception as e:
        logger.error(f"Distributions error: {e}")
        return err(str(e))


@dashboard_bp.route("/dashboard/timeline", methods=["GET"])
def dashboard_timeline():
    days = request.args.get("days", 30, type=int)
    project_id, video_id, is_baseline = parse_common_filters()
    if not _filters_are_owned(project_id, video_id):
        return err("Data not found", 404)
    from flask import session
    try:
        return ok(fetch_timeline(get_db_url(), days, project_id=project_id, video_id=video_id, is_baseline=is_baseline, owner_user_id=session.get("user_id")))
    except Exception as e:
        logger.error(f"Timeline error: {e}")
        return err(str(e))


@dashboard_bp.route("/dashboard/realtime", methods=["GET"])
def dashboard_realtime():
    minutes = request.args.get("minutes", 30, type=int)
    from flask import session
    try:
        return ok(fetch_realtime_metrics(
            get_db_url(), minutes=minutes, owner_user_id=session.get("user_id")
        ))
    except Exception as e:
        logger.error(f"Realtime metrics error: {e}")
        return err(str(e))


@dashboard_bp.route("/dashboard/representative-comments", methods=["GET"])
def dashboard_representative_comments():
    limit = request.args.get("limit", 8, type=int)
    project_id, video_id, is_baseline = parse_common_filters()
    if not _filters_are_owned(project_id, video_id):
        return err("Data not found", 404)
    from flask import session
    try:
        return ok({"comments": sample_inference_rows(limit, get_db_url(), video_id=video_id, is_baseline=is_baseline, project_id=project_id, owner_user_id=session.get("user_id"))})
    except Exception as e:
        logger.error(f"Representative comments error: {e}")
        return err(str(e))


@dashboard_bp.route("/dashboard/interpretation", methods=["GET"])
def dashboard_interpretation():
    project_id, video_id, is_baseline = parse_common_filters()
    if not _filters_are_owned(project_id, video_id):
        return err("Data not found", 404)
    from flask import session
    try:
        return ok(fetch_interpretation(get_db_url(), project_id=project_id, video_id=video_id, is_baseline=is_baseline, owner_user_id=session.get("user_id")))
    except Exception as e:
        logger.error(f"Interpretation error: {e}")
        return err(str(e))


# ---------------------------------------------------------------------------
# Ollama Status
# ---------------------------------------------------------------------------

@dashboard_bp.route("/settings/ollama-status", methods=["GET"])
def ollama_status():
    """Returns health check info for the local Ollama server and model."""
    from backend.ml.ollama_service import check_ollama_health, get_ollama_settings
    try:
        health = check_ollama_health()
        settings = get_ollama_settings()
        return ok({
            "server_online": health["server_online"],
            "model_loaded": health["model_loaded"],
            "model_name": health["model_name"],
            "base_url": settings["base_url"],
            "timeout": settings["timeout"],
            "error": health.get("error"),
        })
    except Exception as e:
        logger.error(f"Ollama status check error: {e}")
        return err(str(e))
