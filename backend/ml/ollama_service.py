"""
ollama_service.py — Centralized Ollama LLM service for sentiment analysis.

Replaces both the Gemini Cloud API (llm_predictor.py) and the sklearn
joblib pipeline (model_loader.py + sentiment_predictor.py).

Public API
----------
- check_ollama_health()             → dict with status, model, memory info
- analyze_comments_batch(comments)  → dict mapping comment_id → analysis result
- normalize_text(text)              → cleaned text string
- build_context_text(...)           → context-enriched text for replies
- get_ollama_settings()             → current Ollama config dict
"""

import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

# Text normalization helpers live in text_utils; re-exported here so the
# documented public API (normalize_text, build_context_text) is unchanged.
from backend.ml.text_utils import (  # re-exported for backward compat
    normalize_text as normalize_text,
    build_context_text as build_context_text,
)

logger = logging.getLogger("youtube_collector.ollama")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "csalab/sahabatai1:llama3_instruct_Q4_K_M"
DEFAULT_OLLAMA_TIMEOUT = 300
MODEL_VERSION_TAG = "sahabatai-8b-ollama-v1"


def get_ollama_settings() -> Dict[str, Any]:
    """Returns the current Ollama configuration from environment."""
    return {
        "base_url": os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
        "model": os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
        "timeout": int(os.getenv("OLLAMA_TIMEOUT", str(DEFAULT_OLLAMA_TIMEOUT))),
    }


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

def check_ollama_health() -> Dict[str, Any]:
    """
    Checks if Ollama server is reachable and the configured model is loaded.
    Returns a dict with status, model name, and server info.
    """
    cfg = get_ollama_settings()
    base_url = cfg["base_url"]
    model = cfg["model"]

    result = {
        "server_online": False,
        "model_loaded": False,
        "model_name": model,
        "base_url": base_url,
        "error": None,
    }

    # 1. Check server
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            result["server_online"] = True
            # 2. Check if our model is in the list
            data = resp.json()
            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models]
            # Match by prefix (ollama may append :latest)
            for mn in model_names:
                if model in mn or mn.startswith(model):
                    result["model_loaded"] = True
                    break
        else:
            result["error"] = f"Ollama returned HTTP {resp.status_code}"
    except requests.ConnectionError:
        result["error"] = "Tidak dapat terhubung ke Ollama. Pastikan Ollama berjalan di background."
    except requests.Timeout:
        result["error"] = "Ollama server timeout."
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"

    return result


# ---------------------------------------------------------------------------
# Prompt Builder — LIGHTWEIGHT version for CPU inference
# ---------------------------------------------------------------------------

# Allowed label values per axis. Used both to list options in the prompt and to
# validate the model's reply (anything outside the set falls back to a safe
# default). Integer-code output was benchmarked and REJECTED: it was faster but
# an 8B model maps concept→arbitrary-number poorly, tanking accuracy. String
# labels — the words the model was trained on — keep accuracy high.
SENTIMENT_LABELS = ["negative", "neutral", "positive"]
DEFAULT_ISSUE_LABELS = [
    "ekonomi_rakyat", "kepercayaan_publik", "pemerintahan_kebijakan",
    "hukum_korupsi", "elite_politik", "geopolitik_keamanan", "media_narasi",
    "demokrasi_aksi_publik", "feedback_video", "lainnya",
]
DEFAULT_STANCE_LABELS = [
    "kritik_pemerintah", "dukung_pemerintah", "dukung_video", "kritik_video",
    "sinis_tidak_percaya", "netral_informatif", "debat_antar_pengguna",
    "tidak_terdeteksi",
]
DEFAULT_ACTION_LABELS = [
    "menuntut_akuntabilitas", "dorongan_aksi_publik", "perubahan_elektoral",
    "menyebarkan_kesadaran", "harapan_doa", "menunggu_mengamati", "apatis_sinis",
    "tidak_terdeteksi",
]

DEFAULT_PROMPT_CONTEXT = (
    "1. Keluhan tentang harga barang, bbm, beras, pajak, gaji, bantuan sosial, atau sulitnya lapangan pekerjaan harus masuk ke issue: \"ekonomi_rakyat\".\n"
    "2. Komentar yang memuji video, host, narasumber, atau mengucapkan terima kasih atas edukasinya harus masuk ke issue: \"feedback_video\" dan stance: \"dukung_video\".\n"
    "3. Komentar sarkasme (pujian bernada mengejek atau memiliki konteks negatif) harus diklasifikasikan sebagai sentiment: \"negative\" dan stance: \"kritik_pemerintah\" atau \"sinis_tidak_percaya\".\n"
    "4. Slang Indonesian: gk/ga/gak=tidak, yg=yang, krn=karena, bgt=banget, mantul=mantap. Bahasa daerah: mundak=naik, mumet=pusing."
)


