"""
dashboard_helpers.py — Business logic helpers for dashboard API routes.

Extracted from dashboard_routes.py to keep route files thin and maintainable.
All heavy DB queries and data transformations live here.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from backend.storage.db import get_db_connection
from backend.storage.repository import column_value_counts


def _row_to_dict(row):
    """Convert sqlite3.Row to plain dict."""
    return dict(row) if row else None


def _rows_to_list(rows):
    return [dict(r) for r in rows]


def fetch_summary(db_url: str, project_id: Optional[str] = None, video_id: Optional[str] = None, is_baseline: Optional[bool] = None, owner_user_id: Optional[int] = None) -> Dict[str, Any]:
    """Aggregated KPI summary for the dashboard."""
    where_clauses = []
    params = []
    if project_id:
        where_clauses.append("video_id IN (SELECT video_id FROM videos WHERE project_id = ?)")
        params.append(project_id)
    elif owner_user_id:
        where_clauses.append("video_id IN (SELECT video_id FROM videos WHERE project_id IN (SELECT project_id FROM projects WHERE owner_user_id = ?))")
        params.append(owner_user_id)
        
    if video_id:
        where_clauses.append("video_id = ?")
        params.append(video_id)
    if is_baseline is not None:
        where_clauses.append("is_baseline = ?")
        params.append(1 if is_baseline else 0)
    
    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    with get_db_connection(db_url) as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM comments {where};", params).fetchone()[0]
        
        cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        where_24h_clauses = list(where_clauses)
        params_24h = list(params)
        where_24h_clauses.append("collected_at >= ?")
        params_24h.append(cutoff_24h)
        where_24h = "WHERE " + " AND ".join(where_24h_clauses)
        
        new_24h = conn.execute(
            f"SELECT COUNT(*) FROM comments {where_24h};", params_24h
        ).fetchone()[0]
        
        vid_where = ""
        vid_params = []
        if project_id:
            vid_where = "WHERE project_id = ?"
            vid_params = [project_id]
        elif owner_user_id:
            vid_where = "WHERE project_id IN (SELECT project_id FROM projects WHERE owner_user_id = ?)"
            vid_params = [owner_user_id]
            
        video_count = conn.execute(f"SELECT COUNT(*) FROM videos {vid_where};", vid_params).fetchone()[0]
        
        vid_active_where = "WHERE monitoring_enabled = 1"
        if project_id: 
            vid_active_where += " AND project_id = ?"
        elif owner_user_id:
            vid_active_where += " AND project_id IN (SELECT project_id FROM projects WHERE owner_user_id = ?)"
        active_video_count = conn.execute(
            f"SELECT COUNT(*) FROM videos {vid_active_where};", vid_params
        ).fetchone()[0]
        
        # completed status counts
        where_completed_clauses = list(where_clauses)
        params_completed = list(params)
        where_completed_clauses.append("inference_status = 'completed'")
        where_completed = "WHERE " + " AND ".join(where_completed_clauses)
        completed_rows = conn.execute(
            f"SELECT COALESCE(inference_status,'null') AS s, COUNT(*) FROM comments {where_completed} GROUP BY s;",
            params_completed
        ).fetchall()
        completed_counts = {r[0]: r[1] for r in completed_rows}
        completed = completed_counts.get("completed", 0)
        
        # total inference counts per status
        all_status_rows = conn.execute(
            f"SELECT COALESCE(inference_status,'null') AS s, COUNT(*) FROM comments {where} GROUP BY s;",
            params
        ).fetchall()
        inf_counts = {r[0]: r[1] for r in all_status_rows}
        
        usage_row = conn.execute(
            "SELECT COALESCE(SUM(units), 0) AS total_units FROM api_usage;"
        ).fetchone()
        total_units = usage_row[0] if usage_row else 0
        
        last_run = conn.execute(
            "SELECT run_id, started_at, finished_at, status, trigger_type, "
            "new_comments, comments_fetched "
            "FROM crawl_runs ORDER BY started_at DESC LIMIT 1;"
        ).fetchone()
        
        per_video = conn.execute(
            "SELECT video_id, COUNT(*) AS cnt FROM comments "
            f"{where_24h} GROUP BY video_id;", params_24h
        ).fetchall()

    return {
        "total_comments": total,
        "new_comments_24h": new_24h,
        "videos_monitored": video_count,
        "active_videos": active_video_count,
        "inference_completed": completed,
        "inference_total": total,
        "api_units_used": total_units,
        "last_run": _row_to_dict(last_run),
        "new_comments_per_video": _rows_to_list(per_video),
        "inference_status_counts": inf_counts,
    }


def fetch_distributions(db_url: str, project_id: Optional[str] = None, video_id: Optional[str] = None, is_baseline: Optional[bool] = None, owner_user_id: Optional[int] = None) -> Dict[str, Dict[str, int]]:
    """Sentiment, issue, stance, action_intent distributions."""
    return {
        "sentiment": column_value_counts("sentiment", db_url, only_completed=True, project_id=project_id, video_id=video_id, is_baseline=is_baseline, owner_user_id=owner_user_id),
        "issue": column_value_counts("issue_label", db_url, only_completed=True, project_id=project_id, video_id=video_id, is_baseline=is_baseline, owner_user_id=owner_user_id),
        "stance": column_value_counts("stance_label", db_url, only_completed=True, project_id=project_id, video_id=video_id, is_baseline=is_baseline, owner_user_id=owner_user_id),
        "action_intent": column_value_counts("action_intent_label", db_url, only_completed=True, project_id=project_id, video_id=video_id, is_baseline=is_baseline, owner_user_id=owner_user_id),
    }


def fetch_timeline(db_url: str, days: int = 30, project_id: Optional[str] = None, video_id: Optional[str] = None, is_baseline: Optional[bool] = None, owner_user_id: Optional[int] = None) -> Dict[str, Any]:
    """Comment count grouped by day for trend chart."""
    clauses = []
    params = []
    if days > 0:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        clauses.append("collected_at >= ?")
        params.append(cutoff)
    else:
        clauses.append("collected_at IS NOT NULL")
        
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

    with get_db_connection(db_url) as conn:
        rows = conn.execute(
            "SELECT DATE(collected_at) AS day, COUNT(*) AS count "
            f"FROM comments {where} "
            "GROUP BY DATE(collected_at) ORDER BY day;", params
        ).fetchall()
        
        sent_clauses = list(clauses)
        sent_clauses.append("inference_status = 'completed'")
        sent_where = "WHERE " + " AND ".join(sent_clauses)
        sent_rows = conn.execute(
            "SELECT DATE(collected_at) AS day, sentiment, COUNT(*) AS count "
            f"FROM comments {sent_where} "
            "GROUP BY DATE(collected_at), sentiment ORDER BY day;", params
        ).fetchall()

    sentiment_by_day: Dict[str, Dict[str, int]] = {}
    for r in sent_rows:
        d = r["day"]
        s = r["sentiment"] or "unknown"
        sentiment_by_day.setdefault(d, {})[s] = r["count"]

    return {"timeline": _rows_to_list(rows), "sentiment_by_day": sentiment_by_day}


def fetch_interpretation(db_url: str, project_id: Optional[str] = None, video_id: Optional[str] = None, is_baseline: Optional[bool] = None, owner_user_id: Optional[int] = None) -> Dict[str, Any]:
    """Generate dashboard interpretation / insight panel data."""
    clauses = []
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
        
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    with get_db_connection(db_url) as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM comments {where};", params).fetchone()[0]
        
        completed_clauses = list(clauses)
        completed_clauses.append("inference_status = 'completed'")
        completed_where = "WHERE " + " AND ".join(completed_clauses)
        completed = conn.execute(
            f"SELECT COUNT(*) FROM comments {completed_where};", params
        ).fetchone()[0]

        if completed == 0:
            return {"has_data": False, "message": "Belum ada cukup data untuk membuat insight."}

        sent = column_value_counts("sentiment", db_url, only_completed=True, project_id=project_id, video_id=video_id, is_baseline=is_baseline, owner_user_id=owner_user_id)
        total_sent = sum(sent.values())
        dominant_sentiment = max(sent, key=sent.get) if sent else "unknown"
        dominant_pct = (sent.get(dominant_sentiment, 0) / total_sent * 100) if total_sent else 0

        issues = column_value_counts("issue_label", db_url, only_completed=True, project_id=project_id, video_id=video_id, is_baseline=is_baseline, owner_user_id=owner_user_id)
        dominant_issue = max(issues, key=issues.get) if issues else "unknown"

        stances = column_value_counts("stance_label", db_url, only_completed=True, project_id=project_id, video_id=video_id, is_baseline=is_baseline, owner_user_id=owner_user_id)
        dominant_stance = max(stances, key=stances.get) if stances else "unknown"

        actions = column_value_counts("action_intent_label", db_url, only_completed=True, project_id=project_id, video_id=video_id, is_baseline=is_baseline, owner_user_id=owner_user_id)
        dominant_action = max(actions, key=actions.get) if actions else "unknown"

        recent_clauses = list(clauses)
        cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        recent_clauses.append("collected_at >= ?")
        recent_clauses.append("inference_status = 'completed'")
        recent_where = "WHERE " + " AND ".join(recent_clauses)
        recent_sent = conn.execute(
            "SELECT sentiment, COUNT(*) AS cnt FROM comments "
            f"{recent_where} GROUP BY sentiment;", (*params, cutoff_24h)
        ).fetchall()
        recent_sent_dict = {r["sentiment"]: r["cnt"] for r in recent_sent}

    warnings = []
    neg_pct = (sent.get("negative", 0) / total_sent * 100) if total_sent else 0
    if neg_pct > 40:
        warnings.append(f"Sentimen negatif mendominasi {neg_pct:.1f}% komentar yang telah dianalisis.")
    if recent_sent_dict.get("negative", 0) > recent_sent_dict.get("positive", 0):
        warnings.append("Komentar negatif lebih banyak dari positif dalam 24 jam terakhir.")

    recommendations = []
    if dominant_sentiment == "negative":
        recommendations.append("Siapkan klarifikasi ringkas terkait isu yang paling sering dikritik.")
        recommendations.append("Pantau respons komentar setelah komunikasi dilakukan.")
    elif dominant_sentiment == "positive":
        recommendations.append("Pertahankan narasi positif dan perkuat pesan yang mendapat respons baik.")
    else:
        recommendations.append("Lanjutkan monitoring untuk memahami tren opini yang berkembang.")

    return {
        "has_data": True,
        "total_analyzed": completed,
        "total_comments": total,
        "dominant_sentiment": {
            "label": dominant_sentiment,
            "percentage": round(dominant_pct, 1),
            "count": sent.get(dominant_sentiment, 0),
        },
        "sentiment_distribution": sent,
        "dominant_issue": dominant_issue,
        "issue_distribution": issues,
        "dominant_stance": dominant_stance,
        "stance_distribution": stances,
        "dominant_action": dominant_action,
        "action_distribution": actions,
        "warnings": warnings,
        "recommendations": recommendations,
        "disclaimer": "Interpretasi hanya berlaku untuk komentar video yang dipantau.",
    }


def fetch_realtime_metrics(db_url: str, minutes: int = 30,
                           owner_user_id: Optional[int] = None) -> Dict[str, Any]:
    """Per-minute counts of newly ingested vs newly inferred comments.

    Returns a continuous series (one bucket per minute, zero-filled) for the last
    `minutes` minutes so the frontend line chart moves smoothly even when some
    minutes have no activity. Times are stored as UTC ISO strings; labels are
    formatted in the server's local timezone for display.
    """
    if minutes < 1:
        minutes = 1

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = now - timedelta(minutes=minutes - 1)
    cutoff_iso = start.isoformat()

    # strftime parses the stored ISO8601 (with 'T' and +00:00 offset) and emits
    # a UTC bucket key 'YYYY-MM-DDTHH:MM' that we match against Python keys below.
    scope = ""
    params = [cutoff_iso]
    if owner_user_id is not None:
        scope = (
            " AND video_id IN (SELECT v.video_id FROM videos v JOIN projects p "
            "ON p.project_id = v.project_id WHERE p.owner_user_id = ?)"
        )
        params.append(owner_user_id)

    with get_db_connection(db_url) as conn:
        ingested_rows = conn.execute(
            "SELECT strftime('%Y-%m-%dT%H:%M', collected_at) AS bucket, COUNT(*) AS cnt "
            f"FROM comments WHERE collected_at >= ?{scope} GROUP BY bucket;",
            params,
        ).fetchall()
        inferred_rows = conn.execute(
            "SELECT strftime('%Y-%m-%dT%H:%M', inferred_at) AS bucket, COUNT(*) AS cnt "
            f"FROM comments WHERE inferred_at >= ? AND inference_status = 'completed'{scope} "
            "GROUP BY bucket;",
            params,
        ).fetchall()

    ingested_map = {r["bucket"]: r["cnt"] for r in ingested_rows}
    inferred_map = {r["bucket"]: r["cnt"] for r in inferred_rows}

    labels: List[str] = []
    ingested: List[int] = []
    inferred: List[int] = []
    cur = start
    for _ in range(minutes):
        key = cur.strftime("%Y-%m-%dT%H:%M")
        labels.append(cur.astimezone().strftime("%H:%M"))
        ingested.append(ingested_map.get(key, 0))
        inferred.append(inferred_map.get(key, 0))
        cur += timedelta(minutes=1)

    total_ingested = sum(ingested)
    total_inferred = sum(inferred)

    return {
        "labels": labels,
        "datasets": {"ingested": ingested, "inferred": inferred},
        "summary": {
            "ingested_this_minute": ingested[-1] if ingested else 0,
            "inferred_this_minute": inferred[-1] if inferred else 0,
            "total_ingested": total_ingested,
            "total_inferred": total_inferred,
            # Average AI throughput across the window (comments analyzed / minute).
            "avg_inference_rate": round(total_inferred / minutes, 1),
        },
        "window_minutes": minutes,
    }


def fetch_crawler_status(db_url: str) -> Dict[str, Any]:
    """Current crawler status and recent runs."""
    from backend.services.scheduler_service import CRAWL_LOCK

    is_running = not CRAWL_LOCK.acquire(blocking=False)
    if not is_running:
        CRAWL_LOCK.release()

    with get_db_connection(db_url) as conn:
        runs = conn.execute(
            "SELECT run_id, started_at, finished_at, status, trigger_type, "
            "videos_checked, comments_fetched, new_comments, duplicate_comments, "
            "replies_fetched, api_units_used, error_message "
            "FROM crawl_runs ORDER BY started_at DESC LIMIT 10;"
        ).fetchall()
        cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        stats_24h = conn.execute(
            "SELECT COUNT(*) AS total_runs, "
            "COALESCE(SUM(new_comments), 0) AS total_new, "
            "COALESCE(SUM(duplicate_comments), 0) AS total_dup, "
            "COALESCE(SUM(replies_fetched), 0) AS total_replies, "
            "COALESCE(SUM(api_units_used), 0) AS total_units "
            "FROM crawl_runs WHERE started_at >= ?;", (cutoff_24h,)
        ).fetchone()

    return {
        "is_running": is_running,
        "recent_runs": _rows_to_list(runs),
        "stats_24h": _row_to_dict(stats_24h),
    }
