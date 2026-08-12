import { EDGE_MARGIN } from "../constants";

export function getContainer(): HTMLElement | null {
  try {
    return window.parent.document.querySelector(".st-key-now_playing_drawer");
  } catch {
    return null;
  }
}

// screenX/screenY (not clientX/clientY) — relative to the physical
// display, not whichever viewport fired the event. The element being
// dragged IS this iframe's own container, so viewport-local coordinates
// while that viewport itself moves create a feedback loop (the delta
// shrinks toward zero as the box catches up to the cursor).
export function pointFromEvent(e: MouseEvent | TouchEvent): { x: number; y: number } | null {
  if ("touches" in e) {
    const t = e.touches[0] ?? e.changedTouches[0];
    if (!t) return null;
    return { x: t.screenX, y: t.screenY };
  }
  return { x: e.screenX, y: e.screenY };
}

export function clampToViewport(left: number, top: number, w: number, h: number, vw: number, vh: number) {
  return {
    left: Math.min(Math.max(left, EDGE_MARGIN), Math.max(EDGE_MARGIN, vw - w - EDGE_MARGIN)),
    top: Math.min(Math.max(top, EDGE_MARGIN), Math.max(EDGE_MARGIN, vh - h - EDGE_MARGIN)),
  };
}