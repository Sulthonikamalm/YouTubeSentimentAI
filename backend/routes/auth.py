"""routes/auth.py — Autentikasi dashboard: sidik jari (WebAuthn/Windows Hello)
dengan password sebagai cadangan.

Alur:
- Daftar  : /api/auth/register/begin  -> /api/auth/register/finish
- Masuk   : /api/auth/login/begin     -> /api/auth/login/finish   (sidik jari)
- Cadangan: /api/auth/login/password
- Tambah sidik jari (saat sudah login): /api/auth/credentials/add/begin -> .../finish

Challenge WebAuthn disimpan sementara di Flask session (cookie ber-tanda-tangan).
credential_id & public_key disimpan di DB sebagai string base64url.
"""

import json
import logging
import secrets
import sqlite3
from pathlib import Path

from flask import Blueprint, request, session, redirect, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    AuthenticatorAttachment,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)

from backend.routes import ok, err, get_db_url
from backend.storage import auth_repo

logger = logging.getLogger("youtube_collector")

auth_bp = Blueprint("auth", __name__)

RP_NAME = "Pantausentimen"
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


# --- Helper: identitas Relying Party diturunkan dari host request ---

def _rp_id() -> str:
    """rp_id = hostname tanpa port (mis. 'localhost')."""
    return request.host.split(":")[0]


def _origin() -> str:
    """Origin lengkap, mis. 'http://localhost:5000'."""
    return request.host_url.rstrip("/")


# --- Serve halaman login ---

@auth_bp.route("/login", methods=["GET"])
@auth_bp.route("/register", methods=["GET"])
def serve_login_page():
    return send_from_directory(str(FRONTEND_DIR), "login.html")


# --- Status user ---

@auth_bp.route("/api/auth/me", methods=["GET"])
def me():
    user_id = session.get("user_id")
    if not user_id:
        return err("Belum login", 401)
    user = auth_repo.get_user_by_id(user_id, get_db_url())
    if not user:
        session.clear()
        return err("Sesi tidak valid", 401)
    return ok({"id": user["id"], "username": user["username"], "display_name": user["display_name"]})


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return ok({"success": True})


# --- Pendaftaran: buat akun + daftarkan sidik jari ---

@auth_bp.route("/api/auth/register/begin", methods=["POST"])
def register_begin():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    display_name = (data.get("display_name") or "").strip() or username
    password = data.get("password") or ""

    if not username or not password:
        return err("Username dan password cadangan wajib diisi", 400)
    if len(password) < 4:
        return err("Password cadangan minimal 4 karakter", 400)

    db = get_db_url()
    # Akun TIDAK dibuat di sini. Hanya tolak bila username sudah benar-benar
    # dipakai oleh akun yang SUDAH punya sidik jari. Akun lama tanpa sidik jari
    # (mis. dibuat sebelum perbaikan, atau akun admin bawaan) boleh dilengkapi.
    existing = auth_repo.get_user_by_username(username, db)
    existing_id = None
    if existing:
        if auth_repo.get_credentials_for_user(existing["id"], db):
            return err("Username sudah dipakai, silakan pilih yang lain", 409)
        existing_id = existing["id"]

    # user handle WebAuthn cukup acak (login kita berbasis credential_id, bukan handle).
    user_handle = secrets.token_bytes(16)
    options = generate_registration_options(
        rp_id=_rp_id(),
        rp_name=RP_NAME,
        user_id=user_handle,
        user_name=username,
        user_display_name=display_name,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )

    # Simpan data pendaftaran TERTUNDA — baru ditulis ke DB setelah sidik jari sukses.
    session["pending_reg"] = {
        "username": username,
        "display_name": display_name,
        "password_hash": generate_password_hash(password),
        "existing_id": existing_id,
        "challenge": bytes_to_base64url(options.challenge),
    }
    return ok(json.loads(options_to_json(options)))


@auth_bp.route("/api/auth/register/finish", methods=["POST"])
def register_finish():
    pending = session.get("pending_reg")
    if not pending:
        return err("Sesi pendaftaran tidak ditemukan, mulai ulang", 400)

    data = request.get_json() or {}
    device_label = (data.get("device_label") or "").strip() or None
    credential = data.get("credential") or data

    try:
        verification = verify_registration_response(
            credential=json.dumps(credential),
            expected_challenge=base64url_to_bytes(pending["challenge"]),
            expected_rp_id=_rp_id(),
            expected_origin=_origin(),
        )
    except Exception as e:
        logger.error(f"register_finish verify error: {e}")
        return err(f"Verifikasi sidik jari gagal: {e}", 400)

    db = get_db_url()
    # Buat akun sekarang (atau lengkapi akun lama yang belum punya sidik jari).
    try:
        if pending["existing_id"]:
            user_id = pending["existing_id"]
            auth_repo.update_user_profile(
                user_id, pending["display_name"], pending["password_hash"], db
            )
        else:
            user_id = auth_repo.create_user(
                pending["username"], pending["display_name"], pending["password_hash"], db
            )
    except sqlite3.IntegrityError:
        # Username keburu dibuat di proses lain — pakai yang sudah ada.
        existing = auth_repo.get_user_by_username(pending["username"], db)
        user_id = existing["id"] if existing else None

    if not user_id:
        return err("Gagal menyimpan akun", 500)

    try:
        auth_repo.add_credential(
            user_id=user_id,
            credential_id=bytes_to_base64url(verification.credential_id),
            public_key=bytes_to_base64url(verification.credential_public_key),
            sign_count=verification.sign_count,
            device_label=device_label,
            database_url=db,
        )
    except sqlite3.IntegrityError:
        pass  # sidik jari ini sudah tersimpan (mis. submit ganda) — anggap sukses

    session.pop("pending_reg", None)
    session["user_id"] = user_id  # langsung login setelah daftar
    return ok({"success": True})


