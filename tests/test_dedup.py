"""
test_dedup.py — Unit tests for comment deduplication and early stop threshold logic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.crawler.dedup import Deduplicator

def test_dedup_consecutive_counting():
    dedup = Deduplicator(threshold=3)
    
    assert dedup.consecutive_duplicates == 0
    assert not dedup.should_stop_early()
    
    dedup.record_occurrence(True)
    assert dedup.consecutive_duplicates == 1
    assert not dedup.should_stop_early()
    
    dedup.record_occurrence(True)
    assert dedup.consecutive_duplicates == 2
    assert not dedup.should_stop_early()
    
    dedup.record_occurrence(False)
    assert dedup.consecutive_duplicates == 0
    assert not dedup.should_stop_early()
    
    dedup.record_occurrence(True)
    dedup.record_occurrence(True)
    dedup.record_occurrence(True)
    assert dedup.consecutive_duplicates == 3
    assert dedup.should_stop_early()
