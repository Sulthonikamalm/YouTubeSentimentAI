"""
test_comment_normalizer.py — Unit tests for comment normalization logic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.youtube.comment_normalizer import normalize_comment

def test_normalize_top_level_complete():
    raw_item = {
        "id": "Ugz...",
        "snippet": {
            "topLevelComment": {
                "id": "comment123",
                "snippet": {
                    "authorDisplayName": "Sulthoni",
                    "authorChannelId": {"value": "channel123"},
                    "textOriginal": "Halo Dunia!",
                    "textDisplay": "Halo Dunia!",
                    "publishedAt": "2026-06-17T14:00:00Z",
                    "updatedAt": "2026-06-17T14:00:00Z",
                    "likeCount": 5
                }
            },
            "totalReplyCount": 2
        }
    }
    
    normalized = normalize_comment(raw_item, video_id="video123")
    
    assert normalized["comment_id"] == "comment123"
    assert normalized["video_id"] == "video123"
    assert normalized["parent_id"] is None
    assert normalized["is_reply"] is False
    assert normalized["author_name"] == "Sulthoni"
    assert normalized["author_channel_id"] == "channel123"
    assert normalized["comment_text"] == "Halo Dunia!"
    assert normalized["published_at"] == "2026-06-17T14:00:00Z"
    assert normalized["like_count"] == 5
    assert normalized["reply_count"] == 2

def test_normalize_top_level_text_original_empty():
    raw_item = {
        "id": "Ugz...",
        "snippet": {
            "topLevelComment": {
                "id": "comment123",
                "snippet": {
                    "authorDisplayName": "Sulthoni",
                    "authorChannelId": {"value": "channel123"},
                    "textOriginal": "",
                    "textDisplay": "Emoji Only 😊",
                    "publishedAt": "2026-06-17T14:00:00Z",
                    "updatedAt": "2026-06-17T14:00:00Z",
                    "likeCount": 0
                }
            },
            "totalReplyCount": 0
        }
    }
    
    normalized = normalize_comment(raw_item, video_id="video123")
    assert normalized["comment_text"] == "Emoji Only 😊"

def test_normalize_top_level_author_missing():
    raw_item = {
        "id": "Ugz...",
        "snippet": {
            "topLevelComment": {
                "id": "comment123",
                "snippet": {
                    "textOriginal": "Anonymous comment",
                    "textDisplay": "Anonymous comment",
                    "publishedAt": "2026-06-17T14:00:00Z",
                    "updatedAt": "2026-06-17T14:00:00Z"
                }
            }
        }
    }
    
    normalized = normalize_comment(raw_item, video_id="video123")
    assert normalized["author_name"] == ""
    assert normalized["author_channel_id"] == ""

def test_normalize_reply():
    raw_item = {
        "id": "reply789",
        "snippet": {
            "authorDisplayName": "Alex",
            "authorChannelId": {"value": "channelAlex"},
            "textOriginal": "Balasan komentar",
            "textDisplay": "Balasan komentar",
            "publishedAt": "2026-06-17T14:05:00Z",
            "updatedAt": "2026-06-17T14:06:00Z",
            "likeCount": 1
        }
    }
    
    normalized = normalize_comment(raw_item, video_id="video123", parent_id="comment123")
    
    assert normalized["comment_id"] == "reply789"
    assert normalized["parent_id"] == "comment123"
    assert normalized["is_reply"] is True
    assert normalized["comment_text"] == "Balasan komentar"
    assert normalized["reply_count"] == 0
