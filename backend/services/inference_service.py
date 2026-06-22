"""
inference_service.py — Orchestrates inference over comments stored in SQLite.

Three modes:
  - infer_comment(comment_id)       — single comment, opens own connection
  - infer_pending(limit=...)        — batch: 1 read + 1 write (not 3N)
  - infer_all(confirm=True)         — full re-run, same batch path

Pipeline:
  1. Prediction cache check (identical texts already analyzed)
  2. Ollama batch analysis (primary — Sahabat-AI 8B)
  3. Rule-based taxonomy fallback (if Ollama unavailable)

Failures on one comment never abort the batch.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.ml.intelligence_engine import infer_comment_intelligence
from backend.ml.ollama_service import analyze_comments_batch
from backend.storage import repository

logger = logging.getLogger("youtube_collector.inference")

ABORT_INFERENCE_EVENT = threading.Event()


def _payload_for_db(result: Dict[str, Any]) -> Dict[str, Any]:
    """Map engine output to the 11 inference columns."""
    return {
        "sentiment": result.get("sentiment"),
        "sentiment_confidence": result.get("sentiment_confidence"),
        "issue_label": result.get("issue_label"),
        "stance_label": result.get("stance_label"),
        "action_intent_label": result.get("action_intent_label"),
        "interpretation_short": result.get("interpretation_short"),
        "model_version": result.get("model_version"),
        "inference_status": result.get("inference_status"),
        "inference_error": result.get("inference_error"),
        "inferred_at": result.get("inferred_at"),
        "is_manually_corrected": result.get("is_manually_corrected", 0),
        "taxonomy_version_id": result.get("taxonomy_version_id"),
    }


def _run_fallback_engine(comment: Dict[str, Any],
                         parent_map: Dict[str, Dict]) -> Dict[str, Any]:
    """Run rule-based taxonomy fallback on a single comment. Never raises."""
    comment_id = comment["comment_id"]
    parent = None
    if comment.get("is_reply") and comment.get("parent_id"):
        parent = parent_map.get(comment["parent_id"])

    try:
        return infer_comment_intelligence(comment, parent)
    except Exception as e:
        logger.exception("Fallback engine crashed for %s", comment_id)
        return {
            "sentiment": None, "sentiment_confidence": None,
            "issue_label": None, "stance_label": None,
            "action_intent_label": None, "interpretation_short": None,
            "model_version": "rule-based-taxonomy-fallback",
            "inference_status": "failed_retryable",
            "inference_error": f"{type(e).__name__}: {e}",
            "inferred_at": None,
            "is_manually_corrected": 0,
        }


def _lookup_cache(comment_texts: List[str], database_url: Optional[str] = None,
                  project_id: Optional[str] = None,
                  taxonomy_version_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Looks up completed predictions for identical comment texts.

    Only returns auto-generated predictions (is_manually_corrected = 0).
    Human corrections are comment-specific and must NOT leak to other
    comments that happen to share the same text.

    When *project_id* is given the cache is scoped to comments belonging to
    videos inside that project.  This prevents label contamination across
    projects that use different custom label sets.
    """
    cache = {}
    valid_texts = [t for t in comment_texts if t and t.strip()]
    if not valid_texts:
        return cache

    try:
        from backend.storage.db import get_db_connection
        for i in range(0, len(valid_texts), 100):
            chunk = valid_texts[i:i+100]
            ph = ",".join("?" for _ in chunk)
            # Build optional project scope filter
            project_clause = ""
            params = list(chunk)
            if project_id:
                project_clause += (
                    "AND video_id IN "
                    "(SELECT video_id FROM videos WHERE project_id = ?) "
                )
                params.append(project_id)
            if taxonomy_version_id:
                project_clause += " AND taxonomy_version_id = ? "
                params.append(taxonomy_version_id)
            else:
                project_clause += " AND taxonomy_version_id IS NULL "
            with get_db_connection(database_url) as conn:
                rows = conn.execute(
                    f"SELECT comment_text, sentiment, sentiment_confidence, issue_label, "
                    f"stance_label, action_intent_label, interpretation_short, model_version, taxonomy_version_id "
                    f"FROM comments WHERE comment_text IN ({ph}) "
                    f"AND inference_status = 'completed' "
                    f"AND is_manually_corrected = 0 "
                    f"{project_clause}"
                    f"ORDER BY inferred_at DESC;",
                    params
                ).fetchall()
                for r in rows:
                    if r["comment_text"] not in cache:
                        cache[r["comment_text"]] = dict(r)
    except Exception as e:
        logger.warning(f"Prediction cache lookup failed: {e}")
    return cache


