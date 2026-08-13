import json
from datetime import datetime

import pandas as pd

from config import TIMEZONE
from db import sheets_db
from utils import youtube


def add_track(url: str, title: str | None, added_by: int) -> tuple[bool, str]:
    normalized = youtube.normalize_url(url)
    if not normalized:
        return False, "That doesn't look like a valid YouTube link."

    video_id = youtube.extract_video_id(normalized)

    tracks = sheets_db.read_all("tracks")
    if not tracks.empty and (tracks["video_id"] == video_id).any():
        return False, "That track is already in the library."

    meta = youtube.fetch_metadata(normalized)
    final_title = (title or meta.get("title") or "").strip() or "Untitled track"
    thumbnail = meta.get("thumbnail_url", "")
    artist = meta.get("author", "")

    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    sheets_db.insert("tracks", {
        "title": final_title,
        "artist": artist,
        "video_id": video_id,
        "youtube_url": normalized,
        "thumbnail_url": thumbnail,
        "lyrics_url": "",
        "added_by": added_by,
        "created_at": t,
    })
    return True, f'Added "{final_title}" to your library.'


def get_all_tracks() -> pd.DataFrame:
    df = sheets_db.read_all("tracks")
    if not df.empty:
        df = df.sort_values("id", ascending=False)
    return df


def delete_track(track_id: int) -> None:
    sheets_db.delete("tracks", track_id)
    sheets_db.delete_where("playlist_tracks", "track_id", track_id)


# ---------------------------------------------------------------------------
# Playlists
# ---------------------------------------------------------------------------

def create_playlist(user_id: int, name: str) -> None:
    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    sheets_db.insert("playlists", {
        "user_id": user_id,
        "name": name.strip() or "Untitled playlist",
        "created_at": t,
    })


def rename_playlist(playlist_id: int, new_name: str) -> None:
    new_name = new_name.strip()
    if not new_name:
        return
    sheets_db.update("playlists", playlist_id, {"name": new_name})


def rename_track(track_id: int, new_title: str) -> None:
    """Renames the track in the shared library — it'll show the new title
    everywhere this track appears (except in playlists that have their own
    per-playlist name override — see rename_track_in_playlist)."""
    new_title = new_title.strip()
    if not new_title:
        return
    sheets_db.update("tracks", track_id, {"title": new_title})


def update_track_details(
    track_id: int,
    artist: str | None = None,
    lyrics_url: str | None = None,
) -> None:
    """Update a track's artist and/or lyrics link. Library-wide, like the
    title — shows up the same in every playlist that includes this track.
    Pass only the field(s) you want to change; the other is left as-is."""
    changes = {}
    if artist is not None:
        changes["artist"] = artist.strip()
    if lyrics_url is not None:
        changes["lyrics_url"] = lyrics_url.strip()
    if changes:
        sheets_db.update("tracks", track_id, changes)


def rename_track_in_playlist(playlist_id: int, track_id: int, new_title: str) -> None:
    """Give this track a custom display name *just within this playlist*,
    without touching the shared library title or any other playlist that
    also has this track."""
    new_title = new_title.strip()
    if not new_title:
        return
    pt = sheets_db.read_all("playlist_tracks")
    if pt.empty:
        return
    match = pt[(pt["playlist_id"] == playlist_id) & (pt["track_id"] == track_id)]
    if match.empty:
        return
    pt_id = int(match.iloc[0]["id"])
    sheets_db.update("playlist_tracks", pt_id, {"custom_title": new_title})


def reset_track_title_in_playlist(playlist_id: int, track_id: int) -> None:
    """Clear a per-playlist name override, falling back to the library title."""
    pt = sheets_db.read_all("playlist_tracks")
    if pt.empty:
        return
    match = pt[(pt["playlist_id"] == playlist_id) & (pt["track_id"] == track_id)]
    if match.empty:
        return
    pt_id = int(match.iloc[0]["id"])
    sheets_db.update("playlist_tracks", pt_id, {"custom_title": ""})


def get_playlists(user_id: int) -> pd.DataFrame:
    df = sheets_db.read_all("playlists")
    if df.empty:
        return df
    df = df[df["user_id"] == user_id]
    return df.sort_values("id", ascending=False)


