/** A single synced lyric line: `time` in seconds from track start. */
export type LyricLine = { time: number; text: string };

/** One lyrics candidate the user can pick from */
export type LyricsCandidate = {
  id: number;
  trackName: string;
  artistName: string;
  albumName: string;
  duration: number;
  lines: LyricLine[];          // parsed synced lyrics
};

/**
 * Fetch multiple synced-lyrics candidates for a track via LRCLIB.
 * Returns an array of candidates (empty array if none found).
 */
export async function fetchLyrics(track: {
  title: string;
  artist?: string;
  video_id: string;
  youtube_url?: string;
}): Promise<LyricsCandidate[]> {
  try {
    // Clean title (remove common YouTube noise)
    const cleanTitle = track.title
      .replace(/\(.*?\)|\[.*?\]/g, "")
      .replace(/\s+/g, " ")
      .trim();

    if (!cleanTitle) return [];

    const cleanArtist = track.artist?.trim() || "";

    let results: Array<{
      id: number;
      trackName: string;
      artistName: string;
      albumName: string;
      duration: number;
      instrumental: boolean;
      syncedLyrics: string | null;
      plainLyrics: string | null;
    }> = [];

    // 1. Prefer structured search when we have an artist
    if (cleanArtist) {
      const url = new URL("https://lrclib.net/api/search");
      url.searchParams.set("track_name", cleanTitle);
      url.searchParams.set("artist_name", cleanArtist);

      const res = await fetch(url.toString(), {
        headers: {
          "User-Agent": "YourAppName/1.0[](https://github.com/your/repo)",
        },
      });

      if (res.ok) {
        results = await res.json();
      }
    }

    // 2. Fallback to free-text search
    if (results.length === 0) {
      const q = cleanArtist ? `${cleanArtist} ${cleanTitle}` : cleanTitle;
      const url = new URL("https://lrclib.net/api/search");
      url.searchParams.set("q", q);

      const res = await fetch(url.toString(), {
        headers: {
          "User-Agent": "YourAppName/1.0[](https://github.com/your/repo)",
        },
      });

      if (!res.ok) return [];
      results = await res.json();
    }

    // Keep only results that actually have synced lyrics
    const candidates: LyricsCandidate[] = [];

    for (const r of results) {
      if (!r.syncedLyrics || r.instrumental) continue;

      const lines = parseLRC(r.syncedLyrics);
      if (lines.length === 0) continue;

      candidates.push({
        id: r.id,
        trackName: r.trackName,
        artistName: r.artistName,
        albumName: r.albumName,
        duration: r.duration,
        lines,
      });
    }

    return candidates;
  } catch (err) {
    console.warn("fetchLyrics failed:", err);
    return [];
  }
}

/**
 * Parse a standard LRC string into sorted LyricLine[].
 */
function parseLRC(lrc: string): LyricLine[] {
  const lines: LyricLine[] = [];
  const lineRegex = /(?:\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\])+(.*)/g;

  for (const raw of lrc.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;

    lineRegex.lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = lineRegex.exec(line)) !== null) {
      const minutes = parseInt(match[1], 10);
      const seconds = parseInt(match[2], 10);
      const fraction = match[3]
        ? parseInt(match[3].padEnd(3, "0").slice(0, 3), 10)
        : 0;
      const text = (match[4] ?? "").trim();

      if (!text) continue;

      const time = minutes * 60 + seconds + fraction / 1000;
      lines.push({ time, text });
    }
  }

  return lines.sort((a, b) => a.time - b.time);
}

// ---------------------------------------------------------------------
// Below this line: generic, source-agnostic support code.
// ---------------------------------------------------------------------

const _cache = new Map<string, Promise<LyricsCandidate[]>>();

/** Cached wrapper, keyed by video_id — avoids re-fetching when a track
 * is revisited (e.g. navigating back to it, or a Streamlit rerun handing
 * back the same queue). */
export function fetchLyricsCached(track: {
  title: string;
  artist?: string;
  video_id: string;
  youtube_url?: string;
}): Promise<LyricsCandidate[]> {
  const key = track.video_id;
  const cached = _cache.get(key);
  if (cached) return cached;
  const promise = fetchLyrics(track).catch(() => []);
  _cache.set(key, promise);
  return promise;
}

/** Given a candidate's lines and the current playback time, returns the
 * index of the line that should be highlighted (-1 if before the first line). */
export function currentLineIndex(lines: LyricLine[], curTime: number): number {
  let idx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].time <= curTime) idx = i;
    else break;
  }
  return idx;
}
