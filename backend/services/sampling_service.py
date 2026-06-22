"""
sampling_service.py — Extracts and formats comment samples for Gemini taxonomy generation.
"""

import hashlib
import json
from typing import Dict, Any

from backend.storage.db import get_db_connection

def get_comment_sample_for_taxonomy(project_id: str, 
                                    database_url: str = None, 
                                    min_sample: int = 20,
                                    max_sample: int = 100) -> Dict[str, Any]:
    """
    Fetches up to `max_sample` comments for a project, balanced across its videos.
    Returns the formatted sample and a deterministic hash of the sample to avoid
    regenerating identical contexts.
    """
    with get_db_connection(database_url) as conn:
        # Get videos for this project
        videos = conn.execute(
            "SELECT video_id, video_title, channel_title FROM videos WHERE project_id = ?",
            (project_id,)
        ).fetchall()
        
        if not videos:
            return {"valid": False, "count": 0, "sample": [], "hash": None, "reason": "No videos found for this project."}
            
        video_map = {v["video_id"]: dict(v) for v in videos}
        video_ids = list(video_map.keys())
        
        # Get count of valid comments per video
        # We only want comments that have actual text and are not deleted.
        ph = ",".join("?" for _ in video_ids)
        counts = conn.execute(
            f"SELECT video_id, COUNT(*) FROM comments "
            f"WHERE video_id IN ({ph}) AND is_deleted = 0 "
            f"AND comment_text IS NOT NULL AND TRIM(comment_text) != '' "
            f"GROUP BY video_id",
            video_ids
        ).fetchall()
        
        total_valid = sum(c[1] for c in counts)
        
        if total_valid < min_sample:
            return {
                "valid": False, 
                "count": total_valid, 
                "sample": [], 
                "hash": None, 
                "reason": f"Project has only {total_valid} valid comments. Minimum {min_sample} required."
            }

        target = min(max_sample, total_valid)
        count_map = {row[0]: row[1] for row in counts}
        eligible = sorted(count_map)
        allocation = {vid: 0 for vid in eligible}

        # Round-robin allocation prevents one large video from dominating.
        while sum(allocation.values()) < target:
            progressed = False
            for vid in eligible:
                if allocation[vid] < count_map[vid]:
                    allocation[vid] += 1
                    progressed = True
                    if sum(allocation.values()) >= target:
                        break
            if not progressed:
                break

        sampled_comments = []
        for vid, alloc in allocation.items():
            if alloc <= 0:
                continue
            
            recent_limit = (alloc + 1) // 2
            recent = conn.execute(
                "SELECT comment_id, comment_text, is_reply, updated_at FROM comments "
                "WHERE video_id = ? AND is_deleted = 0 AND comment_text IS NOT NULL "
                "AND TRIM(comment_text) != '' ORDER BY published_at DESC, comment_id ASC LIMIT ?",
                (vid, recent_limit),
            ).fetchall()
            historical = conn.execute(
                "SELECT comment_id, comment_text, is_reply, updated_at FROM comments "
                "WHERE video_id = ? AND is_deleted = 0 AND comment_text IS NOT NULL "
                "AND TRIM(comment_text) != '' "
                "ORDER BY is_baseline DESC, published_at ASC, comment_id ASC LIMIT ?",
                (vid, alloc * 2),
            ).fetchall()

            rows, seen = [], set()
            for row in [*recent, *historical]:
                if row["comment_id"] in seen:
                    continue
                seen.add(row["comment_id"])
                rows.append(row)
                if len(rows) >= alloc:
                    break
            
            v_info = video_map[vid]
            for r in rows:
                # Truncate comment text securely if it's too long (e.g. max 1000 chars)
                text = r["comment_text"]
                if len(text) > 1000:
                    text = text[:1000] + "... (truncated)"
                    
                sampled_comments.append({
                    "_comment_id": r["comment_id"],
                    "_updated_at": r["updated_at"],
                    "video_title": v_info["video_title"],
                    "channel_title": v_info["channel_title"],
                    "is_reply": bool(r["is_reply"]),
                    "text": text
                })
                
        # Sort so the hash is deterministic based on content
        sampled_comments.sort(key=lambda x: (x["_comment_id"], x["_updated_at"] or ""))
        
        # Create deterministic hash
        sample_json = json.dumps(sampled_comments, sort_keys=True, ensure_ascii=False)
        sample_hash = hashlib.sha256(sample_json.encode("utf-8")).hexdigest()

        public_sample = [
            {key: value for key, value in item.items() if not key.startswith("_")}
            for item in sampled_comments
        ]
        
        return {
            "valid": True,
            "count": len(sampled_comments),
            "sample": public_sample,
            "hash": sample_hash,
            "reason": "Success"
        }
