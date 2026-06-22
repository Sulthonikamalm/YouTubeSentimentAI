<div align="center">
  <h1>🚀 YouTube Sentiment AI</h1>
  <p><b>An Enterprise-Grade YouTube Comment Intelligence & Sentiment Analysis Platform</b></p>
  
  [![Demo Available](https://img.shields.io/badge/Live_Demo-Vercel-black?logo=vercel&style=for-the-badge)](#-live-demo-auto-demo-mode)
  [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/downloads/)
  [![Local LLM](https://img.shields.io/badge/AI-Ollama-orange.svg?style=for-the-badge)](#)
</div>

---

Sistem monitoring dan analisis komentar YouTube menggunakan **YouTube Data API v3 resmi dari Google** dipadukan dengan kekuatan **Local LLM (Ollama)**. Modul ini dirancang agar dapat berjalan secara *incremental* (hemat kuota), mendeteksi perubahan/edit komentar (anti-duplikat), mendeteksi *comments-disabled* secara aman, serta memisahkan data *baseline* dengan komentar baru secara otomatis. Sistem ini menyimpan data terstruktur ke dalam database **SQLite**, dan menyediakan antarmuka Dashboard interaktif.

## Fitur Utama

1. **Official YouTube Data API v3**: Menggunakan request langsung ke endpoint resmi `commentThreads.list` dan `comments.list` (tidak menggunakan scraping Apify/unoffical).
2. **Incremental Crawling**: Hanya mendownload komentar baru dan akan berhenti (early stop) jika mendeteksi sejumlah komentar lama yang sudah tersimpan di database berturut-turut.
3. **Pemisahan Baseline vs Monitoring**:
   - Crawling pertama untuk suatu video akan menandai semua komentar yang didapat sebagai **baseline** (`is_baseline = 1`).
   - Crawling berikutnya (monitoring aktif) akan menandai komentar baru yang masuk sebagai **non-baseline** (`is_baseline = 0`).
4. **Tracking Edit Komentar**: Jika komentar sudah ada di database tetapi diedit oleh pengguna, crawler mendeteksi perubahan timestamp `updated_at` dari API dan mengupdate record di database.
5. **Quota Protection**: Memantau konsumsi unit API harian dan akan menghentikan crawler secara aman jika batas kuota harian (`daily_limit`) terpenuhi.
6. **Error Resilient**: Mengidentifikasi video dengan comments disabled, video not found, atau network timeout dan melanjutkan proses video lainnya tanpa crash.
7. **Background Scheduler**: Scheduler daemon background thread yang prevent-overlap (tidak akan menjalankan dua crawl run secara bertumpuk).
8. **Comment Intelligence (Tahap 2)**: Setiap komentar otomatis dianalisis menggunakan model ML dan taxonomy rule-based untuk menghasilkan: sentiment, issue label, stance label, action intent label, dan interpretation short. Inference berjalan otomatis setelah crawl selesai, atau bisa dijalankan manual.

---

## Struktur Folder

```
sentimenuntoldstory/
├── backend/
│   ├── crawler/
│   │   ├── crawl_runner.py       # Orchestrator alur monitoring & crawling
│   │   ├── dedup.py              # Logika dedup & early stop check
│   │   ├── quota_tracker.py      # Tracking unit API yang dikonsumsi
│   │   └── video_registry.py     # Registry video aktif
│   │
│   ├── ml/                       # Tahap 2 — Comment Intelligence
│   │   ├── model_loader.py       # Singleton loader untuk model .joblib
│   │   ├── sentiment_predictor.py# Adapter model ML + text normalization
│   │   ├── taxonomy.py           # Rule-based: issue, stance, action_intent
│   │   └── intelligence_engine.py# Komposer: sentiment + taxonomy + interpretasi
│   │
│   ├── services/
│   │   ├── inference_service.py  # Batch inference orchestrator
│   │   └── scheduler_service.py  # Background scheduler loop & locks
│   │
│   ├── storage/
│   │   ├── db.py                 # SQLite connection context
│   │   ├── repository.py         # CRUD repository operations
│   │   └── schema.py             # DDL SQLite schemas (videos, comments, runs, usage)
│   │
│   ├── youtube/
│   │   ├── comment_normalizer.py # Normalizer data API ke schema internal
│   │   ├── video_utils.py        # Video ID parser dari berbagai format URL
│   │   └── youtube_client.py     # Wrapper Google API Client dengan retry & backoff
│   │
│   ├── config.py                 # Config loader settings & env
│   ├── app.py                    # Flask server entry point & frontend serving
│   └── dashboard_routes.py       # Blueprint API endpoints untuk dashboard
│
├── frontend/                     # Dashboard Web UI (Tahap 3)
│   ├── index.html                # Layout utama single-page dashboard
│   ├── assets/
│   │   ├── css/
│   │   │   └── styles.css        # Design system CSS lengkap
│   │   └── js/
│   │       └── dashboard.js      # Logika fetch API, render chart, handler UI
│
├── config/
│   └── settings.yaml             # File konfigurasi global YAML
│
├── data/
│   ├── youtube_monitor.db        # Database SQLite (gitignored)
│   └── exports/                  # Target folder export CSV (gitignored)
│
├── outputs/
│   └── models/
│       └── BEST_MODEL_LATEST.joblib  # Model sentiment (gitignored)
│
├── scripts/
│   ├── init_db.py                # Inisialisasi database schema
│   ├── add_video.py              # Registrasi video feed baru
│   ├── run_crawl.py              # Pemicu crawling manual via CLI
│   ├── export_comments.py        # Export seluruh komentar dari DB ke CSV
│   ├── migrate_inference_columns.py  # Migration kolom inference ke DB
│   ├── run_inference.py          # Jalankan inference batch
│   └── inspect_inference_status.py   # Inspeksi status dan distribusi inference
│
├── tests/                        # Automated unit tests
│   ├── test_comment_normalizer.py
│   ├── test_crawl_runner_mock.py
│   ├── test_dedup.py
│   ├── test_video_utils.py
│   ├── test_model_loader.py          # Tahap 2
│   ├── test_sentiment_predictor.py   # Tahap 2
│   ├── test_taxonomy.py              # Tahap 2
│   └── test_inference_service.py     # Tahap 2
│
├── .env.example                  # Template environment variables
├── requirements.txt              # Dependensi library python
└── README.md                     # File dokumentasi ini
```

---

## Cara Setup & Menjalankan

### 1. Instalasi Dependensi
Pastikan Anda menggunakan Python 3.8+ (disarankan 3.10+). Install package dengan perintah:
```bash
pip install -r requirements.txt
```

### 2. Konfigurasi Environment (`.env`)
Salin file `.env.example` menjadi `.env`:
```bash
copy .env.example .env
```
Buka file `.env` dan masukkan API Key YouTube Anda:
```env
YOUTUBE_API_KEY=AIzaSy...
```

### 3. Inisialisasi Database
Jalankan perintah berikut untuk membuat file SQLite database `data/youtube_monitor.db` beserta seluruh tabel dan indeks yang dibutuhkan:
```bash
python scripts/init_db.py
```

### 4. Menambahkan Video ke Monitor Registry
Gunakan script `add_video.py` untuk mendaftarkan video YouTube yang akan dipantau. Mendukung format URL pendek, URL watch, URL shorts, maupun ID langsung:
```bash
python scripts/add_video.py "https://youtu.be/K8EKqxU-UwM"
```

### 5. Menjalankan Crawling Manual
Guna memicu pengambilan komentar secara instan, jalankan:
```bash
python scripts/run_crawl.py
```
- Run pertama akan mengumpulkan seluruh komentar sebagai **baseline** dataset.
- Run berikutnya akan mengumpulkan komentar-komentar baru saja (incremental).
- Setelah crawl selesai, inference otomatis berjalan untuk komentar baru.
Proses crawl ini tercatat dalam file log `logs/crawler.log` dan tabel `crawl_runs` serta `api_usage` di database.

### 6. Comment Intelligence — Inference (Tahap 2)

#### 6a. Jalankan Migration (satu kali saja)
Tambahkan kolom inference ke database yang sudah ada:
```bash
python scripts/migrate_inference_columns.py
```
Script ini idempotent — aman dijalankan berulang kali.

#### 6b. Jalankan Inference pada Komentar yang Belum Diproses
```bash
python scripts/run_inference.py --pending --limit 500
```

#### 6c. Jalankan Ulang Inference pada Semua Komentar
```bash
python scripts/run_inference.py --all --confirm
```
Perlu flag `--confirm` untuk mencegah eksekusi tidak sengaja.

#### 6d. Inspeksi Status Inference
Lihat distribusi sentiment, issue, stance, dan action intent:
```bash
python scripts/inspect_inference_status.py
```

#### Output Inference per Komentar
Setiap komentar yang sudah diproses akan memiliki:
- `sentiment` — positive / neutral / negative (dari model ML)
- `sentiment_confidence` — skor kepercayaan prediksi
- `issue_label` — isu yang dibahas (ekonomi_rakyat, hukum_korupsi, dll.)
- `stance_label` — sikap komentator (kritik_pemerintah, dukung_video, dll.)
- `action_intent_label` — kecenderungan ekspresi (menuntut_akuntabilitas, dll.)
- `interpretation_short` — kalimat interpretasi aman satu baris
- `model_version` — versi model yang digunakan
- `inference_status` — completed / failed / model_unavailable
- `inference_error` — detail error jika ada
- `inferred_at` — timestamp proses inference

### 7. Export Komentar ke CSV
Untuk mengekspor seluruh komentar yang ada di database SQLite ke dalam format CSV, jalankan:
```bash
python scripts/export_comments.py
```
Hasil file CSV akan otomatis disimpan di folder `data/exports/comments_export_YYYYMMDD_HHMMSS.csv`.

### 8. Menjalankan Pengujian (Unit Test)
Untuk memastikan seluruh modul berjalan dengan benar, jalankan unit test menggunakan pytest:
```bash
pytest
```
Semua test menggunakan mock responses, sehingga aman dijalankan tanpa mengonsumsi kuota API YouTube asli Anda.

### 9. Dashboard Web UI (Tahap 3)

Dashboard interaktif berbasis web untuk memantau dan menganalisis komentar YouTube secara visual.

#### Menjalankan Dashboard
```bash
python backend/app.py
```
Buka browser di **http://localhost:5000** untuk mengakses dashboard.

#### Fitur Dashboard
- **KPI Cards** — Total komentar, video dipantau, komentar baru 24h, inference progress, kuota API, last crawl
- **Tren Komentar & Sentimen** — Stacked bar chart per hari (positif/negatif/netral)
- **Distribusi Sentimen** — Doughnut chart dengan custom legend
- **Top Isu** — Horizontal bar chart dari issue_label yang paling sering muncul
- **Stance & Action Intent** — Distribusi sikap dan kecenderungan komentator
- **Word Cloud** — Visualisasi kata kunci populer dari label inference
- **Insight Keputusan** — Rangkuman otomatis: sentimen dominan, isu, stance, rekomendasi, peringatan
- **Komentar Representatif** — Tabel sampel komentar dengan sentimen, isu, dan interpretasi
- **Aktivitas Crawler** — Statistik 24h dan riwayat run terakhir
- **Filter** — Filter berdasarkan video, rentang waktu (24h/7d/30d/semua), dan tipe (baseline/new)
- **Auto Monitoring Toggle** — Aktifkan/nonaktifkan auto-crawl scheduler dari UI
- **Run Crawl Now** — Trigger crawling manual langsung dari dashboard
- **Toast Notifications** — Notifikasi real-time untuk setiap aksi
- **Responsive Design** — Mobile-friendly dengan sidebar collapsible
- **Auto Refresh** — Dashboard otomatis memperbarui data setiap 60 detik

## 🌟 Live Demo (Auto Demo Mode)

Proyek ini mendukung **Auto Demo Mode** melalui Vercel untuk kemudahan demonstrasi kepada *Recruiter/HR*. 
Jika *frontend* di-deploy ke Vercel (URL berakhiran `.vercel.app`), sistem akan **otomatis mem-bypass otentikasi login** dan memuat **Data Simulasi (Dummy Data)** interaktif ke dalam dashboard. Hal ini memungkinkan siapapun untuk merasakan langsung *User Experience (UX)* dari sistem ini tanpa perlu melakukan setup *backend* AI / LLM secara lokal.

*(Masukkan link Vercel Anda di sini nantinya)*

#### API Endpoints
| Endpoint | Method | Deskripsi |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/dashboard/summary` | GET | KPI summary |
| `/api/dashboard/distributions` | GET | Sentiment, issue, stance, action intent distributions |
| `/api/dashboard/timeline?days=30` | GET | Timeline komentar per hari |
| `/api/dashboard/representative-comments?limit=8` | GET | Sample komentar representatif |
| `/api/dashboard/interpretation` | GET | Auto-generated insight panel |
| `/api/comments?video_id=&sentiment=&limit=50&offset=0` | GET | Paginated comment list |
| `/api/videos` | GET | List video yang dipantau |
| `/api/crawler/status` | GET | Status crawler + recent runs |
| `/api/crawler/run` | POST | Trigger manual crawl |
| `/api/crawler/start` | POST | Aktifkan auto-crawl scheduler |
| `/api/crawler/stop` | POST | Hentikan auto-crawl scheduler |