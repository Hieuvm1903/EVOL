"""Google Sheets–backed storage, replacing the old SQLite db/database.py.

Perf notes (fixes for 429 "Quota exceeded" errors):
  - The worksheet handle + its header row are cached via st.cache_resource,
    so resolving a worksheet no longer costs a metadata fetch + header read
    on every single call (previously ~2 extra API calls per op).
  - update() batches all changed columns into ONE batch_update call instead
    of one update_cell() call per column.
  - Row-number lookups reuse the cached read (read_all), instead of doing a
    fresh full-column ws.col_values() read every time.
  - Cache invalidation is scoped to the table that changed, not global.
  - Failed calls get a short exponential-backoff retry on 429s specifically.
"""
import os
import time

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

from config import SPREADSHEET_ID

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(ROOT_DIR, "credentials.json")

SCHEMA: dict[str, list[str]] = {
    "notes":  ["id", "content", "time"],
    "blog":   ["id", "content", "time"],
    "places": ["id", "user_id", "name", "lat", "lon", "description", "icon", "time"],
    "photos": ["id", "user_id", "filename", "caption", "filter", "time"],
    "users":  ["id", "username", "password_hash", "created_at"],
    "sessions": ["token", "user_id", "created_at", "expires_at"],
    "tracks": ["id", "title", "artist", "video_id", "youtube_url", "thumbnail_url",
               "lyrics_url", "added_by", "created_at"],
    "playlists": ["id", "user_id", "name", "created_at"],
    "playlist_tracks": ["id", "playlist_id", "track_id", "custom_title", "position", "added_at"],
}

_INT_COLUMNS: dict[str, list[str]] = {
    "notes": ["id"],
    "blog": ["id"],
    "places": ["id", "user_id"],
    "photos": ["id", "user_id"],
    "users": ["id"],
    "sessions": ["user_id"],
    "tracks": ["id", "added_by"],
    "playlists": ["id", "user_id"],
    "playlist_tracks": ["id", "playlist_id", "track_id", "position"],
}
_FLOAT_COLUMNS: dict[str, list[str]] = {
    "places": ["lat", "lon"],
}

# How long a read_all() result is trusted before hitting the API again.
# Bumped up from 5s — this app doesn't need near-real-time freshness, and
# every second of TTL directly reduces API call volume.
_READ_TTL = 30


# ---------------------------------------------------------------------------
# Retry wrapper — a short backoff specifically for 429s, so a transient
# rate-limit blip doesn't crash the page.
# ---------------------------------------------------------------------------

def _with_retry(fn, *args, **kwargs):
    delays = [1, 2, 4]
    for i, delay in enumerate(delays + [None]):
        try:
            return fn(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            is_429 = getattr(e, "response", None) is not None and e.response.status_code == 429
            if not is_429 or delay is None:
                raise
            time.sleep(delay)


# ---------------------------------------------------------------------------
# Auth / spreadsheet handles
# ---------------------------------------------------------------------------

@st.cache_resource
def _client() -> gspread.Client:
    try:
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=SCOPES
            )
            return gspread.authorize(creds)
    except Exception:
        pass

    if os.path.exists(CREDENTIALS_PATH):
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
        return gspread.authorize(creds)

    raise FileNotFoundError(
        "No Google credentials found. For local dev, place a service-account "
        f"credentials.json at {CREDENTIALS_PATH}. For a deployed app, add a "
        "[gcp_service_account] block to Secrets instead — see the deploy guide."
    )


def _spreadsheet_id() -> str:
    try:
        if "sheets" in st.secrets and st.secrets["sheets"].get("spreadsheet_id"):
            return st.secrets["sheets"]["spreadsheet_id"]
    except Exception:
        pass
    return SPREADSHEET_ID


@st.cache_resource
def _spreadsheet():
    return _with_retry(_client().open_by_key, _spreadsheet_id())


def _pk(table: str) -> str:
    return "token" if table == "sessions" else "id"


# ---------------------------------------------------------------------------
# Worksheet handle + header, cached together so resolving/ensuring a table
# costs API calls exactly ONCE per table per app process — not once per
# read/write like before.
# ---------------------------------------------------------------------------

@st.cache_resource
def _worksheet_and_header(table: str):
    ss = _spreadsheet()
    try:
        ws = _with_retry(ss.worksheet, table)
    except gspread.WorksheetNotFound:
        ws = _with_retry(ss.add_worksheet, title=table, rows=1000, cols=max(len(SCHEMA[table]), 1))
        _with_retry(ws.append_row, SCHEMA[table])
        return ws, list(SCHEMA[table])

    header = _with_retry(ws.row_values, 1)
    missing = [c for c in SCHEMA[table] if c not in header]
    if missing:
        header = header + missing
        _with_retry(ws.update, "A1", [header])
    return ws, header


