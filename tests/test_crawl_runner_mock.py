"""
test_crawl_runner_mock.py — Mocks YouTube API and tests crawl runner incremental logic.
"""

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.storage import repository
from backend.crawler.crawl_runner import run_youtube_crawl
from backend.crawler.video_registry import register_video
from backend.youtube.youtube_client import QuotaExceededError, CommentsDisabledError

def get_test_db(name: str):
    """
    Returns a unique DB URL and path, ensuring a clean isolated SQLite database for each test.
    Keeps URL simple and relative to project root.
    """
    db_file_name = f"test_yt_{name}_{uuid.uuid4().hex}.db"
    db_url = f"sqlite:///data/{db_file_name}"
    
    repository.init_db(db_url)
    
    db_dir = Path(__file__).resolve().parent.parent / "data"
    db_file = db_dir / db_file_name
    return db_url, db_file

def cleanup_test_db(db_file: Path):
    """Clean up DB file."""
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass

@patch.dict(os.environ, {"YOUTUBE_API_KEY": "fake_api_key_for_testing", "ENABLE_INFERENCE_AFTER_CRAWL": "false"})
@patch("backend.crawler.crawl_runner.load_settings")
@patch("backend.youtube.youtube_client.build")
def test_baseline_rule(mock_build, mock_load_settings):
    db_url, db_file = get_test_db("baseline")
    
    mock_load_settings.return_value = {
        "youtube": {
            "order": "time",
            "text_format": "plainText",
            "max_comments_per_video_per_run": 5,
            "fetch_replies": False,
            "request_timeout_seconds": 20
        },
        "quota": {
            "daily_limit": 10000,
            "warning_threshold": 8000
        },
        "crawler": {
            "consecutive_dup_threshold": 30
        }
    }
    
    video_id = "testvideo11"
    register_video(video_id, database_url=db_url)
    
    v_details = repository.get_video(video_id, database_url=db_url)
    assert v_details["first_crawl_done"] == 0
    
    with patch("backend.youtube.youtube_client.YouTubeClient.fetch_video_metadata") as mock_meta, \
         patch("backend.youtube.youtube_client.YouTubeClient.fetch_comment_threads") as mock_threads:
         
        mock_meta.return_value = {
            "video_title": "Test Title",
            "channel_title": "Test Channel",
            "published_at": "2026-06-01T00:00:00Z"
        }
        
        mock_threads.return_value = {
            "items": [
                {
                    "id": "c1",
                    "snippet": {
                        "topLevelComment": {
                            "id": "c1",
                            "snippet": {
                                "authorDisplayName": "User A",
                                "textOriginal": "Comment A",
                                "publishedAt": "2026-06-17T10:00:00Z",
                                "updatedAt": "2026-06-17T10:00:00Z",
                                "likeCount": 1
                            }
                        },
                        "totalReplyCount": 0
                    }
                }
            ]
        }
        
        run_stats = run_youtube_crawl(trigger_type="manual", database_url=db_url)
        assert run_stats["status"] == "completed"
        assert run_stats["new_comments"] == 1
        
        v_details = repository.get_video(video_id, database_url=db_url)
        assert v_details["first_crawl_done"] == 1
        
        c1 = repository.get_comment("c1", database_url=db_url)
        assert c1["is_baseline"] == 1
        
        mock_threads.return_value = {
            "items": [
                {
                    "id": "c2",
                    "snippet": {
                        "topLevelComment": {
                            "id": "c2",
                            "snippet": {
                                "authorDisplayName": "User B",
                                "textOriginal": "Comment B",
                                "publishedAt": "2026-06-17T11:00:00Z",
                                "updatedAt": "2026-06-17T11:00:00Z",
                                "likeCount": 2
                            }
                        },
                        "totalReplyCount": 0
                    }
                },
                {
                    "id": "c1",
                    "snippet": {
                        "topLevelComment": {
                            "id": "c1",
                            "snippet": {
                                "authorDisplayName": "User A",
                                "textOriginal": "Comment A",
                                "publishedAt": "2026-06-17T10:00:00Z",
                                "updatedAt": "2026-06-17T10:00:00Z",
                                "likeCount": 1
                            }
                        },
                        "totalReplyCount": 0
                    }
                }
            ]
        }
        
        run_stats2 = run_youtube_crawl(trigger_type="manual", database_url=db_url)
        assert run_stats2["status"] == "completed"
        assert run_stats2["new_comments"] == 1
        assert run_stats2["duplicate_comments"] == 1
        
        c2 = repository.get_comment("c2", database_url=db_url)
        assert c2["is_baseline"] == 0
        
        c1_after = repository.get_comment("c1", database_url=db_url)
        assert c1_after["is_baseline"] == 1
        
    cleanup_test_db(db_file)