def _batch_run(comment_ids: List[str],
               database_url: Optional[str] = None) -> Dict[str, int]:
    """
    Batch inference with INCREMENTAL saves — writes to DB after each Ollama
    chunk so the dashboard updates in real-time.
    """
    ABORT_INFERENCE_EVENT.clear()
    summary = {"processed": 0, "completed": 0, "failed": 0,
               "model_unavailable": 0, "skipped": 0}

    if not comment_ids:
        return summary

    # --- 1. Batch read: load all target comments + potential parents ---
    comments = repository.get_comments_by_ids(comment_ids, database_url)
    comment_map = {c["comment_id"]: c for c in comments}

    parent_ids = {
        c["parent_id"] for c in comments
        if c.get("is_reply") and c.get("parent_id")
    }
    parent_ids -= set(comment_ids)

    parent_map: Dict[str, Dict] = {}
    if parent_ids:
        parents = repository.get_comments_by_ids(list(parent_ids), database_url)
        parent_map = {p["comment_id"]: p for p in parents}

    # --- 2. Caching: check DB for identical texts already completed ---
    # Determine the project for cache scoping. All comments in one batch
    # typically belong to the same project, but we take the first video's
    # project_id as a conservative scope key.
    video_ids_for_proj = list({c["video_id"] for c in comments if c.get("video_id")})
    _proj_map = repository.get_projects_for_videos(video_ids_for_proj, database_url) if video_ids_for_proj else {}
    _first_proj = next(iter(_proj_map.values()), None) if _proj_map else None
    _cache_project_id = _first_proj["project_id"] if _first_proj else None
    _cache_tax_version_id = _first_proj.get("active_taxonomy_version_id") if _first_proj else None

    comment_texts = [c["comment_text"] for c in comments if c.get("comment_text")]
    cache = _lookup_cache(comment_texts, database_url, project_id=_cache_project_id, taxonomy_version_id=_cache_tax_version_id)

    # Save cached results immediately
    cached_payloads: List[Dict[str, Any]] = []
    to_ollama: List[Dict[str, Any]] = []

    for c in comments:
        cid = c["comment_id"]
        txt = c.get("comment_text")
        if txt in cache:
            cached = cache[txt]
            result = {
                "sentiment": cached["sentiment"],
                "sentiment_confidence": cached["sentiment_confidence"],
                "issue_label": cached["issue_label"],
                "stance_label": cached["stance_label"],
                "action_intent_label": cached["action_intent_label"],
                "interpretation_short": cached["interpretation_short"],
                "model_version": f"{cached['model_version']}-cached",
                "inference_status": "completed",
                "inference_error": None,
                "inferred_at": datetime.now(timezone.utc).isoformat(),
                "is_manually_corrected": 0,
                "taxonomy_version_id": cached.get("taxonomy_version_id")
            }
            cached_payloads.append({"comment_id": cid, **_payload_for_db(result)})
            summary["processed"] += 1
            summary["completed"] += 1
        else:
            to_ollama.append(c)

    # Write cached results to DB immediately
    if cached_payloads:
        repository.batch_update_inference(cached_payloads, database_url)
        logger.info(f"Saved {len(cached_payloads)} cached results to DB immediately.")

    # --- 3. Process remaining via Ollama in chunks — SAVE AFTER EACH CHUNK ---
    if to_ollama:
        from collections import defaultdict
        video_ids = list({c["video_id"] for c in to_ollama if c.get("video_id")})
        video_projects = repository.get_projects_for_videos(video_ids, database_url)
        
        project_groups = defaultdict(list)
        for c in to_ollama:
            vid = c.get("video_id")
            proj = video_projects.get(vid)
            proj_id = proj["project_id"] if proj else "unknown"
            project_groups[proj_id].append((c, proj))

        for proj_id, items in project_groups.items():
            if ABORT_INFERENCE_EVENT.is_set():
                break
                
            project_data = items[0][1]
            ollama_batch_data = []
            for c, _ in items:
                parent_text = None
                if c.get("is_reply") and c.get("parent_id"):
                    parent = parent_map.get(c["parent_id"])
                    if parent:
                        parent_text = parent.get("comment_text")
                ollama_batch_data.append({
                    "comment_id": c["comment_id"],
                    "comment_text": c["comment_text"],
                    "parent_text": parent_text
                })

            chunk_size = 3
            total_chunks = (len(ollama_batch_data) + chunk_size - 1) // chunk_size

            for chunk_idx, i in enumerate(range(0, len(ollama_batch_data), chunk_size)):
                if ABORT_INFERENCE_EVENT.is_set():
                    logger.info("Inference aborted by user request.")
                    break
                chunk = ollama_batch_data[i:i+chunk_size]
                chunk_cids = [item["comment_id"] for item in chunk]
                logger.info(
                    f"[Project: {proj_id}] Ollama chunk {chunk_idx+1}/{total_chunks}: "
                    f"processing {len(chunk)} comments..."
                )

                # Try Ollama
                chunk_results = {}
                try:
                    chunk_results = analyze_comments_batch(chunk, project_data)
                except Exception as e:
                    logger.error(f"Ollama chunk {chunk_idx+1} crashed: {e}")

                # Build payloads for this chunk (Ollama result or fallback)
                chunk_payloads: List[Dict[str, Any]] = []
                for cid in chunk_cids:
                    comment = comment_map.get(cid)
                    if not comment:
                        summary["processed"] += 1
                        summary["failed"] += 1
                        continue

                    summary["processed"] += 1

                    if cid in chunk_results:
                        result = chunk_results[cid]
                    else:
                        # Fallback to rule-based taxonomy
                        result = _run_fallback_engine(comment, parent_map)
                        result["taxonomy_version_id"] = project_data.get("active_taxonomy_version_id") if project_data else None

                    status = result.get("inference_status")
                    if status == "completed":
                        summary["completed"] += 1
                    elif status == "model_unavailable":
                        summary["model_unavailable"] += 1
                    else:
                        summary["failed"] += 1

                    chunk_payloads.append({"comment_id": cid, **_payload_for_db(result)})

                # SAVE THIS CHUNK TO DB IMMEDIATELY
                if chunk_payloads:
                    repository.batch_update_inference(chunk_payloads, database_url)
                    logger.info(
                        f"✅ Chunk {chunk_idx+1}/{total_chunks} saved to DB: "
                        f"{len(chunk_payloads)} comments "
                        f"(total progress: {summary['completed']}/{summary['processed']})"
                    )

    # Handle comment_ids that weren't in the DB at all
    processed_ids = {c["comment_id"] for c in comments}
    for cid in comment_ids:
        if cid not in processed_ids:
            summary["processed"] += 1
            summary["failed"] += 1

    return summary


