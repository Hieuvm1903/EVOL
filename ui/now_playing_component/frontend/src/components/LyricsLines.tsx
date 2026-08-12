import React, { useEffect, useRef } from "react";
import type { LyricLine } from "../lyricsProvider";
import { formatTime } from "../utils/time";

interface Props {
  lines: LyricLine[];
  activeLineIdx: number;
  onSeek: (time: number) => void;
}

// Karaoke-style centering: the active line is kept pinned at the
// viewport's vertical center by translating the whole line list, rather
// than scrolling — "always centered" by construction.
export default function LyricsLines({ lines, activeLineIdx, onSeek }: Props) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const linesRef = useRef<HTMLDivElement>(null);

  function recenter() {
    const viewport = viewportRef.current;
    const linesEl = linesRef.current;
    if (!viewport || !linesEl) return;
    const idx = activeLineIdx >= 0 ? activeLineIdx : 0;
    const activeEl = linesEl.querySelector(`[data-line-idx="${idx}"]`) as HTMLElement | null;
    if (!activeEl) { linesEl.style.transform = "translateY(0px)"; return; }
    const viewportHeight = viewport.offsetHeight;
    const offsetY = viewportHeight / 2 - (activeEl.offsetTop + activeEl.offsetHeight / 2);
    linesEl.style.transform = `translateY(${offsetY}px)`;
  }

  useEffect(() => {
    recenter();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeLineIdx, lines]);

  return (
    <div className="lyrics-viewport" ref={viewportRef}>
      <div className="lyrics-lines" ref={linesRef}>
        {lines.map((line, i) => {
          const distance = activeLineIdx < 0 ? 0 : Math.abs(i - activeLineIdx);
          return (
            <div
              key={i}
              data-line-idx={i}
              data-time={formatTime(line.time)}
              className={`lyrics-line${i === activeLineIdx ? " lyrics-line-active" : ""}`}
              style={{ opacity: Math.max(1 - distance * 0.18, 0.28) }}
              onClick={() => onSeek(line.time)}
            >
              {line.text}
            </div>
          );
        })}
      </div>
    </div>
  );
}