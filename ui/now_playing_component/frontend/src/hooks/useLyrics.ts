import { useEffect, useRef, useState } from "react";
import type { Track } from "../types";
import { splitArtistTitle } from "../utils/artist";
import { currentLineIndex, fetchLyrics, fetchLyricsCached, LyricsCandidate } from "../lyricsProvider";

// Guarded by video_id, not just "did this effect fire" — `queue` is a
// prop Streamlit re-sends as a fresh array on every rerun, even when
// unchanged. The fetch key is only committed to `lastLyricsFetchKeyRef`
// once a fetch actually COMPLETES (inside .then, after the cancelled
// check) — committing it eagerly at effect-start caused a race on rapid
// early reruns (common right at app startup) where the only in-flight
// fetch gets cancelled by a second effect run, but the key was already
// marked "done", so nothing ever retried — a permanent spinner on the
// first track specifically.
export function useLyrics(queue: Track[], currentTrackIdx: number, curTime: number) {
  const [lyricsCandidates, setLyricsCandidates] = useState<LyricsCandidate[] | undefined>(undefined);
  const [selectedCandidateIdx, setSelectedCandidateIdx] = useState(0);
  const [manualTitle, setManualTitle] = useState("");
  const [manualArtist, setManualArtist] = useState("");
  const [manualSearching, setManualSearching] = useState(false);

  const autoCandidatesRef = useRef<LyricsCandidate[]>([]);
  const lastLyricsFetchKeyRef = useRef<string>("");

  useEffect(() => {
    const track = queue[currentTrackIdx];
    const key = track ? track.video_id : "";
    if (key === lastLyricsFetchKeyRef.current) return;

    setLyricsCandidates(undefined);
    setSelectedCandidateIdx(0);
    autoCandidatesRef.current = [];
    if (!track) {
      lastLyricsFetchKeyRef.current = key;
      setManualTitle("");
      setManualArtist("");
      return;
    }

    let cancelled = false;
    const { artist: parsedArtist, title: parsedTitle } = splitArtistTitle(track.title);
    setManualTitle(parsedTitle);
    setManualArtist(parsedArtist ?? "");

    fetchLyricsCached({ ...track, artist: parsedArtist ?? undefined }).then((candidates) => {
      if (cancelled) return; // superseded — leave the key uncommitted so a
                              // later run for the same track can retry
      lastLyricsFetchKeyRef.current = key;
      autoCandidatesRef.current = candidates;
      setLyricsCandidates(candidates);
    });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTrackIdx, queue]);

  async function runManualSearch() {
    const title = manualTitle.trim();
    if (!title) return;
    const track = queue[currentTrackIdx];
    setManualSearching(true);
    try {
      const results = await fetchLyrics({
        title,
        artist: manualArtist.trim() || undefined,
        video_id: track?.video_id ?? "manual-search",
      });
      // Manual results go first — auto-detected candidates stay available
      // right after, as a fallback the user can still pick.
      setLyricsCandidates([...results, ...autoCandidatesRef.current]);
      setSelectedCandidateIdx(0);
    } finally {
      setManualSearching(false);
    }
  }

  const selectedCandidate = lyricsCandidates?.[selectedCandidateIdx];
  const activeLineIdx = selectedCandidate ? currentLineIndex(selectedCandidate.lines, curTime) : -1;

  return {
    lyricsCandidates, selectedCandidateIdx, setSelectedCandidateIdx, selectedCandidate, activeLineIdx,
    manualTitle, setManualTitle, manualArtist, setManualArtist, manualSearching, runManualSearch,
  };
}