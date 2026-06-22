"""
video_utils.py — Helper functions for YouTube videos.
"""

import re
from urllib.parse import urlparse, parse_qs
from typing import Optional

def parse_video_id(url_or_id: str) -> Optional[str]:
    """
    Extracts the 11-character YouTube video ID from a URL or checks if the input is directly an ID.
    """
    if not url_or_id or not isinstance(url_or_id, str):
        return None
        
    url_or_id = url_or_id.strip()
    
    if len(url_or_id) == 11 and re.match(r"^[a-zA-Z0-9_-]{11}$", url_or_id):
        return url_or_id
        
    try:
        parsed = urlparse(url_or_id)
    except Exception:
        return None
        
    if parsed.hostname in ("youtu.be",):
        path_parts = parsed.path.lstrip("/").split("/")
        if path_parts and len(path_parts[0]) == 11:
            return path_parts[0]
            
    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            if "v" in qs and len(qs["v"][0]) == 11:
                return qs["v"][0]
        elif parsed.path.startswith("/shorts/"):
            parts = parsed.path.split("/")
            if len(parts) >= 3 and len(parts[2]) == 11:
                return parts[2]
                
    match = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([a-zA-Z0-9_-]{11})", url_or_id)
    if match:
        return match.group(1)
        
    return None
