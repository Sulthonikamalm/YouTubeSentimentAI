"""
add_video.py — CLI script to register YouTube videos for monitoring.
Usage: python scripts/add_video.py "<url_or_video_id>"
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import load_settings, get_database_url
from backend.crawler.video_registry import register_video, get_video_details

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("add_video")

def main():
    if len(sys.argv) < 2:
        logger.error("Error: YouTube URL or Video ID parameter is required.")
        print('Usage: python scripts/add_video.py "https://youtu.be/VIDEO_ID" or "VIDEO_ID"')
        sys.exit(1)
        
    target = sys.argv[1]
    
    try:
        settings = load_settings()
        db_url = get_database_url(settings)
        
        video_id = register_video(target, database_url=db_url)
        if video_id:
            details = get_video_details(video_id, database_url=db_url)
            logger.info(f"Video {video_id} is successfully registered for monitoring.")
            print("Video Details:")
            print(f" - ID: {details.get('video_id')}")
            print(f" - URL: {details.get('video_url')}")
            print(f" - Monitoring Enabled: {details.get('monitoring_enabled')}")
            print(f" - First Crawl Done: {details.get('first_crawl_done')}")
        else:
            logger.error("Failed to register video. Ensure the URL or ID format is valid.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error during video registration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
