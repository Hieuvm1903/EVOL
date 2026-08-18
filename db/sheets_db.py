"""Google Sheets–backed storage, replacing the old SQLite db/database.py.

One spreadsheet (config.SPREADSHEET_ID), one worksheet (tab) per table. Row 1
of each tab is the header. IDs are integers managed here (no autoincrement
in Sheets); the `sessions` table uses its `token` column as the primary key
instead.

Auth: a service-account key at <project root>/credentials.json — the same
file used by migrate_to_sheets.py. Share the target spreadsheet with that
key's client_email as Editor.
"""
import os

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

# Tab name -> ordered column list. This is the *target* schema — used to
# create a brand-new tab, and to backfill columns onto an existing tab that
# predates a schema change (see _ensure_header). Once a tab exists, its
# live header row (not this list's order) is what writes actually follow,
# so adding a column here is safe even on a sheet with existing data.
SCHEMA: dict[str, list[str]] = {
    "notes":  ["id", "content", "time"],
    "blog":   ["id", "content", "time"],
    "places": ["id", "user_id", "name", "lat", "lon", "description", "icon", "time"],
    "photos": ["id", "user_id", "filename", "caption", "filter", "time"],
    "users":  ["id", "username", "password_hash", "created_at"],
    "sessions": ["token", "user_id", "created_at", "expires_at"],  # token is the PK here
    "tracks": ["id", "title", "artist", "video_id", "youtube_url", "thumbnail_url",
               "lyrics_url", "added_by", "created_at"],
    "playlists": ["id", "user_id", "name", "created_at"],
    "playlist_tracks": ["id", "playlist_id", "track_id", "custom_title", "position", "added_at"],
}

# Columns that should come back as ints (not the strings Sheets stores).
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


@st.cache_resource
def _client() -> gspread.Client:
    """Auth two ways, tried in order:

    1. DEPLOY: a [gcp_service_account] block in st.secrets — how you'll run
       this on Streamlit Community Cloud, since you can't commit
       credentials.json to a public/private repo. Paste the *same* JSON
       key's fields into the app's Secrets panel (see the deploy guide).
    2. DEV: a local credentials.json file at the project root — what you
       already have set up for local runs and migrate_to_sheets.py.

    No code change needed between environments — whichever is present wins.
    """
    try:
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=SCOPES
            )
            return gspread.authorize(creds)
    except Exception:
        pass  # no secrets.toml at all locally — that's fine, fall through

    if os.path.exists(CREDENTIALS_PATH):
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
        return gspread.authorize(creds)

    raise FileNotFoundError(
        "No Google credentials found. For local dev, place a service-account "
        f"credentials.json at {CREDENTIALS_PATH}. For a deployed app, add a "
        "[gcp_service_account] block to Secrets instead — see the deploy guide."
    )


def _spreadsheet_id() -> str:
    """DEPLOY: st.secrets['sheets']['spreadsheet_id'] if set.
    DEV fallback: config.SPREADSHEET_ID."""
    try:
        if "sheets" in st.secrets and st.secrets["sheets"].get("spreadsheet_id"):
            return st.secrets["sheets"]["spreadsheet_id"]
    except Exception:
        pass
    return SPREADSHEET_ID


@st.cache_resource
def _spreadsheet():
    return _client().open_by_key(_spreadsheet_id())


def _pk(table: str) -> str:
    return "token" if table == "sessions" else "id"


def _worksheet(table: str):
    ss = _spreadsheet()
    try:
        ws = ss.worksheet(table)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=table, rows=1000, cols=max(len(SCHEMA[table]), 1))
        ws.append_row(SCHEMA[table])
        return ws
    _ensure_header(ws, table)
    return ws


def _ensure_header(ws, table: str) -> None:
    """If SCHEMA gained columns since this tab was created (e.g. adding
    `user_id` to an existing `places` tab), append the missing ones to the
    live header row. Appending — never reordering — means existing rows and
    column positions are untouched; old rows just read back with an empty
    value for the new column until you backfill them."""
    header = ws.row_values(1)
    missing = [c for c in SCHEMA[table] if c not in header]
    if missing:
        ws.update("A1", [header + missing])


