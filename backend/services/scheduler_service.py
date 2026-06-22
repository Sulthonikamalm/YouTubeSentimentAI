"""
scheduler_service.py — Background auto-scrape scheduler for YouTube Comment Crawler.
"""

import os
import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from backend.config import load_settings
from backend.crawler.crawl_runner import run_youtube_crawl

logger = logging.getLogger("youtube_collector")

CRAWL_LOCK = threading.Lock()

def start_scheduler_service(database_url: Optional[str] = None) -> threading.Thread:
    """
    Spawns a daemon thread running the auto-crawl scheduler loop.
    Checks config options at intervals and triggers execution if enabled.
    """
    def _loop():
        logger.info("Scheduler background loop started.")
        last_run_time = None
        
        while True:
            try:
                settings = load_settings()
                sched_cfg = settings.get("scheduler", {})

                auto_crawl_env = os.getenv("ENABLE_AUTO_CRAWL", "false").lower() == "true"
                auto_crawl_yaml = sched_cfg.get("enabled", False)
                enabled = auto_crawl_env or auto_crawl_yaml
                
                interval_minutes_env = os.getenv("CRAWL_INTERVAL_MINUTES")
                if interval_minutes_env:
                    try:
                        interval_minutes = int(interval_minutes_env)
                    except ValueError:
                        interval_minutes = int(sched_cfg.get("interval_minutes", 10))
                else:
                    interval_minutes = int(sched_cfg.get("interval_minutes", 10))
                
                if enabled:
                    now = datetime.now(timezone.utc)
                    should_run = False
                    if last_run_time is None:
                        should_run = True
                    else:
                        elapsed = now - last_run_time
                        if elapsed >= timedelta(minutes=interval_minutes):
                            should_run = True
                            
                    if should_run:
                        acquired = CRAWL_LOCK.acquire(blocking=False)
                        if acquired:
                            try:
                                logger.info(f"Auto-scheduler triggering comment crawl run (interval: {interval_minutes}m).")
                                last_run_time = now
                                run_youtube_crawl(trigger_type="scheduler", database_url=database_url)
                            except Exception as run_err:
                                logger.error(f"Error during auto-scheduled crawl run: {run_err}")
                            finally:
                                CRAWL_LOCK.release()
                        else:
                            logger.warning("Scheduled crawl tick skipped: another crawl session is currently running.")
                            
            except Exception as e:
                logger.error(f"Error in scheduler service loop: {e}")
                
            time.sleep(10)
            
    thread = threading.Thread(target=_loop, daemon=True, name="YouTubeSchedulerThread")
    thread.start()
    return thread

def trigger_manual_crawl(database_url: Optional[str] = None,
                         target_video_id: Optional[str] = None,
                         enable_inference: Optional[bool] = None) -> Dict[str, Any]:
    """
    Manually triggers a crawl run.

    *enable_inference*: if False, disables post-crawl inference without
    touching os.environ (thread-safe).
    """
    acquired = CRAWL_LOCK.acquire(blocking=False)
    if not acquired:
        logger.warning("Manual trigger rejected: a crawl is already running.")
        return {"status": "crawl_already_running", "error_message": "Another crawl session is currently running."}
        
    try:
        logger.info("Manual comment crawl run triggered.")
        return run_youtube_crawl(
            trigger_type="manual",
            database_url=database_url,
            target_video_id=target_video_id,
            enable_inference=enable_inference,
        )
    finally:
        CRAWL_LOCK.release()
