import React from "react";
import { FileTextOutlined } from "@ant-design/icons";
import type { Track } from "../types";

export function LyricsLoading() {
  return (
    <div className="lyrics-empty">
      <div className="lyrics-spinner" />
      <p>Loading lyrics…</p>
    </div>
  );
}

export function LyricsNotFound({ track }: { track: Track }) {
  return (
    <div className="lyrics-empty">
      <FileTextOutlined style={{ fontSize: 22, color: "#3a3a3a", marginBottom: 8 }} />
      <p>No lyrics found.</p>
      <p className="lyrics-track-title">{track.title}</p>
      <div className="lyrics-links">
        <a href={`https://genius.com/search?q=${encodeURIComponent(track.title)}`} target="_blank" rel="noreferrer">
          Search Genius ↗
        </a>
        <a href={`https://www.musixmatch.com/search?query=${encodeURIComponent(track.title)}`} target="_blank" rel="noreferrer">
          Search Musixmatch ↗
        </a>
      </div>
    </div>
  );
}