import pytest
import os
import sqlite3
from unittest.mock import patch, MagicMock
from backend.services.gemini_service import generate_taxonomy_draft

@pytest.fixture
def test_db():
    # Setup in-memory DB and basic schema
    conn = sqlite3.connect(':memory:')
    conn.execute('''
        CREATE TABLE llm_generation_runs (
            run_id TEXT, project_id TEXT, model TEXT, sample_count INTEGER,
            status TEXT, cache_hit INTEGER, error_type TEXT, started_at TEXT, finished_at TEXT,
            version_id TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE projects (
            project_id TEXT PRIMARY KEY, goal_text TEXT, goal_type TEXT
        )
    ''')
    conn.execute("INSERT INTO projects (project_id) VALUES ('test_proj')")
    
    yield conn
    conn.close()

@patch('backend.services.gemini_service.get_db_connection')
@patch('backend.services.gemini_service.get_project')
@patch('backend.services.gemini_service.get_comment_sample_for_taxonomy')
@patch('backend.services.gemini_service.genai.Client')
def test_generate_taxonomy_draft_success(mock_client_class, mock_sample, mock_get_proj, mock_db, monkeypatch, test_db):
    # Setup mocks
    monkeypatch.setenv("ENABLE_GEMINI_TAXONOMY", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")
    
    mock_db.return_value = test_db
    
    mock_get_proj.return_value = {"project_id": "test_proj", "goal_text": "Goal"}
    mock_sample.return_value = {
        "valid": True,
        "hash": "dummy_hash",
        "count": 20,
        "sample": [{"text": "Sample comment 1"}]
    }

    # Setup GenAI Mock
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Provide raw text instead of parsed, since gemini_service parses it
    mock_response.text = '{"issues": [{"key": "harga_beras", "name": "Harga Beras"}], "stances": [], "actions": []}'
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    # Execute
    res = generate_taxonomy_draft("test_proj", None, "sqlite:///:memory:")
    
    # Assertions
    assert res["success"] is True
    assert res["cache_hit"] is False
    assert "version_id" in res

    # Verify fallback injection worked via the DB log or directly if we were unit testing inner funcs
    # But for e2e function mock, we just check it returns success.
    
@patch('backend.services.gemini_service.get_db_connection')
@patch('backend.services.gemini_service.get_project')
@patch('backend.services.gemini_service.get_comment_sample_for_taxonomy')
@patch('backend.services.gemini_service.genai.Client')
def test_generate_taxonomy_draft_quota_error(mock_client_class, mock_sample, mock_get_proj, mock_db, monkeypatch, test_db):
    monkeypatch.setenv("ENABLE_GEMINI_TAXONOMY", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")
    
    mock_db.return_value = test_db
    mock_get_proj.return_value = {"project_id": "test_proj"}
    mock_sample.return_value = {"valid": True, "hash": "dummy", "count": 20, "sample": []}

    mock_client = MagicMock()
    # Trigger a 429 quota error
    mock_client.models.generate_content.side_effect = Exception("429 ResourceExhausted")
    mock_client_class.return_value = mock_client

    res = generate_taxonomy_draft("test_proj", None, "sqlite:///:memory:")
    
    assert res["success"] is False
    assert "Quota Gemini" in res["error"]
    
    # Verify no retries happened (only called once)
    assert mock_client.models.generate_content.call_count == 1