def build_prompt(comment_text: str, parent_text: Optional[str] = None, project: Optional[Dict[str, Any]] = None) -> str:
    """Builds a single-comment prompt asking for one JSON object of labels with Chain of Thought.

    Includes the 'analisis' field first to let Llama perform planning and reasoning
    before selecting classification labels, improving classification accuracy.
    """
    issue_labels = DEFAULT_ISSUE_LABELS
    stance_labels = DEFAULT_STANCE_LABELS
    action_labels = DEFAULT_ACTION_LABELS
    prompt_context = DEFAULT_PROMPT_CONTEXT
    
    if project:
        def parse_labels(val):
            if not val: return []
            try:
                if val.startswith('['):
                    return [x['key'] for x in json.loads(val)]
            except: pass
            return [l.strip() for l in val.split(',')]
            
        if project.get("issue_labels"): issue_labels = parse_labels(project["issue_labels"])
        if project.get("stance_labels"): stance_labels = parse_labels(project["stance_labels"])
        if project.get("action_labels"): action_labels = parse_labels(project["action_labels"])
        if project.get("prompt_context"): prompt_context = project["prompt_context"]

    category_header = (
        "sentiment: " + "|".join(SENTIMENT_LABELS) + "\n"
        "issue: " + "|".join(issue_labels) + "\n"
        "stance: " + "|".join(stance_labels) + "\n"
        "action: " + "|".join(action_labels) + "\n"
        "ATURAN KLASIFIKASI:\n" + prompt_context
    )

    context = ""
    if parent_text:
        snippet = " ".join(str(parent_text).split()[:40])
        if snippet:
            context = f'KONTEKS INDUK:"{snippet}"\n'

    return (
        "Analisis 1 komentar YouTube Bahasa Indonesia. Pilih 1 label tiap kategori.\n"
        f"{category_header}\n"
        'CONTOH 1:\n'
        'KOMENTAR:"harga beras meroket menyusahkan rakyat kecil"\n'
        'OUTPUT:{"analisis":"Komentar mengeluhkan kenaikan harga beras yang membebani rakyat kecil, menunjukkan ketidakpuasan.","sentiment":"negative","issue":"ekonomi_rakyat","stance":"kritik_pemerintah","action":"menuntut_akuntabilitas"}\n'
        'CONTOH 2:\n'
        'KOMENTAR:"terima kasih analisanya sangat mencerahkan dan objektif"\n'
        'OUTPUT:{"analisis":"Komentar mengapresiasi dan memuji kualitas analisis video secara positif.","sentiment":"positive","issue":"feedback_video","stance":"dukung_video","action":"tidak_terdeteksi"}\n'
        'CONTOH 3:\n'
        'KOMENTAR:"bagaimana kelanjutan kasus ini menurut hukum?"\n'
        'OUTPUT:{"analisis":"Komentar bertanya secara netral tentang aspek hukum tanpa memihak.","sentiment":"neutral","issue":"hukum_korupsi","stance":"netral_informatif","action":"menunggu_mengamati"}\n'
        f"{context}"
        f'KOMENTAR:"{comment_text}"\n'
        "Balas HANYA 1 objek JSON (analisis, sentiment, issue, stance, action), tanpa teks lain:"
    )


# ---------------------------------------------------------------------------
# Ollama API Call
# ---------------------------------------------------------------------------

def _call_ollama(prompt: str, cfg: Dict[str, Any]) -> Optional[str]:
    """
    Sends a prompt to Ollama's /api/generate endpoint.
    Returns the raw text response or None on failure.
    Retries up to 2 times with exponential backoff.
    """
    url = f"{cfg['base_url']}/api/generate"
    payload = {
        "model": cfg["model"],
        "prompt": prompt,
        "stream": False,
        # NOTE: Ollama's native "format":"json" was tried and REVERTED — with this
        # model it biases decoding toward a single object and dropped comments
        # from batch arrays. num_ctx/num_thread overrides were also measured and
        # made decode SLOWER, so we leave them at Ollama's defaults.
        "options": {
            "temperature": 0.1,
            # We increase num_predict to 150 to allow the model to output a short
            # reasoning sentence in "analisis" before the final category keys.
            "num_predict": 150,
        },
    }

    max_retries = 2
    backoff = 3.0

    for attempt in range(max_retries):
        try:
            logger.info(
                f"Ollama request attempt {attempt + 1}/{max_retries} "
                f"(model: {cfg['model']}, prompt_len: {len(prompt)} chars)"
            )
            resp = requests.post(url, json=payload, timeout=cfg["timeout"])

            if resp.status_code == 200:
                data = resp.json()
                response_text = data.get("response", "")
                eval_count = data.get("eval_count", 0)
                prompt_count = data.get("prompt_eval_count", 0)
                total_ms = data.get("total_duration", 0) / 1_000_000
                logger.info(
                    f"Ollama OK: prompt_tokens={prompt_count}, "
                    f"output_tokens={eval_count}, "
                    f"total_time={total_ms:.0f}ms"
                )
                return response_text
            else:
                logger.warning(
                    f"Ollama returned HTTP {resp.status_code}: {resp.text[:200]}"
                )
        except requests.ConnectionError:
            logger.error(
                "Cannot connect to Ollama. Is it running? "
                f"(URL: {cfg['base_url']})"
            )
        except requests.Timeout:
            logger.warning(
                f"Ollama request timed out after {cfg['timeout']}s "
                f"(attempt {attempt + 1}/{max_retries})"
            )
        except Exception as e:
            logger.error(f"Unexpected Ollama error: {e}")

        if attempt < max_retries - 1:
            sleep_time = backoff * (2 ** attempt)
            logger.info(f"Retrying in {sleep_time:.1f}s...")
            time.sleep(sleep_time)

    return None


