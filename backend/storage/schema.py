"""
schema.py — SQL schema definitions for SQLite database.
"""

CREATE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    description TEXT,
    owner_user_id INTEGER,
    goal_type TEXT,
    goal_text TEXT,
    status TEXT DEFAULT 'draft',
    active_taxonomy_version_id TEXT,
    prompt_context TEXT,
    issue_labels TEXT,
    stance_labels TEXT,
    action_labels TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_VIDEOS_TABLE = """
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT UNIQUE NOT NULL,
    video_url TEXT NOT NULL,
    video_title TEXT,
    channel_title TEXT,
    project_id TEXT,
    monitoring_enabled BOOLEAN DEFAULT 1,
    first_crawl_done BOOLEAN DEFAULT 0,
    first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    monitoring_started_at DATETIME,
    last_checked_at DATETIME,
    last_seen_comment_at DATETIME,
    total_comments_collected INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_COMMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comment_id TEXT UNIQUE NOT NULL,
    video_id TEXT NOT NULL,
    parent_id TEXT,
    is_reply BOOLEAN NOT NULL,
    author_name TEXT,
    author_channel_id TEXT,
    comment_text TEXT,
    text_original TEXT,
    text_display TEXT,
    published_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    like_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_baseline BOOLEAN NOT NULL,
    is_deleted BOOLEAN DEFAULT 0,
    last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    raw_json_hash TEXT,
    raw_json TEXT,
    sentiment TEXT,
    sentiment_confidence REAL,
    issue_label TEXT,
    stance_label TEXT,
    action_intent_label TEXT,
    interpretation_short TEXT,
    model_version TEXT,
    inference_status TEXT,
    inference_error TEXT,
    inferred_at TEXT,
    is_manually_corrected INTEGER DEFAULT 0,
    taxonomy_version_id TEXT
);
"""

# Inference columns expected on `comments`. Used by both migration script and
# the test bootstrap path that creates a fresh DB from this DDL.
INFERENCE_COLUMNS = [
    ("sentiment", "TEXT"),
    ("sentiment_confidence", "REAL"),
    ("issue_label", "TEXT"),
    ("stance_label", "TEXT"),
    ("action_intent_label", "TEXT"),
    ("interpretation_short", "TEXT"),
    ("model_version", "TEXT"),
    ("inference_status", "TEXT"),
    ("inference_error", "TEXT"),
    ("inferred_at", "TEXT"),
    ("is_manually_corrected", "INTEGER DEFAULT 0"),
    ("taxonomy_version_id", "TEXT"),
]

CREATE_PROJECT_TAXONOMY_VERSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS project_taxonomy_versions (
    version_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    status TEXT NOT NULL, -- 'draft', 'active', 'archived'
    source TEXT NOT NULL, -- 'manual', 'gemini', 'legacy'
    prompt_context TEXT,
    issue_labels TEXT,
    stance_labels TEXT,
    action_labels TEXT,
    regenerate_instruction TEXT,
    model TEXT,
    sample_hash TEXT,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    activated_at DATETIME
);
"""

CREATE_LLM_GENERATION_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS llm_generation_runs (
    run_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    version_id TEXT,
    model TEXT,
    sample_count INTEGER,
    status TEXT, -- 'success', 'failed', 'timeout', 'quota_exceeded'
    token_input INTEGER,
    token_output INTEGER,
    cache_hit BOOLEAN,
    error_type TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME
);
"""

CREATE_CRAWL_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS crawl_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME,
    status TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    videos_checked INTEGER DEFAULT 0,
    comments_fetched INTEGER DEFAULT 0,
    new_comments INTEGER DEFAULT 0,
    duplicate_comments INTEGER DEFAULT 0,
    updated_comments INTEGER DEFAULT 0,
    replies_fetched INTEGER DEFAULT 0,
    api_units_used INTEGER DEFAULT 0,
    error_message TEXT
);
"""

CREATE_API_USAGE_TABLE = """
CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    endpoint TEXT NOT NULL,
    units INTEGER NOT NULL,
    called_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status INTEGER,
    error_message TEXT
);
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_comments_video_id ON comments(video_id);",
    "CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON comments(parent_id);",
    "CREATE INDEX IF NOT EXISTS idx_comments_published_at ON comments(published_at);",
    "CREATE INDEX IF NOT EXISTS idx_comments_is_baseline ON comments(is_baseline);",
    "CREATE INDEX IF NOT EXISTS idx_comments_inference_status ON comments(inference_status);",
    "CREATE INDEX IF NOT EXISTS idx_comments_taxonomy_version ON comments(taxonomy_version_id);",
    "CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_user_id);",
    "CREATE INDEX IF NOT EXISTS idx_taxonomy_project_status ON project_taxonomy_versions(project_id, status);",
    "CREATE INDEX IF NOT EXISTS idx_llm_runs_project_started ON llm_generation_runs(project_id, started_at);",
]

# --- Auth tables (login dashboard: sidik jari/WebAuthn + password cadangan) ---

# Satu baris = satu pengguna. password_hash dipakai untuk login cadangan
# (werkzeug.security), sidik jari disimpan terpisah di tabel `credentials`.
CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT,
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# Satu baris = satu sidik jari/passkey (WebAuthn credential). Satu user boleh
# punya banyak kredensial (sidik jari sendiri, teman, atau perangkat lain).
# credential_id & public_key disimpan sebagai base64url string hasil ceremony.
CREATE_CREDENTIALS_TABLE = """
CREATE TABLE IF NOT EXISTS credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    credential_id TEXT UNIQUE NOT NULL,
    public_key TEXT NOT NULL,
    sign_count INTEGER DEFAULT 0,
    device_label TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""
