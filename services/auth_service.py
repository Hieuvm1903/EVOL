"""Simple username/password auth for a personal/small-group app.

Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib `hashlib`, no extra
dependency) with a random salt per user. Login state lives in
st.session_state, so it's per-browser-tab/session — there's no persistent
cookie, meaning a page refresh in some setups may require logging in again.
That's an intentional trade-off to keep this dependency-free; swap in
`streamlit-authenticator` later if you want cookie-based "stay logged in".
"""
import hashlib
import os
from datetime import datetime

from config import TIMEZONE
from db.database import get_connection, push_db


def _hash_password(password: str, salt = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    expected = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000).hex()
    return expected == digest_hex


def register_user(username: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    if not username or not password:
        return False, "Username and password are required."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    conn = get_connection()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.close()
        return False, "That username is already taken."

    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    conn.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, _hash_password(password), t),
    )
    conn.commit()
    conn.close()
    push_db()
    return True, "Account created — you can log in now."


def verify_user(username: str, password: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?", (username.strip(),)
    ).fetchone()
    conn.close()
    if row and _verify_password(password, row[2]):
        return {"id": row[0], "username": row[1]}
    return None