def _valid_label(value: Any, allowed: List[str], default: str) -> str:
    """Return value if it is an allowed label, else the safe default."""
    return value if isinstance(value, str) and value in allowed else default


def _parse_label_response(text_response: str, project: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, str]]:
    """Parse the single JSON object reply into a labels dict (DB column names).

    Returns None if no JSON object can be found (caller then routes the comment
    to the rule-based fallback). Out-of-vocabulary values are coerced to a safe
    default rather than rejected.
    """
    if not text_response:
        return None

    start = text_response.find("{")
    end = text_response.rfind("}")
    if start == -1 or end == -1 or end <= start:
        logger.warning(f"Ollama reply had no JSON object: {text_response[:80]!r}")
        return None

    try:
        obj = json.loads(text_response[start:end + 1])
    except json.JSONDecodeError as e:
        logger.warning(f"Ollama JSON parse failed ({e}): {text_response[:80]!r}")
        return None

    if not isinstance(obj, dict):
        return None

    issue_labels = DEFAULT_ISSUE_LABELS
    stance_labels = DEFAULT_STANCE_LABELS
    action_labels = DEFAULT_ACTION_LABELS
    
    if project:
        def parse_labels(val):
            if not val: return []
            try:
                if val.startswith('['):
                    return [x['key'] for x in json.loads(val)]
            except: pass
            return [l.strip() for l in val.split(',')]
            
        if project.get("issue_labels"): issue_labels = parse_labels(project["issue_labels"])
        if project.get("stance_labels"): stance_labels = parse_labels(project["stance_labels"])
        if project.get("action_labels"): action_labels = parse_labels(project["action_labels"])

    return {
        "sentiment": _valid_label(obj.get("sentiment"), SENTIMENT_LABELS, "neutral"),
        "issue_label": _valid_label(obj.get("issue"), issue_labels, "lainnya"),
        "stance_label": _valid_label(obj.get("stance"), stance_labels, "tidak_terdeteksi"),
        "action_intent_label": _valid_label(obj.get("action"), action_labels, "tidak_terdeteksi"),
    }


def analyze_comments_batch(
    comments_data: List[Dict[str, Any]],
    project: Optional[Dict[str, Any]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Analyzes comments ONE PER CALL (despite the legacy "batch" name).

    Benchmarks on CPU showed batching gave no speed-up (prompt eval is ~free on
    a cached prefix) yet made the model drop comments from multi-item arrays.
    Sequential single calls are ~2.8x faster than the old string-batch and 100%
    reliable. The interpretation sentence is rebuilt locally from the predicted
    labels instead of being decoded by the model — saving the most expensive
    (free-text) output tokens.

    Returns a dict mapping comment_id → analysis results dict. Comments whose
    call fails are simply omitted (the caller routes them to the fallback).
    """
    if not comments_data:
        return {}

    from backend.ml.intelligence_engine import _build_interpretation

    cfg = get_ollama_settings()
    results_dict: Dict[str, Dict[str, Any]] = {}

    for c in comments_data:
        cid = c.get("comment_id")
        text = c.get("comment_text")
        if not cid or not text:
            continue

        prompt = build_prompt(text, c.get("parent_text"), project)
        text_response = _call_ollama(prompt, cfg)
        if text_response is None:
            logger.warning(f"Ollama no response for {cid}; will fall back.")
            continue

        labels = _parse_label_response(text_response, project)
        if labels is None:
            continue

        interpretation = _build_interpretation(
            status="completed",
            sentiment=labels["sentiment"],
            issue_label=labels["issue_label"],
            stance_label=labels["stance_label"],
            action_intent_label=labels["action_intent_label"],
            clean_text=normalize_text(text),
        )

        results_dict[cid] = {
            **labels,
            # The model no longer emits confidence; use the prior default.
            "sentiment_confidence": 0.85,
            "interpretation_short": interpretation,
            "model_version": MODEL_VERSION_TAG,
            "inference_status": "completed",
            "inference_error": None,
            "inferred_at": datetime.now(timezone.utc).isoformat(),
            "taxonomy_version_id": project.get("active_taxonomy_version_id") if project else None,
        }

    logger.info(
        f"Ollama analyzed {len(results_dict)}/{len(comments_data)} comments successfully."
    )
    return results_dict
