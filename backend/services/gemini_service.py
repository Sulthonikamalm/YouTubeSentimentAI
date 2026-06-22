"""
gemini_service.py — Wraps the Google GenAI SDK to generate project taxonomy drafts.
"""

import os
import json
import logging
import time
import uuid
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

from backend.storage.db import get_db_connection
from backend.storage.projects_repo import get_project
from backend.services.sampling_service import get_comment_sample_for_taxonomy

logger = logging.getLogger("youtube_collector.gemini")

# Global lock manager for generation jobs
GENERATION_LOCKS = {}
LOCK_MANAGER = threading.Lock()

def _get_project_lock(project_id: str) -> threading.Lock:
    with LOCK_MANAGER:
        if project_id not in GENERATION_LOCKS:
            GENERATION_LOCKS[project_id] = threading.Lock()
        return GENERATION_LOCKS[project_id]

class LabelDefinition(BaseModel):
    key: str = Field(description="Unique key, lowercase with underscores. (e.g. 'harga_bahan_pokok')")
    name: str = Field(description="Human readable name of the label.")
    description: str = Field(description="Clear explanation of what comments fall into this label.")
    examples: List[str] = Field(description="List of 2-3 sample phrases for this label.")

class TaxonomyDraft(BaseModel):
    prompt_context: str = Field(description="Prompt context instructions for the local classification AI.")
    issues: List[LabelDefinition] = Field(description="List of 5-10 issue labels. MUST include a 'lainnya' key.")
    stances: List[LabelDefinition] = Field(description="List of 3-8 stance labels. MUST include a 'tidak_terdeteksi' key.")
    actions: List[LabelDefinition] = Field(description="List of 4-8 action intent labels. MUST include a 'tidak_terdeteksi' key.")

def generate_taxonomy_draft(project_id: str, 
                            instructions: Optional[str] = None,
                            database_url: str = None) -> Dict[str, Any]:
    lock = _get_project_lock(project_id)
    if not lock.acquire(blocking=False):
        return {"success": False, "error": "Proses generate sedang berjalan untuk project ini. Silakan tunggu."}
        
    try:
        return _generate_taxonomy_draft_internal(project_id, instructions, database_url)
    finally:
        lock.release()

