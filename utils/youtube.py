"""Minimal YouTube helpers: pull a video ID out of any link shape, fetch
title/thumbnail via YouTube's public oEmbed endpoint, and pull every video
out of a public YouTube playlist link. No API key needed for any of this —
oEmbed is a public endpoint meant exactly for the single-video case, and the
playlist reader just parses the same JSON blob (`ytInitialData`) the
playlist page itself ships to render server-side, no login/key required.
"""
import json
import re
import urllib.parse
import urllib.request

_VIDEO_ID_PATTERNS = [
    r"(?:v=|/embed/|/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})",
]
_PLAYLIST_ID_PATTERN = re.compile(r"[?&]list=([A-Za-z0-9_-]+)")


def extract_video_id(url: str) -> str | None:
    for pattern in _VIDEO_ID_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_playlist_id(url: str) -> str | None:
    match = _PLAYLIST_ID_PATTERN.search(url)
    return match.group(1) if match else None


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


def _extract_balanced_json(text: str, start_idx: int) -> str | None:
    """Given `text` and the index of an opening '{', return the substring
    up to (and including) its matching closing '}' — respecting quoted
    strings and escapes so braces *inside* JSON string values don't throw
    off the count. This replaces a naive `re.search(r"\\{.*?\\});", ...)`,
    which is fragile: YouTube's markup around ytInitialData shifts often
    enough (extra scripts, different trailing punctuation) that a fixed
    end-of-regex pattern silently stops matching. Returns None if the
    braces never balance (truncated/unexpected input)."""
    depth = 0
    in_string = False
    escape = False
    for i in range(start_idx, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start_idx:i + 1]
    return None


def _parse_ytinitialdata(html: str) -> dict | None:
    for marker in ('var ytInitialData = ', 'ytInitialData"] = ', '"ytInitialData":'):
        idx = html.find(marker)
        if idx == -1:
            continue
        brace_idx = html.find("{", idx)
        if brace_idx == -1:
            continue
        json_str = _extract_balanced_json(html, brace_idx)
        if not json_str:
            continue
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


_RAW_VIDEO_ID_PATTERN = re.compile(r'"videoId":"([A-Za-z0-9_-]{11})"')


def fetch_playlist_videos(url: str, limit: int = 200) -> list[dict]:
    """Best-effort read of every video in a public YouTube playlist, no API
    key needed — fetches the playlist's own page and parses the
    `ytInitialData` JSON blob it embeds for server-side rendering.

    Returns [{"video_id", "title", "thumbnail_url"}, ...] in playlist order
    (title/thumbnail_url may be "" if only the raw-id fallback below kicked
    in — callers should treat a missing title as "look it up separately",
    which add_playlist_from_youtube already does via add_track_and_attach).
    Returns [] on total failure: no `list=` id, private/deleted playlist,
    network error — callers should treat that as "couldn't import", not crash.

    Limitation: YouTube only renders roughly the first 100 items
    server-side; going further requires a paginated "continuation" request
    this doesn't make, so very long playlists only return their first
    batch (still capped at `limit`, whichever is smaller).
    """
    playlist_id = extract_playlist_id(url)
    if not playlist_id:
        return []

    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    try:
        req = urllib.request.Request(
            playlist_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                # Skips YouTube's EU cookie-consent interstitial page, which
                # otherwise replaces the real playlist page (and its
                # ytInitialData) with a consent form on many server IPs —
                # this was the most common cause of "couldn't read that
                # playlist" even for a perfectly valid public link.
                "Cookie": "CONSENT=YES+1",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    videos: list[dict] = []
    seen: set[str] = set()

    data = _parse_ytinitialdata(html)
    if data is not None:
        def _walk(node) -> None:
            if len(videos) >= limit:
                return
            if isinstance(node, dict):
                renderer = node.get("playlistVideoRenderer") or node.get("playlistPanelVideoRenderer")
                if renderer:
                    video_id = renderer.get("videoId")
                    if video_id and video_id not in seen:
                        title_obj = renderer.get("title", {})
                        title = (
                            (title_obj.get("runs") or [{}])[0].get("text")
                            or title_obj.get("simpleText")
                            or ""
                        )
                        thumbs = (renderer.get("thumbnail") or {}).get("thumbnails") or []
                        thumbnail_url = thumbs[-1]["url"] if thumbs else ""
                        seen.add(video_id)
                        videos.append({
                            "video_id": video_id,
                            "title": title,
                            "thumbnail_url": thumbnail_url,
                        })
                    return
                for value in node.values():
                    if len(videos) >= limit:
                        return
                    _walk(value)
            elif isinstance(node, list):
                for item in node:
                    if len(videos) >= limit:
                        return
                    _walk(item)

        _walk(data)

    if not videos:
        # Last resort: YouTube's markup/JSON shape changed, or ytInitialData
        # itself wasn't found. Every video id still appears as a bare
        # "videoId":"..." pair elsewhere in the page's embedded JSON, even
        # when we can't reliably parse out titles/thumbnails alongside it.
        # add_playlist_from_youtube looks up each track's title separately
        # (same oEmbed lookup used for a single pasted link) when title
        # comes back empty, so this fallback still produces usable tracks.
        for match in _RAW_VIDEO_ID_PATTERN.finditer(html):
            video_id = match.group(1)
            if video_id not in seen:
                seen.add(video_id)
                videos.append({"video_id": video_id, "title": "", "thumbnail_url": ""})
            if len(videos) >= limit:
                break

    return videos[:limit]