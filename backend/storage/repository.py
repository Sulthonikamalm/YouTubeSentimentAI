"""repository.py — Database operations repository (videos, comments, runs, usage).

Project CRUD and the schema bootstrap live in projects_repo.py; they are
re-exported here so `repository.init_db`, `repository.get_projects`, etc. keep
working for existing callers.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import sqlite3

from backend.storage.db import get_db_connection
from backend.storage.projects_repo import (  # re-exported for backward compat
    init_db,
    get_projects,
    get_project,
    create_project,
    delete_project,
    get_projects_for_videos,
)

# Re-exported project helpers are listed in __all__ so they remain part of this
# module's public surface (and so static checkers see them as used, not dead).
__all__ = [
    "init_db", "get_projects", "get_project", "create_project", "delete_project",
    "get_projects_for_videos",
    "get_video", "get_active_videos", "get_all_videos", "add_video",
    "update_video_metadata", "update_video_last_checked", "mark_video_first_crawl_done",
    "toggle_video_monitoring", "delete_video",
    "get_comment", "get_comment_dedup_meta", "save_comment", "update_comment",
    "count_comments_for_video",
    "get_pending_comment_ids", "get_all_comment_ids", "update_comment_inference",
    "get_comments_by_ids", "batch_update_inference", "mark_inference_pending_for_status_null",
    "inference_status_counts", "column_value_counts", "sample_inference_rows",
    "save_crawl_run", "save_api_usage",
]

# --- Videos ---

def get_video(video_id: str, database_url: str = None) -> Optional[Dict[str, Any]]:
    with get_db_connection(database_url) as conn:
        row = conn.execute("SELECT * FROM videos WHERE video_id = ?;", (video_id,)).fetchone()
        return dict(row) if row else None

def get_active_videos(database_url: str = None) -> List[Dict[str, Any]]:
    with get_db_connection(database_url) as conn:
        rows = conn.execute("SELECT * FROM videos WHERE monitoring_enabled = 1;").fetchall()
        return [dict(r) for r in rows]

def get_all_videos(database_url: str = None, owner_user_id: int = None) -> List[Dict[str, Any]]:
    with get_db_connection(database_url) as conn:
        if owner_user_id:
            return [dict(r) for r in conn.execute(
                "SELECT v.* FROM videos v JOIN projects p ON v.project_id = p.project_id "
                "WHERE p.owner_user_id = ?;", (owner_user_id,)
            ).fetchall()]
        return [dict(r) for r in conn.execute("SELECT * FROM videos;").fetchall()]

def add_video(video_id: str, video_url: str, project_id: str, database_url: str = None) -> Optional[Dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection(database_url) as conn:
        with conn:
            try:
                conn.execute(
                    "INSERT INTO videos (video_id,video_url,project_id,monitoring_enabled,first_crawl_done,created_at,updated_at) "
                    "VALUES (?, ?, ?, 1, 0, ?, ?);",
                    (video_id, video_url, project_id, now, now),
                )
            except sqlite3.IntegrityError:
                pass
    return get_video(video_id, database_url)

def update_video_metadata(video_id: str, video_title: str, channel_title: str,
                          first_seen_at: str, database_url: str = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection(database_url) as conn:
        with conn:
            conn.execute(
                "UPDATE videos SET video_title=?, channel_title=?, first_seen_at=?, updated_at=? WHERE video_id=?;",
                (video_title, channel_title, first_seen_at, now, video_id),
            )

def update_video_last_checked(video_id: str, last_checked_at: str,
                              last_seen_comment_at: Optional[str],
                              total_comments_collected: int,
                              database_url: str = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection(database_url) as conn:
        with conn:
            if last_seen_comment_at:
                conn.execute(
                    "UPDATE videos SET last_checked_at=?, last_seen_comment_at=?, "
                    "total_comments_collected=?, updated_at=? WHERE video_id=?;",
                    (last_checked_at, last_seen_comment_at, total_comments_collected, now, video_id),
                )
            else:
                conn.execute(
                    "UPDATE videos SET last_checked_at=?, total_comments_collected=?, updated_at=? WHERE video_id=?;",
                    (last_checked_at, total_comments_collected, now, video_id),
                )

def mark_video_first_crawl_done(video_id: str, monitoring_started_at: str,
                                database_url: str = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection(database_url) as conn:
        with conn:
            conn.execute(
                "UPDATE videos SET first_crawl_done=1, monitoring_started_at=?, updated_at=? WHERE video_id=?;",
                (monitoring_started_at, now, video_id),
            )

def toggle_video_monitoring(video_id: str, database_url: str = None) -> Optional[Dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection(database_url) as conn:
        with conn:
            conn.execute(
                "UPDATE videos SET monitoring_enabled = 1 - monitoring_enabled, updated_at=? WHERE video_id=?;",
                (now, video_id)
            )
    return get_video(video_id, database_url)

def delete_video(video_id: str, database_url: str = None) -> bool:
    with get_db_connection(database_url) as conn:
        with conn:
            # We don't delete comments so we keep historical data, just remove the video from active monitoring
            res = conn.execute("DELETE FROM videos WHERE video_id=?;", (video_id,))
            return res.rowcount > 0

# --- Comments ---

def get_comment(comment_id: str, database_url: str = None) -> Optional[Dict[str, Any]]:
    with get_db_connection(database_url) as conn:
        row = conn.execute("SELECT * FROM comments WHERE comment_id = ?;", (comment_id,)).fetchone()
        return dict(row) if row else None

def get_comment_dedup_meta(comment_id: str, database_url: str = None) -> Optional[Dict[str, Any]]:
    """Lightweight existence check for the crawl dedup hot-path.

    Returns only {comment_id, updated_at} — the fields the crawler compares to
    detect edits — instead of SELECT *, so the large raw_json blob is not
    ferried across the connection on every comment/reply check. None if absent.
    """
    with get_db_connection(database_url) as conn:
        row = conn.execute(
            "SELECT comment_id, updated_at FROM comments WHERE comment_id = ?;",
            (comment_id,),
        ).fetchone()
        return dict(row) if row else None

def save_comment(comment: Dict[str, Any], database_url: str = None) -> None:
    payload = dict(comment)
    payload.setdefault("inference_status", "pending")
    with get_db_connection(database_url) as conn:
        with conn:
            conn.execute(
                "INSERT INTO comments ("
                "comment_id, video_id, parent_id, is_reply, author_name, author_channel_id,"
                "comment_text, text_original, text_display, published_at, updated_at,"
                "like_count, reply_count, collected_at, is_baseline, is_deleted,"
                "last_seen_at, raw_json_hash, raw_json, inference_status"
                ") VALUES ("
                ":comment_id, :video_id, :parent_id, :is_reply, :author_name, :author_channel_id,"
                ":comment_text, :text_original, :text_display, :published_at, :updated_at,"
                ":like_count, :reply_count, :collected_at, :is_baseline, :is_deleted,"
                ":last_seen_at, :raw_json_hash, :raw_json, :inference_status"
                ");",
                payload,
            )

def update_comment(comment: Dict[str, Any], database_url: str = None) -> None:
    """Updates comment. Resets inference to 'pending' when text actually changes."""
    with get_db_connection(database_url) as conn:
        row = conn.execute(
            "SELECT comment_text FROM comments WHERE comment_id = ?;",
            (comment.get("comment_id"),),
        ).fetchone()
        text_changed = row and row[0] != comment.get("comment_text")
        with conn:
            if text_changed:
                conn.execute(
                    "UPDATE comments SET comment_text=:comment_text, text_original=:text_original, "
                    "text_display=:text_display, updated_at=:updated_at, like_count=:like_count, "
                    "reply_count=:reply_count, last_seen_at=:last_seen_at, raw_json_hash=:raw_json_hash, "
                    "raw_json=:raw_json, inference_status='pending', sentiment=NULL, "
                    "sentiment_confidence=NULL, issue_label=NULL, stance_label=NULL, "
                    "action_intent_label=NULL, interpretation_short=NULL, model_version=NULL, "
                    "inference_error=NULL, inferred_at=NULL, taxonomy_version_id=NULL WHERE comment_id=:comment_id;",
                    comment,
                )
            else:
                conn.execute(
                    "UPDATE comments SET comment_text=:comment_text, text_original=:text_original, "
                    "text_display=:text_display, updated_at=:updated_at, like_count=:like_count, "
                    "reply_count=:reply_count, last_seen_at=:last_seen_at, raw_json_hash=:raw_json_hash, "
                    "raw_json=:raw_json WHERE comment_id=:comment_id;",
                    comment,
                )

def count_comments_for_video(video_id: str, database_url: str = None) -> int:
    with get_db_connection(database_url) as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM comments WHERE video_id = ?;", (video_id,)
        ).fetchone()[0]

# --- Inference column operations ---

_INFERENCE_UPDATE_SQL = (
    "UPDATE comments SET sentiment=:sentiment, sentiment_confidence=:sentiment_confidence, "
    "issue_label=:issue_label, stance_label=:stance_label, action_intent_label=:action_intent_label, "
    "interpretation_short=:interpretation_short, model_version=:model_version, "
    "inference_status=:inference_status, inference_error=:inference_error, "
    "inferred_at=:inferred_at, taxonomy_version_id=:taxonomy_version_id "
    "WHERE comment_id=:comment_id;"
)

def get_pending_comment_ids(limit: int = 500, database_url: str = None, target_video_id: str = None) -> List[str]:
    """Returns IDs needing inference, parents first."""
    with get_db_connection(database_url) as conn:
        query = (
            "SELECT comment_id FROM comments "
            "WHERE (inference_status IS NULL OR inference_status IN ('pending','failed_retryable'))"
        )
        params = []
        if target_video_id:
            query += " AND video_id = ?"
            params.append(target_video_id)
        
        query += " ORDER BY is_reply ASC, published_at ASC LIMIT ?;"
        params.append(limit)

        rows = conn.execute(query, tuple(params)).fetchall()
        return [r[0] for r in rows]

def get_all_comment_ids(database_url: str = None) -> List[str]:
    with get_db_connection(database_url) as conn:
        rows = conn.execute(
            "SELECT comment_id FROM comments ORDER BY is_reply ASC, published_at ASC;"
        ).fetchall()
        return [r[0] for r in rows]

def update_comment_inference(comment_id: str, payload: Dict[str, Any],
                             database_url: str = None) -> None:
    with get_db_connection(database_url) as conn:
        with conn:
            conn.execute(_INFERENCE_UPDATE_SQL, {**payload, "comment_id": comment_id})

def get_comments_by_ids(comment_ids: List[str],
                        database_url: str = None) -> List[Dict[str, Any]]:
    if not comment_ids:
        return []
    ph = ",".join("?" for _ in comment_ids)
    with get_db_connection(database_url) as conn:
        rows = conn.execute(
            f"SELECT * FROM comments WHERE comment_id IN ({ph});", comment_ids
        ).fetchall()
        return [dict(r) for r in rows]

def batch_update_inference(payloads: List[Dict[str, Any]],
                           database_url: str = None) -> None:
    if not payloads:
        return
    with get_db_connection(database_url) as conn:
        with conn:
            conn.executemany(_INFERENCE_UPDATE_SQL, payloads)

def mark_inference_pending_for_status_null(database_url: str = None, target_video_id: str = None) -> int:
    with get_db_connection(database_url) as conn:
        with conn:
            if target_video_id:
                return conn.execute(
                    "UPDATE comments SET inference_status='pending' WHERE inference_status IS NULL AND video_id=?;",
                    (target_video_id,)
                ).rowcount
            else:
                return conn.execute(
                    "UPDATE comments SET inference_status='pending' WHERE inference_status IS NULL;"
                ).rowcount

def inference_status_counts(database_url: str = None) -> Dict[str, int]:
    with get_db_connection(database_url) as conn:
        rows = conn.execute(
            "SELECT COALESCE(inference_status,'null') AS s, COUNT(*) FROM comments GROUP BY s;"
        ).fetchall()
        return {r[0]: r[1] for r in rows}

def column_value_counts(column: str, database_url: str = None,
                        only_completed: bool = True,
                        project_id: Optional[str] = None,
                        video_id: Optional[str] = None,
                        is_baseline: Optional[bool] = None,
                        owner_user_id: Optional[int] = None) -> Dict[str, int]:
    allowed = {"sentiment", "issue_label", "stance_label", "action_intent_label"}
    if column not in allowed:
        raise ValueError(f"column {column!r} not in allowed inference columns")
    clauses = []
    params = []
    if only_completed:
        clauses.append("inference_status = 'completed'")
    if project_id:
        clauses.append("video_id IN (SELECT video_id FROM videos WHERE project_id = ?)")
        params.append(project_id)
    if owner_user_id is not None:
        clauses.append(
            "video_id IN (SELECT v.video_id FROM videos v JOIN projects p "
            "ON p.project_id = v.project_id WHERE p.owner_user_id = ?)"
        )
        params.append(owner_user_id)
    if video_id:
        clauses.append("video_id = ?")
        params.append(video_id)
    if is_baseline is not None:
        clauses.append("is_baseline = ?")
        params.append(1 if is_baseline else 0)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_db_connection(database_url) as conn:
        rows = conn.execute(
            f"SELECT COALESCE({column},'null') AS v, COUNT(*) FROM comments {where} "
            "GROUP BY v ORDER BY COUNT(*) DESC;", params
        ).fetchall()
        return {r[0]: r[1] for r in rows}

def sample_inference_rows(limit: int = 5, database_url: str = None,
                          video_id: Optional[str] = None,
                          is_baseline: Optional[bool] = None,
                          project_id: Optional[str] = None,
                          owner_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    clauses = ["inference_status = 'completed'"]
    params = []
    if project_id:
        clauses.append("video_id IN (SELECT video_id FROM videos WHERE project_id = ?)")
        params.append(project_id)
    elif owner_user_id:
        clauses.append("video_id IN (SELECT video_id FROM videos WHERE project_id IN (SELECT project_id FROM projects WHERE owner_user_id = ?))")
        params.append(owner_user_id)
        
    if video_id:
        clauses.append("video_id = ?")
        params.append(video_id)
    if is_baseline is not None:
        clauses.append("is_baseline = ?")
        params.append(1 if is_baseline else 0)
    where = "WHERE " + " AND ".join(clauses)
    with get_db_connection(database_url) as conn:
        rows = conn.execute(
            "SELECT comment_id, video_id, is_reply, author_name, comment_text, "
            "published_at, sentiment, sentiment_confidence, issue_label, "
            "stance_label, action_intent_label, interpretation_short, inference_status "
            f"FROM comments {where} ORDER BY RANDOM() LIMIT ?;",
            (*params, limit),
        ).fetchall()
        return [dict(r) for r in rows]

# --- Crawl Runs ---

def save_crawl_run(run: Dict[str, Any], database_url: str = None) -> None:
    with get_db_connection(database_url) as conn:
        with conn:
            exists = conn.execute(
                "SELECT 1 FROM crawl_runs WHERE run_id = ?;", (run["run_id"],)
            ).fetchone()
            if exists:
                conn.execute(
                    "UPDATE crawl_runs SET finished_at=:finished_at, status=:status, "
                    "videos_checked=:videos_checked, comments_fetched=:comments_fetched, "
                    "new_comments=:new_comments, duplicate_comments=:duplicate_comments, "
                    "updated_comments=:updated_comments, replies_fetched=:replies_fetched, "
                    "api_units_used=:api_units_used, error_message=:error_message WHERE run_id=:run_id;",
                    run,
                )
            else:
                conn.execute(
                    "INSERT INTO crawl_runs ("
                    "run_id, started_at, finished_at, status, trigger_type, videos_checked, "
                    "comments_fetched, new_comments, duplicate_comments, updated_comments, "
                    "replies_fetched, api_units_used, error_message"
                    ") VALUES ("
                    ":run_id, :started_at, :finished_at, :status, :trigger_type, :videos_checked, "
                    ":comments_fetched, :new_comments, :duplicate_comments, :updated_comments, "
                    ":replies_fetched, :api_units_used, :error_message);",
                    run,
                )

# --- API Usage ---

def save_api_usage(usage: Dict[str, Any], database_url: str = None) -> None:
    with get_db_connection(database_url) as conn:
        with conn:
            conn.execute(
                "INSERT INTO api_usage (run_id, endpoint, units, called_at, status, error_message) "
                "VALUES (:run_id, :endpoint, :units, :called_at, :status, :error_message);",
                usage,
            )
