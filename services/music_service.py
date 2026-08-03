import json
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


def rename_playlist(playlist_id: int, new_name: str) -> None:
    new_name = new_name.strip()
    if not new_name:
        return
    conn = get_connection()
    conn.execute("UPDATE playlists SET name = ? WHERE id = ?", (new_name, playlist_id))
    conn.commit()
    conn.close()
    push_db()


def rename_track(track_id: int, new_title: str) -> None:
    """Renames the track in the shared library — it'll show the new title
    everywhere this track appears, not just in the playlist you renamed it from."""
    new_title = new_title.strip()
    if not new_title:
        return
    conn = get_connection()
    conn.execute("UPDATE tracks SET title = ? WHERE id = ?", (new_title, track_id))
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


def copy_playlist_tracks(source_playlist_id: int, target_playlist_id: int) -> int:
    """Copy every track from source into target. Duplicates are skipped
    automatically (add_track_to_playlist no-ops if already present).
    Returns how many *new* tracks were actually added."""
    source_tracks = get_playlist_tracks(source_playlist_id)
    if source_tracks.empty:
        return 0
    existing_ids = set(get_playlist_tracks(target_playlist_id)["id"])
    added = 0
    for track_id in source_tracks["id"]:
        if int(track_id) not in existing_ids:
            add_track_to_playlist(target_playlist_id, int(track_id))
            added += 1
    return added


def add_track_and_attach(
    playlist_id: int,
    url: str,
    added_by: int,
    known_title: str | None = None,
    known_thumbnail: str | None = None,
) -> tuple[bool, str, int | None]:
    """Add a track to the library (reusing it if the video is already there)
    and attach it to `playlist_id` in one step. `known_title`/`known_thumbnail`
    let a caller that already has metadata (e.g. from search) skip the
    oEmbed lookup add_track() would otherwise do."""
    normalized = youtube.normalize_url(url)
    if not normalized:
        return False, "That doesn't look like a valid YouTube link.", None
    video_id = youtube.extract_video_id(normalized)

    conn = get_connection()
    existing = conn.execute(
        "SELECT id, title FROM tracks WHERE video_id = ?", (video_id,)
    ).fetchone()

    if existing:
        track_id, title = existing
        conn.close()
    else:
        if known_title:
            title = known_title
            thumbnail = known_thumbnail or ""
        else:
            meta = youtube.fetch_metadata(normalized)
            title = meta.get("title") or "Untitled track"
            thumbnail = meta.get("thumbnail_url", "")

        t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
        cur = conn.execute(
            "INSERT INTO tracks (title, video_id, youtube_url, thumbnail_url, added_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, video_id, normalized, thumbnail, added_by, t),
        )
        track_id = cur.lastrowid
        conn.commit()
        conn.close()
        push_db()

    add_track_to_playlist(playlist_id, track_id)
    return True, f'Added "{title}" to the playlist.', track_id


# ---------------------------------------------------------------------------
# Export / import (share a playlist between accounts)
# ---------------------------------------------------------------------------

def _playlist_name(playlist_id: int) -> str:
    conn = get_connection()
    row = conn.execute("SELECT name FROM playlists WHERE id = ?", (playlist_id,)).fetchone()
    conn.close()
    return row[0] if row else "Untitled playlist"


def export_playlist_json(playlist_id: int) -> str:
    name = _playlist_name(playlist_id)
    tracks = get_playlist_tracks(playlist_id)
    payload = {
        "playlist_name": name,
        "tracks": [
            {"title": t["title"], "youtube_url": t["youtube_url"]}
            for _, t in tracks.iterrows()
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def export_playlist_text(playlist_id: int) -> str:
    name = _playlist_name(playlist_id)
    tracks = get_playlist_tracks(playlist_id)
    lines = [f"# {name}"]
    for _, t in tracks.iterrows():
        lines.append(f"{t['title']} - {t['youtube_url']}")
    return "\n".join(lines)


def import_playlist(user_id: int, raw: str) -> tuple[bool, str, int]:
    """Parse JSON (as produced by export_playlist_json) or plain text
    ('# Name' header + one 'Title - URL' per line), create a new playlist,
    and add every track. Duplicates within the source are naturally
    deduplicated by add_track_and_attach."""
    raw = raw.strip()
    if not raw:
        return False, "Nothing to import.", 0

    name = None
    entries: list[tuple[str | None, str]] = []

    parsed = None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        parsed = None

    if isinstance(parsed, dict) and "tracks" in parsed:
        name = parsed.get("playlist_name") or "Imported playlist"
        for t in parsed.get("tracks", []):
            url = t.get("youtube_url") or t.get("url")
            if url:
                entries.append((t.get("title"), url))
    else:
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                if name is None:
                    name = line.lstrip("#").strip()
                continue
            if " - " in line:
                title, url = line.rsplit(" - ", 1)
                entries.append((title.strip(), url.strip()))
            else:
                entries.append((None, line))

    if not entries:
        return False, "Couldn't find any tracks to import in that text.", 0

    final_name = name or "Imported playlist"
    create_playlist(user_id, final_name)
    playlist_id = int(get_playlists(user_id).iloc[0]["id"])  # most recently created

    added = 0
    for title, url in entries:
        ok, _msg, _track_id = add_track_and_attach(playlist_id, url, user_id, known_title=title)
        if ok:
            added += 1

    if added == 0:
        delete_playlist(playlist_id)
        return False, "Couldn't import any valid tracks from that text.", 0

    return True, f'Imported "{final_name}" with {added} track(s).', added
