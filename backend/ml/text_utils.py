"""
text_utils.py — Comment text normalization helpers.

Light cleaner that mirrors notebook v7.2 normalization plus a small slang map.
Kept separate from the Ollama LLM service so text cleaning can be reused (and
tested) without importing the HTTP client. Re-exported by ollama_service for
backward compatibility.
"""

import re
import html
from typing import Optional

SLANG_MAP = {
    "gk": "tidak", "ga": "tidak", "gak": "tidak", "nggak": "tidak", "ngga": "tidak",
    "tdk": "tidak", "tak": "tidak", "yg": "yang", "dgn": "dengan", "krn": "karena",
    "karna": "karena", "bgt": "banget", "bgtt": "banget", "sm": "sama", "org": "orang",
    "skrng": "sekarang", "skrg": "sekarang", "jd": "jadi", "jdi": "jadi", "utk": "untuk",
    "dlm": "dalam", "dr": "dari", "dri": "dari", "kyk": "seperti", "kek": "seperti",
    "kayak": "seperti", "gw": "saya", "gue": "saya", "gua": "saya", "lu": "kamu", "lo": "kamu",
    "wkwk": "tertawa", "wkwkwk": "tertawa", "mantul": "mantap",
}

_URL_RE = re.compile(r"http\S+|www\.\S+")
_HTML_RE = re.compile(r"<.*?>")
_MENTION_RE = re.compile(r"[@#]\S+")
_NONALNUM_RE = re.compile(r"[^0-9a-zA-ZÀ-ÿĀ-ž\s]")
_WS_RE = re.compile(r"\s+")
_ELONG_RE = re.compile(r"(.)\1{2,}")


def _reduce_elongation(token: str) -> str:
    return _ELONG_RE.sub(r"\1\1", str(token))


def normalize_text(text: Optional[str]) -> str:
    """Light cleaner mirroring notebook v7.2 normalization."""
    if text is None:
        return ""
    text = html.unescape(str(text)).lower()
    text = _URL_RE.sub(" ", text)
    text = _HTML_RE.sub(" ", text)
    text = _MENTION_RE.sub(" ", text)
    text = _NONALNUM_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    if not text:
        return ""
    tokens = []
    for tok in text.split():
        tok = _reduce_elongation(tok)
        tok = SLANG_MAP.get(tok, tok)
        tokens.append(tok)
    return _WS_RE.sub(" ", " ".join(tokens)).strip()


def build_context_text(clean_text: str,
                       is_reply: bool,
                       parent_clean_text: Optional[str]) -> str:
    """
    Builds context_text_model: for replies with a parent, prefix up to 40
    words of parent text so very short replies gain semantic context.
    """
    clean_text = clean_text or ""
    if is_reply and parent_clean_text:
        parent_snip = " ".join(str(parent_clean_text).split()[:40])
        if parent_snip:
            return f"parent_context {parent_snip} reply_text {clean_text}".strip()
    return clean_text
