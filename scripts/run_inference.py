"""
run_inference.py — CLI script to run comment inference.

Usage:
    python scripts/run_inference.py --pending --limit 500
    python scripts/run_inference.py --all --confirm
"""

import sys
import io
import logging
from pathlib import Path

# Force UTF-8 stdout on Windows to avoid cp1252 UnicodeEncodeError.
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import load_settings, get_database_url
from backend.services.inference_service import infer_pending, infer_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("youtube_collector.inference")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run sentiment/inference pipeline on comments."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--pending", action="store_true",
        help="Process comments with inference_status NULL/pending/failed_retryable.",
    )
    group.add_argument(
        "--all", action="store_true",
        help="Re-run inference on ALL comments (requires --confirm).",
    )
    parser.add_argument("--limit", type=int, default=500,
                        help="Max comments to process (default: 500). Only for --pending.")
    parser.add_argument("--confirm", action="store_true",
                        help="Required flag for --all to prevent accidental full re-run.")

    args = parser.parse_args()

    # Resolve the configured database so inference targets the SAME database the
    # crawler writes to (honors settings.storage.database_url / DATABASE_URL env),
    # not just the built-in default path. Without this, a customized database_url
    # would make inference silently run against the wrong (empty) database.
    db_url = get_database_url(load_settings())

    if args.pending:
        logger.info("Starting infer_pending (limit=%d)...", args.limit)
        summary = infer_pending(limit=args.limit, database_url=db_url)
    elif args.all:
        if not args.confirm:
            logger.error("--all requires --confirm flag. Aborting.")
            print("Error: --all requires --confirm. Re-run with --all --confirm.")
            sys.exit(1)
        logger.info("Starting infer_all (confirm=True)...")
        summary = infer_all(confirm=True, database_url=db_url)

    print("\n" + "=" * 50)
    print("INFERENCE RUN SUMMARY")
    print("=" * 50)
    for k, v in summary.items():
        print(f"  {k:20s}: {v}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
