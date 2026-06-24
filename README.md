<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1a1a2e,50:16213e,100:0f3460&height=230&section=header&text=YouTube%20Sentiment%20AI&fontSize=56&fontColor=e2e8f0&animation=fadeIn&fontAlignY=40&desc=Untold%20Story%20%7C%20Comment%20Intelligence%20Platform&descAlignY=60&descAlign=50&descColor=7c83fd" width="100%"/>

<br/>

[![Typing SVG](https://readme-typing-svg.demolab.com?font=Fira+Code&size=17&duration=3000&pause=1000&color=7C83FD&background=FFFFFF00&center=true&vCenter=true&width=720&lines=Crawling+%E2%86%92+Preprocessing+%E2%86%92+ML+%E2%86%92+LLM+%E2%86%92+Dashboard;YouTube+Data+API+v3+%7C+Google+Gemini+%7C+Sahabat+AI;Analisis+Sentimen+Komentar+Untold+Story+Indonesia)](https://git.io/typing-svg)

<br/>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-Backend-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?style=flat-square&logo=scikitlearn&logoColor=white)](https://scikit-learn.org)
[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?style=flat-square&logo=jupyter&logoColor=white)](https://jupyter.org)
[![Pandas](https://img.shields.io/badge/Pandas-Data-150458?style=flat-square&logo=pandas&logoColor=white)](https://pandas.pydata.org)
[![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white)](https://numpy.org)

[![YouTube API](https://img.shields.io/badge/YouTube_Data_API-v3-FF0000?style=flat-square&logo=youtube&logoColor=white)](https://developers.google.com/youtube/v3)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-Draft_AI-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![Ollama](https://img.shields.io/badge/Ollama-Local_Runtime-FF6B35?style=flat-square&logo=ollama&logoColor=white)](https://ollama.ai)
[![Sahabat AI](https://img.shields.io/badge/Sahabat_AI-8B_Model-16A34A?style=flat-square&logo=openai&logoColor=white)](https://sahabat.ai)
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)](https://developer.mozilla.org)
[![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)](https://developer.mozilla.org)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)](https://developer.mozilla.org)
[![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?style=flat-square&logo=chartdotjs&logoColor=white)](https://chartjs.org)

</div>

---

## Tentang Project

Semuanya berawal dari dua video YouTube: **Untold Story Part 1 dan Part 2**. Keduanya membahas kondisi politik dan sosial Indonesia yang cukup tajam dan jujur. Setelah menontonnya, satu pertanyaan terus berputar di kepala: bagaimana sebenarnya orang-orang di kolom komentar merespons konten seperti ini?

Apakah mayoritas komentar berisi kemarahan dan kritik? Atau justru banyak yang mendukung narasi videonya? Atau sebagian besar justru bersikap netral, sekadar menonton tanpa opini yang kuat? Dari rasa penasaran itulah project ini lahir. Bukan dari template atau tutorial yang sudah jadi, tapi mulai dari nol dan berjalan pelan-pelan.

---

## Perjalanan Project

### Fase 1 - Mengumpulkan Data dengan API Resmi

Langkah pertama yang terlintas adalah: dari mana datanya? Pilihan yang paling masuk akal adalah menggunakan cara yang benar-benar resmi. Google menyediakan **YouTube Data API v3** yang bisa diakses langsung dari Google Cloud Console. Prosesnya butuh waktu, mulai dari membuat project di console, mengaktifkan API, sampai mendapatkan API key yang sah. Setelah itu, crawling komentar dari kedua video Untold Story bisa mulai dijalankan.

### Fase 2 - Eksplorasi di Jupyter Notebook

Setelah punya data mentah, saya tidak langsung melompat ke sistem yang besar. Semua eksplorasi dilakukan pelan-pelan di Jupyter Notebook, tersimpan di file `YouTube_Comment_Intelligence_v7_2_RUN_READY_FIXED.ipynb`, dan hasilnya ada di folder `outputs/`.

Di sinilah saya pertama kali serius mempelajari NLP bahasa Indonesia. Beberapa istilah yang baru saya temui di sini:

- **Case folding** - semua huruf disamakan jadi lowercase supaya "BAGUS" dan "bagus" tidak dianggap kata yang berbeda
- **Tokenisasi** - kalimat dipecah menjadi token atau kata-kata individual
- **Normalisasi slang** - kata gaul atau typo dikonversi ke bentuk bakunya ("gk" jadi "tidak", "bgt" jadi "banget")
- **Stemming** - kata dikembalikan ke bentuk dasarnya ("membangun" jadi "bangun")

Beberapa model dicoba sekaligus untuk melihat perbandingan performanya. Akurasi belum sempurna, dan itu bukan masalah besar, karena tujuan project ini memang bukan semata-mata mengejar angka akurasi tertinggi.

### Fase 3 - Membangun Sistem Web

Setelah eksplorasi di notebook dirasa cukup, mulai terpikirkan: bagaimana kalau ini dibuat jadi sistem yang bisa langsung dipakai? User tinggal tambahkan link video, bisa crawling kapan saja, bisa lihat hasil analisis, bahkan bisa hapus data yang tidak diinginkan.

Dari situ mulai dibangunlah aplikasi web dengan Flask. Model terbaik dari notebook diintegrasikan, dan alur dasarnya sudah berjalan. Tapi ada masalah yang cepat ketahuan: model itu masih sering salah, terutama untuk komentar sarkasme atau bahasa gaul yang sangat spesifik Indonesia. Apakah masalahnya di tahap preprocessing, di tuning model, atau memang butuh data latih yang lebih baik, saya belum bisa pastikan saat itu karena masih dalam proses belajar.

### Fase 4 - Pendekatan Hybrid: ML + Gemini

Ide yang kemudian muncul adalah pendekatan hybrid: model ML sebagai analisis awal, lalu hasilnya dibantu dan divalidasi oleh **Google Gemini**. Hasilnya memang lebih baik. Gemini jauh lebih paham konteks, sarkasme, dan bahasa informal Indonesia. Tapi ada batas yang tidak bisa dihindari: limit free tier Gemini sangat terbatas, dan untuk dataset komentar yang besar, itu jelas tidak akan cukup.

### Fase 5 - Beralih ke AI Lokal: Sahabat AI

Setelah berdiskusi panjang, saya menemukan **Sahabat AI**, sebuah AI lokal buatan Indonesia. Kelebihannya jelas: tidak ada limit API, akurasi untuk konten bahasa Indonesia sangat tinggi, dan tingkat halusinasi jauh lebih rendah dibanding model generik.

Tantangannya ada di performa di laptop sendiri. Saya menjalankan model dengan parameter 8B di laptop dengan spesifikasi yang pas-pasan. Awalnya untuk menganalisis 3 komentar saja butuh sekitar 20 detik. Angka itu cukup berat untuk sistem yang ingin dipakai secara interaktif.

Setelah beberapa iterasi optimasi, mulai dari cara menyusun prompt sampai format output yang diminta model, hasilnya seperti ini:

| Pendekatan | Waktu per komentar | Reliabilitas | Output tokens |
|---|---|---|---|
| Produksi lama (string, batch 3) | ~13 detik | Tidak stabil | ~70/batch |
| Single JSON coded | 7.1 detik | 5/5 | 18/kmt |
| Single CSV coded | 4.6 detik | 5/5 | 8/kmt |

Pemenangnya adalah pendekatan **single-comment + output CSV integer**, sekitar 2.8x lebih cepat dari produksi lama dan 100% andal. Waktu total untuk 3 komentar berhasil dipangkas dari 20 detik menjadi sekitar 12 detik. Bukan angka yang impresif secara absolut, tapi itu murni karena keterbatasan spesifikasi laptop, bukan karena sistem-nya.

### Fase 6 - Dynamic Few-Shot Prompting

Sarkasme dan ungkapan khas Indonesia yang sangat lokal bisa membuat LLM salah. Solusinya: membuat file konfigurasi kecil berisi contoh komentar yang sering salah dideteksi beserta label yang benar. Contoh-contoh itu otomatis disisipkan ke dalam setiap prompt, sehingga model belajar langsung dari contoh konkret, bukan hanya dari instruksi abstrak. Akurasi pada komentar bercorak sarkasme naik signifikan dari sini.

### Fase 7 - Human-in-the-Loop

LLM tidak selalu 100% benar, dan itu wajar. Fitur ini memungkinkan pengguna mengoreksi label analisis langsung dari dashboard. Setiap koreksi manual disimpan di database dengan tanda `is_manually_corrected = true`. Data koreksi itu kemudian otomatis masuk ke dalam few-shot examples untuk prompt berikutnya, jadi sistem terus belajar dari kesalahan tanpa perlu retraining model dari awal.

---

## Alur Kerja

```
Buat project
     |
     v
Tambah video YouTube
     |
     v
Crawl komentar (minimal 20)
     |
     v
Generate draft taxonomy via Gemini
     |
     v
Edit manual / generate ulang draft
     |
     v
Aktifkan versi taxonomy
     |
     v
Analisis lokal berjalan otomatis
```

---

## Fitur Utama

- **Crawling resmi via API** - Request langsung ke endpoint `commentThreads.list` dan `comments.list`, tanpa scraping tidak resmi
- **Incremental crawling** - Hanya mengambil komentar baru, berhenti otomatis saat menemukan komentar lama berturut-turut
- **Pemisahan baseline vs monitoring** - Crawl pertama ditandai sebagai baseline, crawl berikutnya sebagai komentar baru
- **Tracking edit komentar** - Mendeteksi perubahan timestamp `updated_at` dari API dan memperbarui record
- **Quota protection** - Memantau konsumsi unit API harian dan berhenti aman sebelum limit tercapai
- **Hybrid inference** - ML model + Gemini (draft taxonomy) + Sahabat AI via Ollama (analisis massal lokal)
- **Few-shot prompting dinamis** - Contoh komentar sulit otomatis disisipkan ke prompt untuk akurasi lebih tinggi
- **Human-in-the-loop** - Koreksi label dari dashboard langsung menjadi bahan few-shot berikutnya
- **Background scheduler** - Daemon thread dengan prevent-overlap untuk auto-crawl berkala
- **Dashboard interaktif** - Visualisasi sentimen, isu, stance, word cloud, dan insight otomatis

---

## Stack Teknologi

| Lapisan | Teknologi |
|---|---|
| Data Collection | YouTube Data API v3 (Official Google) |
| NLP Preprocessing | NLTK, PySastrawi (Stemmer Bahasa Indonesia) |
| Machine Learning | scikit-learn, Pandas, NumPy |
| LLM / AI | Google Gemini API (draft taxonomy), Sahabat AI via Ollama (analisis massal) |
| Backend | Python, Flask, SQLite |
| Frontend | HTML5, CSS3, Vanilla JavaScript, Chart.js |
| Eksplorasi | Jupyter Notebook |

---

## Struktur Folder

```
sentimenuntoldstory/
├── backend/
│   ├── crawler/
│   │   ├── crawl_runner.py           # Orchestrator alur monitoring & crawling
│   │   ├── dedup.py                  # Logika dedup & early stop check
│   │   ├── quota_tracker.py          # Tracking unit API yang dikonsumsi
│   │   └── video_registry.py         # Registry video aktif
│   ├── ml/
│   │   ├── model_loader.py           # Singleton loader model .joblib
│   │   ├── sentiment_predictor.py    # Adapter model ML + normalisasi teks
│   │   ├── taxonomy.py               # Rule-based: issue, stance, action_intent
│   │   └── intelligence_engine.py    # Komposer: sentiment + taxonomy + interpretasi
│   ├── services/
│   │   ├── inference_service.py      # Batch inference orchestrator
│   │   └── scheduler_service.py      # Background scheduler loop & locks
│   ├── storage/
│   │   ├── db.py                     # SQLite connection context
│   │   ├── repository.py             # CRUD repository operations
│   │   └── schema.py                 # DDL SQLite schemas
│   ├── youtube/
│   │   ├── comment_normalizer.py     # Normalizer data API ke schema internal
│   │   ├── video_utils.py            # Video ID parser dari berbagai format URL
│   │   └── youtube_client.py         # Wrapper Google API Client dengan retry & backoff
│   ├── config.py
│   ├── app.py                        # Flask server entry point
│   └── dashboard_routes.py           # Blueprint API endpoints dashboard
├── frontend/
│   ├── index.html
│   └── assets/
│       ├── css/styles.css
│       └── js/dashboard.js
├── config/
│   └── settings.yaml
├── data/
│   ├── youtube_monitor.db            # Database SQLite (gitignored)
│   └── exports/                      # Target folder export CSV (gitignored)
├── outputs/
│   └── models/
│       └── BEST_MODEL_LATEST.joblib  # Model sentiment dari notebook (gitignored)
├── scripts/
│   ├── init_db.py
│   ├── add_video.py
│   ├── run_crawl.py
│   ├── export_comments.py
│   ├── migrate_inference_columns.py
│   ├── run_inference.py
│   └── inspect_inference_status.py
├── tests/
├── YouTube_Comment_Intelligence_v7_2_RUN_READY_FIXED.ipynb
├── .env.example
└── requirements.txt
```

---

## Cara Setup & Menjalankan

### 1. Instalasi Dependensi

Pastikan Python 3.10+ sudah terpasang, lalu jalankan:

```bash
pip install -r requirements.txt
```

### 2. Konfigurasi Environment

Salin `.env.example` menjadi `.env` lalu isi API key YouTube:

```bash
copy .env.example .env
```

```env
YOUTUBE_API_KEY=AIzaSy...
```

**Konfigurasi Gemini (opsional)**

Gemini hanya digunakan untuk menyusun draft taxonomy dan konteks project. Analisis komentar massal tetap berjalan di pipeline lokal, Gemini tidak dipanggil per komentar.

```env
ENABLE_GEMINI_TAXONOMY=true
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_TIMEOUT_SECONDS=30
GEMINI_MAX_GENERATIONS_PER_PROJECT_PER_DAY=3
GEMINI_SAMPLE_LIMIT=100
GEMINI_MIN_SAMPLE_SIZE=20
```

Jangan memasukkan API key ke source code atau commit Git. Key yang pernah dibagikan melalui chat atau media lain harus dicabut di Google Cloud dan diganti dengan key baru.

Alur penggunaan Gemini di dashboard:

1. Buat project dengan nama dan tujuan pemantauan.
2. Tambahkan video, lalu crawl sedikitnya 20 komentar valid.
3. Buka menu `Taxonomy AI` dan pilih `Generate dengan Gemini`.
4. Tinjau, tambah, hapus, atau ubah seluruh label pada draft.
5. Gunakan kolom instruksi untuk generate ulang seluruh draft jika diperlukan.
6. Aktifkan hanya untuk komentar berikutnya, atau pilih analisis ulang secara eksplisit.

Saat Gemini tidak aktif, quota habis, atau API key tidak tersedia, gunakan `Buat draft manual`. Mode ini tidak memanggil Gemini dan tetap mendukung edit, versioning, aktivasi, serta analisis ulang.

Request Gemini yang identik memakai cache. Maksimal tiga request baru per project per hari dicatat di tabel `llm_generation_runs`, cache hit tidak dihitung.

### 3. Inisialisasi Database

```bash
python scripts/init_db.py
```

Untuk database yang sudah ada sebelumnya, jalankan migrasi idempotent:

```bash
python scripts/migrate_project_taxonomy.py
```

### 4. Tambahkan Video

```bash
python scripts/add_video.py "https://youtu.be/K8EKqxU-UwM"
```

Mendukung URL pendek, URL watch, URL Shorts, maupun ID langsung.

### 5. Crawling

```bash
python scripts/run_crawl.py
```

Run pertama mengumpulkan semua komentar sebagai baseline dataset. Run berikutnya hanya mengambil komentar baru (incremental). Setelah crawl selesai, inference berjalan otomatis untuk komentar baru.

### 6. Inference Manual

```bash
# Hanya komentar yang belum diproses
python scripts/run_inference.py --pending --limit 500

# Ulang semua komentar
python scripts/run_inference.py --all --confirm

# Lihat distribusi status
python scripts/inspect_inference_status.py
```

Flag `--confirm` diperlukan untuk mencegah eksekusi tidak sengaja saat mengulang semua komentar.

### 7. Export ke CSV

```bash
python scripts/export_comments.py
```

Hasil tersimpan di `data/exports/comments_export_YYYYMMDD_HHMMSS.csv`.

### 8. Jalankan Dashboard

```bash
python backend/app.py
```

Buka `http://localhost:5000` di browser.

### 9. Unit Test

```bash
pytest
```

Semua test menggunakan mock, aman dijalankan tanpa mengonsumsi kuota API.

---

## Fitur Dashboard

- KPI Cards: total komentar, video dipantau, komentar baru 24h, progress inference, kuota API harian
- Tren komentar dan sentimen per hari (stacked bar chart)
- Distribusi sentimen (doughnut chart)
- Top isu, stance, dan action intent (horizontal bar chart)
- Word cloud dari label inference
- Insight otomatis: sentimen dominan, isu terbesar, stance, rekomendasi
- Komentar representatif dengan label lengkap
- Koreksi label manual langsung dari tabel komentar
- Filter berdasarkan video, rentang waktu (24h/7d/30d/semua), dan tipe (baseline/baru)
- Auto-refresh setiap 60 detik
- Trigger crawl manual dari UI
- Toggle auto-crawl scheduler dari UI
- Toast notifications untuk setiap aksi
- Responsive design dengan sidebar collapsible

---

## Output Inference per Komentar

| Kolom | Keterangan |
|---|---|
| `sentiment` | positive / neutral / negative |
| `sentiment_confidence` | skor kepercayaan prediksi |
| `issue_label` | isu yang dibahas (ekonomi_rakyat, hukum_korupsi, dll.) |
| `stance_label` | sikap komentator (kritik_pemerintah, dukung_video, dll.) |
| `action_intent_label` | kecenderungan ekspresi (menuntut_akuntabilitas, dll.) |
| `interpretation_short` | interpretasi satu kalimat |
| `model_version` | versi model yang digunakan |
| `inference_status` | completed / failed / model_unavailable |
| `inference_error` | detail error jika ada |
| `inferred_at` | timestamp proses inference |

---

## API Endpoints

| Endpoint | Method | Deskripsi |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/dashboard/summary` | GET | KPI summary |
| `/api/dashboard/distributions` | GET | Distribusi sentimen, isu, stance, action intent |
| `/api/dashboard/timeline?days=30` | GET | Timeline komentar per hari |
| `/api/dashboard/representative-comments?limit=8` | GET | Sampel komentar representatif |
| `/api/dashboard/interpretation` | GET | Panel insight otomatis |
| `/api/comments?video_id=&sentiment=&limit=50&offset=0` | GET | Daftar komentar (paginated) |
| `/api/videos` | GET | Daftar video yang dipantau |
| `/api/crawler/status` | GET | Status crawler dan riwayat run |
| `/api/crawler/run` | POST | Trigger crawl manual |
| `/api/crawler/start` | POST | Aktifkan auto-crawl |
| `/api/crawler/stop` | POST | Hentikan auto-crawl |

---

## System Architecture & Pipeline

Berikut adalah arsitektur sistem lengkap dari **YouTube Comment Intelligence Platform** — mulai dari pengumpulan data mentah di YouTube hingga visualisasi insight di dashboard. Alur ini dirancang berdasarkan prinsip *incremental crawling*, *dual-engine inference*, dan *real-time monitoring*.

---

### 1. Overview Arsitektur Sistem

```mermaid
flowchart TD
    subgraph INPUT["① DATA SOURCE"]
        YT["🎬 YouTube Videos\n(Untold Story Pt.1 & Pt.2)"]
        API["YouTube Data API v3\n(commentThreads.list\ncomments.list\nvideos.list)"]
        YT --> API
    end

    subgraph CRAWL["② CRAWLING LAYER\ncrawl_runner.py"]
        direction TB
        QT["Quota Tracker\n≤10.000 unit/hari"]
        DED["Deduplicator\n(consecutive-dup early-stop)"]
        NORM["Comment Normalizer\n(Unicode, slang, emoji)"]
        API --> QT --> DED --> NORM
    end

    subgraph STORE["③ STORAGE\nSQLite · repository.py"]
        DB[("SQLite DB\ncomments\nvideos\ncrawl_runs\napi_usage\ntaxonomy")]
        NORM --> DB
    end

    subgraph INFER["④ INFERENCE ENGINE\ninference_service.py"]
        direction TB
        CACHE{"Prediction\nCache Hit?"}
        LLM["🤖 Sahabat AI 8B\n(Ollama · local)\nChain-of-Thought Prompt"]
        FALLBACK["📋 Rule-Based Taxonomy\n(keyword matching)"]
        PARSE["JSON Label Parser\n+ Label Validator"]
        INTERP["Interpretation Builder\n(human-readable sentence)"]
        DB --> CACHE
        CACHE -- "HIT (same text)" --> INTERP
        CACHE -- "MISS" --> LLM
        LLM -- "Ollama down" --> FALLBACK
        LLM --> PARSE --> INTERP
        FALLBACK --> INTERP
        INTERP --> DB
    end

    subgraph OUTPUT["⑤ OUTPUT LABELS"]
        direction LR
        S["sentiment\nnegative·neutral\n·positive"]
        I["issue\n10 kategori"]
        ST["stance\n8 kategori"]
        A["action_intent\n8 kategori"]
    end

    subgraph DASH["⑥ DASHBOARD\nFlask API + Vanilla JS"]
        KPI["KPI Cards\n(total, 24h, pending)"]
        CHART["Distribusi Chart\n(Chart.js)"]
        TIMELINE["Timeline Trend\n(per hari)"]
        INSIGHT["Auto Insight Panel\n(warnings + rekomendasi)"]
        REALTIME["Real-time Feed\n(per menit)"]
    end

    INTERP --> S & I & ST & A
    DB --> KPI & CHART & TIMELINE & INSIGHT & REALTIME

    style INPUT fill:#1e3a5f,color:#e2e8f0,stroke:#3b82f6
    style CRAWL fill:#1e3a5f,color:#e2e8f0,stroke:#3b82f6
    style STORE fill:#1a2e1a,color:#e2e8f0,stroke:#22c55e
    style INFER fill:#3b1f2b,color:#e2e8f0,stroke:#ec4899
    style OUTPUT fill:#2d1f3d,color:#e2e8f0,stroke:#a855f7
    style DASH fill:#1f2937,color:#e2e8f0,stroke:#f59e0b
```

---

### 2. Dual-Engine Inference Pipeline

Sistem menggunakan dua mesin inferensi yang bekerja secara hierarkis — prioritas utama ke **LLM lokal** (Sahabat AI 8B via Ollama), dengan *fallback* otomatis ke **Rule-Based Taxonomy** jika model tidak tersedia.

```mermaid
flowchart LR
    subgraph INPUT2["Input Representation"]
        direction TB
        RAW["Raw Comment Text\n(Bahasa Indonesia)"]
        CTX["Context Builder\n+ parent reply text\n+ is_reply flag"]
        NORM2["Text Normalizer\n(slang · emoji · unicode)"]
        RAW --> NORM2 --> CTX
    end

    subgraph ENGINE["SentimentAI-Indonesia\n(Dual-Engine)"]
        direction TB

        subgraph PRIMARY["Primary: LLM Inference"]
            COT["Chain-of-Thought Prompt\nanalisis → labels"]
            SAHABAT["Sahabat AI 8B\n(llama3_instruct_Q4_K_M)\nvia Ollama · localhost:11434"]
            RETRY["Retry (×2)\n+ Exponential Backoff"]
            COT --> SAHABAT --> RETRY
        end

        subgraph FALLBACK2["Fallback: Rule-Based Taxonomy"]
            KW["Keyword Matcher\n(taxonomy.py)"]
            classify["classify_issue()\nclassify_stance()\nclassify_action_intent()"]
            KW --> classify
        end

        VOTE["Label Validator\n(out-of-vocab → safe default)\n+ Interpretation Builder"]
        PRIMARY -- "success" --> VOTE
        PRIMARY -- "no response / Ollama down" --> FALLBACK2 --> VOTE
    end

    subgraph OUTPUT2["Final Decision"]
        direction TB
        SEN["sentiment\nnegative / neutral / positive"]
        ISS["issue label\n10 kategori isu publik"]
        STA["stance label\n8 kategori sikap"]
        ACT["action intent\n8 kategori intensi"]
        SHO["interpretation_short\n(kalimat naratif)"]
        VOTE --> SEN & ISS & STA & ACT & SHO
    end

    subgraph CACHE2["Prediction Cache\n(SQLite · same text → reuse)"]
        CHK{"Cache\nHit?"}
    end

    CTX --> CHK
    CHK -- "HIT" --> VOTE
    CHK -- "MISS" --> ENGINE

    style ENGINE fill:#2d1b2e,color:#f3e8ff,stroke:#c084fc
    style PRIMARY fill:#1e1b4b,color:#e0e7ff,stroke:#818cf8
    style FALLBACK2 fill:#1c2432,color:#dbeafe,stroke:#60a5fa
    style OUTPUT2 fill:#14202e,color:#fef9c3,stroke:#facc15
    style CACHE2 fill:#0f2318,color:#dcfce7,stroke:#4ade80
    style INPUT2 fill:#1e293b,color:#e2e8f0,stroke:#94a3b8
```

---

### 3. Alur Crawling Inkremental

```mermaid
sequenceDiagram
    actor User as 👤 User / Scheduler
    participant Sched as Scheduler Service
    participant Runner as Crawl Runner
    participant YT as YouTube API v3
    participant DB as SQLite DB
    participant Infer as Inference Service
    participant LLM as Sahabat AI (Ollama)

    User->>Sched: Manual trigger / Auto (interval)
    Sched->>Runner: run_youtube_crawl(trigger_type)
    Runner->>DB: save_crawl_run(status=running)
    Runner->>YT: videos.list (metadata)
    YT-->>Runner: video_title, channel_title

    loop Setiap video yang dipantau
        Runner->>YT: commentThreads.list(page_token)
        YT-->>Runner: comment items + inline replies

        loop Setiap komentar
            Runner->>DB: check dedup (comment_id)
            alt Komentar baru
                Runner->>DB: save_comment(status=pending)
            else Komentar diperbarui
                Runner->>DB: update_comment(reset→pending)
            else Duplikat identik
                Runner->>Runner: increment dup_counter
            end

            opt total_replies > inline_count
                Runner->>YT: comments.list(parent_id)
                YT-->>Runner: full reply thread
                Runner->>DB: save_replies
            end
        end

        Runner->>DB: update_video_last_checked
    end

    Runner->>DB: save_crawl_run(status=completed)

    alt new_comments > 0 OR updated_comments > 0
        Runner->>Infer: infer_pending(limit=500)
        Infer->>DB: get_pending_comment_ids
        Infer->>LLM: analyze_comments_batch (chunk=3)
        LLM-->>Infer: JSON labels (sentiment, issue, stance, action)
        Infer->>DB: batch_update_inference (per chunk)
    end

    Infer-->>User: ✅ Dashboard diperbarui secara real-time
```

---

### 4. Taksonomi Label

Label yang diprediksi mencakup **4 dimensi analisis** yang saling melengkapi:

```mermaid
mindmap
  root((Analisis\nKomentar))
    Sentiment
      negative
      neutral
      positive
    Issue
      ekonomi_rakyat
      kepercayaan_publik
      pemerintahan_kebijakan
      hukum_korupsi
      elite_politik
      geopolitik_keamanan
      media_narasi
      demokrasi_aksi_publik
      feedback_video
      lainnya
    Stance
      kritik_pemerintah
      dukung_pemerintah
      dukung_video
      kritik_video
      sinis_tidak_percaya
      netral_informatif
      debat_antar_pengguna
      tidak_terdeteksi
    Action Intent
      menuntut_akuntabilitas
      dorongan_aksi_publik
      perubahan_elektoral
      menyebarkan_kesadaran
      harapan_doa
      menunggu_mengamati
      apatis_sinis
      tidak_terdeteksi
```

---

### 5. Ringkasan Teknis Pipeline

| Tahap | Komponen | Teknologi |
|---|---|---|
| **① Data Source** | YouTube comment threads + replies | YouTube Data API v3 |
| **② Crawling** | Incremental crawl, dedup, quota guard | `crawl_runner.py` · Python |
| **③ Preprocessing** | Normalisasi teks, slang Bahasa Indonesia, emoji stripping | `text_utils.py` · `normalize_text()` |
| **④ Inference (Primary)** | Chain-of-Thought prompting → 4-label JSON | Sahabat AI 8B · Ollama · `ollama_service.py` |
| **④ Inference (Fallback)** | Keyword-based taxonomy matching | `intelligence_engine.py` · `taxonomy.py` |
| **⑤ Caching** | Identical text → reuse prediction (scoped per project) | SQLite · `_lookup_cache()` |
| **⑥ Storage** | Structured relational store | SQLite · `repository.py` |
| **⑦ API Layer** | RESTful endpoints, auth guard, blueprint modular | Flask · `app.py` |
| **⑧ Visualization** | KPI, distribusi, timeline, real-time feed, insight panel | Chart.js · Vanilla JS |

---

## Live Demo

Project ini bisa di-deploy ke Vercel sebagai static site. Tidak perlu backend aktif karena semua data di halaman demo sudah disimulasikan langsung di browser.

**Cara deploy:**

1. Push repository ke GitHub
2. Buka [vercel.com](https://vercel.com) dan import repository tersebut
3. Vercel otomatis mendeteksi `vercel.json` di root project
4. Klik Deploy, tidak ada environment variable yang dibutuhkan

**URL yang tersedia setelah deploy:**

| URL | Halaman |
|---|---|
| `https://nama-project.vercel.app/` | Landing page |
| `https://nama-project.vercel.app/dashboard` | Dashboard (langsung masuk, tanpa login) |

Ketika diakses dari domain `*.vercel.app`, seluruh API call otomatis dialihkan ke data simulasi yang sudah disiapkan di `api.js`. Data yang muncul adalah contoh analisis sentimen komentar Untold Story Part 1 dan Part 2.

**Vercel Live Demo:** [https://youtubesentimensahabatai.vercel.app/](https://youtubesentimensahabatai.vercel.app/)

---

## Terima Kasih

<div align="center">

Salah satu keputusan paling berpengaruh dalam project ini adalah beralih ke AI lokal Indonesia. Model yang dipakai berjalan di atas infrastruktur **Sahabat AI** - platform kecerdasan buatan lokal yang dibangun untuk bahasa dan konteks Indonesia. Hasilnya jauh lebih akurat untuk komentar berbahasa Indonesia, tingkat halusinasi lebih rendah, dan tidak ada batasan kuota yang menghambat analisis skala besar.

<br/>

<a href="https://sahabat-ai.com/" target="_blank">
  <img src="https://d2v6npc8wmnkqk.cloudfront.net/storage/23244/Sahabat-AI-Logo---Dark-(Horizontal).png" alt="Sahabat AI" height="48"/>
</a>

<br/><br/>

[![Sahabat AI](https://img.shields.io/badge/Powered_by-Sahabat_AI-16A34A?style=for-the-badge&logo=openai&logoColor=white)](https://sahabat-ai.com/)

</div>

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f3460,50:16213e,100:1a1a2e&height=120&section=footer" width="100%"/>

</div>