@patch.dict(os.environ, {"YOUTUBE_API_KEY": "fake_api_key_for_testing", "ENABLE_INFERENCE_AFTER_CRAWL": "false"})
@patch("backend.crawler.crawl_runner.load_settings")
@patch("backend.youtube.youtube_client.build")
def test_quota_exceeded_handling(mock_build, mock_load_settings):
    db_url, db_file = get_test_db("quota")
    
    mock_load_settings.return_value = {
        "youtube": {
            "order": "time",
            "text_format": "plainText",
            "max_comments_per_video_per_run": 5,
            "fetch_replies": False,
            "request_timeout_seconds": 20
        },
        "quota": {
            "daily_limit": 10000,
            "warning_threshold": 8000
        },
        "crawler": {
            "consecutive_dup_threshold": 30
        }
    }
    
    video_id = "testvideo22"
    register_video(video_id, database_url=db_url)
    
    with patch("backend.youtube.youtube_client.YouTubeClient.fetch_video_metadata") as mock_meta:
        mock_meta.side_effect = QuotaExceededError("Quota limits reached.")
        
        run_stats = run_youtube_crawl(trigger_type="manual", database_url=db_url)
        
        assert run_stats["status"] == "quota_exceeded"
        assert "quota" in run_stats["error_message"].lower()
        
    cleanup_test_db(db_file)

@patch.dict(os.environ, {"YOUTUBE_API_KEY": "fake_api_key_for_testing", "ENABLE_INFERENCE_AFTER_CRAWL": "false"})
@patch("backend.crawler.crawl_runner.load_settings")
@patch("backend.youtube.youtube_client.build")
def test_comments_disabled_handling(mock_build, mock_load_settings):
    db_url, db_file = get_test_db("disabled")
    
    mock_load_settings.return_value = {
        "youtube": {
            "order": "time",
            "text_format": "plainText",
            "max_comments_per_video_per_run": 5,
            "fetch_replies": False,
            "request_timeout_seconds": 20
        },
        "quota": {
            "daily_limit": 10000,
            "warning_threshold": 8000
        },
        "crawler": {
            "consecutive_dup_threshold": 30
        }
    }
    
    video_disabled = "disabledvid"
    video_normal = "normalvideo"
    
    register_video(video_disabled, database_url=db_url)
    register_video(video_normal, database_url=db_url)
    
    with patch("backend.youtube.youtube_client.YouTubeClient.fetch_video_metadata") as mock_meta, \
         patch("backend.youtube.youtube_client.YouTubeClient.fetch_comment_threads") as mock_threads:
         
        mock_meta.return_value = {
            "video_title": "Title",
            "channel_title": "Channel",
            "published_at": "2026-06-01T00:00:00Z"
        }
        
        def thread_side_effect(video_id, **kwargs):
            if video_id == video_disabled:
                raise CommentsDisabledError("Comments disabled.")
            else:
                return {
                    "items": [
                        {
                            "id": "c_normal",
                            "snippet": {
                                "topLevelComment": {
                                    "id": "c_normal",
                                    "snippet": {
                                        "authorDisplayName": "Normal User",
                                        "textOriginal": "Normal",
                                        "publishedAt": "2026-06-17T10:00:00Z",
                                        "updatedAt": "2026-06-17T10:00:00Z",
                                        "likeCount": 1
                                    }
                                },
                                "totalReplyCount": 0
                            }
                        }
                    ]
                }
        
        mock_threads.side_effect = thread_side_effect
        
        run_stats = run_youtube_crawl(trigger_type="manual", database_url=db_url)
        
        assert run_stats["status"] == "completed"
        assert run_stats["videos_checked"] == 2
        assert run_stats["new_comments"] == 1
        
        c_norm = repository.get_comment("c_normal", database_url=db_url)
        assert c_norm is not None
        
    cleanup_test_db(db_file)

