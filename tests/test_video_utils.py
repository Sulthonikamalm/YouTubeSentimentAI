"""
test_video_utils.py — Unit tests for video ID parsing logic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.youtube.video_utils import parse_video_id

def test_parse_standard_watch_url():
    url = "https://www.youtube.com/watch?v=K8EKqxU-UwM"
    assert parse_video_id(url) == "K8EKqxU-UwM"

def test_parse_short_url():
    url = "https://youtu.be/zc7vQz_MHxw?si=yBC-xcK5pHSHy1OA"
    assert parse_video_id(url) == "zc7vQz_MHxw"

def test_parse_shorts_url():
    url = "https://www.youtube.com/shorts/zc7vQz_MHxw"
    assert parse_video_id(url) == "zc7vQz_MHxw"

def test_parse_mobile_url():
    url = "https://m.youtube.com/watch?v=K8EKqxU-UwM&feature=shared"
    assert parse_video_id(url) == "K8EKqxU-UwM"

def test_parse_direct_id():
    video_id = "K8EKqxU-UwM"
    assert parse_video_id(video_id) == "K8EKqxU-UwM"

def test_parse_invalid_url():
    assert parse_video_id("https://google.com") is None
    assert parse_video_id("https://youtube.com/feed/subscriptions") is None
    assert parse_video_id("") is None
    assert parse_video_id(None) is None
