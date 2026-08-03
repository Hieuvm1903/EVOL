"""Simple username/password auth for a personal/small-group app, plus a
"remember me" layer so a page reload doesn't log you out.

Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib `hashlib`, no extra
dependency) with a random salt per user.

Login state is kept two ways:
  - st.session_state["user"] — fast, in-memory, cleared on a hard reload.
  - A `sessions` DB row + a same-named token in a browser cookie
    (via streamlit-cookies-controller) — survives reloads/new tabs, expires
    after 30 days or on explicit logout.
"""
import hashlib
import os
import secrets
from datetime import datetime, timedelta

import streamlit as st
from streamlit_cookies_controller import CookieController

from config import TIMEZONE
from db.database import get_connection, push_db

COOKIE_NAME = "evol_session"
SESSION_LIFETIME_DAYS = 30


def _hash_password(password: str, salt: bytes | None = None) -> str:
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


# ---------------------------------------------------------------------------
# "Remember me" sessions
# ---------------------------------------------------------------------------

def _cookie_controller() -> CookieController:
    # Constructed fresh each run (cheap) — its `key` is what gives it a
    # stable identity across reruns on the frontend side, not caching here.
    return CookieController(key="evol_cookies")


def _now() -> datetime:
    return datetime.now().astimezone(tz=TIMEZONE)


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = _now()
    expires = now + timedelta(days=SESSION_LIFETIME_DAYS)
    conn = get_connection()
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, now.strftime("%Y-%m-%d %H:%M:%S %z"), expires.strftime("%Y-%m-%d %H:%M:%S %z")),
    )
    conn.commit()
    conn.close()
    push_db()
    return token


def _get_user_by_session(token: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT u.id, u.username, s.expires_at FROM sessions s
           JOIN users u ON u.id = s.user_id
           WHERE s.token = ?""",
        (token,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    try:
        expires_at = datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S %z")
    except (ValueError, TypeError):
        delete_session(token)
        return None
    if expires_at < _now():
        delete_session(token)
        return None
    return {"id": row[0], "username": row[1]}


def delete_session(token: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    push_db()


def remember_login(user: dict) -> None:
    """Call right after a successful login/signup to persist it across reloads."""
    token = create_session(user["id"])
    _cookie_controller().set(COOKIE_NAME, token, max_age=SESSION_LIFETIME_DAYS * 24 * 3600)


def forget_login() -> None:
    """Call on logout to clear both the server-side session and the cookie."""
    controller = _cookie_controller()
    token = controller.get(COOKIE_NAME)
    if token:
        delete_session(token)
        controller.remove(COOKIE_NAME)


def restore_session() -> None:
    """If the browser has a valid remember-me cookie and we don't already
    have a logged-in user in this script run, log them back in from it.
    Call this once, early, on every page."""
    if st.session_state.get("user"):
        return
    token = _cookie_controller().get(COOKIE_NAME)
    if not token:
        return
    user = _get_user_by_session(token)
    if user:
        st.session_state["user"] = user
