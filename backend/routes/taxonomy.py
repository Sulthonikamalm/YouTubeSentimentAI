"""Owner-scoped project taxonomy generation, editing, and activation routes."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from flask import Blueprint, request, session

from backend.routes import err, get_db_url, get_owned_project, ok
from backend.services.gemini_service import generate_taxonomy_draft
from backend.services.taxonomy_config import dumps_labels, parse_labels, validate_config
from backend.storage.db import get_db_connection

logger = logging.getLogger("youtube_collector.taxonomy")
taxonomy_bp = Blueprint("taxonomy", __name__, url_prefix="/api")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_version(row) -> dict:
    data = dict(row)
    for field in ("issue_labels", "stance_labels", "action_labels"):
        data[field] = parse_labels(data.get(field))
    return data


def _mark_project_comments_pending(conn, project_id: str) -> int:
    result = conn.execute(
        "UPDATE comments SET inference_status = 'pending', sentiment = NULL, "
        "sentiment_confidence = NULL, issue_label = NULL, stance_label = NULL, "
        "action_intent_label = NULL, interpretation_short = NULL, model_version = NULL, "
        "inference_error = NULL, inferred_at = NULL, taxonomy_version_id = NULL "
        "WHERE is_manually_corrected = 0 AND video_id IN "
        "(SELECT video_id FROM videos WHERE project_id = ?)",
        (project_id,),
    )
    return result.rowcount


def _activate(project_id: str, version_id: str, reprocess: bool) -> tuple[dict, int]:
    db_url = get_db_url()
    with get_db_connection(db_url) as conn:
        with conn:
            target = conn.execute(
                "SELECT * FROM project_taxonomy_versions WHERE project_id = ? AND version_id = ?",
                (project_id, version_id),
            ).fetchone()
            if not target:
                raise LookupError("Version not found")
            if target["status"] not in ("draft", "active"):
                raise ValueError("Hanya draft yang dapat diaktifkan.")

            config = validate_config(
                target["prompt_context"], target["issue_labels"],
                target["stance_labels"], target["action_labels"],
            )
            now = _now()
            conn.execute(
                "UPDATE project_taxonomy_versions SET status = 'archived', updated_at = ? "
                "WHERE project_id = ? AND status = 'active' AND version_id != ?",
                (now, project_id, version_id),
            )
            conn.execute(
                "UPDATE project_taxonomy_versions SET status = 'active', activated_at = COALESCE(activated_at, ?), updated_at = ? "
                "WHERE project_id = ? AND version_id = ?",
                (now, now, project_id, version_id),
            )
            conn.execute(
                "UPDATE projects SET active_taxonomy_version_id = ?, status = 'active', "
                "prompt_context = ?, issue_labels = ?, stance_labels = ?, action_labels = ?, updated_at = ? "
                "WHERE project_id = ?",
                (
                    version_id, config["prompt_context"], dumps_labels(config["issues"]),
                    dumps_labels(config["stances"]), dumps_labels(config["actions"]),
                    now, project_id,
                ),
            )
            affected = _mark_project_comments_pending(conn, project_id) if reprocess else 0
    return config, affected


@taxonomy_bp.route("/projects/<project_id>/taxonomy/generate", methods=["POST"])
def generate_taxonomy(project_id):
    if not get_owned_project(project_id):
        return err("Project not found", 404)
    data = request.get_json() or {}
    result = generate_taxonomy_draft(project_id, data.get("instructions"), get_db_url())
    if result.get("success"):
        return ok(result)
    status_by_code = {
        "already_running": 409,
        "quota_exceeded": 429,
        "daily_limit": 429,
        "timeout": 504,
        "provider_error": 503,
        "dependency_missing": 503,
        "not_found": 404,
    }
    return err(result.get("error", "Generate taxonomy gagal."), status_by_code.get(result.get("error_code"), 400))


@taxonomy_bp.route("/projects/<project_id>/taxonomy/versions", methods=["GET"])
def get_versions(project_id):
    if not get_owned_project(project_id):
        return err("Project not found", 404)
    with get_db_connection(get_db_url()) as conn:
        rows = conn.execute(
            "SELECT * FROM project_taxonomy_versions WHERE project_id = ? "
            "ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    return ok({"versions": [_serialize_version(row) for row in rows]})


@taxonomy_bp.route("/projects/<project_id>/taxonomy/versions", methods=["POST"])
def create_manual_version(project_id):
    if not get_owned_project(project_id):
        return err("Project not found", 404)
    data = request.get_json() or {}
    try:
        config = validate_config(
            data.get("prompt_context"), data.get("issue_labels"),
            data.get("stance_labels"), data.get("action_labels"),
        )
    except ValueError as exc:
        return err(str(exc), 400)
    version_id = f"{project_id}_v_{uuid.uuid4().hex[:10]}"
    now = _now()
    with get_db_connection(get_db_url()) as conn:
        with conn:
            conn.execute(
                "INSERT INTO project_taxonomy_versions "
                "(version_id, project_id, status, source, prompt_context, issue_labels, "
                "stance_labels, action_labels, created_by, created_at, updated_at) "
                "VALUES (?, ?, 'draft', 'manual', ?, ?, ?, ?, ?, ?, ?)",
                (
                    version_id, project_id, config["prompt_context"],
                    dumps_labels(config["issues"]), dumps_labels(config["stances"]),
                    dumps_labels(config["actions"]), session.get("user_id"), now, now,
                ),
            )
    return ok({"success": True, "version_id": version_id}, 201)


@taxonomy_bp.route("/projects/<project_id>/taxonomy/versions/<version_id>", methods=["PATCH"])
def edit_version(project_id, version_id):
    if not get_owned_project(project_id):
        return err("Project not found", 404)
    data = request.get_json() or {}
    with get_db_connection(get_db_url()) as conn:
        current = conn.execute(
            "SELECT * FROM project_taxonomy_versions WHERE project_id = ? AND version_id = ? AND status = 'draft'",
            (project_id, version_id),
        ).fetchone()
        if not current:
            return err("Draft not found or already activated.", 404)
        try:
            config = validate_config(
                data.get("prompt_context", current["prompt_context"]),
                data.get("issue_labels", current["issue_labels"]),
                data.get("stance_labels", current["stance_labels"]),
                data.get("action_labels", current["action_labels"]),
            )
        except ValueError as exc:
            return err(str(exc), 400)
        with conn:
            conn.execute(
                "UPDATE project_taxonomy_versions SET source = 'manual', prompt_context = ?, "
                "issue_labels = ?, stance_labels = ?, action_labels = ?, updated_at = ? "
                "WHERE project_id = ? AND version_id = ? AND status = 'draft'",
                (
                    config["prompt_context"], dumps_labels(config["issues"]),
                    dumps_labels(config["stances"]), dumps_labels(config["actions"]),
                    _now(), project_id, version_id,
                ),
            )
    return ok({"success": True, "version": {"version_id": version_id, **config}})


@taxonomy_bp.route("/projects/<project_id>/taxonomy/versions/<version_id>/activate", methods=["POST"])
def activate_version(project_id, version_id):
    if not get_owned_project(project_id):
        return err("Project not found", 404)
    reprocess = bool((request.get_json() or {}).get("reprocess_all", False))
    try:
        _, affected = _activate(project_id, version_id, reprocess)
    except LookupError:
        return err("Version not found.", 404)
    except ValueError as exc:
        return err(str(exc), 400)
    return ok({"success": True, "reprocess_all": reprocess, "comments_queued": affected})


@taxonomy_bp.route("/projects/<project_id>/taxonomy/versions/<version_id>/reprocess", methods=["POST"])
def activate_and_reprocess(project_id, version_id):
    if not get_owned_project(project_id):
        return err("Project not found", 404)
    try:
        _, affected = _activate(project_id, version_id, True)
    except LookupError:
        return err("Version not found.", 404)
    except ValueError as exc:
        return err(str(exc), 400)
    return ok({"success": True, "comments_queued": affected})


@taxonomy_bp.route("/projects/<project_id>/taxonomy/reprocess", methods=["POST"])
def reprocess_active(project_id):
    project = get_owned_project(project_id)
    if not project:
        return err("Project not found", 404)
    active_id = project.get("active_taxonomy_version_id")
    if not active_id:
        return err("Project belum memiliki taxonomy aktif.", 400)
    with get_db_connection(get_db_url()) as conn:
        with conn:
            affected = _mark_project_comments_pending(conn, project_id)
    return ok({"success": True, "comments_queued": affected})