@patch.dict(os.environ, {"YOUTUBE_API_KEY": "fake_api_key_for_testing", "ENABLE_INFERENCE_AFTER_CRAWL": "false"})
@patch("backend.crawler.crawl_runner.load_settings")
@patch("backend.youtube.youtube_client.build")
def test_update_comment_flow(mock_build, mock_load_settings):
    db_url, db_file = get_test_db("update")
    
    mock_load_settings.return_value = {
        "youtube": {
            "order": "time",
            "text_format": "plainText",
            "max_comments_per_video_per_run": 5,
            "fetch_replies": False,
            "request_timeout_seconds": 20
        },
        "quota": {
            "daily_limit": 10000,
            "warning_threshold": 8000
        },
        "crawler": {
            "consecutive_dup_threshold": 30
        }
    }
    
    video_id = "testvideo33"
    register_video(video_id, database_url=db_url)
    
    setup_comment = {
        "comment_id": "c_edited",
        "video_id": video_id,
        "parent_id": None,
        "is_reply": False,
        "author_name": "Author",
        "author_channel_id": "author_channel",
        "comment_text": "Original Text",
        "text_original": "Original Text",
        "text_display": "Original Text",
        "published_at": "2026-06-17T10:00:00Z",
        "updated_at": "2026-06-17T10:00:00Z",
        "like_count": 0,
        "reply_count": 0,
        "collected_at": "2026-06-17T10:00:00Z",
        "is_baseline": True,
        "is_deleted": False,
        "last_seen_at": "2026-06-17T10:00:00Z",
        "raw_json_hash": "hash123",
        "raw_json": "{}"
    }
    repository.save_comment(setup_comment, database_url=db_url)
    repository.mark_video_first_crawl_done(video_id, "2026-06-17T10:00:00Z", database_url=db_url)
    
    with patch("backend.youtube.youtube_client.YouTubeClient.fetch_video_metadata") as mock_meta, \
         patch("backend.youtube.youtube_client.YouTubeClient.fetch_comment_threads") as mock_threads:
         
        mock_meta.return_value = {
            "video_title": "Title",
            "channel_title": "Channel",
            "published_at": "2026-06-01T00:00:00Z"
        }
        
        mock_threads.return_value = {
            "items": [
                {
                    "id": "c_edited",
                    "snippet": {
                        "topLevelComment": {
                            "id": "c_edited",
                            "snippet": {
                                "authorDisplayName": "Author",
                                "textOriginal": "Edited Text! 😊",
                                "publishedAt": "2026-06-17T10:00:00Z",
                                "updatedAt": "2026-06-17T11:00:00Z",
                                "likeCount": 10
                            }
                        },
                        "totalReplyCount": 0
                    }
                }
            ]
        }
        
        run_stats = run_youtube_crawl(trigger_type="manual", database_url=db_url)
        
        assert run_stats["status"] == "completed"
        assert run_stats["new_comments"] == 0
        assert run_stats["duplicate_comments"] == 1
        assert run_stats["updated_comments"] == 1
        
        updated = repository.get_comment("c_edited", database_url=db_url)
        assert updated["comment_text"] == "Edited Text! 😊"
        assert updated["updated_at"] == "2026-06-17T11:00:00Z"
        assert updated["like_count"] == 10

    cleanup_test_db(db_file)


def _reply_item(rid, text, hh):
    """Build a comments.list-style reply item (id + snippet, no topLevelComment)."""
    return {
        "id": rid,
        "snippet": {
            "authorDisplayName": f"Author {rid}",
            "textOriginal": text,
            "publishedAt": f"2026-06-17T{hh:02d}:00:00Z",
            "updatedAt": f"2026-06-17T{hh:02d}:00:00Z",
            "likeCount": 1,
        },
    }


