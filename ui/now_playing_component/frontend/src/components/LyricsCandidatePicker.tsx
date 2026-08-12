import React from "react";
import { Select } from "antd";
import type { LyricsCandidate } from "../lyricsProvider";

interface Props {
  candidates: LyricsCandidate[];
  selectedIdx: number;
  onChange: (idx: number) => void;
}

export default function LyricsCandidatePicker({ candidates, selectedIdx, onChange }: Props) {
  if (candidates.length <= 1) return null;
  return (
    <Select
      size="small"
      className="lyrics-candidate-select"
      value={selectedIdx}
      onChange={onChange}
      options={candidates.map((c, idx) => ({
        value: idx,
        label: c.artistName ? `${c.trackName} — ${c.artistName}` : c.trackName,
      }))}
    />
  );
}