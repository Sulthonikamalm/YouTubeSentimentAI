"""
test_inference_service.py — Unit tests for backend.services.inference_service.

Uses a temporary file-based SQLite and mocks Ollama to avoid touching real
database or external services. File-based SQLite shares state across connections,
unlike :memory: which is per-connection.
"""

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.storage import repository
from backend.services.inference_service import (
    infer_comment,
    infer_pending,
    infer_all,
)
import pytest


@pytest.fixture(autouse=True)
def mock_ollama_for_tests():
    """Mock Ollama to return rule-based fallback results (no real Ollama needed)."""
    with patch("backend.services.inference_service.analyze_comments_batch", return_value={}):
        yield


def _make_test_db(tmp_path):
    """Create a temporary file-based database with schema applied."""
    db_file = tmp_path / f"test_inf_{uuid.uuid4().hex}.db"
    db_url = f"sqlite:///{db_file}"
    repository.init_db(db_url)
    return db_url


def _insert_test_comment(db_url, comment_id="c1", video_id="vid1",
                         is_reply=False, parent_id=None,
                         comment_text="test komentar", inference_status=None):
    """Insert a test comment with optional inference_status."""
    comment = {
        "comment_id": comment_id,
        "video_id": video_id,
        "parent_id": parent_id,
        "is_reply": is_reply,
        "author_name": "TestUser",
        "author_channel_id": "UC_test",
        "comment_text": comment_text,
        "text_original": comment_text,
        "text_display": comment_text,
        "published_at": "2026-06-17T10:00:00Z",
        "updated_at": "2026-06-17T10:00:00Z",
        "like_count": 0,
        "reply_count": 0,
        "collected_at": "2026-06-17T10:00:00Z",
        "is_baseline": True,
        "is_deleted": False,
        "last_seen_at": "2026-06-17T10:00:00Z",
        "raw_json_hash": "hash123",
        "raw_json": "{}",
    }
    if inference_status is not None:
        comment["inference_status"] = inference_status
    repository.save_comment(comment, db_url)
    return comment


# --- Tests ---

def test_inference_service_updates_database(tmp_path):
    """After infer_comment, inference columns are populated in DB (rule-based fallback)."""
    db_url = _make_test_db(tmp_path)
    _insert_test_comment(db_url, comment_id="c_inf1",
                         comment_text="pemerintah gagal, rakyat menderita karena korupsi")

    result = infer_comment("c_inf1", database_url=db_url)

    assert result["inference_status"] == "completed"
    assert result["issue_label"] is not None
    assert result["stance_label"] is not None
    assert result["action_intent_label"] is not None
    assert result["interpretation_short"] is not None

    # Verify DB was updated
    comment = repository.get_comment("c_inf1", db_url)
    assert comment["inference_status"] == "completed"
    assert comment["issue_label"] is not None
    assert comment["interpretation_short"] is not None


def test_infer_pending_batch(tmp_path):
    """Pending comments are processed in batch."""
    db_url = _make_test_db(tmp_path)
    _insert_test_comment(db_url, comment_id="p1",
                         comment_text="harga beras mahal sekali", inference_status="pending")
    _insert_test_comment(db_url, comment_id="p2",
                         comment_text="video bagus, terima kasih", inference_status="pending")
    _insert_test_comment(db_url, comment_id="p3",
                         comment_text="korupsi merajalela", inference_status="pending")

    summary = infer_pending(limit=10, database_url=db_url)

    assert summary["processed"] == 3
    assert summary["completed"] == 3
    assert summary["failed"] == 0

    # Verify all comments are now completed
    for cid in ["p1", "p2", "p3"]:
        c = repository.get_comment(cid, db_url)
        assert c["inference_status"] == "completed"


def test_infer_pending_skips_completed(tmp_path):
    """Already completed comments are not re-processed."""
    db_url = _make_test_db(tmp_path)
    _insert_test_comment(db_url, comment_id="done1",
                         comment_text="sudah selesai", inference_status="completed")
    _insert_test_comment(db_url, comment_id="pending1",
                         comment_text="belum selesai", inference_status="pending")

    summary = infer_pending(limit=10, database_url=db_url)

    assert summary["processed"] == 1  # Only pending1


def test_infer_all_requires_confirm(tmp_path):
    """infer_all does nothing without confirm=True."""
    db_url = _make_test_db(tmp_path)

    summary = infer_all(confirm=False, database_url=db_url)
    assert summary["processed"] == 0
    assert "confirm" in summary.get("note", "").lower()


