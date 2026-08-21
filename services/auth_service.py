"""Simple username/password auth for a personal/small-group app, plus a
"remember me" layer so a page reload doesn't log you out.

Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib `hashlib`, no extra
dependency) with a random salt per user.

Login state is kept two ways:
  - st.session_state["user"] — fast, in-memory, cleared on a hard reload.
  - A `sessions` row in Sheets (keyed by its `token` column) + a same-named
    token in a browser cookie (via streamlit-cookies-controller) — survives
    reloads/new tabs, expires after 30 days or on explicit logout.
"""
import hashlib
import os
import secrets
from datetime import datetime, timedelta

import streamlit as st
from streamlit_cookies_controller import CookieController

from config import TIMEZONE
from db import sheets_db

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


DEFAULT_ROLE = "member"


def register_user(username: str, password: str, name: str = "", role: str = DEFAULT_ROLE) -> tuple[bool, str]:
    username = username.strip()
    if not username or not password:
        return False, "Username and password are required."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    users = sheets_db.read_all("users")
    if not users.empty and (users["username"] == username).any():
        return False, "That username is already taken."

    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    sheets_db.insert("users", {
        "username": username,
        "password_hash": _hash_password(password),
        "name": name.strip(),
        "role": role,
        "created_at": t,
    })
    return True, "Account created — you can log in now."


def _user_dict(row) -> dict:
    return {
        "id": int(row["id"]),
        "username": row["username"],
        "name": row.get("name") or "",
        "role": row.get("role") or DEFAULT_ROLE,
    }


def verify_user(username: str, password: str) -> dict | None:
    users = sheets_db.read_all("users")
    if users.empty:
        return None
    match = users[users["username"] == username.strip()]
    if match.empty:
        return None
    row = match.iloc[0]
    if _verify_password(password, row["password_hash"]):
        return _user_dict(row)
    return None


# ---------------------------------------------------------------------------
# "Remember me" sessions
# ---------------------------------------------------------------------------

def _cookie_controller() -> CookieController:
    # IMPORTANT: must be the SAME Python instance for the whole session,
    # not a fresh one per call. A brand-new CookieController hasn't
    # round-tripped to the browser yet, so its internal cookie store is
    # still None right after construction — calling .set()/.remove() on
    # it then raises "TypeError: 'NoneType' object does not support item
    # assignment". Caching one instance in session_state lets it sync
    # once (e.g. during restore_session() on initial page load) and stay
    # synced across reruns, instead of resetting to "not synced" on
    # every single call.
    if "_cookie_controller" not in st.session_state:
        st.session_state["_cookie_controller"] = CookieController(key="evol_cookies")
    return st.session_state["_cookie_controller"]


def _now() -> datetime:
    return datetime.now().astimezone(tz=TIMEZONE)


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = _now()
    expires = now + timedelta(days=SESSION_LIFETIME_DAYS)
    sheets_db.insert("sessions", {
        "token": token,
        "user_id": user_id,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S %z"),
        "expires_at": expires.strftime("%Y-%m-%d %H:%M:%S %z"),
    })
    return token


def _get_user_by_session(token: str) -> dict | None:
    sessions = sheets_db.read_all("sessions")
    if sessions.empty:
        return None
    match = sessions[sessions["token"] == token]
    if match.empty:
        return None
    row = match.iloc[0]

    try:
        expires_at = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S %z")
    except (ValueError, TypeError):
        delete_session(token)
        return None
    if expires_at < _now():
        delete_session(token)
        return None

    users = sheets_db.read_all("users")
    user_match = users[users["id"] == int(row["user_id"])] if not users.empty else users
    if user_match is None or user_match.empty:
        return None
    return _user_dict(user_match.iloc[0])


def delete_session(token: str) -> None:
    sheets_db.delete("sessions", token)


def remember_login(user: dict) -> None:
    """Call right after a successful login/signup to persist it across reloads."""
    token = create_session(user["id"])
    controller = _cookie_controller()
    if controller.getAll() is None:
        # Cookie component hasn't finished its first browser round-trip
        # in this session yet. The user is already logged in for this
        # run (st.session_state["user"] was set by the caller before
        # remember_login was called) — just skip persisting the
        # "remember me" cookie this once rather than crashing; it'll be
        # set correctly next time they log in (by then the controller,
        # which is now cached, will be synced).
        return
    controller.set(COOKIE_NAME, token, max_age=SESSION_LIFETIME_DAYS * 24 * 3600)


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
