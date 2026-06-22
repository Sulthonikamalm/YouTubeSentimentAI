"""
run_crawl.py — CLI script to trigger manual YouTube comment crawling sessions.
Usage: python scripts/run_crawl.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import load_settings, get_database_url
from backend.services.scheduler_service import trigger_manual_crawl

project_root = Path(__file__).resolve().parent.parent
logs_dir = project_root / "logs"
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / "crawler.log"

logger = logging.getLogger("youtube_collector")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

file_handler = logging.FileHandler(str(log_file), mode="a", encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def main():
    logger.info("Initializing manual crawl run...")
    try:
        settings = load_settings()
        db_url = get_database_url(settings)
        
        result = trigger_manual_crawl(database_url=db_url)
        
        status = result.get("status")
        if status == "crawl_already_running":
            logger.warning("Crawl execution rejected: another crawl is currently running.")
            print("\nError: crawl_already_running")
            sys.exit(1)
            
        print("\n" + "="*50)
        print("CRAWL SESSION DETAILS")
        print("="*50)
        print(f"Run ID:             {result.get('run_id')}")
        print(f"Status:             {result.get('status')}")
        print(f"Started At:         {result.get('started_at')}")
        print(f"Finished At:        {result.get('finished_at')}")
        print(f"Videos Checked:     {result.get('videos_checked')}")
        print(f"Comments Fetched:   {result.get('comments_fetched')}")
        print(f"New Comments:       {result.get('new_comments')}")
        print(f"Dups Skipped:       {result.get('duplicate_comments')}")
        print(f"Comments Updated:   {result.get('updated_comments')}")
        print(f"Replies Fetched:    {result.get('replies_fetched')}")
        print(f"API Units Consumed: {result.get('api_units_used')}")
        
        if result.get("error_message"):
            print(f"Error Message:      {result.get('error_message')}")
        print("="*50 + "\n")
        
        if status == "failed":
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Failed to execute manual crawl: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
