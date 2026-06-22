"""projects_repo.py — Project CRUD + database bootstrap.

Holds the schema initializer (which also seeds the default project) and all
project-scoped queries. Split out of repository.py to keep each storage module
focused on a single concern. Re-exported by repository.py for backward
compatibility, so existing `repository.init_db` / `repository.get_projects`
call sites continue to work unchanged.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import json
import re
import sqlite3

from backend.storage.db import get_db_connection
from backend.storage.schema import (
    CREATE_PROJECTS_TABLE, CREATE_VIDEOS_TABLE, CREATE_COMMENTS_TABLE,
    CREATE_CRAWL_RUNS_TABLE, CREATE_API_USAGE_TABLE, INDEXES,
    CREATE_USERS_TABLE, CREATE_CREDENTIALS_TABLE,
    CREATE_PROJECT_TAXONOMY_VERSIONS_TABLE, CREATE_LLM_GENERATION_RUNS_TABLE
)

DEFAULT_PROJECT_ID = "default_politik"

# Seed values for the default project, created on first init so a fresh install
# has a working classification taxonomy out of the box.
_DEFAULT_PROMPT_CONTEXT = (
    "1. Keluhan tentang harga barang, bbm, beras, pajak, gaji, bantuan sosial, atau sulitnya lapangan pekerjaan harus masuk ke issue: \"ekonomi_rakyat\".\n"
    "2. Komentar yang memuji video, host, narasumber, atau mengucapkan terima kasih atas edukasinya harus masuk ke issue: \"feedback_video\" dan stance: \"dukung_video\".\n"
    "3. Komentar sarkasme (pujian bernada mengejek atau memiliki konteks negatif) harus diklasifikasikan sebagai sentiment: \"negative\" dan stance: \"kritik_pemerintah\" atau \"sinis_tidak_percaya\".\n"
    "4. Slang Indonesian: gk/ga/gak=tidak, yg=yang, krn=karena, bgt=banget, mantul=mantap. Bahasa daerah: mundak=naik, mumet=pusing."
)
_DEFAULT_ISSUE_LABELS = "ekonomi_rakyat,kepercayaan_publik,pemerintahan_kebijakan,hukum_korupsi,elite_politik,geopolitik_keamanan,media_narasi,demokrasi_aksi_publik,feedback_video,lainnya"
_DEFAULT_STANCE_LABELS = "kritik_pemerintah,dukung_pemerintah,dukung_video,kritik_video,sinis_tidak_percaya,netral_informatif,debat_antar_pengguna,tidak_terdeteksi"
_DEFAULT_ACTION_LABELS = "menuntut_akuntabilitas,dorongan_aksi_publik,perubahan_elektoral,menyebarkan_kesadaran,harapan_doa,menunggu_mengamati,apatis_sinis,tidak_terdeteksi"


def _legacy_labels_json(value: Optional[str]) -> str:
    """Convert legacy comma-separated labels to structured JSON."""
    if not value:
        return "[]"
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return json.dumps(parsed, ensure_ascii=False)
    except (TypeError, json.JSONDecodeError):
        pass

    labels = []
    for raw in str(value).split(","):
        key = re.sub(r"[^a-z0-9]+", "_", raw.strip().lower()).strip("_")
        if key:
            labels.append({
                "key": key,
                "name": key.replace("_", " ").title(),
                "description": f"Label legacy: {key.replace('_', ' ')}.",
                "examples": [],
            })
    return json.dumps(labels, ensure_ascii=False)


def init_db(database_url: str = None) -> None:
    with get_db_connection(database_url) as conn:
        with conn:
            conn.execute(CREATE_PROJECTS_TABLE)
            conn.execute(CREATE_VIDEOS_TABLE)
            conn.execute(CREATE_COMMENTS_TABLE)
            conn.execute(CREATE_CRAWL_RUNS_TABLE)
            conn.execute(CREATE_API_USAGE_TABLE)
            conn.execute(CREATE_USERS_TABLE)
            conn.execute(CREATE_CREDENTIALS_TABLE)
            conn.execute(CREATE_PROJECT_TAXONOMY_VERSIONS_TABLE)
            conn.execute(CREATE_LLM_GENERATION_RUNS_TABLE)

            # Migration: Add project_id to videos if missing
            try:
                conn.execute("ALTER TABLE videos ADD COLUMN project_id TEXT;")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Migration: Add new columns to projects
            for col, dtype in [
                ("owner_user_id", "INTEGER"),
                ("goal_type", "TEXT"),
                ("goal_text", "TEXT"),
                ("status", "TEXT DEFAULT 'draft'"),
                ("active_taxonomy_version_id", "TEXT"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE projects ADD COLUMN {col} {dtype};")
                except sqlite3.OperationalError:
                    pass

            # Migration: Add taxonomy_version_id to comments
            try:
                conn.execute("ALTER TABLE comments ADD COLUMN taxonomy_version_id TEXT;")
            except sqlite3.OperationalError:
                pass

            for col, dtype in [
                ("updated_at", "DATETIME"),
                ("activated_at", "DATETIME"),
            ]:
                try:
                    conn.execute(
                        f"ALTER TABLE project_taxonomy_versions ADD COLUMN {col} {dtype};"
                    )
                except sqlite3.OperationalError:
                    pass

            # Seed the login owner before assigning or creating projects.
            admin = conn.execute(
                "SELECT id FROM users WHERE username = ?", ("admin",)
            ).fetchone()
            if not admin:
                from werkzeug.security import generate_password_hash
                cursor = conn.execute(
                    "INSERT INTO users (username, display_name, password_hash) VALUES (?, ?, ?)",
                    ("admin", "Administrator", generate_password_hash("admin123")),
                )
                admin_id = cursor.lastrowid
            else:
                admin_id = admin[0]

            # Migration: Create default project if not exists
            proj = conn.execute(
                "SELECT project_id FROM projects WHERE project_id = ?", (DEFAULT_PROJECT_ID,)
            ).fetchone()
            if not proj:
                conn.execute(
                    "INSERT INTO projects (project_id, project_name, description, owner_user_id, status, prompt_context, issue_labels, stance_labels, action_labels) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        DEFAULT_PROJECT_ID,
                        "Proyek Default (Politik Publik)",
                        "Proyek bawaan untuk analisis sentimen politik dan kebijakan publik.",
                        admin_id,
                        "active",
                        _DEFAULT_PROMPT_CONTEXT,
                        _DEFAULT_ISSUE_LABELS,
                        _DEFAULT_STANCE_LABELS,
                        _DEFAULT_ACTION_LABELS,
                    )
                )

            conn.execute(
                "UPDATE projects SET owner_user_id = ? WHERE owner_user_id IS NULL",
                (admin_id,),
            )

            # Convert every existing configured project into an auditable v1.
            projects = conn.execute("SELECT * FROM projects").fetchall()
            now_ts = datetime.now(timezone.utc).isoformat()
            for row in projects:
                project_id = row["project_id"]
                active_id = row["active_taxonomy_version_id"]
                active = None
                if active_id:
                    active = conn.execute(
                        "SELECT * FROM project_taxonomy_versions WHERE version_id = ? AND project_id = ?",
                        (active_id, project_id),
                    ).fetchone()

                if not active and row["issue_labels"]:
                    active_id = f"{project_id}_legacy_v1"
                    exists = conn.execute(
                        "SELECT version_id FROM project_taxonomy_versions WHERE version_id = ?",
                        (active_id,),
                    ).fetchone()
                    if not exists:
                        conn.execute(
                            "INSERT INTO project_taxonomy_versions "
                            "(version_id, project_id, status, source, prompt_context, issue_labels, stance_labels, action_labels, created_by, created_at, updated_at, activated_at) "
                            "VALUES (?, ?, 'active', 'legacy', ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                active_id, project_id, row["prompt_context"],
                                _legacy_labels_json(row["issue_labels"]),
                                _legacy_labels_json(row["stance_labels"]),
                                _legacy_labels_json(row["action_labels"]),
                                row["owner_user_id"], now_ts, now_ts, now_ts,
                            ),
                        )
                    active = conn.execute(
                        "SELECT * FROM project_taxonomy_versions WHERE version_id = ?",
                        (active_id,),
                    ).fetchone()

                if active:
                    # Normalize old comma-based version rows and repair status drift.
                    conn.execute(
                        "UPDATE project_taxonomy_versions SET status = 'active', "
                        "issue_labels = ?, stance_labels = ?, action_labels = ?, "
                        "updated_at = COALESCE(updated_at, created_at), "
                        "activated_at = COALESCE(activated_at, created_at) "
                        "WHERE version_id = ?",
                        (
                            _legacy_labels_json(active["issue_labels"]),
                            _legacy_labels_json(active["stance_labels"]),
                            _legacy_labels_json(active["action_labels"]),
                            active_id,
                        ),
                    )
                    conn.execute(
                        "UPDATE projects SET active_taxonomy_version_id = ?, status = 'active' WHERE project_id = ?",
                        (active_id, project_id),
                    )

            # Migration: Assign orphaned videos to default project
            conn.execute(
                "UPDATE videos SET project_id = ? WHERE project_id IS NULL OR project_id = ''",
                (DEFAULT_PROJECT_ID,)
            )

            # Existing completed inference used the active legacy taxonomy.
            conn.execute(
                "UPDATE comments SET taxonomy_version_id = ("
                "SELECT p.active_taxonomy_version_id FROM videos v "
                "JOIN projects p ON p.project_id = v.project_id "
                "WHERE v.video_id = comments.video_id"
                ") WHERE taxonomy_version_id IS NULL AND inference_status = 'completed'"
            )

            for idx in INDEXES:
                conn.execute(idx)


def get_projects(database_url: str = None, owner_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_db_connection(database_url) as conn:
        if owner_user_id is not None:
            rows = conn.execute("SELECT * FROM projects WHERE owner_user_id = ? ORDER BY created_at DESC;", (owner_user_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC;").fetchall()
        return [dict(r) for r in rows]


def get_project(project_id: str, database_url: str = None) -> Optional[Dict[str, Any]]:
    with get_db_connection(database_url) as conn:
        row = conn.execute("SELECT * FROM projects WHERE project_id = ?;", (project_id,)).fetchone()
        return dict(row) if row else None


def create_project(project_data: Dict[str, Any], database_url: str = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    # Provide default values for columns if not present in project_data
    payload = {
        "description": None,
        "owner_user_id": None,
        "goal_type": None,
        "goal_text": None,
        "status": "draft",
        "prompt_context": None,
        "issue_labels": None,
        "stance_labels": None,
        "action_labels": None,
        **project_data,
        "now": now
    }
    with get_db_connection(database_url) as conn:
        with conn:
            conn.execute(
                "INSERT INTO projects (project_id, project_name, description, owner_user_id, goal_type, goal_text, status, prompt_context, issue_labels, stance_labels, action_labels, created_at, updated_at) "
                "VALUES (:project_id, :project_name, :description, :owner_user_id, :goal_type, :goal_text, :status, :prompt_context, :issue_labels, :stance_labels, :action_labels, :now, :now);",
                payload
            )


def delete_project(project_id: str, database_url: str = None) -> None:
    with get_db_connection(database_url) as conn:
        with conn:
            # Only delete the project if there are no videos associated.
            video_count = conn.execute(
                "SELECT COUNT(*) FROM videos WHERE project_id = ?", (project_id,)
            ).fetchone()[0]
            if video_count > 0:
                raise ValueError("Project contains videos. Delete them first.")
            conn.execute("DELETE FROM projects WHERE project_id = ?;", (project_id,))


def get_projects_for_videos(video_ids: List[str], database_url: str = None) -> Dict[str, Dict[str, Any]]:
    if not video_ids:
        return {}
    ph = ",".join("?" for _ in video_ids)
    with get_db_connection(database_url) as conn:
        rows = conn.execute(
            f"SELECT v.video_id, p.* FROM videos v "
            f"JOIN projects p ON v.project_id = p.project_id "
            f"WHERE v.video_id IN ({ph});", video_ids
        ).fetchall()
        return {r["video_id"]: dict(r) for r in rows}
