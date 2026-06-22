"""
export_comments.py — CLI script to export comments from SQLite database to CSV files.
Usage: python scripts/export_comments.py [output_path]
"""

import sys
import logging
import csv
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import load_settings, get_database_url
from backend.storage.db import get_db_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("export_comments")

def main():
    try:
        settings = load_settings()
        db_url = get_database_url(settings)
        
        project_root = Path(__file__).resolve().parent.parent
        if len(sys.argv) >= 2:
            out_path = Path(sys.argv[1])
        else:
            exports_dir = project_root / "data" / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            out_path = exports_dir / f"comments_export_{timestamp}.csv"
            
        logger.info("Connecting to database to retrieve comments...")
        
        with get_db_connection(db_url) as conn:
            query = """
                SELECT 
                    c.comment_id, 
                    c.video_id, 
                    v.video_url,
                    v.video_title,
                    c.parent_id, 
                    c.is_reply, 
                    c.author_name, 
                    c.author_channel_id, 
                    c.comment_text, 
                    c.text_original,
                    c.text_display,
                    c.published_at, 
                    c.updated_at, 
                    c.like_count, 
                    c.reply_count, 
                    c.collected_at, 
                    c.is_baseline, 
                    c.is_deleted,
                    c.sentiment,
                    c.sentiment_confidence,
                    c.issue_label,
                    c.stance_label,
                    c.action_intent_label,
                    c.interpretation_short,
                    c.inference_status,
                    c.inferred_at
                FROM comments c
                LEFT JOIN videos v ON c.video_id = v.video_id
                ORDER BY c.published_at DESC;
            """
            rows = conn.execute(query).fetchall()
            
            if not rows:
                logger.warning("No comments found in database to export.")
                print("Export failed: Database is empty.")
                sys.exit(0)
                
            logger.info(f"Found {len(rows)} comments. Writing to {out_path}...")
            
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            headers = [
                "comment_id", "video_id", "video_url", "video_title", "parent_id", "is_reply",
                "author_name", "author_channel_id", "comment_text", "text_original", "text_display",
                "published_at", "updated_at", "like_count", "reply_count", "collected_at",
                "is_baseline", "is_deleted",
                "sentiment", "sentiment_confidence", "issue_label", "stance_label",
                "action_intent_label", "interpretation_short", "inference_status", "inferred_at"
            ]
            
            with open(out_path, mode="w", newline="", encoding="utf-8-sig") as csv_file:
                writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
                writer.writerow(headers)
                
                for row in rows:
                    writer.writerow([row[h] for h in headers])
                    
            logger.info(f"Comments exported successfully to {out_path}.")
            print(f"\nSuccess: Exported {len(rows)} comments to: {out_path}\n")
            
    except Exception as e:
        logger.error(f"Error during export: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
