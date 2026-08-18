"""Search via ytmusicapi — talks to YouTube Music's public search
endpoint anonymously, so no Google API key or login is needed."""
from functools import lru_cache

from ytmusicapi import YTMusic


@lru_cache(maxsize=1)
def _client() -> YTMusic:
    return YTMusic()


def search_songs(query: str, limit: int = 8) -> list[dict]:
    """Return [{title, artist, video_id, thumbnail_url, duration}, ...]."""
    query = query.strip()
    if not query:
        return []
    try:
        results = _client().search(query, filter="songs", limit=limit)
    except Exception:
        return []

    songs = []
    for r in results:
        video_id = r.get("videoId")
        if not video_id:
            continue
        artists = r.get("artists") or []
        artist_names = ", ".join(a.get("name", "") for a in artists if a.get("name"))
        thumbnails = r.get("thumbnails") or []
        thumbnail_url = thumbnails[-1]["url"] if thumbnails else ""
        songs.append({
            "title": r.get("title") or "Untitled",
            "artist": artist_names,
            "video_id": video_id,
            "thumbnail_url": thumbnail_url,
            "duration": r.get("duration") or "",
        })
    return songs


def search_playlists(query: str, limit: int = 8) -> list[dict]:
    """Return [{title, author, item_count, thumbnail_url, playlist_id}, ...].

    Only returns *community* playlists (ytmusicapi browseId starting with
    "VL") — those are the ones with a normal public
    youtube.com/playlist?list=<id> page, which is what
    utils.youtube.fetch_playlist_videos scrapes to pull out tracks.
    YouTube Music's algorithmic mixes/radios (other browseId shapes)
    don't have that page, so they're filtered out here rather than
    surfaced as a result that would fail to import.
    """
    query = query.strip()
    if not query:
        return []
    try:
        results = _client().search(query, filter="playlists", limit=limit)
    except Exception:
        return []

    playlists = []
    for r in results:
        browse_id = r.get("browseId") or ""
        if not browse_id.startswith("VL"):
            continue
        playlist_id = browse_id[2:]
        thumbnails = r.get("thumbnails") or []
        thumbnail_url = thumbnails[-1]["url"] if thumbnails else ""
        playlists.append({
            "title": r.get("title") or "Untitled playlist",
            "author": r.get("author") or "",
            "item_count": r.get("itemCount") or "",
            "thumbnail_url": thumbnail_url,
            "playlist_id": playlist_id,
        })
    return playlists