def _generate_taxonomy_draft_internal(project_id: str, 
                                      instructions: Optional[str] = None,
                                      database_url: str = None) -> Dict[str, Any]:
    # 1. Environment Config
    enabled = os.getenv("ENABLE_GEMINI_TAXONOMY", "false").lower() == "true"
    if not enabled:
        return {"success": False, "error": "Gemini taxonomy generation is disabled in .env"}
        
    api_key_env = os.getenv("GEMINI_API_KEY")
    if not api_key_env:
        return {"success": False, "error": "GEMINI_API_KEY is missing from environment variables."}
        
    api_keys = [k.strip() for k in api_key_env.split(",") if k.strip()]
    if not api_keys:
        return {"success": False, "error": "No valid API keys found in GEMINI_API_KEY."}

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    max_generations_per_day = int(os.getenv("GEMINI_MAX_GENERATIONS_PER_PROJECT_PER_DAY", "3"))
    timeout_sec = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))

    # 2. Check Generation Quota for Today
    today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_db_connection(database_url) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM llm_generation_runs "
            "WHERE project_id = ? AND status = 'success' AND cache_hit = 0 AND started_at LIKE ?",
            (project_id, f"{today_prefix}%")
        ).fetchone()[0]
        if count >= max_generations_per_day:
            return {"success": False, "error": "Daily generation quota exceeded for this project."}

    # 3. Get Project details
    project = get_project(project_id, database_url)
    if not project:
        return {"success": False, "error": "Project not found."}

    # 4. Get Comment Sample
    min_sample = int(os.getenv("GEMINI_MIN_SAMPLE_SIZE", "20"))
    max_sample = int(os.getenv("GEMINI_SAMPLE_LIMIT", "100"))
    sample_result = get_comment_sample_for_taxonomy(project_id, database_url, min_sample=min_sample, max_sample=max_sample)
    if not sample_result["valid"]:
        return {"success": False, "error": sample_result["reason"]}
        
    sample_hash = sample_result["hash"]
    sample_count = sample_result["count"]
    
    # 5. Build Combined Hash (Hash = Sample Hash + Instructions + Goal)
    combined_input = f"{sample_hash}_{instructions or ''}_{project.get('goal_text', '')}_{project.get('goal_type', '')}"
    import hashlib
    full_hash = hashlib.sha256(combined_input.encode("utf-8")).hexdigest()

    # 6. Check Cache
    with get_db_connection(database_url) as conn:
        cached = conn.execute(
            "SELECT version_id, prompt_context, issue_labels, stance_labels, action_labels "
            "FROM project_taxonomy_versions "
            "WHERE project_id = ? AND sample_hash = ? AND status = 'draft' "
            "ORDER BY created_at DESC LIMIT 1",
            (project_id, full_hash)
        ).fetchone()
        
        if cached:
            # Record Cache Hit
            run_id = f"run_{uuid.uuid4().hex}"
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO llm_generation_runs (run_id, project_id, version_id, model, sample_count, status, cache_hit, started_at, finished_at) "
                "VALUES (?, ?, ?, ?, ?, 'success', 1, ?, ?)",
                (run_id, project_id, cached["version_id"], model, sample_count, now, now)
            )
            return {"success": True, "cache_hit": True, "version_id": cached["version_id"]}

    # 7. Prepare Prompt
    system_instruction = (
        "You are an expert social media analyst and taxonomy designer. "
        "Your task is to analyze a sample of comments and generate a structured taxonomy (issues, stances, action intents) "
        "that will be used by a local LLM to classify all comments in this project.\n"
        "Follow these rules strictly:\n"
        "1. Keys must be snake_case (e.g. 'harga_beras').\n"
        "2. The 'issues' array MUST contain a label with key 'lainnya'.\n"
        "3. The 'stances' array MUST contain a label with key 'tidak_terdeteksi'.\n"
        "4. The 'actions' array MUST contain a label with key 'tidak_terdeteksi'.\n"
        "5. The 'prompt_context' should explain to the local LLM how to distinguish ambiguous categories."
    )
    
    prompt = (
        f"Project Goal Type: {project.get('goal_type', 'N/A')}\n"
        f"Project Goal Description: {project.get('goal_text', 'N/A')}\n"
    )
    if instructions:
        prompt += f"\nUser Edit Instructions:\n{instructions}\n"
        
    prompt += f"\nSample Comments ({sample_count} comments):\n"
    prompt += json.dumps(sample_result["sample"], indent=2, ensure_ascii=False)

    run_id = f"run_{uuid.uuid4().hex}"
    start_time = datetime.now(timezone.utc).isoformat()
    
    client = genai.Client(api_key=api_keys[0], http_options={'timeout': timeout_sec * 1000})
    response = None
    last_error = None
    
    max_retries = 2
    backoff = 2.0
    run_status = "failed"
    
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2, # Low temp for stable taxonomy
                    response_mime_type="application/json",
                    response_schema=TaxonomyDraft,
                ),
            )
            run_status = "success"
            break
        except Exception as e:
            last_error = e
            err_msg = str(e).lower()
            if "429" in err_msg or "quota" in err_msg or "resourceexhausted" in err_msg:
                run_status = "quota_exceeded"
                break # Do NOT retry on quota limits
            
            if attempt < max_retries:
                time.sleep(backoff * (2 ** attempt))

    if not response:
        logger.error(f"Gemini taxonomy generation failed: {last_error}")
        finish_time = datetime.now(timezone.utc).isoformat()
        error_type = type(last_error).__name__ if last_error else "UnknownError"
        with get_db_connection(database_url) as conn:
            with conn:
                conn.execute(
                    "INSERT INTO llm_generation_runs (run_id, project_id, model, sample_count, status, cache_hit, error_type, started_at, finished_at) "
                    "VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)",
                    (run_id, project_id, model, sample_count, run_status, error_type, start_time, finish_time)
                )
        return {"success": False, "error": str(last_error) if run_status == "failed" else "Quota Gemini sudah habis. Silakan gunakan versi manual."}
        
    try:
        finish_time = datetime.now(timezone.utc).isoformat()
        
        # Parse the structured response
        raw_json = response.text
        parsed = json.loads(raw_json)
        
        import re
        def validate_labels(labels, max_count=10):
            seen = set()
            valid = []
            for lbl in labels:
                raw_key = lbl.get("key", "").lower()
                key = re.sub(r'[^a-z0-9]+', '_', raw_key).strip('_')
                if not key:
                    continue
                if key not in seen:
                    seen.add(key)
                    lbl["key"] = key
                    valid.append(lbl)
                if len(valid) >= max_count:
                    break
            return valid

        parsed["issues"] = validate_labels(parsed.get("issues", []), 10)
        parsed["stances"] = validate_labels(parsed.get("stances", []), 8)
        parsed["actions"] = validate_labels(parsed.get("actions", []), 8)
        
        # Ensure mandatory keys exist
        if not any(i.get("key") == "lainnya" for i in parsed["issues"]):
            if len(parsed["issues"]) >= 10: parsed["issues"].pop()
            parsed["issues"].append({"key": "lainnya", "name": "Lainnya", "description": "Topik lain yang tidak masuk ke kategori di atas.", "examples": []})
        if not any(s.get("key") == "tidak_terdeteksi" for s in parsed["stances"]):
            if len(parsed["stances"]) >= 8: parsed["stances"].pop()
            parsed["stances"].append({"key": "tidak_terdeteksi", "name": "Tidak Terdeteksi", "description": "Stance tidak jelas.", "examples": []})
        if not any(a.get("key") == "tidak_terdeteksi" for a in parsed["actions"]):
            if len(parsed["actions"]) >= 8: parsed["actions"].pop()
            parsed["actions"].append({"key": "tidak_terdeteksi", "name": "Tidak Terdeteksi", "description": "Niat tindakan tidak jelas.", "examples": []})
            
        issue_str = json.dumps(parsed["issues"], ensure_ascii=False)
        stance_str = json.dumps(parsed["stances"], ensure_ascii=False)
        action_str = json.dumps(parsed["actions"], ensure_ascii=False)
        prompt_context = parsed.get("prompt_context", "")
        
        version_id = f"{project_id}_v{int(time.time())}"
        
        # Save Draft
        with get_db_connection(database_url) as conn:
            with conn:
                conn.execute(
                    "INSERT INTO project_taxonomy_versions (version_id, project_id, status, source, prompt_context, issue_labels, stance_labels, action_labels, regenerate_instruction, model, sample_hash, created_at) "
                    "VALUES (?, ?, 'draft', 'gemini', ?, ?, ?, ?, ?, ?, ?, ?)",
                    (version_id, project_id, prompt_context, issue_str, stance_str, action_str, instructions, model, full_hash, finish_time)
                )
                conn.execute(
                    "INSERT INTO llm_generation_runs (run_id, project_id, version_id, model, sample_count, status, cache_hit, started_at, finished_at) "
                    "VALUES (?, ?, ?, ?, ?, 'success', 0, ?, ?)",
                    (run_id, project_id, version_id, model, sample_count, start_time, finish_time)
                )
                
        return {"success": True, "cache_hit": False, "version_id": version_id}
        
    except Exception as e:
        logger.error(f"Gemini response parsing failed: {e}")
        finish_time = datetime.now(timezone.utc).isoformat()
        error_type = type(e).__name__
        with get_db_connection(database_url) as conn:
            with conn:
                conn.execute(
                    "INSERT INTO llm_generation_runs (run_id, project_id, model, sample_count, status, cache_hit, error_type, started_at, finished_at) "
                    "VALUES (?, ?, ?, ?, 'failed', 0, ?, ?, ?)",
                    (run_id, project_id, model, sample_count, error_type, start_time, finish_time)
                )
        return {"success": False, "error": str(e)}
