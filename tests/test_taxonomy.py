"""
test_taxonomy.py — Unit tests for backend.ml.taxonomy.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ml.taxonomy import (
    classify_issue,
    classify_stance,
    classify_action_intent,
    keyword_score,
    human_label,
    ISSUE_HUMAN,
    STANCE_HUMAN,
    ACTION_HUMAN,
)


# --- ISSUE ---

def test_taxonomy_issue_ekonomi():
    """Ekonomi keywords → ekonomi_rakyat."""
    text = "harga beras semakin mahal, rakyat kecil menderita"
    label, scores = classify_issue(text)
    assert label == "ekonomi_rakyat"


def test_taxonomy_issue_korupsi():
    """Korupsi keywords → hukum_korupsi."""
    text = "korupsi merajalela, KPK harus bertindak tegas terhadap para koruptor"
    label, scores = classify_issue(text)
    assert label == "hukum_korupsi"


def test_taxonomy_issue_pemerintah():
    text = "kebijakan pemerintah dan presiden sangat buruk"
    label, _ = classify_issue(text)
    assert label == "pemerintahan_kebijakan"


def test_taxonomy_issue_elite_politik():
    text = "oligarki dan elite partai menguasai negara"
    label, _ = classify_issue(text)
    assert label == "elite_politik"


def test_taxonomy_issue_feedback_video():
    text = "video ini sangat bagus, terima kasih sudah membuat konten berkualitas"
    label, _ = classify_issue(text)
    assert label == "feedback_video"


def test_taxonomy_issue_lainnya_fallback():
    """No strong signal → lainnya."""
    text = "wkwk lucu banget"
    label, _ = classify_issue(text)
    assert label == "lainnya"


def test_taxonomy_issue_priority_tie_break():
    """If two categories have the same score, priority order (dict insertion) wins."""
    # "harga" → ekonomi_rakyat (1pt), "korupsi" → hukum_korupsi (1pt)
    # Same score → ekonomi_rakyat wins because it appears first in the dict.
    text = "harga dan korupsi"
    label, scores = classify_issue(text)
    assert label == "ekonomi_rakyat"  # priority (first in dict) wins tie


# --- STANCE ---

def test_taxonomy_stance_kritik_pemerintah():
    """Kritik pemerintah keywords detected."""
    text = "pemerintah gagal total, rakyat semakin susah karena kebijakan buruk"
    label, _ = classify_stance(text)
    assert label == "kritik_pemerintah"


def test_taxonomy_stance_dukung_video():
    text = "pembahasan bagus dan narasumber berani, membuka mata"
    label, _ = classify_stance(text)
    assert label == "dukung_video"


def test_taxonomy_stance_sinis():
    text = "percuma saja, semua sama saja, tidak ada harapan"
    label, _ = classify_stance(text)
    assert label == "sinis_tidak_percaya"


def test_taxonomy_stance_tidak_terdeteksi_fallback():
    text = "wkwkwk"
    label, _ = classify_stance(text)
    assert label == "tidak_terdeteksi"


def test_taxonomy_stance_debat():
    text = "anda salah paham, kamu tidak paham konteksnya"
    label, _ = classify_stance(text)
    assert label == "debat_antar_pengguna"


# --- ACTION INTENT ---

def test_taxonomy_action_accountability():
    """Kata audit/usut/bertanggung jawab → menuntut_akuntabilitas."""
    text = "harus di audit dan usut tuntas, mereka harus bertanggung jawab"
    label, _ = classify_action_intent(text)
    assert label == "menuntut_akuntabilitas"


def test_taxonomy_action_dorongan_aksi():
    text = "mahasiswa harus turun jalan dan demo"
    label, _ = classify_action_intent(text)
    assert label == "dorongan_aksi_publik"


def test_taxonomy_action_elektoral():
    text = "jangan pilih lagi di 2029, ganti pemimpin"
    label, _ = classify_action_intent(text)
    assert label == "perubahan_elektoral"


def test_taxonomy_action_sebarkan():
    text = "share dan viralkan video ini, buka mata masyarakat"
    label, _ = classify_action_intent(text)
    assert label == "menyebarkan_kesadaran"


def test_taxonomy_action_harapan():
    text = "semoga pemerintah sadar dan mudah-mudahan berubah"
    label, _ = classify_action_intent(text)
    assert label == "harapan_doa"


def test_taxonomy_action_apatis():
    text = "percuma capek muak sama saja"
    label, _ = classify_action_intent(text)
    assert label == "apatis_sinis"


def test_taxonomy_action_tidak_terdeteksi_fallback():
    text = "ok"
    label, _ = classify_action_intent(text)
    assert label == "tidak_terdeteksi"


# --- keyword_score ---

def test_keyword_score_single_word():
    assert keyword_score("pemerintah gagal total", ["gagal"]) == 1


def test_keyword_score_multi_word():
    assert keyword_score("rakyat kecil menderita", ["rakyat kecil"]) == 2


def test_keyword_score_no_match():
    assert keyword_score("biasa saja", ["korupsi", "demo"]) == 0


def test_keyword_score_empty():
    assert keyword_score("", ["test"]) == 0


def test_keyword_score_none():
    assert keyword_score(None, ["test"]) == 0


# --- human_label ---

def test_human_label_known():
    assert human_label("ekonomi_rakyat", ISSUE_HUMAN) == "ekonomi rakyat"


def test_human_label_unknown():
    result = human_label("custom_label", ISSUE_HUMAN)
    assert "custom" in result


def test_human_label_none():
    """human_label with None should not crash (returns fallback or empty)."""
    result = human_label(None, ISSUE_HUMAN)
    assert isinstance(result, str)  # should not crash
