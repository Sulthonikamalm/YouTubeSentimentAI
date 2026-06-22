"""
quota_tracker.py — Tracks and restricts YouTube API quota usage.

Queries the api_usage table for today's total to enforce the daily limit,
not just the current run's consumption. Caches the daily total and
invalidates only when a new call is recorded.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from backend.storage import repository
from backend.storage.db import get_db_connection

logger = logging.getLogger("youtube_collector")

class QuotaTracker:
    """Manages and monitors API call limits and unit consumption."""

    def __init__(
        self,
        daily_limit: int = 10000,
        warning_threshold: int = 8000,
        database_url: Optional[str] = None
    ):
        self.daily_limit = daily_limit
        self.warning_threshold = warning_threshold
        self.database_url = database_url
        self.units_consumed_this_run = 0
        self._cached_daily_total: Optional[int] = None

    def _get_today_total_units(self) -> int:
        """Query api_usage table for total units consumed today (UTC). Cached."""
        if self._cached_daily_total is not None:
            return self._cached_daily_total
        today_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00")
        try:
            with get_db_connection(self.database_url) as conn:
                row = conn.execute(
                    "SELECT COALESCE(SUM(units), 0) AS total FROM api_usage WHERE called_at >= ?;",
                    (today_start,)
                ).fetchone()
                total = int(row["total"]) if row else 0
        except Exception as e:
            logger.warning(f"Failed to query daily API usage: {e}")
            total = self.units_consumed_this_run
        self._cached_daily_total = total
        return total

    def track_call(
        self, run_id: str, endpoint: str, units: int, status: int,
        error_message: Optional[str] = None
    ) -> None:
        self.units_consumed_this_run += units
        # Invalidate cache so next is_limit_exceeded() re-queries.
        self._cached_daily_total = None

        called_at = datetime.now(timezone.utc).isoformat()
        usage_record = {
            "run_id": run_id,
            "endpoint": endpoint,
            "units": units,
            "called_at": called_at,
            "status": status,
            "error_message": error_message
        }

        try:
            repository.save_api_usage(usage_record, self.database_url)
        except Exception as e:
            logger.error(f"Failed to log API usage to database: {e}")

    def is_limit_exceeded(self) -> bool:
        """Check if daily quota limit is exceeded (queries DB, cached)."""
        return self._get_today_total_units() >= self.daily_limit
