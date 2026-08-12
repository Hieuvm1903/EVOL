import React from "react";
import type { Track } from "../types";
import type { useLyrics } from "../hooks/useLyrics";
import LyricsSearchBox from "./LyricsSearchBox";
import LyricsCandidatePicker from "./LyricsCandidatePicker";
import LyricsLines from "./LyricsLines";
import { LyricsLoading, LyricsNotFound } from "./LyricsEmptyStates";

interface Props {
  visible: boolean;
  track: Track;
  lyrics: ReturnType<typeof useLyrics>;
  onSeek: (time: number) => void;
}

export default function LyricsView({ visible, track, lyrics, onSeek }: Props) {
  const {
    lyricsCandidates, selectedCandidateIdx, setSelectedCandidateIdx, selectedCandidate,
    activeLineIdx, manualTitle, setManualTitle, manualArtist, setManualArtist,
    manualSearching, runManualSearch,
  } = lyrics;

  return (
    <div className="lyrics-panel" style={{ display: visible ? "flex" : "none" }}>
      <LyricsSearchBox
        title={manualTitle} onTitleChange={setManualTitle}
        artist={manualArtist} onArtistChange={setManualArtist}
        searching={manualSearching}
        onSearch={runManualSearch}
      />

      {lyricsCandidates && (
        <LyricsCandidatePicker
          candidates={lyricsCandidates}
          selectedIdx={selectedCandidateIdx}
          onChange={setSelectedCandidateIdx}
        />
      )}

      {lyricsCandidates === undefined && <LyricsLoading />}
      {lyricsCandidates && lyricsCandidates.length === 0 && <LyricsNotFound track={track} />}

      {selectedCandidate && selectedCandidate.lines.length > 0 && (
        <LyricsLines lines={selectedCandidate.lines} activeLineIdx={activeLineIdx} onSeek={onSeek} />
      )}
    </div>
  );
}