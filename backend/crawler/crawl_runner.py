"""
crawl_runner.py — Coordinates the incremental crawling flow for YouTube comments.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from backend.config import load_settings
from backend.youtube.youtube_client import (
    YouTubeClient,
    QuotaExceededError,
    CommentsDisabledError,
    VideoNotFoundError,
    InvalidApiKeyError,
)
from backend.youtube.comment_normalizer import normalize_comment
from backend.crawler.quota_tracker import QuotaTracker
from backend.crawler.dedup import Deduplicator
from backend.crawler.video_registry import get_monitored_videos
from backend.storage import repository

logger = logging.getLogger("youtube_collector")


def _run_post_crawl_inference(database_url: Optional[str] = None,
                              enable_inference: Optional[bool] = None) -> None:
    """Run inference on pending comments after crawl. Never crashes the crawler.

    *enable_inference* overrides the environment variable when explicitly set by
    the caller, avoiding the thread-unsafe pattern of mutating os.environ.
    """
    if enable_inference is not None:
        should_run = enable_inference
    else:
        should_run = os.getenv("ENABLE_INFERENCE_AFTER_CRAWL", "true").lower() in ("true", "1", "yes")

    if not should_run:
        logger.info("Post-crawl inference disabled.")
        return
    try:
        from backend.services.inference_service import infer_pending
        summary = infer_pending(
            limit=int(os.getenv("INFERENCE_BATCH_SIZE", "500")),
            database_url=database_url,
        )
        logger.info("Post-crawl inference summary: %s", summary)
    except Exception as e:
        logger.warning("Post-crawl inference skipped: %s", e)


def _persist_reply(rep_item, video_id, parent_id, run_stats, deduplicator,
                   database_url, first_crawl_done, started_at):
    """Normalize + dedup + persist one reply. Shared by both reply paths."""
    rep_normalized = normalize_comment(rep_item, video_id, parent_id=parent_id)
    rep_normalized["collected_at"] = started_at
    rep_normalized["last_seen_at"] = started_at
    rep_normalized["is_baseline"] = not first_crawl_done

    run_stats["comments_fetched"] += 1
    rep_existing = deduplicator.check(rep_normalized["comment_id"])
    if rep_existing is not None:
        run_stats["duplicate_comments"] += 1
        if rep_normalized["updated_at"] != rep_existing["updated_at"]:
            repository.update_comment(rep_normalized, database_url)
            run_stats["updated_comments"] += 1
    else:
        repository.save_comment(rep_normalized, database_url)
        run_stats["new_comments"] += 1
        run_stats["replies_fetched"] += 1


def run_youtube_crawl(trigger_type: str = "manual", database_url: Optional[str] = None,
                      target_video_id: Optional[str] = None,
                      enable_inference: Optional[bool] = None) -> Dict[str, Any]:
    """
    Executes a YouTube comments crawl run.
    Fetches comments incrementally, updates records, tracks quotas, and handles errors.

    *enable_inference*: explicitly controls post-crawl inference.  When None,
    the decision falls through to _run_post_crawl_inference which reads the
    ENABLE_INFERENCE_AFTER_CRAWL env var.  Passing False here avoids the
    thread-unsafe pattern of mutating os.environ from a request handler.
    """
    now_utc = datetime.now(timezone.utc)
    run_id = f"run_{now_utc.strftime('%Y%m%d_%H%M%S')}_{now_utc.microsecond // 1000:03d}"
    started_at = now_utc.isoformat()
    
    run_stats = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": None,
        "status": "running",
        "trigger_type": trigger_type,
        "videos_checked": 0,
        "comments_fetched": 0,
        "new_comments": 0,
        "duplicate_comments": 0,
        "updated_comments": 0,
        "replies_fetched": 0,
        "api_units_used": 0,
        "error_message": None
    }
    
    logger.info(f"Crawl session {run_id} started. Trigger: {trigger_type}")
    
    try:
        repository.save_crawl_run(run_stats, database_url)
    except Exception as e:
        logger.error(f"Failed to record initial crawl run in DB: {e}")
        
    try:
        settings = load_settings()
    except Exception as e:
        err_msg = f"Failed to load settings configuration: {e}"
        logger.error(err_msg)
        run_stats["status"] = "failed"
        run_stats["finished_at"] = datetime.now(timezone.utc).isoformat()
        run_stats["error_message"] = err_msg
        repository.save_crawl_run(run_stats, database_url)
        return run_stats

    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key or api_key.strip() == "" or api_key.strip() == "your_api_key_here":
        err_msg = "YouTube API key is missing. Check your .env file."
        logger.error(err_msg)
        run_stats["status"] = "failed"
        run_stats["finished_at"] = datetime.now(timezone.utc).isoformat()
        run_stats["error_message"] = err_msg
        repository.save_crawl_run(run_stats, database_url)
        return run_stats

    yt_conf = settings.get("youtube", {})
    order = yt_conf.get("order", "time")
    text_format = yt_conf.get("text_format", "plainText")
    max_comments_per_video = yt_conf.get("max_comments_per_video_per_run", 100)
    fetch_replies_enabled = yt_conf.get("fetch_replies", True)
    max_replies_per_comment = yt_conf.get("max_replies_per_comment", 100)
    timeout_seconds = yt_conf.get("request_timeout_seconds", 20)
    
    quota_conf = settings.get("quota", {})
    daily_limit = quota_conf.get("daily_limit", 10000)
    warning_threshold = quota_conf.get("warning_threshold", 8000)
    
    consecutive_dup_threshold = settings.get("crawler", {}).get("consecutive_dup_threshold", 30)

    try:
        client = YouTubeClient(api_key=api_key, timeout_seconds=timeout_seconds)
    except Exception as e:
        err_msg = f"Failed to initialize YouTube Client: {e}"
        logger.error(err_msg)
        run_stats["status"] = "failed"
        run_stats["finished_at"] = datetime.now(timezone.utc).isoformat()
        run_stats["error_message"] = err_msg
        repository.save_crawl_run(run_stats, database_url)
        return run_stats

    tracker = QuotaTracker(
        daily_limit=daily_limit,
        warning_threshold=warning_threshold,
        database_url=database_url
    )
    
    deduplicator = Deduplicator(
        threshold=consecutive_dup_threshold,
        database_url=database_url
    )
    
    active_videos = []
    try:
        active_videos = get_monitored_videos(database_url)
    except Exception as e:
        logger.error(f"Failed to fetch active monitored videos list: {e}")

    logger.info(f"Loaded {len(active_videos)} monitored video feeds.")
    
    if target_video_id:
        active_videos = [v for v in active_videos if v["video_id"] == target_video_id]
        logger.info(f"Filtered to 1 specific video: {target_video_id} based on user request.")

    quota_exceeded = False
    
    for video in active_videos:
        if tracker.is_limit_exceeded():
            logger.warning("Session reached strict YouTube API quota limit. Halting run.")
            quota_exceeded = True
            break
            
        video_id = video["video_id"]
        first_crawl_done = bool(video["first_crawl_done"])

        logger.info(f"Processing Video ID: {video_id} (Baseline done: {first_crawl_done})")
        run_stats["videos_checked"] += 1
        
        if not video["video_title"] or not video["channel_title"]:
            try:
                meta = client.fetch_video_metadata(video_id)
                tracker.track_call(run_id, "videos.list", 1, 200)
                repository.update_video_metadata(
                    video_id=video_id,
                    video_title=meta["video_title"],
                    channel_title=meta["channel_title"],
                    first_seen_at=started_at,
                    database_url=database_url
                )
                video["video_title"] = meta["video_title"]
                video["channel_title"] = meta["channel_title"]
            except VideoNotFoundError:
                logger.warning(f"Video {video_id} not found on YouTube. Skipping.")
                tracker.track_call(run_id, "videos.list", 1, 404, "videoNotFound")
                continue
            except QuotaExceededError:
                tracker.track_call(run_id, "videos.list", 1, 403, "quotaExceeded")
                quota_exceeded = True
                break
            except InvalidApiKeyError:
                tracker.track_call(run_id, "videos.list", 1, 400, "invalidApiKey")
                run_stats["status"] = "failed"
                run_stats["error_message"] = "Invalid YouTube API key."
                break
            except Exception as e:
                err_lbl = client.normalize_error(e)
                tracker.track_call(run_id, "videos.list", 1, 500, err_lbl)
                logger.error(f"Error fetching metadata for {video_id}: {e}")
                continue

        page_token = None
        video_comments_collected = 0
        deduplicator.reset()
        video_last_seen_comment_at = None
        early_stop_triggered = False
        
        while video_comments_collected < max_comments_per_video:
            if tracker.is_limit_exceeded():
                quota_exceeded = True
                break
                
            try:
                threads_resp = client.fetch_comment_threads(
                    video_id=video_id,
                    page_token=page_token,
                    max_results=min(100, max_comments_per_video - video_comments_collected),
                    order=order,
                    text_format=text_format
                )
                tracker.track_call(run_id, "commentThreads.list", 1, 200)
            except CommentsDisabledError:
                tracker.track_call(run_id, "commentThreads.list", 1, 403, "commentsDisabled")
                logger.warning(f"Comments are disabled for video {video_id}. Skipping.")
                break
            except VideoNotFoundError:
                tracker.track_call(run_id, "commentThreads.list", 1, 404, "videoNotFound")
                logger.warning(f"Video {video_id} not found. Skipping.")
                break
            except QuotaExceededError:
                tracker.track_call(run_id, "commentThreads.list", 1, 403, "quotaExceeded")
                quota_exceeded = True
                break
            except InvalidApiKeyError:
                tracker.track_call(run_id, "commentThreads.list", 1, 400, "invalidApiKey")
                run_stats["status"] = "failed"
                run_stats["error_message"] = "Invalid YouTube API key."
                break
            except Exception as e:
                err_lbl = client.normalize_error(e)
                tracker.track_call(run_id, "commentThreads.list", 1, 500, err_lbl)
                logger.error(f"Error fetching comment threads for video {video_id}: {e}")
                break

            items = threads_resp.get("items", [])
            if not items:
                logger.info(f"No more comment threads available for {video_id}.")
                break
                
            early_stop_triggered = False
            
            for item in items:
                normalized = normalize_comment(item, video_id)
                normalized["collected_at"] = started_at
                normalized["last_seen_at"] = started_at
                normalized["is_baseline"] = not first_crawl_done
                
                comment_id = normalized["comment_id"]
                run_stats["comments_fetched"] += 1
                video_comments_collected += 1
                
                pub_at = normalized["published_at"]
                if not video_last_seen_comment_at or pub_at > video_last_seen_comment_at:
                    video_last_seen_comment_at = pub_at

                existing_comment = deduplicator.check(comment_id)
                if existing_comment is not None:
                    run_stats["duplicate_comments"] += 1
                    deduplicator.record_occurrence(True)
                    if normalized["updated_at"] != existing_comment["updated_at"]:
                        repository.update_comment(normalized, database_url)
                        run_stats["updated_comments"] += 1
                        logger.info(f"Comment {comment_id} was updated. Saving new version.")
                else:
                    repository.save_comment(normalized, database_url)
                    run_stats["new_comments"] += 1
                    deduplicator.record_occurrence(False)

                total_replies = normalized["reply_count"]
                inline_replies = (
                    ((item.get("snippet") or {}).get("replies") or {}).get("comments") or []
                )
                # Fast-path: commentThreads.list already ships up to 5 replies inline
                # (part=snippet,replies). When those inline replies are the COMPLETE set
                # and within the per-comment cap, persist them directly and SKIP the extra
                # comments.list API call — the saved reply set is identical, one fewer call.
                inline_handled = False
                if (fetch_replies_enabled and total_replies > 0
                        and len(inline_replies) >= total_replies
                        and total_replies <= max_replies_per_comment):
                    for rep_item in inline_replies:
                        _persist_reply(rep_item, video_id, comment_id, run_stats,
                                       deduplicator, database_url, first_crawl_done, started_at)
                    inline_handled = True

                if fetch_replies_enabled and total_replies > 0 and not inline_handled:
                    reply_page_token = None
                    replies_collected = 0
                    
                    while replies_collected < max_replies_per_comment:
                        if tracker.is_limit_exceeded():
                            quota_exceeded = True
                            break
                            
                        try:
                            replies_resp = client.fetch_replies(
                                parent_id=comment_id,
                                page_token=reply_page_token,
                                max_results=min(100, max_replies_per_comment - replies_collected),
                                text_format=text_format
                            )
                            tracker.track_call(run_id, "comments.list", 1, 200)
                        except QuotaExceededError:
                            tracker.track_call(run_id, "comments.list", 1, 403, "quotaExceeded")
                            quota_exceeded = True
                            break
                        except Exception as e:
                            err_lbl = client.normalize_error(e)
                            tracker.track_call(run_id, "comments.list", 1, 500, err_lbl)
                            logger.warning(f"Error fetching replies for comment {comment_id}: {e}")
                            break
                            
                        reply_items = replies_resp.get("items", [])
                        if not reply_items:
                            break
                            
                        for rep_item in reply_items:
                            _persist_reply(rep_item, video_id, comment_id, run_stats,
                                           deduplicator, database_url, first_crawl_done, started_at)
                            replies_collected += 1
                                
                        reply_page_token = replies_resp.get("nextPageToken")
                        if not reply_page_token or quota_exceeded:
                            break

                if deduplicator.should_stop_early():
                    early_stop_triggered = True
                    break
                    
            if early_stop_triggered or quota_exceeded:
                break
                
            page_token = threads_resp.get("nextPageToken")
            if not page_token or video_comments_collected >= max_comments_per_video:
                break

        # Track whether the per-video loop ended naturally (all pages fetched)
        # vs. was cut short by max_comments or dedup early-stop. We must NOT
        # mark first_crawl_done when the loop was truncated — doing so would
        # permanently lose older historical comments beyond the per-run limit.
        all_pages_exhausted = (
            not early_stop_triggered
            and not quota_exceeded
            and page_token is None
            and video_comments_collected < max_comments_per_video
        )

        try:
            if not first_crawl_done and not quota_exceeded and run_stats["status"] != "failed":
                if all_pages_exhausted:
                    repository.mark_video_first_crawl_done(video_id, started_at, database_url)
                    logger.info(f"Initial baseline crawl completed for video {video_id}.")
                else:
                    logger.info(
                        f"Baseline crawl for {video_id} incomplete "
                        f"(collected {video_comments_collected}/{max_comments_per_video}, "
                        f"pages_remaining={page_token is not None}). "
                        f"Will continue on next run."
                    )
                
            current_comments_count = repository.count_comments_for_video(video_id, database_url)
            repository.update_video_last_checked(
                video_id=video_id,
                last_checked_at=started_at,
                last_seen_comment_at=video_last_seen_comment_at,
                total_comments_collected=current_comments_count,
                database_url=database_url
            )
        except Exception as e:
            logger.error(f"Error finalizing video stats for {video_id}: {e}")
            
        if quota_exceeded or run_stats["status"] == "failed":
            break

    run_stats["finished_at"] = datetime.now(timezone.utc).isoformat()
    run_stats["api_units_used"] = tracker.units_consumed_this_run
    
    if run_stats["status"] == "running":
        if quota_exceeded:
            run_stats["status"] = "quota_exceeded"
            run_stats["error_message"] = "Session terminated due to daily API quota limit limits."
        else:
            run_stats["status"] = "completed"

    try:
        repository.save_crawl_run(run_stats, database_url)
    except Exception as e:
        logger.error(f"Failed to save final crawl run details: {e}")

    logger.info(
        f"Crawl session {run_id} completed. Status: {run_stats['status']}. "
        f"New: {run_stats['new_comments']}, Dups: {run_stats['duplicate_comments']}, "
        f"Updated: {run_stats['updated_comments']}, Units: {run_stats['api_units_used']}."
    )

    # Re-run inference on new OR edited comments. update_comment resets edited
    # comments to 'pending', so without this they'd silently stay pending forever.
    # Wrapped so inference failure never aborts or marks the crawl as failed.
    if run_stats.get("new_comments", 0) > 0 or run_stats.get("updated_comments", 0) > 0:
        _run_post_crawl_inference(database_url, enable_inference=enable_inference)

    return run_stats
