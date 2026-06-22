"""Generate versioned project taxonomy drafts with the Gemini API."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.services.sampling_service import get_comment_sample_for_taxonomy
from backend.services.taxonomy_config import dumps_labels, validate_config
from backend.storage.db import get_db_connection
from backend.storage.projects_repo import get_project

logger = logging.getLogger("youtube_collector.gemini")

_LOCKS: Dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()

_current_key_idx = 0
_KEY_LOCK = threading.Lock()


class LabelDefinition(BaseModel):
    key: str
    name: str
    description: str
    examples: List[str] = Field(default_factory=list)


class TaxonomyDraft(BaseModel):
    prompt_context: str
    issues: List[LabelDefinition]
    stances: List[LabelDefinition]
    actions: List[LabelDefinition]


def _project_lock(project_id: str) -> threading.Lock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(project_id, threading.Lock())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_run(database_url: str, **values: Any) -> None:
    payload = {
        "run_id": values.get("run_id") or f"llm_{uuid.uuid4().hex}",
        "project_id": values["project_id"],
        "version_id": values.get("version_id"),
        "model": values.get("model"),
        "sample_count": values.get("sample_count", 0),
        "status": values.get("status", "failed"),
        "token_input": values.get("token_input"),
        "token_output": values.get("token_output"),
        "cache_hit": int(bool(values.get("cache_hit"))),
        "error_type": values.get("error_type"),
        "started_at": values.get("started_at") or _now(),
        "finished_at": values.get("finished_at") or _now(),
    }
    with get_db_connection(database_url) as conn:
        with conn:
            conn.execute(
                "INSERT INTO llm_generation_runs "
                "(run_id, project_id, version_id, model, sample_count, status, "
                "token_input, token_output, cache_hit, error_type, started_at, finished_at) "
                "VALUES (:run_id, :project_id, :version_id, :model, :sample_count, "
                ":status, :token_input, :token_output, :cache_hit, :error_type, "
                ":started_at, :finished_at)",
                payload,
            )


def _classify_error(exc: Exception) -> tuple[str, str, bool]:
    message = str(exc).lower()
    if any(token in message for token in ("429", "quota", "resourceexhausted")):
        return "quota_exceeded", "Quota Gemini habis. Gunakan editor manual atau coba lagi setelah cooldown.", False
    if any(token in message for token in ("api key", "invalid_argument", "unauthenticated", "401", "403")):
        return "invalid_api_key", "API key Gemini tidak valid atau tidak memiliki akses.", False
    if any(token in message for token in ("timeout", "deadline", "timed out")):
        return "timeout", "Permintaan Gemini timeout.", True
    if any(token in message for token in ("500", "502", "503", "504", "unavailable")):
        return "provider_error", "Layanan Gemini sedang bermasalah.", True
    return "request_failed", "Gemini gagal membuat taxonomy.", False


def _ensure_required_fallbacks(payload: Dict[str, Any]) -> Dict[str, Any]:
    fallbacks = {
        "issues": {
            "key": "lainnya", "name": "Lainnya",
            "description": "Topik lain yang tidak sesuai dengan issue khusus.", "examples": [],
        },
        "stances": {
            "key": "tidak_terdeteksi", "name": "Tidak Terdeteksi",
            "description": "Posisi komentator tidak dapat ditentukan.", "examples": [],
        },
        "actions": {
            "key": "tidak_terdeteksi", "name": "Tidak Terdeteksi",
            "description": "Niat tindakan tidak dapat ditentukan.", "examples": [],
        },
    }
    for axis, fallback in fallbacks.items():
        labels = payload.setdefault(axis, [])
        if not any(str(item.get("key", "")).lower() == fallback["key"] for item in labels):
            labels.append(fallback)
    return payload


def _create_client(api_key: str, timeout_ms: int):
    """Create the SDK client lazily so startup and tests never require a live API."""
    from google import genai

    return genai.Client(api_key=api_key, http_options={"timeout": timeout_ms})


def _create_generation_config(system_instruction: str):
    from google.genai import types

    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=TaxonomyDraft,
    )


def generate_taxonomy_draft(
    project_id: str,
    instructions: Optional[str] = None,
    database_url: str = None,
) -> Dict[str, Any]:
    lock = _project_lock(project_id)
    if not lock.acquire(blocking=False):
        return {"success": False, "error_code": "already_running", "error": "Generate taxonomy sedang berjalan."}
    try:
        return _generate(project_id, (instructions or "").strip()[:2000], database_url)
    finally:
        lock.release()


def _generate(project_id: str, instructions: str, database_url: str) -> Dict[str, Any]:
    if os.getenv("ENABLE_GEMINI_TAXONOMY", "false").lower() != "true":
        return {"success": False, "error_code": "disabled", "error": "Gemini taxonomy belum diaktifkan."}

    api_keys = [k.strip() for k in (os.getenv("GEMINI_API_KEY") or "").split(",") if k.strip()]
    if not api_keys:
        return {"success": False, "error_code": "missing_api_key", "error": "GEMINI_API_KEY belum diisi."}

    project = get_project(project_id, database_url)
    if not project:
        return {"success": False, "error_code": "not_found", "error": "Project tidak ditemukan."}

    minimum = int(os.getenv("GEMINI_MIN_SAMPLE_SIZE", "20"))
    maximum = int(os.getenv("GEMINI_SAMPLE_LIMIT", "100"))
    sample = get_comment_sample_for_taxonomy(project_id, database_url, minimum, maximum)
    if not sample["valid"]:
        return {"success": False, "error_code": "insufficient_sample", "error": sample["reason"], "sample_count": sample["count"]}

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    cache_material = json.dumps({
        "sample_hash": sample["hash"],
        "instruction": instructions,
        "project_name": project.get("project_name"),
        "goal_type": project.get("goal_type"),
        "goal_text": project.get("goal_text"),
        "model": model,
    }, sort_keys=True, ensure_ascii=False)
    request_hash = hashlib.sha256(cache_material.encode("utf-8")).hexdigest()

    with get_db_connection(database_url) as conn:
        cached = conn.execute(
            "SELECT version_id FROM project_taxonomy_versions "
            "WHERE project_id = ? AND sample_hash = ? AND status = 'draft' "
            "ORDER BY created_at DESC LIMIT 1",
            (project_id, request_hash),
        ).fetchone()
    if cached:
        _record_run(
            database_url, project_id=project_id, version_id=cached["version_id"],
            model=model, sample_count=sample["count"], status="success", cache_hit=True,
        )
        return {"success": True, "cache_hit": True, "version_id": cached["version_id"]}

    daily_limit = int(os.getenv("GEMINI_MAX_GENERATIONS_PER_PROJECT_PER_DAY", "3"))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_db_connection(database_url) as conn:
        used = conn.execute(
            "SELECT COUNT(*) FROM llm_generation_runs WHERE project_id = ? "
            "AND cache_hit = 0 AND started_at LIKE ?",
            (project_id, f"{today}%"),
        ).fetchone()[0]
    if used >= daily_limit:
        return {"success": False, "error_code": "daily_limit", "error": "Batas generate harian project sudah tercapai."}

    prompt = {
        "project": {
            "name": project.get("project_name"),
            "goal_type": project.get("goal_type"),
            "goal_text": project.get("goal_text"),
            "description": project.get("description"),
        },
        "user_refinement_instruction": instructions or None,
        "comment_samples": sample["sample"],
    }
    system_instruction = (
        "Rancang taxonomy komentar YouTube berbahasa Indonesia untuk project ini. "
        "Buat 5-10 issues termasuk 'lainnya', 3-8 stances termasuk "
        "'tidak_terdeteksi', dan 4-8 actions termasuk 'tidak_terdeteksi'. "
        "Setiap key wajib snake_case, unik, dan setiap label wajib memiliki nama, "
        "deskripsi yang tidak tumpang tindih, serta maksimal tiga contoh."
    )

    run_id = f"llm_{uuid.uuid4().hex}"
    started_at = _now()
    timeout_ms = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "30")) * 1000
    global _current_key_idx
    start_idx = _current_key_idx
    num_keys = len(api_keys)

    response = None
    last_error: Optional[Exception] = None
    status, public_error = "request_failed", "Gemini gagal membuat taxonomy."

    for i in range(num_keys):
        key_idx = (start_idx + i) % num_keys
        api_key = api_keys[key_idx]

        try:
            client = _create_client(api_key, timeout_ms)
            generation_config = _create_generation_config(system_instruction)
        except ImportError:
            return {"success": False, "error_code": "dependency_missing", "error": "Dependency google-genai belum terinstal."}

        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=json.dumps(prompt, ensure_ascii=False),
                    config=generation_config,
                )
                break
            except Exception as exc:  # SDK exposes provider-specific exception classes.
                last_error = exc
                status, public_error, retryable = _classify_error(exc)
                if status in ("quota_exceeded", "invalid_api_key"):
                    break  # Pindah ke API key selanjutnya
                if not retryable or attempt == 2:
                    break
                time.sleep(2 ** (attempt + 1))
                
        if response is not None:
            with _KEY_LOCK:
                _current_key_idx = key_idx
            break

    if response is None:
        logger.error("Gemini taxonomy request failed: %s", status)
        _record_run(
            database_url, run_id=run_id, project_id=project_id, model=model,
            sample_count=sample["count"], status=status, cache_hit=False,
            error_type=type(last_error).__name__ if last_error else status,
            started_at=started_at,
        )
        return {"success": False, "error_code": status, "error": public_error}

    try:
        if isinstance(getattr(response, "parsed", None), TaxonomyDraft):
            raw = response.parsed.model_dump()
        else:
            raw = TaxonomyDraft.model_validate_json(response.text).model_dump()
        raw = _ensure_required_fallbacks(raw)
        config = validate_config(raw["prompt_context"], raw["issues"], raw["stances"], raw["actions"])
    except Exception as exc:
        _record_run(
            database_url, run_id=run_id, project_id=project_id, model=model,
            sample_count=sample["count"], status="invalid_response", cache_hit=False,
            error_type=type(exc).__name__, started_at=started_at,
        )
        return {"success": False, "error_code": "invalid_response", "error": f"Respons Gemini tidak valid: {exc}"}

    version_id = f"{project_id}_v_{uuid.uuid4().hex[:10]}"
    finished_at = _now()
    usage = getattr(response, "usage_metadata", None)
    token_input = getattr(usage, "prompt_token_count", None)
    token_output = getattr(usage, "candidates_token_count", None)
    with get_db_connection(database_url) as conn:
        with conn:
            conn.execute(
                "INSERT INTO project_taxonomy_versions "
                "(version_id, project_id, status, source, prompt_context, issue_labels, "
                "stance_labels, action_labels, regenerate_instruction, model, sample_hash, "
                "created_by, created_at, updated_at) "
                "VALUES (?, ?, 'draft', 'gemini', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    version_id, project_id, config["prompt_context"],
                    dumps_labels(config["issues"]), dumps_labels(config["stances"]),
                    dumps_labels(config["actions"]), instructions or None, model,
                    request_hash, project.get("owner_user_id"), finished_at, finished_at,
                ),
            )
    _record_run(
        database_url, run_id=run_id, project_id=project_id, version_id=version_id,
        model=model, sample_count=sample["count"], status="success", cache_hit=False,
        token_input=token_input, token_output=token_output,
        started_at=started_at, finished_at=finished_at,
    )
    return {"success": True, "cache_hit": False, "version_id": version_id}
