"""
intelligence_engine.py — Composes taxonomy classification + safe interpretation.

Public entrypoint
-----------------
infer_comment_intelligence(comment, parent_comment=None) -> dict
    Uses rule-based taxonomy as fallback classifier.
    Always returns the 10 inference columns, plus diagnostic metadata. Never
    raises — failures are reflected via `inference_status` / `inference_error`.

Outputs keys:
    sentiment, sentiment_confidence,
    issue_label, stance_label, action_intent_label,
    interpretation_short, model_version,
    inference_status, inference_error, inferred_at
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.ml.ollama_service import normalize_text
from backend.ml.taxonomy import (
    classify_issue,
    classify_stance,
    classify_action_intent,
    ISSUE_HUMAN,
    STANCE_HUMAN,
    ACTION_HUMAN,
    human_label,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_interpretation(*,
                          status: str,
                          sentiment: Optional[str],
                          issue_label: str,
                          stance_label: str,
                          action_intent_label: str,
                          clean_text: str) -> Optional[str]:
    """
    Produces a single safe sentence. Always returns either a hedged sentence
    or None (when the comment did not get a usable inference at all).
    """
    if status not in ("completed",):
        return None

    if not clean_text.strip():
        return ("Komentar terlalu pendek atau hanya berisi simbol untuk "
                "diinterpretasikan secara aman.")

    issue_h = human_label(issue_label, ISSUE_HUMAN)
    stance_h = human_label(stance_label, STANCE_HUMAN)
    action_h = human_label(action_intent_label, ACTION_HUMAN)

    if issue_label == "lainnya":
        sentiment_h = sentiment or "respons umum"
        return (f"Komentar ini belum menunjukkan isu spesifik yang kuat, "
                f"tetapi tetap terbaca sebagai respons {sentiment_h}.")

    return (f"Komentar ini terindikasi {stance_h} pada isu {issue_h}, "
            f"dengan kecenderungan ekspresi {action_h}.")


def infer_comment_intelligence(comment: Dict[str, Any],
                               parent_comment: Optional[Dict[str, Any]] = None
                               ) -> Dict[str, Any]:
    """
    Runs rule-based taxonomy classification as a fallback inference engine.
    This is used when Ollama does not cover a comment (e.g., Ollama is down).
    Returns the inference column payload (no DB writes).
    """
    parent_clean: Optional[str] = None
    if parent_comment and parent_comment.get("comment_text"):
        parent_clean = normalize_text(parent_comment.get("comment_text"))

    inference_error: Optional[str] = None
    raw_text = comment.get("comment_text")
    clean = normalize_text(raw_text)

    from backend.ml.ollama_service import build_context_text
    context_text = build_context_text(
        clean_text=clean,
        is_reply=bool(comment.get("is_reply")),
        parent_clean_text=parent_clean,
    )

    # Taxonomy works on the context_text.
    try:
        issue_label, _ = classify_issue(context_text)
        stance_label, _ = classify_stance(context_text)
        action_label, _ = classify_action_intent(context_text)
    except Exception as e:
        issue_label = "lainnya"
        stance_label = "tidak_terdeteksi"
        action_label = "tidak_terdeteksi"
        inference_error = f"taxonomy crash: {type(e).__name__}: {e}"

    # Rule-based engine cannot predict sentiment — set to None so dashboard
    # knows this is a partial result.
    inference_status = "completed" if not inference_error else "failed"

    interpretation = _build_interpretation(
        status=inference_status,
        sentiment=None,
        issue_label=issue_label,
        stance_label=stance_label,
        action_intent_label=action_label,
        clean_text=clean,
    )

    return {
        "sentiment": None,
        "sentiment_confidence": None,
        "issue_label": issue_label if inference_status == "completed" else None,
        "stance_label": stance_label if inference_status == "completed" else None,
        "action_intent_label": action_label if inference_status == "completed" else None,
        "interpretation_short": interpretation,
        "model_version": "rule-based-taxonomy-fallback",
        "inference_status": inference_status,
        "inference_error": inference_error,
        "inferred_at": _now_iso(),
    }
