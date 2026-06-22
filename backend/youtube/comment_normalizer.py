"""
comment_normalizer.py — Formats YouTube comment API data into our internal schemas.
"""

import json
import hashlib
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("youtube_collector")

def calculate_json_hash(raw_dict: Dict[str, Any]) -> str:
    """Computes a SHA-256 hash of the JSON string representation of a dict."""
    try:
        raw_json_str = json.dumps(raw_dict, sort_keys=True)
        return hashlib.sha256(raw_json_str.encode("utf-8")).hexdigest()
    except Exception as e:
        logger.warning(f"Failed to calculate JSON hash: {e}")
        return ""

def normalize_comment(raw_item: Dict[str, Any], video_id: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Normalizes a top-level comment or reply comment dictionary.
    """
    snippet = raw_item.get("snippet", {})
    
    if "topLevelComment" in snippet:
        comment_id = snippet["topLevelComment"].get("id", "")
        c_snippet = snippet["topLevelComment"].get("snippet", {})
        reply_count = snippet.get("totalReplyCount", 0)
    else:
        comment_id = raw_item.get("id", "")
        c_snippet = snippet
        reply_count = 0

    is_reply = parent_id is not None
    
    author_name = c_snippet.get("authorDisplayName", "")
    author_channel_info = c_snippet.get("authorChannelId", {})
    author_channel_id = author_channel_info.get("value", "") if isinstance(author_channel_info, dict) else ""
    
    text_original = c_snippet.get("textOriginal", "")
    text_display = c_snippet.get("textDisplay", "")
    
    comment_text = text_original if text_original is not None else ""
    if not comment_text.strip():
        comment_text = text_display if text_display is not None else ""
        
    if not comment_text.strip():
        logger.warning(f"Comment {comment_id} text is empty or missing.")
        comment_text = ""
        
    published_at = c_snippet.get("publishedAt", "")
    updated_at = c_snippet.get("updatedAt", "")
    like_count = c_snippet.get("likeCount", 0)
    
    raw_json_str = ""
    raw_hash = ""
    try:
        raw_json_str = json.dumps(raw_item)
        raw_hash = calculate_json_hash(raw_item)
    except Exception as e:
        logger.warning(f"Could not serialize raw JSON for comment {comment_id}: {e}")

    return {
        "comment_id": comment_id,
        "video_id": video_id,
        "parent_id": parent_id,
        "is_reply": is_reply,
        "author_name": author_name,
        "author_channel_id": author_channel_id,
        "comment_text": comment_text,
        "text_original": text_original,
        "text_display": text_display,
        "published_at": published_at,
        "updated_at": updated_at,
        "like_count": like_count,
        "reply_count": reply_count,
        "collected_at": None,
        "is_baseline": False,
        "is_deleted": False,
        "last_seen_at": None,
        "raw_json_hash": raw_hash,
        "raw_json": raw_json_str,
    }
