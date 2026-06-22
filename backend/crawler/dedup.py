"""
dedup.py — Handles deduplication and early stopping based on duplicate thresholds.
"""

import logging
from typing import Optional
from backend.storage import repository

logger = logging.getLogger("youtube_collector")

class Deduplicator:
    """Manages comment deduplication checks and consecutive duplicates threshold tracking."""
    
    def __init__(self, threshold: int = 30, database_url: Optional[str] = None):
        self.threshold = threshold
        self.database_url = database_url
        self.consecutive_duplicates = 0
        
    def reset(self) -> None:
        self.consecutive_duplicates = 0
        
    def check(self, comment_id: str):
        """Returns existing {comment_id, updated_at} if found, else None.

        Uses the lightweight dedup-meta query (no raw_json blob) since the
        crawler only compares updated_at to detect edits.
        """
        try:
            return repository.get_comment_dedup_meta(comment_id, self.database_url)
        except Exception as e:
            logger.error(f"Error checking database for duplicate comment {comment_id}: {e}")
            return None

    def record_occurrence(self, is_dup: bool) -> None:
        if is_dup:
            self.consecutive_duplicates += 1
        else:
            self.consecutive_duplicates = 0

    def should_stop_early(self) -> bool:
        if self.consecutive_duplicates >= self.threshold:
            logger.info(
                f"Consecutive duplicate count ({self.consecutive_duplicates}) "
                f"reached threshold ({self.threshold}). Early stop triggered."
            )
            return True
        return False
