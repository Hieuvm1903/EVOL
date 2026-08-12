import { useEffect, RefObject } from "react";
import { Streamlit } from "streamlit-component-lib";

// Throttled to one update per animation frame (avoids CSS transitions —
// e.g. the queue list's collapse animation — firing dozens of
// intermediate resizes, which reads as content jumping around).
// Uses getBoundingClientRect (sub-pixel accurate) instead of scrollHeight
// (integer, rounds down) plus a +2px buffer — scrollHeight rounding was
// clipping the panel's bottom border by a fraction of a pixel in flex
// layouts, which showed up as the outline disappearing in lyrics mode.
export function useFrameHeight(rootRef: RefObject<HTMLDivElement>) {
  useEffect(() => {
    if (!rootRef.current) return;
    const el = rootRef.current;
    let lastHeight = 0;
    let raf: number | null = null;
    const report = () => {
      raf = null;
      const h = Math.ceil(el.getBoundingClientRect().height) + 2;
      if (h !== lastHeight) { lastHeight = h; Streamlit.setFrameHeight(h); }
    };
    const scheduleReport = () => { if (!raf) raf = requestAnimationFrame(report); };
    const observer = new ResizeObserver(scheduleReport);
    observer.observe(el);
    scheduleReport();
    return () => { observer.disconnect(); if (raf) cancelAnimationFrame(raf); };
  }, [rootRef]);
}