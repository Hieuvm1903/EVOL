// Common YouTube title conventions for music videos: "Artist - Title",
// "Artist – Title" (en dash), "Artist: Title". Best-effort only — some
// videos won't match (e.g. no separator, or the channel name isn't the
// artist), in which case `artist` comes back null and the UI should just
// omit it rather than showing something wrong.
const ARTIST_TITLE_PATTERN = /^\s*(.+?)\s*[-–:]\s*(.+?)\s*$/;

export function splitArtistTitle(rawTitle: string): { artist: string | null; title: string } {
  const match = rawTitle.match(ARTIST_TITLE_PATTERN);
  if (!match) return { artist: null, title: rawTitle };
  return { artist: match[1].trim(), title: match[2].trim() };
}