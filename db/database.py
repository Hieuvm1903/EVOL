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
]


def get_connection() -> sqlite3.Connection:
    """Return a connection with the schema guaranteed to exist."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    for statement in SCHEMA:
        conn.execute(statement)
    conn.commit()
    return conn
