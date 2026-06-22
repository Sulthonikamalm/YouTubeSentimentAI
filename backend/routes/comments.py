"""
routes/comments.py — Comment listing and correction routes.

Handles: /api/comments, /api/comments/correct, /api/comments/reset,
/api/comments/delete_all.
"""

import logging
from datetime import datetime, timezone
from flask import Blueprint, request, session

from backend.storage.db import get_db_connection
from backend.routes import ok, err, get_db_url, parse_type_filter

logger = logging.getLogger("youtube_collector")

comments_bp = Blueprint("comments", __name__, url_prefix="/api")

OWNER_COMMENT_SCOPE = (
    "video_id IN (SELECT v.video_id FROM videos v "
    "JOIN projects p ON p.project_id = v.project_id WHERE p.owner_user_id = ?)"
)


@comments_bp.route("/comments", methods=["GET"])
def get_comments():
    project_id = request.args.get("project_id")
    video_id = request.args.get("video_id")
    sentiment = request.args.get("sentiment")
    issue_label = request.args.get("issue_label")
    stance_label = request.args.get("stance_label")
    action_intent_label = request.args.get("action_intent_label")
    type_filter = request.args.get("type")
    search = request.args.get("search")
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    try:
        with get_db_connection(get_db_url()) as conn:
            where_clauses, params = [OWNER_COMMENT_SCOPE], [session.get("user_id")]
            if project_id:
                where_clauses.append("video_id IN (SELECT video_id FROM videos WHERE project_id = ?)")
                params.append(project_id)
            if video_id:
                where_clauses.append("video_id = ?")
                params.append(video_id)
            if sentiment:
                if sentiment == "pending":
                    where_clauses.append("(sentiment IS NULL OR inference_status != 'completed')")
                else:
                    where_clauses.append("sentiment = ?")
                    params.append(sentiment)
            if issue_label:
                where_clauses.append("issue_label = ?")
                params.append(issue_label)
            if stance_label:
                where_clauses.append("stance_label = ?")
                params.append(stance_label)
            if action_intent_label:
                where_clauses.append("action_intent_label = ?")
                params.append(action_intent_label)
            if type_filter:
                if type_filter == "baseline":
                    where_clauses.append("is_baseline = 1")
                elif type_filter == "new":
                    where_clauses.append("is_baseline = 0")
            if search:
                where_clauses.append("comment_text LIKE ?")
                params.append(f"%{search}%")

            where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

            rows = conn.execute(
                f"SELECT comment_id, video_id, author_name, comment_text, "
                f"sentiment, sentiment_confidence, issue_label, stance_label, "
                f"action_intent_label, interpretation_short, published_at, "
                f"like_count, is_baseline "
                f"FROM comments {where} "
                f"ORDER BY published_at DESC LIMIT ? OFFSET ?;",
                (*params, limit, offset),
            ).fetchall()
            total = conn.execute(
                f"SELECT COUNT(*) FROM comments {where};", params
            ).fetchone()[0]

        return ok({"comments": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset})
    except Exception as e:
        logger.error(f"Comments list error: {e}")
        return err(str(e))


@comments_bp.route("/comments/correct", methods=["POST"])
def correct_comment():
    from backend.ml.ollama_service import normalize_text
    from backend.ml.intelligence_engine import _build_interpretation

    db_url = get_db_url()
    comment_id = None
    try:
        data = request.json or {}
        comment_id = data.get("comment_id")
        sentiment = data.get("sentiment")
        issue_label = data.get("issue_label")
        stance_label = data.get("stance_label")
        action_intent_label = data.get("action_intent_label")

        if not comment_id:
            return err("Missing comment_id", 400)

        with get_db_connection(db_url) as conn:
            row = conn.execute(
                "SELECT comment_text FROM comments WHERE comment_id = ? AND "
                + OWNER_COMMENT_SCOPE,
                (comment_id, session.get("user_id")),
            ).fetchone()
            if not row:
                return err("Comment not found", 404)

            interpretation = _build_interpretation(
                status="completed", sentiment=sentiment,
                issue_label=issue_label, stance_label=stance_label,
                action_intent_label=action_intent_label,
                clean_text=normalize_text(row[0]),
            )
            now = datetime.now(timezone.utc).isoformat()
            with conn:
                conn.execute(
                    "UPDATE comments SET sentiment=?, sentiment_confidence=1.0, "
                    "issue_label=?, stance_label=?, action_intent_label=?, "
                    "interpretation_short=?, model_version='human_corrected', "
                    "inference_status='completed', inference_error=NULL, "
                    "inferred_at=?, is_manually_corrected=1 WHERE comment_id=? AND "
                    + OWNER_COMMENT_SCOPE,
                    (sentiment, issue_label, stance_label, action_intent_label,
                     interpretation, now, comment_id, session.get("user_id")),
                )
        return ok({"success": True, "comment_id": comment_id, "interpretation": interpretation})
    except Exception as e:
        logger.error(f"Failed to manually correct comment {comment_id or 'unknown'}: {e}")
        return err(str(e))


@comments_bp.route("/comments/reset", methods=["POST"])
def reset_comments():
    try:
        with get_db_connection(get_db_url()) as conn:
            conn.execute(
                "UPDATE comments SET inference_status='pending', sentiment=NULL, "
                "sentiment_confidence=NULL, issue_label=NULL, stance_label=NULL, "
                "action_intent_label=NULL, interpretation_short=NULL, model_version=NULL, "
                "inference_error=NULL, inferred_at=NULL, taxonomy_version_id=NULL "
                "WHERE is_manually_corrected=0 AND " + OWNER_COMMENT_SCOPE,
                (session.get("user_id"),),
            )
            conn.commit()
        return ok({"success": True, "message": "Hasil analisis telah di-reset ke status pending."})
    except Exception as e:
        logger.error(f"Reset comments error: {e}")
        return err(str(e))


@comments_bp.route("/comments/delete_all", methods=["POST"])
def delete_all_comments():
    try:
        with get_db_connection(get_db_url()) as conn:
            conn.execute(
                "DELETE FROM comments WHERE " + OWNER_COMMENT_SCOPE,
                (session.get("user_id"),),
            )
            conn.commit()
        return ok({"success": True, "message": "Seluruh data komentar telah dihapus."})
    except Exception as e:
        logger.error(f"Delete all comments error: {e}")
        return err(str(e))
