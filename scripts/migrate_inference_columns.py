"""
migrate_inference_columns.py — Idempotent SQLite migration that adds the 10
inference columns to the `comments` table without touching existing rows.

Safety rules:
  - never DROP a table
  - never DELETE rows
  - only ALTER TABLE ADD COLUMN if the column does not already exist
  - fail loudly if the row count changes
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.storage.db import get_db_connection
from backend.storage.schema import INFERENCE_COLUMNS


def get_existing_columns(conn, table: str) -> list:
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return [r[1] for r in rows]


def comments_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM comments;").fetchone()[0]


def migrate(database_url: str = None) -> dict:
    """
    Returns a summary dict so the script can be wrapped by other tooling
    (e.g. tests) without scraping stdout.
    """
    summary = {
        "columns_already_present": [],
        "columns_added": [],
        "comments_before": None,
        "comments_after": None,
        "status": "pending",
        "indexes_added": [],
    }

    with get_db_connection(database_url) as conn:
        existing_tables = [
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        ]
        if "comments" not in existing_tables:
            summary["status"] = "failed_no_comments_table"
            return summary

        summary["comments_before"] = comments_count(conn)
        existing = set(get_existing_columns(conn, "comments"))

        with conn:
            for name, sql_type in INFERENCE_COLUMNS:
                if name in existing:
                    summary["columns_already_present"].append(name)
                    continue
                # ALTER TABLE ADD COLUMN never rewrites rows; safe.
                conn.execute(
                    f"ALTER TABLE comments ADD COLUMN {name} {sql_type};"
                )
                summary["columns_added"].append(name)

            # Index for the pending query. IF NOT EXISTS makes this idempotent.
            try:
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_comments_inference_status "
                    "ON comments(inference_status);"
                )
                summary["indexes_added"].append("idx_comments_inference_status")
            except Exception as e:
                summary["indexes_added"].append(f"failed:{e}")

        summary["comments_after"] = comments_count(conn)

    if summary["comments_before"] != summary["comments_after"]:
        summary["status"] = "failed_row_count_changed"
    else:
        summary["status"] = "ok"

    return summary


def main():
    print("=== Tahap 2 — Migration: inference columns on `comments` ===")
    summary = migrate()
    print(f"  comments_before : {summary['comments_before']}")
    print(f"  comments_after  : {summary['comments_after']}")
    print(f"  already present : {summary['columns_already_present']}")
    print(f"  newly added     : {summary['columns_added']}")
    print(f"  indexes         : {summary['indexes_added']}")
    print(f"  status          : {summary['status']}")
    if summary["status"] != "ok":
        sys.exit(1)


if __name__ == "__main__":
    main()
