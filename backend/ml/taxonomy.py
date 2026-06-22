"""
taxonomy.py — Rule-based labellers for `issue`, `stance`, and `action_intent`.

Each labeller is a keyword scorer:
  * 2-word phrases count for 2 points, single words for 1 point.
  * Single-label output: highest scoring category, tie-broken by declared
    priority (the dict insertion order is the priority order — Python 3.7+ keeps
    it).
  * If every category scores 0, fall back to a default ("lainnya" /
    "tidak_terdeteksi").

These rules are deliberately conservative. Inference is text-only — the labels
describe *expression* in the comment, not predicted real-world behaviour.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


# --- ISSUE --------------------------------------------------------------------

ISSUE_TAXONOMY: Dict[str, List[str]] = {
    "ekonomi_rakyat": [
        "harga", "mahal", "pangan", "beras", "kerja", "pekerjaan", "gaji",
        "pajak", "rakyat kecil", "ekonomi", "miskin", "subsidi", "biaya hidup",
        "bbm", "sembako", "mbg", "bantuan", "hutang", "pengangguran",
    ],
    "kepercayaan_publik": [
        "bohong", "janji", "kecewa", "tidak percaya", "pencitraan",
        "omong kosong", "dikhianati", "tipu", "manipulasi", "kapok", "muak",
    ],
    "pemerintahan_kebijakan": [
        "pemerintah", "presiden", "menteri", "kabinet", "program", "kebijakan",
        "negara", "anggaran", "prabowo", "jokowi", "gibran", "aturan",
    ],
    "hukum_korupsi": [
        "korupsi", "koruptor", "kpk", "hukum", "aparat", "hakim", "jaksa",
        "polisi", "keadilan", "suap", "mafia", "adil", "nepotisme",
    ],
    "elite_politik": [
        "elite", "oligarki", "partai", "pejabat", "dinasti", "kekuasaan",
        "koalisi", "dpr", "politisi", "penguasa", "istana", "politik",
    ],
    "geopolitik_keamanan": [
        "asing", "china", "amerika", "perang", "pertahanan", "militer",
        "geopolitik", "keamanan", "laut china selatan", "israel", "rusia",
        "kerusuhan", "1998",
    ],
    "media_narasi": [
        "media", "berita", "framing", "narasi", "podcast", "konten",
        "jurnalis", "channel", "buzzer", "hoax", "propaganda", "youtube",
    ],
    "demokrasi_aksi_publik": [
        "demo", "demonstrasi", "turun jalan", "pemilu", "coblos", "gerakan",
        "lawan", "suara rakyat", "mahasiswa", "aksi", "reformasi", "protes",
        "revolusi",
    ],
    "feedback_video": [
        "video", "host", "narasumber", "pembahasan", "channel", "judul",
        "podcast", "terima kasih", "konten bagus", "mantap", "analisa",
        "jelas",
    ],
    "lainnya": [],  # fallback
}


# --- STANCE -------------------------------------------------------------------

STANCE_TAXONOMY: Dict[str, List[str]] = {
    "kritik_pemerintah": [
        "pemerintah gagal", "rakyat susah", "kebijakan buruk", "presiden gagal",
        "negara kacau", "menteri tidak becus", "rezim", "janji palsu",
        "pemerintah tidak", "tidak becus", "gagal pemerintah",
    ],
    "dukung_pemerintah": [
        "sudah bagus", "beri kesempatan", "program jalan", "pemerintah benar",
        "dukung presiden", "dukung pemerintah", "percaya pemerintah",
        "prabowo bisa", "program bagus", "sabar", "kasih waktu",
        "semoga berhasil",
    ],
    "dukung_video": [
        "pembahasan bagus", "narasumber berani", "membuka mata", "terima kasih",
        "konten berkualitas", "analisis bagus", "mantap", "benar sekali",
        "masuk akal", "setuju", "konten bagus",
    ],
    "kritik_video": [
        "provokatif", "clickbait", "tidak netral", "narasumber ngawur",
        "judul menyesatkan", "berlebihan", "menakut nakuti", "tidak setuju",
        "kurang data", "provokasi",
    ],
    "sinis_tidak_percaya": [
        "percuma", "semua sama saja", "tidak ada harapan", "rakyat dibohongi",
        "omong kosong", "sama saja", "susah berubah", "capek",
        "rakyat dibodohi",
    ],
    "netral_informatif": [
        "menurut data", "informasi", "fakta", "pertanyaannya", "bagaimana",
        "penjelasan", "data menunjukkan",
    ],
    "debat_antar_pengguna": [
        "anda salah", "lu salah", "kamu tidak paham", "setuju sama komen",
        "balas komentar", "salah paham", "komen di atas",
    ],
    "tidak_terdeteksi": [],
}


# --- ACTION INTENT ------------------------------------------------------------

ACTION_TAXONOMY: Dict[str, List[str]] = {
    "menuntut_akuntabilitas": [
        "harus bertanggung jawab", "usut", "audit", "buka data", "transparan",
        "periksa", "tuntut", "tangkap", "adili", "bertanggung jawab",
        "pecat", "evaluasi", "perbaiki",
    ],
    "dorongan_aksi_publik": [
        "demo", "turun jalan", "lawan", "bergerak", "aksi", "turun ke jalan",
        "mahasiswa turun", "rakyat bergerak", "protes", "reformasi",
    ],
    "perubahan_elektoral": [
        "jangan pilih lagi", "2029", "pemilu", "coblos", "ganti pemimpin",
        "jangan dicoblos", "pilih", "jangan pilih", "ganti", "suara rakyat",
        "pilpres", "partai",
    ],
    "menyebarkan_kesadaran": [
        "share", "sebarin", "viralkan", "buka mata", "edukasi", "kasih tahu",
        "sebarkan", "bagikan", "sadar", "bangun",
    ],
    "harapan_doa": [
        "semoga", "mudah-mudahan", "mudah mudahan", "doakan", "berharap",
        "semoga sadar", "doa", "amin", "insyaallah",
    ],
    "menunggu_mengamati": [
        "kita lihat", "tunggu saja", "pantau", "lihat nanti", "kita tunggu",
        "tunggu", "kasih waktu",
    ],
    "apatis_sinis": [
        "percuma", "tidak ada harapan", "sama saja", "capek", "muak", "pasrah",
        "biarin",
    ],
    "tidak_terdeteksi": [],
}


def keyword_score(text: str, keywords: List[str]) -> int:
    """Sum keyword weights — 2 for multi-word phrases, 1 for single tokens."""
    if not isinstance(text, str) or not text:
        return 0
    score = 0
    for kw in keywords:
        if not kw:
            continue
        if kw in text:
            score += 2 if " " in kw else 1
    return score


def assign_single_label(text: str,
                        taxonomy: Dict[str, List[str]],
                        default_label: str,
                        min_score: int = 1) -> Tuple[str, Dict[str, int]]:
    """
    Picks the highest-scoring label. Tie-breaker is dict insertion order, which
    is documented in the constants above as priority order.
    """
    scores: Dict[str, int] = {}
    for label, kws in taxonomy.items():
        if not kws:
            continue
        scores[label] = keyword_score(text, kws)

    if not scores:
        return default_label, {}

    best_label = default_label
    best_score = 0
    for label, score in scores.items():
        if score > best_score:
            best_score = score
            best_label = label
    if best_score < min_score:
        return default_label, scores
    return best_label, scores


def classify_issue(text: str) -> Tuple[str, Dict[str, int]]:
    return assign_single_label(text, ISSUE_TAXONOMY, default_label="lainnya")


def classify_stance(text: str) -> Tuple[str, Dict[str, int]]:
    return assign_single_label(text, STANCE_TAXONOMY, default_label="tidak_terdeteksi")


def classify_action_intent(text: str) -> Tuple[str, Dict[str, int]]:
    return assign_single_label(text, ACTION_TAXONOMY, default_label="tidak_terdeteksi")


# --- Human-readable label hints (for interpretation_short) ---------------------

ISSUE_HUMAN = {
    "ekonomi_rakyat": "ekonomi rakyat",
    "kepercayaan_publik": "kepercayaan publik",
    "pemerintahan_kebijakan": "pemerintahan & kebijakan",
    "hukum_korupsi": "hukum & korupsi",
    "elite_politik": "elite politik",
    "geopolitik_keamanan": "geopolitik & keamanan",
    "media_narasi": "media & narasi",
    "demokrasi_aksi_publik": "demokrasi & aksi publik",
    "feedback_video": "feedback video",
    "lainnya": "isu umum",
}

STANCE_HUMAN = {
    "kritik_pemerintah": "kritik terhadap pemerintah",
    "dukung_pemerintah": "dukungan terhadap pemerintah",
    "dukung_video": "apresiasi terhadap video",
    "kritik_video": "kritik terhadap video",
    "sinis_tidak_percaya": "sinisme terhadap situasi",
    "netral_informatif": "sikap netral-informatif",
    "debat_antar_pengguna": "debat antar pengguna",
    "tidak_terdeteksi": "sikap yang belum tegas",
}

ACTION_HUMAN = {
    "menuntut_akuntabilitas": "menuntut akuntabilitas",
    "dorongan_aksi_publik": "dorongan aksi publik",
    "perubahan_elektoral": "perubahan melalui jalur elektoral",
    "menyebarkan_kesadaran": "menyebarkan kesadaran",
    "harapan_doa": "harapan dan doa",
    "menunggu_mengamati": "menunggu dan mengamati",
    "apatis_sinis": "apatis-sinis",
    "tidak_terdeteksi": "kecenderungan yang belum tegas",
}


def human_label(label: Optional[str], mapping: Dict[str, str]) -> str:
    if not label:
        return mapping.get("tidak_terdeteksi", label or "")
    return mapping.get(label, label.replace("_", " "))