def test_infer_all_with_confirm(tmp_path):
    """infer_all re-processes all comments when confirm=True."""
    db_url = _make_test_db(tmp_path)
    _insert_test_comment(db_url, comment_id="a1",
                         comment_text="komentar pertama", inference_status="completed")
    _insert_test_comment(db_url, comment_id="a2",
                         comment_text="komentar kedua", inference_status="pending")

    summary = infer_all(confirm=True, database_url=db_url)
    assert summary["processed"] == 2
    assert summary["completed"] == 2


def test_infer_comment_not_found(tmp_path):
    """Non-existent comment_id → failed status."""
    db_url = _make_test_db(tmp_path)

    result = infer_comment("nonexistent_id", database_url=db_url)
    assert result["inference_status"] == "failed"
    assert "not found" in (result["inference_error"] or "").lower()


def test_reply_uses_parent_context(tmp_path):
    """Reply comment uses parent_text for context."""
    db_url = _make_test_db(tmp_path)
    # Insert parent
    _insert_test_comment(db_url, comment_id="parent1",
                         comment_text="menurut saya pemerintah sudah bagus program ini",
                         is_reply=False)
    # Insert reply (short text)
    _insert_test_comment(db_url, comment_id="reply1",
                         comment_text="setuju",
                         is_reply=True, parent_id="parent1")

    result = infer_comment("reply1", database_url=db_url)
    assert result["inference_status"] == "completed"
    assert result["interpretation_short"] is not None


def test_inference_with_empty_comment_text(tmp_path):
    """Empty comment text → inference completes with fallback."""
    db_url = _make_test_db(tmp_path)
    _insert_test_comment(db_url, comment_id="empty1", comment_text="")

    result = infer_comment("empty1", database_url=db_url)
    assert result["inference_status"] == "completed"


def test_ollama_result_used_when_available(tmp_path):
    """When Ollama returns results, they should be used instead of rule-based."""
    db_url = _make_test_db(tmp_path)
    _insert_test_comment(db_url, comment_id="ollama1",
                         comment_text="pemerintah gagal total")

    mock_result = {
        "ollama1": {
            "sentiment": "negative",
            "sentiment_confidence": 0.95,
            "issue_label": "pemerintahan_kebijakan",
            "stance_label": "kritik_pemerintah",
            "action_intent_label": "menuntut_akuntabilitas",
            "interpretation_short": "Komentar mengkritik pemerintah.",
            "model_version": "sahabatai-8b-ollama-v1",
            "inference_status": "completed",
            "inference_error": None,
            "inferred_at": "2026-06-19T12:00:00Z",
        }
    }

    with patch("backend.services.inference_service.analyze_comments_batch", return_value=mock_result):
        result = infer_comment("ollama1", database_url=db_url)

    comment = repository.get_comment("ollama1", db_url)
    assert comment["inference_status"] == "completed"
    assert comment["sentiment"] == "negative"
    assert comment["model_version"] == "sahabatai-8b-ollama-v1"


def test_inference_abort(tmp_path):
    """Setting ABORT_INFERENCE_EVENT aborts the batch loop early."""
    db_url = _make_test_db(tmp_path)
    for i in range(6):
        _insert_test_comment(db_url, comment_id=f"c_abort_{i}",
                             comment_text=f"komentar ke {i}", inference_status="pending")

    from backend.services.inference_service import ABORT_INFERENCE_EVENT

    def side_effect(chunk, project=None):
        ABORT_INFERENCE_EVENT.set()
        return {item["comment_id"]: {
            "sentiment": "neutral",
            "sentiment_confidence": 1.0,
            "issue_label": "lainnya",
            "stance_label": "netral_informatif",
            "action_intent_label": "tidak_terdeteksi",
            "interpretation_short": "neutral",
            "model_version": "test",
            "inference_status": "completed",
            "inference_error": None,
            "inferred_at": "2026-06-19T12:00:00Z",
        } for item in chunk}

    with patch("backend.services.inference_service.analyze_comments_batch", side_effect=side_effect):
        summary = infer_pending(limit=10, database_url=db_url)

    assert summary["processed"] == 3
    assert summary["completed"] == 3

    for i in range(3):
        assert repository.get_comment(f"c_abort_{i}", db_url)["inference_status"] == "completed"
    for i in range(3, 6):
        assert repository.get_comment(f"c_abort_{i}", db_url)["inference_status"] == "pending"