def delete_playlist(playlist_id: int) -> None:
    sheets_db.delete("playlists", playlist_id)
    sheets_db.delete_where("playlist_tracks", "playlist_id", playlist_id)


def add_track_to_playlist(playlist_id: int, track_id: int) -> None:
    pt = sheets_db.read_all("playlist_tracks")
    max_pos = -1
    if not pt.empty:
        existing = pt[(pt["playlist_id"] == playlist_id) & (pt["track_id"] == track_id)]
        if not existing.empty:
            return
        same_playlist = pt[pt["playlist_id"] == playlist_id]
        if not same_playlist.empty:
            max_pos = int(same_playlist["position"].max())

    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    sheets_db.insert("playlist_tracks", {
        "playlist_id": playlist_id,
        "track_id": track_id,
        "position": max_pos + 1,
        "added_at": t,
    })


def remove_track_from_playlist(playlist_id: int, track_id: int) -> None:
    pt = sheets_db.read_all("playlist_tracks")
    if pt.empty:
        return
    match = pt[(pt["playlist_id"] == playlist_id) & (pt["track_id"] == track_id)]
    for pt_id in match["id"].tolist():
        sheets_db.delete("playlist_tracks", int(pt_id))


def get_playlist_tracks(playlist_id: int) -> pd.DataFrame:
    """Tracks for this playlist, in position order. `title` reflects this
    playlist's own custom name if one's been set (rename_track_in_playlist);
    `original_title` always holds the shared library title, so the UI can
    show "renamed from X" / offer a reset."""
    pt = sheets_db.read_all("playlist_tracks")
    tracks = sheets_db.read_all("tracks")
    if pt.empty or tracks.empty:
        cols = list(sheets_db.SCHEMA["tracks"]) + ["position", "original_title"]
        return pd.DataFrame(columns=cols)

    pt = pt[pt["playlist_id"] == playlist_id].sort_values("position")
    merged = pt.merge(tracks, left_on="track_id", right_on="id", suffixes=("_pt", ""))
    merged["original_title"] = merged["title"]

    custom = merged["custom_title"].fillna("").astype(str).str.strip()
    has_custom = custom != ""
    merged.loc[has_custom, "title"] = custom[has_custom]

    cols = list(tracks.columns) + ["position", "original_title"]
    return merged[cols].reset_index(drop=True)


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
    known_artist: str | None = None,
) -> tuple[bool, str, int | None]:
    """Add a track to the library (reusing it if the video is already there)
    and attach it to `playlist_id` in one step. `known_title`/`known_thumbnail`/
    `known_artist` let a caller that already has metadata (e.g. from search)
    skip the oEmbed lookup add_track() would otherwise do."""
    normalized = youtube.normalize_url(url)
    if not normalized:
        return False, "That doesn't look like a valid YouTube link.", None
    video_id = youtube.extract_video_id(normalized)

    tracks = sheets_db.read_all("tracks")
    existing = tracks[tracks["video_id"] == video_id] if not tracks.empty else tracks

    if existing is not None and not existing.empty:
        track_id = int(existing.iloc[0]["id"])
        title = existing.iloc[0]["title"]
    else:
        if known_title:
            title = known_title
            thumbnail = known_thumbnail or ""
            artist = known_artist or ""
        else:
            meta = youtube.fetch_metadata(normalized)
            title = meta.get("title") or "Untitled track"
            thumbnail = meta.get("thumbnail_url", "")
            artist = known_artist or meta.get("author", "")

        t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
        new_row = sheets_db.insert("tracks", {
            "title": title,
            "artist": artist,
            "video_id": video_id,
            "youtube_url": normalized,
            "thumbnail_url": thumbnail,
            "lyrics_url": "",
            "added_by": added_by,
            "created_at": t,
        })
        track_id = new_row["id"]

    add_track_to_playlist(playlist_id, track_id)
    return True, f'Added "{title}" to the playlist.', track_id


# ---------------------------------------------------------------------------
# Export / import (share a playlist between accounts)
# ---------------------------------------------------------------------------

def _playlist_name(playlist_id: int) -> str:
    playlists = sheets_db.read_all("playlists")
    match = playlists[playlists["id"] == playlist_id] if not playlists.empty else playlists
    return match.iloc[0]["name"] if match is not None and not match.empty else "Untitled playlist"


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