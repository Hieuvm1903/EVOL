"""SQLite connection + schema. No external service (e.g. Supabase) required —
everything lives in a single data.db file plus an assets/photos/ folder,
both stored next to the project root.

NOTE: on hosts with an ephemeral filesystem (e.g. Streamlit Community Cloud's
free tier) these files reset on redeploy/restart. For durable storage across
redeploys, swap this module for a hosted SQLite-compatible service (e.g. Turso)
or Postgres (e.g. Neon) — the rest of the app only talks to `services/`, so no
other file needs to change.
"""
import os
import sqlite3

import streamlit as st

from services import remote_storage

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT_DIR, "data.db")
PHOTOS_DIR = os.path.join(ROOT_DIR, "assets", "photos")

os.makedirs(PHOTOS_DIR, exist_ok=True)

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            time TEXT NOT NULL
        )""",
    """CREATE TABLE IF NOT EXISTS blog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            time TEXT NOT NULL
        )""",
    """CREATE TABLE IF NOT EXISTS places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            description TEXT,
            icon TEXT,
            time TEXT NOT NULL
        )""",
    """CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            caption TEXT,
            filter TEXT,
            time TEXT NOT NULL
        )""",
    """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""",
    """CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )""",
    """CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            video_id TEXT NOT NULL UNIQUE,
            youtube_url TEXT NOT NULL,
            thumbnail_url TEXT,
            added_by INTEGER,
            created_at TEXT NOT NULL
        )""",
    """CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""",
    """CREATE TABLE IF NOT EXISTS playlist_tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id INTEGER NOT NULL,
            track_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            added_at TEXT NOT NULL
        )""",
]


def _ensure_synced_from_remote() -> None:
    """Pull the latest data.db from R2 once per Streamlit session.

    No-ops automatically if R2 isn't configured in st.secrets, so local
    dev keeps working against the plain local file with zero setup.
    """
    if st.session_state.get("_db_synced_from_remote"):
        return
    remote_storage.pull_db(DB_PATH)
    st.session_state["_db_synced_from_remote"] = True


def get_connection() -> sqlite3.Connection:
    """Return a connection with the schema guaranteed to exist."""
    _ensure_synced_from_remote()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    for statement in SCHEMA:
        conn.execute(statement)
    conn.commit()
    return conn


def push_db() -> None:
    """Push the local data.db up to R2. Call this after any write.

    No-op if R2 isn't configured.
    """
    remote_storage.push_db(DB_PATH)