# ---------------------------------------------------------------------------
# Reads — cached briefly so a page that reads several tables in one rerun
# doesn't burn one API call per read, and rapid reruns don't hammer the API.
# Every write below clears this cache.
# ---------------------------------------------------------------------------

@st.cache_data(ttl=5, show_spinner=False)
def _read_records(table: str) -> list[dict]:
    return _worksheet(table).get_all_records()


def _invalidate() -> None:
    _read_records.clear()


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


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

def _next_id(table: str) -> int:
    df = read_all(table)
    if df.empty or "id" not in df.columns or df["id"].isna().all():
        return 1
    return int(df["id"].max()) + 1


def insert(table: str, row: dict) -> dict:
    """Insert a row (column -> value). Auto-fills 'id' for every table
    except `sessions` (whose PK, `token`, the caller must supply). Returns
    the row as stored, including the generated id.

    For inserting many rows at once, use insert_many() instead — this
    single-row version does its own read (for the next id) plus an
    append, i.e. ~2 Sheets API calls *per call*, which is fine for one-off
    inserts but adds up fast in a loop (see insert_many's docstring)."""
    pk = _pk(table)
    if pk == "id" and "id" not in row:
        row = {**row, "id": _next_id(table)}

    ws = _worksheet(table)
    header = ws.row_values(1)  # live header, not SCHEMA — see _ensure_header
    ordered = [row.get(col, "") for col in header]
    ws.append_row(ordered, value_input_option="USER_ENTERED")
    _invalidate()
    return row


def insert_many(table: str, rows: list[dict]) -> list[dict]:
    """Bulk insert — appends every row in ONE Sheets API call
    (`append_rows`) instead of one call per row like insert() does in a
    loop. Auto-fills sequential 'id' values for every table except
    `sessions` (whose PK, `token`, callers must already supply per-row).

    This matters more than it might look: insert() in a loop of N calls
    is ~2N Sheets API calls (a read for the next id + an append, each
    time), which for a large batch (e.g. importing a 100-track YouTube
    playlist) is slow enough to be noticeable and can run into Sheets'
    per-minute rate limit — which manifests as later rows in the loop
    silently failing or the whole run stalling out. insert_many computes
    every id from a single read up front, then does exactly one
    "read header" + one "append" call no matter how many rows.

    Returns the rows as stored (same order as given), each with its
    generated id filled in.
    """
    if not rows:
        return []

    pk = _pk(table)
    ws = _worksheet(table)
    header = ws.row_values(1)  # live header, not SCHEMA — see _ensure_header

    out_rows: list[dict] = []
    if pk == "id":
        next_id = _next_id(table)
        for row in rows:
            if "id" not in row:
                row = {**row, "id": next_id}
                next_id += 1
            out_rows.append(row)
    else:
        out_rows = list(rows)

    values = [[r.get(col, "") for col in header] for r in out_rows]
    ws.append_rows(values, value_input_option="USER_ENTERED")
    _invalidate()
    return out_rows


def _row_number(ws, pk_col: str, pk_value) -> int | None:
    """1-indexed sheet row number for the record with this PK, or None."""
    header = ws.row_values(1)
    col_idx = header.index(pk_col) + 1
    col_values = ws.col_values(col_idx)
    for i, v in enumerate(col_values[1:], start=2):  # skip header row
        if str(v) == str(pk_value):
            return i
    return None


def update(table: str, pk_value, changes: dict) -> None:
    """Update selected columns on the row matching pk_value."""
    ws = _worksheet(table)
    row_num = _row_number(ws, _pk(table), pk_value)
    if row_num is None:
        return
    header = ws.row_values(1)
    for col, value in changes.items():
        ws.update_cell(row_num, header.index(col) + 1, value)
    _invalidate()


def delete(table: str, pk_value) -> None:
    ws = _worksheet(table)
    row_num = _row_number(ws, _pk(table), pk_value)
    if row_num:
        ws.delete_rows(row_num)
        _invalidate()


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
    # delete bottom-up so earlier row numbers don't shift under us
    for pk_value in sorted(matches[pk_col].tolist(), reverse=True):
        row_num = _row_number(ws, pk_col, pk_value)
        if row_num:
            ws.delete_rows(row_num)
    _invalidate()