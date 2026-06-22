"""auth_repo.py — Operasi DB untuk autentikasi (users + credentials).

Dipakai oleh routes/auth.py untuk login dashboard via sidik jari (WebAuthn /
Windows Hello) dengan password sebagai cadangan. Mengikuti pola repository.py:
setiap fungsi membuka koneksi lewat get_db_connection() dan mengembalikan dict.
"""

from typing import List, Dict, Any, Optional

from backend.storage.db import get_db_connection


# --- Users ---

def count_users(database_url: str = None) -> int:
    with get_db_connection(database_url) as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM users;").fetchone()
        return int(row["n"]) if row else 0


def create_user(username: str, display_name: str, password_hash: str,
                database_url: str = None) -> int:
    """Buat user baru, kembalikan id-nya. Raise sqlite3.IntegrityError bila username dipakai."""
    with get_db_connection(database_url) as conn:
        with conn:
            cur = conn.execute(
                "INSERT INTO users (username, display_name, password_hash) VALUES (?, ?, ?);",
                (username, display_name, password_hash),
            )
            return int(cur.lastrowid)


def get_user_by_username(username: str, database_url: str = None) -> Optional[Dict[str, Any]]:
    with get_db_connection(database_url) as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?;", (username,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int, database_url: str = None) -> Optional[Dict[str, Any]]:
    with get_db_connection(database_url) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
        return dict(row) if row else None


def update_user_profile(user_id: int, display_name: str, password_hash: str,
                        database_url: str = None) -> None:
    """Perbarui nama tampilan & password (dipakai saat melengkapi akun lama
    yang belum punya sidik jari)."""
    with get_db_connection(database_url) as conn:
        with conn:
            conn.execute(
                "UPDATE users SET display_name = ?, password_hash = ? WHERE id = ?;",
                (display_name, password_hash, user_id),
            )


# --- Credentials (sidik jari / passkey) ---

def add_credential(user_id: int, credential_id: str, public_key: str,
                   sign_count: int = 0, device_label: str = None,
                   database_url: str = None) -> int:
    with get_db_connection(database_url) as conn:
        with conn:
            cur = conn.execute(
                "INSERT INTO credentials (user_id, credential_id, public_key, sign_count, device_label) "
                "VALUES (?, ?, ?, ?, ?);",
                (user_id, credential_id, public_key, sign_count, device_label),
            )
            return int(cur.lastrowid)


def get_credentials_for_user(user_id: int, database_url: str = None) -> List[Dict[str, Any]]:
    with get_db_connection(database_url) as conn:
        rows = conn.execute(
            "SELECT * FROM credentials WHERE user_id = ? ORDER BY id;", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_credential_by_id(credential_id: str, database_url: str = None) -> Optional[Dict[str, Any]]:
    with get_db_connection(database_url) as conn:
        row = conn.execute(
            "SELECT * FROM credentials WHERE credential_id = ?;", (credential_id,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_credential_id(credential_id: str, database_url: str = None) -> Optional[Dict[str, Any]]:
    """Cari user pemilik sebuah credential (untuk login tanpa menyebut username)."""
    with get_db_connection(database_url) as conn:
        row = conn.execute(
            "SELECT u.* FROM users u JOIN credentials c ON c.user_id = u.id "
            "WHERE c.credential_id = ?;",
            (credential_id,),
        ).fetchone()
        return dict(row) if row else None


def update_sign_count(credential_id: str, new_sign_count: int, database_url: str = None) -> None:
    with get_db_connection(database_url) as conn:
        with conn:
            conn.execute(
                "UPDATE credentials SET sign_count = ? WHERE credential_id = ?;",
                (new_sign_count, credential_id),
            )
