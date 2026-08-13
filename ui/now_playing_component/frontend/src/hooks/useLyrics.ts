import { useEffect, useRef, useState } from "react";
import { Streamlit } from "streamlit-component-lib";
import type { Track } from "../types";
import { splitArtistTitle } from "../utils/artist";
import {
  currentLineIndex, fetchLyrics, fetchLyricsCached, fetchLyricsByIdCached, LyricsCandidate,
} from "../lyricsProvider";

export function useLyrics(queue: Track[], currentTrackIdx: number, curTime: number) {
  const [lyricsCandidates, setLyricsCandidates] = useState<LyricsCandidate[] | undefined>(undefined);
  const [selectedCandidateIdx, setSelectedCandidateIdx] = useState(0);
  const [manualTitle, setManualTitle] = useState("");
  const [manualArtist, setManualArtist] = useState("");
  const [manualSearching, setManualSearching] = useState(false);

  const autoCandidatesRef = useRef<LyricsCandidate[]>([]);
  const lastLyricsFetchKeyRef = useRef<string>("");
  // Maps video_id -> the candidate id we last persisted to the DB for
  // that track. Keyed by CANDIDATE, not just "have we saved anything yet
  // for this track" — the previous version used a single per-track flag,
  // which meant the very first save (even a no-op "already matches the
  // DB" case) permanently blocked every later, genuinely different
  // selection from ever being persisted again for that track.
  const persistedCandidateIdRef = useRef<Record<string, string>>({});

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
    const fallbackArtist = track.artist || parsedArtist || undefined;
    setManualTitle(parsedTitle);
    setManualArtist(track.artist || parsedArtist || "");

    async function resolve() {
      // lyrics_url actually stores the previously-saved candidate's id —
      // if we have one, fetch exactly that instead of re-searching.
      if (track.lyrics_url) {
        const saved = await fetchLyricsByIdCached(track.lyrics_url);
        if (cancelled) return;
        if (saved) {
          lastLyricsFetchKeyRef.current = key;
          autoCandidatesRef.current = [saved];
          setLyricsCandidates([saved]);
          setSelectedCandidateIdx(0);
          // This selection already matches the DB — mark it so the
          // persist effect below doesn't immediately re-send it.
          persistedCandidateIdRef.current[key] = String(saved.id);
          return;
        }
        // saved id no longer resolves — fall through to a fresh search
      }

      const candidates = await fetchLyricsCached({ ...track, artist: fallbackArtist });
      if (cancelled) return;
      lastLyricsFetchKeyRef.current = key;
      autoCandidatesRef.current = candidates;
      setLyricsCandidates(candidates);
      setSelectedCandidateIdx(0);
    }

    resolve();
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
      setLyricsCandidates([...results, ...autoCandidatesRef.current]);
      setSelectedCandidateIdx(0);
    } finally {
      setManualSearching(false);
    }
  }

  const selectedCandidate = lyricsCandidates?.[selectedCandidateIdx];
  const activeLineIdx = selectedCandidate ? currentLineIndex(selectedCandidate.lines, curTime) : -1;

  // Persist whenever the EFFECTIVE candidate actually changes — compares
  // the candidate's own id against the last one we sent for this specific
  // track, not just "has anything been sent yet."
  useEffect(() => {
    if (!selectedCandidate) return;
    const track = queue[currentTrackIdx];
    if (!track || track.id == null) return;
    const key = track.video_id;
    const candidateKey = String(selectedCandidate.id);
    if (persistedCandidateIdRef.current[key] === candidateKey) return;

    persistedCandidateIdRef.current[key] = candidateKey;
    Streamlit.setComponentValue({
      action: "save_lyrics_selection",
      track_id: track.id,
      artist_name: selectedCandidate.artistName || null,
      lyrics_url: candidateKey,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCandidate]);

  return {
    lyricsCandidates, selectedCandidateIdx, setSelectedCandidateIdx, selectedCandidate, activeLineIdx,
    manualTitle, setManualTitle, manualArtist, setManualArtist, manualSearching, runManualSearch,
  };
}