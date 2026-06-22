"""
routes/crawler.py — Crawler control and log routes.

Handles: /api/crawler/status, /api/crawler/run, /api/crawler/start,
/api/crawler/stop, /api/crawler/stop_inference, /api/crawler/logs.
"""

import os
import logging
from pathlib import Path
from flask import Blueprint, request

from backend.dashboard_helpers import fetch_crawler_status
from backend.routes import ok, err, get_db_url
from backend.config import load_settings, update_settings, update_env_var

logger = logging.getLogger("youtube_collector")

crawler_bp = Blueprint("crawler", __name__, url_prefix="/api")


@crawler_bp.route("/crawler/status", methods=["GET"])
def crawler_status():
    try:
        return ok(fetch_crawler_status(get_db_url()))
    except Exception as e:
        logger.error(f"Crawler status error: {e}")
        return err(str(e))


@crawler_bp.route("/crawler/run", methods=["POST"])
def crawler_run():
    from backend.services.scheduler_service import trigger_manual_crawl, CRAWL_LOCK

    db_url = get_db_url()
    mode = request.args.get("mode", "both")
    target_video_id = request.args.get("video_id")

    try:
        if mode == "inference_only":
            from backend.services.inference_service import infer_pending
            acquired = CRAWL_LOCK.acquire(blocking=False)
            if not acquired:
                return ok({"success": False, "error": "crawl_already_running"}, 409)
            try:
                summary = infer_pending(
                    limit=int(os.getenv("INFERENCE_BATCH_SIZE", "50")),
                    database_url=db_url,
                    target_video_id=target_video_id
                )
            finally:
                CRAWL_LOCK.release()
            return ok({"success": True, "status": "completed", "inference_summary": summary})

        elif mode == "crawl_only":
            result = trigger_manual_crawl(
                database_url=db_url,
                target_video_id=target_video_id,
                enable_inference=False,
            )
            if result.get("status") == "crawl_already_running":
                return ok({"success": False, "error": "crawl_already_running"}, 409)
            return ok({"success": True, "run_id": result.get("run_id"), "status": result.get("status")})

        else:  # both
            result = trigger_manual_crawl(database_url=db_url, target_video_id=target_video_id)
            if result.get("status") == "crawl_already_running":
                return ok({"success": False, "error": "crawl_already_running"}, 409)
            return ok({"success": True, "run_id": result.get("run_id"), "status": result.get("status")})

    except Exception as e:
        logger.error(f"Manual run error: {e}")
        return err(str(e))


@crawler_bp.route("/crawler/start", methods=["POST"])
def crawler_start():
    os.environ["ENABLE_AUTO_CRAWL"] = "true"
    return ok({"success": True, "scheduler_enabled": True})


@crawler_bp.route("/crawler/stop", methods=["POST"])
def crawler_stop():
    os.environ["ENABLE_AUTO_CRAWL"] = "false"
    return ok({"success": True, "scheduler_enabled": False})


@crawler_bp.route("/crawler/stop_inference", methods=["POST"])
def crawler_stop_inference():
    try:
        from backend.services.inference_service import ABORT_INFERENCE_EVENT
        ABORT_INFERENCE_EVENT.set()
        logger.info("User requested to abort inference.")
        return ok({"success": True, "message": "Inference abort requested."})
    except Exception as e:
        logger.error(f"Stop inference error: {e}")
        return err(str(e))


@crawler_bp.route("/crawler/logs", methods=["GET"])
def crawler_logs():
    limit = request.args.get("limit", 20, type=int)
    log_file = Path(__file__).resolve().parent.parent.parent / "logs" / "crawler.log"

    if not log_file.exists():
        return ok({"logs": ["[INFO] File log belum tersedia..."]})

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        tail_lines = [line.strip() for line in lines[-limit:] if line.strip()]
        return ok({"logs": tail_lines})
    except Exception as e:
        logger.error(f"Logs read error: {e}")
        return err(str(e))

@crawler_bp.route("/crawler/config", methods=["GET", "POST"])
def crawler_config():
    if request.method == "GET":
        try:
            settings = load_settings()
            api_key = os.getenv("YOUTUBE_API_KEY", "")
            masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else ("***" if api_key else "")
            
            return ok({
                "youtube_api_key": masked_key,
                "interval_minutes": settings.get("scheduler", {}).get("interval_minutes", 10),
                "max_comments": settings.get("youtube", {}).get("max_comments_per_video_per_run", 100)
            })
        except Exception as e:
            logger.error(f"Config GET error: {e}")
            return err(str(e))
            
    if request.method == "POST":
        try:
            data = request.json or {}
            
            # Update API Key if provided and not masked
            new_key = data.get("youtube_api_key")
            if new_key and not new_key.startswith("AIza") and "..." not in new_key:
                update_env_var("YOUTUBE_API_KEY", new_key.strip())
                
            # Update settings
            new_settings = {}
            if "interval_minutes" in data:
                new_settings["scheduler"] = {"interval_minutes": int(data["interval_minutes"])}
            if "max_comments" in data:
                new_settings["youtube"] = {"max_comments_per_video_per_run": int(data["max_comments"])}
                
            if new_settings:
                update_settings(new_settings)
                
            return ok({"success": True, "message": "Konfigurasi crawler berhasil disimpan."})
        except Exception as e:
            logger.error(f"Config POST error: {e}")
            return err(str(e))

