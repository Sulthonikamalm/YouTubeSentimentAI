"""
app.py — Flask app entry point for YouTube Comment Monitoring.
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask, jsonify, session, redirect, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import load_settings, get_database_url
from backend.storage.repository import init_db
from backend.services.scheduler_service import start_scheduler_service, trigger_manual_crawl
from backend.routes.dashboard import dashboard_bp
from backend.routes.taxonomy import taxonomy_bp
from backend.routes.comments import comments_bp
from backend.routes.videos import videos_bp
from backend.routes.projects import projects_bp
from backend.routes.crawler import crawler_bp
from backend.routes.auth import auth_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("youtube_collector")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
LANDING_DIR = PROJECT_ROOT / "landing"

# Persist crawler/inference logs to logs/crawler.log so the dashboard live-feed
# (/api/crawler/logs) has something to tail. Without this, the web server only
# logged to stdout and the activity terminal stayed empty. Attached once to the
# "youtube_collector" parent logger — child loggers (.inference, .llm) propagate.
if os.environ.get("VERCEL"):
    _LOG_FILE = Path("/tmp/logs/crawler.log")
else:
    _LOG_FILE = PROJECT_ROOT / "logs" / "crawler.log"

_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
if not any(
    isinstance(h, logging.FileHandler)
    and getattr(h, "baseFilename", "") == str(_LOG_FILE)
    for h in logger.handlers
):
    _file_handler = logging.FileHandler(str(_LOG_FILE), mode="a", encoding="utf-8")
    _file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_file_handler)

app = Flask(__name__)
# SECRET_KEY menandatangani cookie session (penanda login). Diambil dari env
# AUTH_SECRET_KEY bila ada, agar bisa dirahasiakan di produksi.
app.config["SECRET_KEY"] = os.getenv("AUTH_SECRET_KEY", "surabayasambat-youtube-2026")

# Register modular API blueprints (split from the former monolithic dashboard_routes.py)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(comments_bp)
app.register_blueprint(videos_bp)
app.register_blueprint(projects_bp)
app.register_blueprint(taxonomy_bp)
app.register_blueprint(crawler_bp)

# --- Gerbang autentikasi ---
# Dashboard (/dashboard) dan seluruh API hanya bisa diakses setelah login.
# Path di bawah ini tetap terbuka: halaman login, endpoint auth, halaman landing,
# dan aset statis (CSS/JS/gambar) yang dibutuhkan halaman login untuk tampil.
_PUBLIC_PREFIXES = ("/login", "/register", "/api/auth/", "/assets/")
_PUBLIC_EXACT = {"/", "/favicon.ico"}


def _is_public_path(path: str) -> bool:
    if path in _PUBLIC_EXACT or path.startswith(_PUBLIC_PREFIXES):
        return True
    # Aset landing page (file statis di root landing/) tetap publik.
    if "." in path.rsplit("/", 1)[-1] and not path.startswith("/api/"):
        return True
    return False


@app.before_request
def require_login():
    if session.get("user_id"):
        return None
    path = request.path
    if _is_public_path(path):
        return None
    # API yang belum login -> 401 JSON; halaman -> redirect ke /login.
    if path.startswith("/api/"):
        return jsonify({"error": "Belum login"}), 401
    return redirect("/login")

settings = load_settings()
db_url = get_database_url(settings)

try:
    init_db(db_url)
    logger.info("SQLite Database initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing SQLite Database: {e}")

start_scheduler_service(database_url=db_url)

# --- Legacy routes kept for backward compatibility ---

@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({
        "status": "online",
        "project": settings.get("app", {}).get("name", "YouTube Comment Monitoring"),
        "database_url": db_url
    })

@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    result = trigger_manual_crawl(database_url=db_url)
    if result.get("status") == "crawl_already_running":
        return jsonify({"success": False, "error": "crawl_already_running"}), 409
    return jsonify({"success": True, "run_id": result.get("run_id"), "status": result.get("status")})

# --- Serve frontend ---

@app.route("/")
def serve_index():
    return send_from_directory(str(LANDING_DIR), "index.html")

@app.route("/dashboard")
def serve_dashboard():
    return send_from_directory(str(FRONTEND_DIR), "index.html")

@app.route("/<path:path>")
def serve_static(path):
    landing_path = LANDING_DIR / path
    if landing_path.is_file():
        return send_from_directory(str(LANDING_DIR), path)
    return send_from_directory(str(FRONTEND_DIR), path)

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 60)
    print(f"  {settings.get('app', {}).get('name', 'YouTube Comment Monitoring')}")
    print("  Dashboard: http://localhost:5000")
    print("=" * 60)

    app.run(host="0.0.0.0", port=5000, debug=False)
