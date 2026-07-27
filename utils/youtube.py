"""Minimal YouTube helpers: pull a video ID out of any link shape, and fetch
the title/thumbnail via YouTube's public oEmbed endpoint. No API key needed
for either — oEmbed is a public, unauthenticated endpoint meant exactly for
this ("give me a title/thumbnail for this URL").
"""
import json
import re
import urllib.parse
import urllib.request

_VIDEO_ID_PATTERNS = [
    r"(?:v=|/embed/|/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})",
]


def extract_video_id(url: str) -> str | None:
    for pattern in _VIDEO_ID_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def normalize_url(url: str) -> str | None:
    """Return a canonical watch?v= URL, or None if this isn't a YouTube link."""
    video_id = extract_video_id(url.strip())
    if not video_id:
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def fetch_metadata(url: str) -> dict:
    """Best-effort title/author/thumbnail lookup. Returns {} on any failure —
    callers should fall back to letting the user type a title manually."""
    endpoints = [
        f"https://www.youtube.com/oembed?url={urllib.parse.quote(url)}&format=json",
        f"https://noembed.com/embed?url={urllib.parse.quote(url)}&format=json",
    ]
    for endpoint in endpoints:
        try:
            with urllib.request.urlopen(endpoint, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("title"):
                    return {
                        "title": data.get("title"),
                        "author": data.get("author_name", ""),
                        "thumbnail_url": data.get("thumbnail_url", ""),
                    }
        except Exception:
            continue
    return {}
