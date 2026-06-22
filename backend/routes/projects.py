"""
routes/projects.py — Project CRUD routes.

Handles: GET /api/projects, POST /api/projects, DELETE /api/projects/<id>.
"""

import logging
from flask import Blueprint, request, session
import uuid
import re

from backend.storage.repository import get_projects, create_project, delete_project
from backend.routes import ok, err, get_db_url, get_owned_project

logger = logging.getLogger("youtube_collector")

projects_bp = Blueprint("projects", __name__, url_prefix="/api")


@projects_bp.route("/projects", methods=["GET"])
def get_projects_route():
    try:
        user_id = session.get("user_id")
        return ok({"projects": get_projects(get_db_url(), owner_user_id=user_id)})
    except Exception as e:
        logger.error(f"Projects list error: {e}")
        return err(str(e))

@projects_bp.route("/projects/<project_id>", methods=["GET"])
def get_project_detail_route(project_id):
    try:
        project = get_owned_project(project_id)
        if not project:
            return err("Project not found", 404)
            
        # Get valid sample count
        from backend.storage.db import get_db_connection
        with get_db_connection(get_db_url()) as conn:
            cnt = conn.execute(
                "SELECT COUNT(*) FROM comments c "
                "JOIN videos v ON c.video_id = v.video_id "
                "WHERE v.project_id = ? AND c.is_deleted = 0 AND c.comment_text IS NOT NULL AND c.comment_text != ''",
                (project_id,)
            ).fetchone()[0]
            
        project["valid_sample_count"] = cnt
        return ok({"project": project})
    except Exception as e:
        logger.error(f"Project detail error: {e}")
        return err(str(e))


@projects_bp.route("/projects", methods=["POST"])
def post_project():
    data = request.get_json() or {}
    project_name = data.get("project_name", "").strip()

    if not project_name:
        return err("Project Name tidak boleh kosong", 400)

    # Generate slug for project_id
    base_slug = re.sub(r'[^a-zA-Z0-9]+', '-', project_name).strip('-').lower()
    if not base_slug:
        base_slug = "project"
    project_id = f"{base_slug}_{uuid.uuid4().hex[:6]}"

    # Prepare project data with new fields
    project_data = {
        "project_id": project_id,
        "project_name": project_name,
        "description": data.get("description", "").strip() or None,
        "owner_user_id": session.get("user_id"),
        "goal_type": data.get("goal_type", "").strip() or None,
        "goal_text": data.get("goal_text", "").strip() or None,
        "status": "draft",
    }

    try:
        create_project(project_data, get_db_url())
        return ok({"success": True, "project_id": project_id})
    except Exception as e:
        logger.error(f"Add project error: {e}")
        return err(str(e))


@projects_bp.route("/projects/<project_id>", methods=["PATCH"])
def patch_project(project_id):
    try:
        project = get_owned_project(project_id)
        if not project:
            return err("Project not found", 404)
            
        data = request.get_json() or {}
        project_name = data.get("project_name")
        description = data.get("description")
        goal_type = data.get("goal_type")
        goal_text = data.get("goal_text")
        
        from backend.storage.db import get_db_connection
        with get_db_connection(get_db_url()) as conn:
            with conn:
                conn.execute(
                    "UPDATE projects SET "
                    "project_name = COALESCE(?, project_name), "
                    "description = COALESCE(?, description), "
                    "goal_type = COALESCE(?, goal_type), "
                    "goal_text = COALESCE(?, goal_text), "
                    "updated_at = CURRENT_TIMESTAMP "
                    "WHERE project_id = ?",
                    (project_name, description, goal_type, goal_text, project_id)
                )
        return ok({"success": True})
    except Exception as e:
        logger.error(f"Patch project error: {e}")
        return err(str(e))


@projects_bp.route("/projects/<project_id>", methods=["DELETE"])
def delete_project_route(project_id):
    try:
        if not get_owned_project(project_id):
            return err("Project not found", 404)
        delete_project(project_id, get_db_url())
        return ok({"success": True})
    except ValueError as e:
        return err(str(e), 400)
    except Exception as e:
        logger.error(f"Delete project error: {e}")
        return err(str(e))
