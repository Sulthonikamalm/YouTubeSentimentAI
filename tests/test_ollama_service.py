"""
test_ollama_service.py — Unit tests for backend.ml.ollama_service.

Tests text normalization, prompt building, response parsing, and
health check logic. Ollama HTTP calls are mocked.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.ml.ollama_service import (
    normalize_text,
    build_context_text,
    build_prompt,
    _parse_label_response,
    analyze_comments_batch,
    check_ollama_health,
    get_ollama_settings,
)


# --- Text Normalization Tests ---

def test_normalize_text_basic():
    assert normalize_text("Ini TEKS BIASA") == "ini teks biasa"

def test_normalize_text_slang():
    assert normalize_text("gk mau yg bgtt") == "tidak mau yang banget"

def test_normalize_text_empty():
    assert normalize_text("") == ""
    assert normalize_text(None) == ""

def test_normalize_text_url_strip():
    assert "http" not in normalize_text("cek https://example.com sekarang")

def test_normalize_text_html_strip():
    assert normalize_text("<b>bold</b> text") == "bold text"

def test_normalize_text_elongation():
    """Elongated chars reduced to 2."""
    result = normalize_text("Mantaaap sekaliiii")
    assert "mantaap" in result
    assert "sekaliiii" not in result

def test_normalize_text_mention_strip():
    result = normalize_text("@username halo #trending apa kabar")
    assert "@" not in result
    assert "#" not in result


# --- Context Text Tests ---

def test_build_context_text_plain():
    assert build_context_text("halo dunia", False, None) == "halo dunia"

def test_build_context_text_reply():
    result = build_context_text("setuju", True, "pemerintah sudah bagus")
    assert "parent_context" in result
    assert "reply_text" in result
    assert "setuju" in result

def test_build_context_text_reply_no_parent():
    result = build_context_text("setuju", True, None)
    assert result == "setuju"


# --- Prompt Builder Tests ---

def test_build_prompt_structure():
    prompt = build_prompt("test comment", "parent says")
    assert "test comment" in prompt
    assert "parent says" in prompt or "KONTEKS INDUK" in prompt
    assert "sentiment" in prompt
    assert "CONTOH" in prompt


# --- Response Parsing Tests ---

def test_parse_label_response_valid_json():
    response = '{"sentiment": "negative", "issue": "ekonomi_rakyat", "stance": "kritik_pemerintah", "action": "menuntut_akuntabilitas"}'
    result = _parse_label_response(response)
    assert result is not None
    assert result["sentiment"] == "negative"
    assert result["issue_label"] == "ekonomi_rakyat"
    assert result["stance_label"] == "kritik_pemerintah"
    assert result["action_intent_label"] == "menuntut_akuntabilitas"

def test_parse_label_response_with_markdown_fences():
    response = '```json\n{"sentiment": "positive", "issue": "pemerintahan_kebijakan"}\n```'
    result = _parse_label_response(response)
    assert result is not None
    assert result["sentiment"] == "positive"
    assert result["issue_label"] == "pemerintahan_kebijakan"

def test_parse_label_response_invalid_json():
    result = _parse_label_response("not valid json at all")
    assert result is None

def test_parse_label_response_empty():
    result = _parse_label_response("")
    assert result is None

def test_parse_label_response_json_with_preamble():
    response = 'Here is the analysis:\n{"sentiment": "neutral", "issue": "lainnya"}\nDone.'
    result = _parse_label_response(response)
    assert result is not None
    assert result["sentiment"] == "neutral"


# --- Health Check Tests ---

@patch("backend.ml.ollama_service.requests.get")
def test_health_check_online(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [{"name": "csalab/sahabatai1:llama3_instruct_Q4_K_M"}]
    }
    mock_get.return_value = mock_resp

    result = check_ollama_health()
    assert result["server_online"] is True
    assert result["model_loaded"] is True

@patch("backend.ml.ollama_service.requests.get")
def test_health_check_model_not_loaded(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"models": [{"name": "some-other-model:latest"}]}
    mock_get.return_value = mock_resp

    result = check_ollama_health()
    assert result["server_online"] is True
    assert result["model_loaded"] is False

@patch("backend.ml.ollama_service.requests.get")
def test_health_check_connection_error(mock_get):
    import requests
    mock_get.side_effect = requests.ConnectionError("Connection refused")

    result = check_ollama_health()
    assert result["server_online"] is False
    assert result["error"] is not None


# --- Batch Analysis Tests ---

@patch("backend.ml.ollama_service._call_ollama")
def test_analyze_batch_success(mock_call):
    mock_call.return_value = '{"sentiment": "negative", "issue": "ekonomi_rakyat", "stance": "kritik_pemerintah", "action": "menuntut_akuntabilitas"}'
    comments = [{"comment_id": "c1", "comment_text": "harga beras mahal"}]
    results = analyze_comments_batch(comments)
    assert "c1" in results
    assert results["c1"]["sentiment"] == "negative"
    assert results["c1"]["model_version"] == "sahabatai-8b-ollama-v1"

@patch("backend.ml.ollama_service._call_ollama")
def test_analyze_batch_ollama_failure(mock_call):
    mock_call.return_value = None
    comments = [{"comment_id": "c1", "comment_text": "test"}]
    results = analyze_comments_batch(comments)
    assert results == {}

def test_analyze_batch_empty():
    results = analyze_comments_batch([])
    assert results == {}
    assert results == {}


# --- Settings Tests ---

def test_get_ollama_settings_defaults():
    with patch.dict("os.environ", {}, clear=True):
        settings = get_ollama_settings()
        assert settings["base_url"] == "http://localhost:11434"
        assert "csalab" in settings["model"]
        assert settings["timeout"] == 300

def test_get_ollama_settings_custom():
    with patch.dict("os.environ", {
        "OLLAMA_BASE_URL": "http://remote:11434",
        "OLLAMA_MODEL": "custom-model",
        "OLLAMA_TIMEOUT": "60"
    }):
        settings = get_ollama_settings()
        assert settings["base_url"] == "http://remote:11434"
        assert settings["model"] == "custom-model"
        assert settings["timeout"] == 60
