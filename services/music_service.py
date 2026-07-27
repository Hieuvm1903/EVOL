from datetime import datetime

import pandas as pd

from config import TIMEZONE
from db.database import get_connection, push_db
from utils import youtube


def add_track(url: str, title: str | None, added_by: int) -> tuple[bool, str]:
    normalized = youtube.normalize_url(url)
    if not normalized:
        return False, "That doesn't look like a valid YouTube link."

    video_id = youtube.extract_video_id(normalized)

    conn = get_connection()
    existing = conn.execute("SELECT id FROM tracks WHERE video_id = ?", (video_id,)).fetchone()
    if existing:
        conn.close()
        return False, "That track is already in the library."

    meta = youtube.fetch_metadata(normalized)
    final_title = (title or meta.get("title") or "").strip() or "Untitled track"
    thumbnail = meta.get("thumbnail_url", "")

    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    conn.execute(
        "INSERT INTO tracks (title, video_id, youtube_url, thumbnail_url, added_by, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (final_title, video_id, normalized, thumbnail, added_by, t),
    )
    conn.commit()
    conn.close()
    push_db()
    return True, f'Added "{final_title}" to your library.'


def get_all_tracks() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM tracks ORDER BY id DESC", conn)
    conn.close()
    return df


def delete_track(track_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM tracks WHERE id = ?", (track_id,))
    conn.execute("DELETE FROM playlist_tracks WHERE track_id = ?", (track_id,))
    conn.commit()
    conn.close()
    push_db()


# ---------------------------------------------------------------------------
# Playlists
# ---------------------------------------------------------------------------

def create_playlist(user_id: int, name: str) -> None:
    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    conn = get_connection()
    conn.execute(
        "INSERT INTO playlists (user_id, name, created_at) VALUES (?, ?, ?)",
        (user_id, name.strip() or "Untitled playlist", t),
    )
    conn.commit()
    conn.close()
    push_db()


def get_playlists(user_id: int) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM playlists WHERE user_id = ? ORDER BY id DESC", conn, params=(user_id,)
    )
    conn.close()
    return df


def delete_playlist(playlist_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
    conn.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,))
    conn.commit()
    conn.close()
    push_db()


def add_track_to_playlist(playlist_id: int, track_id: int) -> None:
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
        (playlist_id, track_id),
    ).fetchone()
    if existing:
        conn.close()
        return
    max_pos = conn.execute(
        "SELECT COALESCE(MAX(position), -1) FROM playlist_tracks WHERE playlist_id = ?",
        (playlist_id,),
    ).fetchone()[0]
    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    conn.execute(
        "INSERT INTO playlist_tracks (playlist_id, track_id, position, added_at) VALUES (?, ?, ?, ?)",
        (playlist_id, track_id, max_pos + 1, t),
    )
    conn.commit()
    conn.close()
    push_db()


def remove_track_from_playlist(playlist_id: int, track_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "DELETE FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
        (playlist_id, track_id),
    )
    conn.commit()
    conn.close()
    push_db()


def get_playlist_tracks(playlist_id: int) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT t.*, pt.position FROM playlist_tracks pt
           JOIN tracks t ON t.id = pt.track_id
           WHERE pt.playlist_id = ?
           ORDER BY pt.position ASC""",
        conn, params=(playlist_id,),
    )
    conn.close()
    return df
