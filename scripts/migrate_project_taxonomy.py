"""Idempotently migrate project ownership and taxonomy versioning."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.storage.db import get_db_connection
from backend.storage.projects_repo import init_db


TRACKED_TABLES = ("projects", "videos", "comments")


def _counts(database_url=None):
    with get_db_connection(database_url) as conn:
        return {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in TRACKED_TABLES
        }


def migrate(database_url=None):
    before = _counts(database_url)
    init_db(database_url)
    after = _counts(database_url)
    if before != after:
        raise RuntimeError(f"Row counts changed during migration: {before} -> {after}")

    with get_db_connection(database_url) as conn:
        versions = conn.execute(
            "SELECT COUNT(*) FROM project_taxonomy_versions"
        ).fetchone()[0]
        versioned_comments = conn.execute(
            "SELECT COUNT(*) FROM comments WHERE taxonomy_version_id IS NOT NULL"
        ).fetchone()[0]
    return {
        "status": "ok",
        "before": before,
        "after": after,
        "taxonomy_versions": versions,
        "versioned_comments": versioned_comments,
    }


def main():
    summary = migrate()
    print("Project taxonomy migration complete")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
