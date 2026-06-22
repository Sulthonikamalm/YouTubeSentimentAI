import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.services.gemini_service import generate_taxonomy_draft
from backend.storage import repository
from backend.storage.db import get_db_connection


def _labels(prefix, count, required=None):
    labels = [
        {
            "key": f"{prefix}_{index}",
            "name": f"{prefix.title()} {index}",
            "description": f"Kategori {prefix} nomor {index}.",
            "examples": [f"contoh {index}"],
        }
        for index in range(1, count + 1)
    ]
    if required:
        labels[-1] = {
            "key": required,
            "name": required.replace("_", " ").title(),
            "description": f"Kategori fallback {required}.",
            "examples": [],
        }
    return labels


def _valid_response():
    payload = {
        "prompt_context": "Baca komentar sebagai respons terhadap layanan publik.",
        "issues": _labels("issue", 5, "lainnya"),
        "stances": _labels("stance", 3, "tidak_terdeteksi"),
        "actions": _labels("action", 4, "tidak_terdeteksi"),
    }
    return SimpleNamespace(
        parsed=None,
        text=json.dumps(payload),
        usage_metadata=SimpleNamespace(prompt_token_count=120, candidates_token_count=80),
    )


@pytest.fixture
def gemini_db(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'gemini.db'}"
    repository.init_db(db_url)
    with get_db_connection(db_url) as conn:
        admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()[0]
        with conn:
            conn.execute(
                "INSERT INTO projects (project_id, project_name, owner_user_id, goal_type, goal_text, status) "
                "VALUES ('test_project', 'Test Project', ?, 'keluhan', 'Cari masalah utama', 'draft')",
                (admin_id,),
            )
            conn.execute(
                "INSERT INTO videos (video_id, video_url, video_title, channel_title, project_id) "
                "VALUES ('video_test', 'https://youtu.be/video_test', 'Video Test', 'Channel Test', 'test_project')"
            )
            for index in range(20):
                timestamp = f"2026-06-{(index % 20) + 1:02d}T10:00:00+00:00"
                conn.execute(
                    "INSERT INTO comments (comment_id, video_id, is_reply, comment_text, published_at, "
                    "updated_at, is_baseline, is_deleted) VALUES (?, 'video_test', 0, ?, ?, ?, ?, 0)",
                    (f"comment_{index}", f"Komentar valid {index}", timestamp, timestamp, int(index < 10)),
                )
    return db_url


@pytest.fixture(autouse=True)
def gemini_env(monkeypatch):
    monkeypatch.setenv("ENABLE_GEMINI_TAXONOMY", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    monkeypatch.setenv("GEMINI_MIN_SAMPLE_SIZE", "20")
    monkeypatch.setenv("GEMINI_SAMPLE_LIMIT", "100")
    monkeypatch.setenv("GEMINI_MAX_GENERATIONS_PER_PROJECT_PER_DAY", "3")


def test_generate_taxonomy_draft_success_and_cache(gemini_db):
    client = MagicMock()
    client.models.generate_content.return_value = _valid_response()
    with patch("backend.services.gemini_service._create_client", return_value=client), \
         patch("backend.services.gemini_service._create_generation_config", return_value={"mock": True}):
        first = generate_taxonomy_draft("test_project", None, gemini_db)
        second = generate_taxonomy_draft("test_project", None, gemini_db)

    assert first["success"] is True
    assert first["cache_hit"] is False
    assert second == {"success": True, "cache_hit": True, "version_id": first["version_id"]}
    assert client.models.generate_content.call_count == 1

    with get_db_connection(gemini_db) as conn:
        version = conn.execute(
            "SELECT * FROM project_taxonomy_versions WHERE version_id = ?", (first["version_id"],)
        ).fetchone()
        runs = conn.execute(
            "SELECT status, cache_hit, token_input, token_output FROM llm_generation_runs "
            "WHERE project_id = 'test_project' ORDER BY started_at"
        ).fetchall()
    assert version["status"] == "draft"
    assert version["source"] == "gemini"
    assert json.loads(version["issue_labels"])[-1]["key"] == "lainnya"
    assert [(row["status"], row["cache_hit"]) for row in runs] == [("success", 0), ("success", 1)]
    assert runs[0]["token_input"] == 120
    assert runs[0]["token_output"] == 80


def test_quota_error_is_not_retried(gemini_db):
    client = MagicMock()
    client.models.generate_content.side_effect = Exception("429 ResourceExhausted quota")
    with patch("backend.services.gemini_service._create_client", return_value=client), \
         patch("backend.services.gemini_service._create_generation_config", return_value={}):
        result = generate_taxonomy_draft("test_project", "buat lebih spesifik", gemini_db)

    assert result["success"] is False
    assert result["error_code"] == "quota_exceeded"
    assert client.models.generate_content.call_count == 1


def test_fourth_real_generation_is_rejected(gemini_db):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_db_connection(gemini_db) as conn:
        with conn:
            for index in range(3):
                conn.execute(
                    "INSERT INTO llm_generation_runs "
                    "(run_id, project_id, model, sample_count, status, cache_hit, started_at, finished_at) "
                    "VALUES (?, 'test_project', 'mock', 20, 'success', 0, ?, ?)",
                    (f"prior_{index}", f"{today}T0{index}:00:00+00:00", f"{today}T0{index}:01:00+00:00"),
                )

    with patch("backend.services.gemini_service._create_client") as create_client:
        result = generate_taxonomy_draft("test_project", "instruksi baru", gemini_db)

    assert result["success"] is False
    assert result["error_code"] == "daily_limit"
    create_client.assert_not_called()


def test_invalid_structured_output_does_not_create_draft(gemini_db):
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(
        parsed=None, text='{"prompt_context":"x","issues":[],"stances":[],"actions":[]}', usage_metadata=None
    )
    with patch("backend.services.gemini_service._create_client", return_value=client), \
         patch("backend.services.gemini_service._create_generation_config", return_value={}):
        result = generate_taxonomy_draft("test_project", "invalid response test", gemini_db)

    assert result["success"] is False
    assert result["error_code"] == "invalid_response"
    with get_db_connection(gemini_db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM project_taxonomy_versions WHERE project_id = 'test_project'"
        ).fetchone()[0]
    assert count == 0