def _worksheet(table: str):
    ws, _ = _worksheet_and_header(table)
    return ws


def _header(table: str) -> list[str]:
    _, header = _worksheet_and_header(table)
    return header


def _refresh_worksheet_cache(table: str) -> None:
    """Call only if you suspect the live header changed underneath us
    (e.g. someone edited the sheet by hand) — forces one re-check."""
    _worksheet_and_header.clear()


# ---------------------------------------------------------------------------
# Reads — cached, scoped invalidation per table.
# ---------------------------------------------------------------------------

@st.cache_data(ttl=_READ_TTL, show_spinner=False)
def _read_records(table: str) -> list[dict]:
    ws = _worksheet(table)
    return _with_retry(ws.get_all_records)


def _invalidate(table: str) -> None:
    """Clear the cache for just this one table, not every table."""
    _read_records.clear(table)


def read_all(table: str) -> pd.DataFrame:
    records = _read_records(table)
    df = pd.DataFrame(records, columns=SCHEMA[table])
    for col in _INT_COLUMNS.get(table, []):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in _FLOAT_COLUMNS.get(table, []):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def read_many(tables: list[str]) -> dict[str, pd.DataFrame]:
    """Read several tables in one shot. Each table is still served from its
    own 30s cache when warm, so this mainly helps the *first* read of a
    page that needs several tables (e.g. a playlist detail view needing
    both `playlist_tracks` and `tracks`) by avoiding sequential round trips
    hitting a cold cache back-to-back."""
    return {t: read_all(t) for t in tables}


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

def _next_id(table: str) -> int:
    df = read_all(table)
    if df.empty or "id" not in df.columns or df["id"].isna().all():
        return 1
    return int(df["id"].max()) + 1


def insert(table: str, row: dict) -> dict:
    pk = _pk(table)
    if pk == "id" and "id" not in row:
        row = {**row, "id": _next_id(table)}

    ws = _worksheet(table)
    header = _header(table)  # cached — no extra API call
    ordered = [row.get(col, "") for col in header]
    _with_retry(ws.append_row, ordered, value_input_option="USER_ENTERED")
    _invalidate(table)
    return row


def _find_row(table: str, pk_value) -> int | None:
    """1-indexed sheet row number for pk_value, using the cached read
    instead of a fresh full-column API read."""
    pk_col = _pk(table)
    records = _read_records(table)
    for i, rec in enumerate(records):
        if str(rec.get(pk_col)) == str(pk_value):
            return i + 2  # +1 for header row, +1 for 1-indexing
    return None


def _row_number(table: str, pk_value) -> int | None:
    row = _find_row(table, pk_value)
    if row is None:
        # Cache might just be stale (e.g. row inserted a moment ago) —
        # force one fresh read and try again, instead of silently no-op'ing.
        _invalidate(table)
        row = _find_row(table, pk_value)
    return row


def update(table: str, pk_value, changes: dict) -> None:
    """Update selected columns on the row matching pk_value — batched into
    a single API call instead of one update_cell() per column."""
    if not changes:
        return
    ws = _worksheet(table)
    row_num = _row_number(table, pk_value)
    if row_num is None:
        return
    header = _header(table)

    data = []
    for col, value in changes.items():
        if col not in header:
            continue
        col_idx = header.index(col) + 1
        a1 = gspread.utils.rowcol_to_a1(row_num, col_idx)
        data.append({"range": a1, "values": [[value]]})

    if data:
        _with_retry(ws.batch_update, data, value_input_option="USER_ENTERED")
    _invalidate(table)


def delete(table: str, pk_value) -> None:
    ws = _worksheet(table)
    row_num = _row_number(table, pk_value)
    if row_num:
        _with_retry(ws.delete_rows, row_num)
        _invalidate(table)


def delete_where(table: str, column: str, value) -> None:
    """Delete every row where `column == value` (cascading deletes)."""
    df = read_all(table)
    if df.empty or column not in df.columns:
        return
    matches = df[df[column] == value]
    if matches.empty:
        return
    ws = _worksheet(table)
    pk_col = _pk(table)
    for pk_value in sorted(matches[pk_col].tolist(), reverse=True):
        row_num = _row_number(table, pk_value)
        if row_num:
            _with_retry(ws.delete_rows, row_num)
    _invalidate(table)