def infer_comment(comment_id: str,
                  database_url: Optional[str] = None) -> Dict[str, Any]:
    """Runs inference on a single comment_id (with cache, Ollama and rule fallbacks)."""
    comment = repository.get_comment(comment_id, database_url)
    if not comment:
        return {
            "sentiment": None, "sentiment_confidence": None,
            "issue_label": None, "stance_label": None,
            "action_intent_label": None, "interpretation_short": None,
            "model_version": "unavailable",
            "inference_status": "failed",
            "inference_error": f"comment_id {comment_id!r} not found",
            "inferred_at": None,
            "is_manually_corrected": 0,
        }

    summary = _batch_run([comment_id], database_url)

    if summary.get("processed", 0) > 0:
        updated = repository.get_comment(comment_id, database_url)
        if updated:
            return updated

    return comment


def infer_pending(limit: int = 50,
                  database_url: Optional[str] = None,
                  target_video_id: Optional[str] = None) -> Dict[str, int]:
    """Processes pending comments in batch. Default limit=50 for CPU Ollama."""
    repository.mark_inference_pending_for_status_null(database_url, target_video_id)
    ids = repository.get_pending_comment_ids(limit, database_url, target_video_id)
    logger.info(f"infer_pending: found {len(ids)} pending comments (limit={limit})")
    summary = _batch_run(ids, database_url)
    logger.info("infer_pending summary: %s", summary)
    return summary


def infer_all(confirm: bool = False,
              database_url: Optional[str] = None) -> Dict[str, int]:
    """Re-runs inference over every comment. Requires confirm=True."""
    if not confirm:
        return {
            "processed": 0, "completed": 0, "failed": 0, "skipped": 0,
            "model_unavailable": 0,
            "note": "infer_all aborted: confirm=False",
        }

    ids = repository.get_all_comment_ids(database_url)
    summary = _batch_run(ids, database_url)
    logger.info("infer_all summary: %s", summary)
    return summary
