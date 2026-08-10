"""Lyrics preview via the Musixmatch API.

Musixmatch's free tier is explicitly designed for this use case: the
`lyrics_body` field it returns is auto-truncated to a short preview (with
their own required watermark appended) rather than the full song — we
never fetch, store, or display complete lyrics ourselves. Every snippet
is shown alongside a link back to the full, licensed lyrics on
musixmatch.com.

Requires a (free) API key in .streamlit/secrets.toml:

    [musixmatch]
    api_key = "..."

If not configured, every function here just returns "unavailable" instead
of raising, same pattern as services/remote_storage.py.
"""
import requests
import streamlit as st

_BASE = "https://api.musixmatch.com/ws/1.1"


def _api_key() -> str | None:
    try:
        return st.secrets["musixmatch"]["api_key"]
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_lyrics_preview(title: str) -> dict:
    """Best-effort lyrics preview lookup by track title.

    Returns {"snippet": str|None, "url": str|None}. `snippet` is whatever
    truncated preview Musixmatch's API returns (never the full lyrics —
    that's their API's own behavior, not something we do); `url` points to
    the full lyrics on musixmatch.com. Both are None if unavailable for
    any reason (no API key, not found, request failure) — callers should
    fall back to a plain search-link instead.
    """
    api_key = _api_key()
    if not api_key or not title.strip():
        return {"snippet": None, "url": None}

    try:
        search = requests.get(
            f"{_BASE}/track.search",
            params={"q_track": title, "apikey": api_key, "page_size": 1, "s_track_rating": "desc"},
            timeout=5,
        )
        track_list = search.json()["message"]["body"]["track_list"]
        if not track_list:
            return {"snippet": None, "url": None}
        track = track_list[0]["track"]

        lyrics_resp = requests.get(
            f"{_BASE}/track.lyrics.get",
            params={"track_id": track["track_id"], "apikey": api_key},
            timeout=5,
        )
        lyrics = lyrics_resp.json()["message"]["body"].get("lyrics")
        if not lyrics or not lyrics.get("lyrics_body"):
            return {"snippet": None, "url": None}

        return {
            "snippet": lyrics["lyrics_body"],  # pre-truncated by Musixmatch's free tier
            "url": lyrics.get("backlink_url") or track.get("track_share_url"),
        }
    except Exception:
        return {"snippet": None, "url": None}