@patch.dict(os.environ, {"YOUTUBE_API_KEY": "fake_api_key_for_testing", "ENABLE_INFERENCE_AFTER_CRAWL": "false"})
@patch("backend.crawler.crawl_runner.load_settings")
@patch("backend.youtube.youtube_client.build")
def test_inline_replies_fast_path_skips_comments_list(mock_build, mock_load_settings):
    """When commentThreads ships ALL replies inline, persist them directly and
    skip the extra comments.list API call (quota optimization)."""
    db_url, db_file = get_test_db("inline")

    mock_load_settings.return_value = {
        "youtube": {
            "order": "time", "text_format": "plainText",
            "max_comments_per_video_per_run": 5,
            "fetch_replies": True, "max_replies_per_comment": 100,
            "request_timeout_seconds": 20,
        },
        "quota": {"daily_limit": 10000, "warning_threshold": 8000},
        "crawler": {"consecutive_dup_threshold": 30},
    }

    video_id = "inlinevid01"
    register_video(video_id, database_url=db_url)

    with patch("backend.youtube.youtube_client.YouTubeClient.fetch_video_metadata") as mock_meta, \
         patch("backend.youtube.youtube_client.YouTubeClient.fetch_comment_threads") as mock_threads, \
         patch("backend.youtube.youtube_client.YouTubeClient.fetch_replies") as mock_replies:

        mock_meta.return_value = {
            "video_title": "Inline Title", "channel_title": "Inline Channel",
            "published_at": "2026-06-01T00:00:00Z",
        }
        mock_threads.return_value = {
            "items": [
                {
                    "id": "top1",
                    "snippet": {
                        "topLevelComment": {
                            "id": "top1",
                            "snippet": {
                                "authorDisplayName": "Top",
                                "textOriginal": "Top comment",
                                "publishedAt": "2026-06-17T10:00:00Z",
                                "updatedAt": "2026-06-17T10:00:00Z",
                                "likeCount": 5,
                            },
                        },
                        "totalReplyCount": 2,
                        "replies": {"comments": [_reply_item("rep1", "reply one", 11),
                                                  _reply_item("rep2", "reply two", 12)]},
                    },
                }
            ]
        }

        run_stats = run_youtube_crawl(trigger_type="manual", database_url=db_url)

        assert run_stats["status"] == "completed"
        assert run_stats["new_comments"] == 3      # 1 top-level + 2 inline replies
        assert run_stats["replies_fetched"] == 2
        mock_replies.assert_not_called()           # comments.list must be skipped

        r1 = repository.get_comment("rep1", database_url=db_url)
        r2 = repository.get_comment("rep2", database_url=db_url)
        assert r1 is not None and r2 is not None
        assert r1["is_reply"] == 1 and r1["parent_id"] == "top1"
        assert r1["is_baseline"] == 1              # first crawl -> baseline
        assert r2["parent_id"] == "top1"

    cleanup_test_db(db_file)


@patch.dict(os.environ, {"YOUTUBE_API_KEY": "fake_api_key_for_testing", "ENABLE_INFERENCE_AFTER_CRAWL": "false"})
@patch("backend.crawler.crawl_runner.load_settings")
@patch("backend.youtube.youtube_client.build")
def test_replies_fetched_when_inline_incomplete(mock_build, mock_load_settings):
    """When inline replies are incomplete (totalReplyCount > inline count),
    fall back to the paginated comments.list call as before."""
    db_url, db_file = get_test_db("partial")

    mock_load_settings.return_value = {
        "youtube": {
            "order": "time", "text_format": "plainText",
            "max_comments_per_video_per_run": 5,
            "fetch_replies": True, "max_replies_per_comment": 100,
            "request_timeout_seconds": 20,
        },
        "quota": {"daily_limit": 10000, "warning_threshold": 8000},
        "crawler": {"consecutive_dup_threshold": 30},
    }

    video_id = "partialvid1"
    register_video(video_id, database_url=db_url)

    with patch("backend.youtube.youtube_client.YouTubeClient.fetch_video_metadata") as mock_meta, \
         patch("backend.youtube.youtube_client.YouTubeClient.fetch_comment_threads") as mock_threads, \
         patch("backend.youtube.youtube_client.YouTubeClient.fetch_replies") as mock_replies:

        mock_meta.return_value = {
            "video_title": "Partial Title", "channel_title": "Partial Channel",
            "published_at": "2026-06-01T00:00:00Z",
        }
        # totalReplyCount=5 but NO inline replies -> must use comments.list.
        mock_threads.return_value = {
            "items": [
                {
                    "id": "topP",
                    "snippet": {
                        "topLevelComment": {
                            "id": "topP",
                            "snippet": {
                                "authorDisplayName": "Top",
                                "textOriginal": "Top comment",
                                "publishedAt": "2026-06-17T10:00:00Z",
                                "updatedAt": "2026-06-17T10:00:00Z",
                                "likeCount": 5,
                            },
                        },
                        "totalReplyCount": 5,
                    },
                }
            ]
        }
        mock_replies.return_value = {
            "items": [_reply_item("rp1", "r1", 11), _reply_item("rp2", "r2", 12)]
        }

        run_stats = run_youtube_crawl(trigger_type="manual", database_url=db_url)

        assert run_stats["status"] == "completed"
        assert run_stats["new_comments"] == 3      # 1 top-level + 2 replies
        assert run_stats["replies_fetched"] == 2
        mock_replies.assert_called_once()          # comments.list WAS called

        rp1 = repository.get_comment("rp1", database_url=db_url)
        assert rp1 is not None and rp1["is_reply"] == 1 and rp1["parent_id"] == "topP"

    cleanup_test_db(db_file)