# --- Login dengan sidik jari (usernameless / discoverable) ---

@auth_bp.route("/api/auth/login/begin", methods=["POST"])
def login_begin():
    options = generate_authentication_options(
        rp_id=_rp_id(),
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    session["auth_challenge"] = bytes_to_base64url(options.challenge)
    return ok(json.loads(options_to_json(options)))


@auth_bp.route("/api/auth/login/finish", methods=["POST"])
def login_finish():
    challenge_b64 = session.get("auth_challenge")
    if not challenge_b64:
        return err("Sesi login tidak ditemukan, coba lagi", 400)

    data = request.get_json() or {}
    credential = data.get("credential") or data

    cred_id = credential.get("id") if isinstance(credential, dict) else None
    if not cred_id:
        return err("Data sidik jari tidak lengkap", 400)

    db = get_db_url()
    stored = auth_repo.get_credential_by_id(cred_id, db)
    if not stored:
        return err("Sidik jari belum terdaftar di sistem ini", 404)

    try:
        verification = verify_authentication_response(
            credential=json.dumps(credential),
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=_rp_id(),
            expected_origin=_origin(),
            credential_public_key=base64url_to_bytes(stored["public_key"]),
            credential_current_sign_count=stored["sign_count"] or 0,
            require_user_verification=True,
        )
    except Exception as e:
        logger.error(f"login_finish verify error: {e}")
        return err("Verifikasi sidik jari gagal", 401)

    auth_repo.update_sign_count(cred_id, verification.new_sign_count, db)
    session.pop("auth_challenge", None)
    session["user_id"] = stored["user_id"]
    return ok({"success": True})


# --- Login cadangan dengan password ---

@auth_bp.route("/api/auth/login/password", methods=["POST"])
def login_password():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return err("Username dan password wajib diisi", 400)

    user = auth_repo.get_user_by_username(username, get_db_url())
    if not user or not check_password_hash(user["password_hash"], password):
        return err("Username atau password salah", 401)

    session["user_id"] = user["id"]
    return ok({"success": True})


# --- Tambah sidik jari baru ke akun yang sedang login ---

@auth_bp.route("/api/auth/credentials/add/begin", methods=["POST"])
def add_credential_begin():
    user_id = session.get("user_id")
    if not user_id:
        return err("Harus login dulu", 401)

    db = get_db_url()
    user = auth_repo.get_user_by_id(user_id, db)
    if not user:
        return err("Sesi tidak valid", 401)

    existing = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["credential_id"]))
        for c in auth_repo.get_credentials_for_user(user_id, db)
    ]

    options = generate_registration_options(
        rp_id=_rp_id(),
        rp_name=RP_NAME,
        user_id=str(user_id).encode("utf-8"),
        user_name=user["username"],
        user_display_name=user["display_name"] or user["username"],
        exclude_credentials=existing,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )
    session["addcred_user_id"] = user_id
    session["addcred_challenge"] = bytes_to_base64url(options.challenge)
    return ok(json.loads(options_to_json(options)))


@auth_bp.route("/api/auth/credentials/add/finish", methods=["POST"])
def add_credential_finish():
    user_id = session.get("addcred_user_id")
    challenge_b64 = session.get("addcred_challenge")
    if not user_id or not challenge_b64:
        return err("Sesi penambahan sidik jari tidak ditemukan, mulai ulang", 400)
    if session.get("user_id") != user_id:
        return err("Harus login dulu", 401)

    data = request.get_json() or {}
    device_label = (data.get("device_label") or "").strip() or None
    credential = data.get("credential") or data

    try:
        verification = verify_registration_response(
            credential=json.dumps(credential),
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=_rp_id(),
            expected_origin=_origin(),
        )
    except Exception as e:
        logger.error(f"add_credential_finish verify error: {e}")
        return err(f"Verifikasi sidik jari gagal: {e}", 400)

    try:
        auth_repo.add_credential(
            user_id=user_id,
            credential_id=bytes_to_base64url(verification.credential_id),
            public_key=bytes_to_base64url(verification.credential_public_key),
            sign_count=verification.sign_count,
            device_label=device_label,
            database_url=get_db_url(),
        )
    except sqlite3.IntegrityError:
        return err("Sidik jari ini sudah terdaftar", 409)

    session.pop("addcred_user_id", None)
    session.pop("addcred_challenge", None)
    return ok({"success": True})
