"""Song search via ytmusicapi — talks to YouTube Music's public search
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
