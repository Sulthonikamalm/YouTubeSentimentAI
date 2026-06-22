"""
routes/taxonomy.py — Project taxonomy configuration and generation routes.
"""

import logging
from flask import Blueprint, request

from backend.routes import ok, err, get_db_url
from backend.storage.db import get_db_connection
from backend.services.gemini_service import generate_taxonomy_draft

logger = logging.getLogger("youtube_collector.taxonomy")

taxonomy_bp = Blueprint("taxonomy", __name__, url_prefix="/api")


@taxonomy_bp.route("/projects/<project_id>/taxonomy/generate", methods=["POST"])
def generate_taxonomy(project_id):
    from flask import session
    from backend.storage.projects_repo import get_project
    user_id = session.get("user_id")
    project = get_project(project_id, get_db_url())
    if not project:
        return err("Project not found", 404)
    if project.get("owner_user_id") != user_id and project_id != "default_politik":
        return err("Project not found", 404)

    data = request.get_json() or {}
    instructions = data.get("instructions")
    
    try:
        result = generate_taxonomy_draft(project_id, instructions, get_db_url())
        if not result["success"]:
            return err(result["error"], 400)
        return ok(result)
    except Exception as e:
        logger.error(f"Generate taxonomy error: {e}")
        return err(str(e))


@taxonomy_bp.route("/projects/<project_id>/taxonomy/versions", methods=["GET"])
def get_versions(project_id):
    from flask import session
    from backend.storage.projects_repo import get_project
    user_id = session.get("user_id")
    project = get_project(project_id, get_db_url())
    if not project:
        return err("Project not found", 404)
    if project.get("owner_user_id") != user_id and project_id != "default_politik":
        return err("Project not found", 404)

    try:
        with get_db_connection(get_db_url()) as conn:
            rows = conn.execute(
                "SELECT version_id, status, source, prompt_context, issue_labels, stance_labels, action_labels, regenerate_instruction, created_at "
                "FROM project_taxonomy_versions WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,)
            ).fetchall()
        return ok({"versions": [dict(r) for r in rows]})
    except Exception as e:
        return err(str(e))


@taxonomy_bp.route("/projects/<project_id>/taxonomy/versions/<version_id>", methods=["PATCH"])
def edit_version(project_id, version_id):
    from flask import session
    from backend.storage.projects_repo import get_project
    user_id = session.get("user_id")
    project = get_project(project_id, get_db_url())
    if not project:
        return err("Project not found", 404)
    if project.get("owner_user_id") != user_id and project_id != "default_politik":
        return err("Project not found", 404)

    data = request.get_json() or {}
    prompt_context = data.get("prompt_context")
    issue_labels = data.get("issue_labels")
    stance_labels = data.get("stance_labels")
    action_labels = data.get("action_labels")
    
    try:
        with get_db_connection(get_db_url()) as conn:
            with conn:
                # Update only if it's still a draft
                res = conn.execute(
                    "UPDATE project_taxonomy_versions "
                    "SET prompt_context = COALESCE(?, prompt_context), "
                    "issue_labels = COALESCE(?, issue_labels), "
                    "stance_labels = COALESCE(?, stance_labels), "
                    "action_labels = COALESCE(?, action_labels) "
                    "WHERE project_id = ? AND version_id = ? AND status = 'draft'",
                    (prompt_context, issue_labels, stance_labels, action_labels, project_id, version_id)
                )
                if res.rowcount == 0:
                    return err("Draft not found or already activated.", 404)
        return ok({"success": True})
    except Exception as e:
        return err(str(e))


@taxonomy_bp.route("/projects/<project_id>/taxonomy/versions/<version_id>/activate", methods=["POST"])
def activate_version(project_id, version_id):
    from flask import session
    from backend.storage.projects_repo import get_project
    user_id = session.get("user_id")
    project = get_project(project_id, get_db_url())
    if not project:
        return err("Project not found", 404)
    if project.get("owner_user_id") != user_id and project_id != "default_politik":
        return err("Project not found", 404)

    data = request.get_json() or {}
    reprocess_all = data.get("reprocess_all", False)
    
    try:
        with get_db_connection(get_db_url()) as conn:
            with conn:
                # Archive currently active
                conn.execute(
                    "UPDATE project_taxonomy_versions SET status = 'archived' "
                    "WHERE project_id = ? AND status = 'active'",
                    (project_id,)
                )
                
                # Activate new version
                res = conn.execute(
                    "UPDATE project_taxonomy_versions SET status = 'active' "
                    "WHERE project_id = ? AND version_id = ?",
                    (project_id, version_id)
                )
                if res.rowcount == 0:
                    return err("Version not found.", 404)
                    
                # Update project table
                # Also fetch the labels to update the project table for legacy compatibility
                v_data = conn.execute(
                    "SELECT prompt_context, issue_labels, stance_labels, action_labels "
                    "FROM project_taxonomy_versions WHERE version_id = ?",
                    (version_id,)
                ).fetchone()
                
                conn.execute(
                    "UPDATE projects SET active_taxonomy_version_id = ?, status = 'active', "
                    "prompt_context = ?, issue_labels = ?, stance_labels = ?, action_labels = ? "
                    "WHERE project_id = ?",
                    (version_id, v_data["prompt_context"], v_data["issue_labels"], v_data["stance_labels"], v_data["action_labels"], project_id)
                )

        return ok({"success": True})
    except Exception as e:
        logger.error(f"Activate version error: {e}")
        return err(str(e))

@taxonomy_bp.route("/projects/<project_id>/taxonomy/reprocess", methods=["POST"])
def reprocess_comments(project_id):
    from flask import session
    from backend.storage.projects_repo import get_project
    user_id = session.get("user_id")
    project = get_project(project_id, get_db_url())
    if not project:
        return err("Project not found", 404)
    if project.get("owner_user_id") != user_id and project_id != "default_politik":
        return err("Project not found", 404)

    try:
        with get_db_connection(get_db_url()) as conn:
            with conn:
                videos = conn.execute("SELECT video_id FROM videos WHERE project_id = ?", (project_id,)).fetchall()
                for v in videos:
                    conn.execute(
                        "UPDATE comments SET inference_status = 'pending', "
                        "sentiment = NULL, sentiment_confidence = NULL, "
                        "issue_label = NULL, stance_label = NULL, action_intent_label = NULL, "
                        "interpretation_short = NULL, model_version = NULL, taxonomy_version_id = NULL "
                        "WHERE video_id = ?",
                        (v["video_id"],)
                    )
        return ok({"success": True, "message": "Comments marked for reprocessing"})
    except Exception as e:
        logger.error(f"Reprocess comments error: {e}")
        return err(str(e))
