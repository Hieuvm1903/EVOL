import { useEffect, useRef } from "react";
import { POS_KEY, DRAG_THRESHOLD, PANEL_WIDTH, EDGE_MARGIN } from "../constants";
import { getContainer, pointFromEvent, clampToViewport } from "../utils/dom";
import { DEFAULT_SNAP, nearestSnapId, snapPixelPosition, SnapId } from "../utils/snapPoints";

type DragMeta = {
  el: HTMLElement; origLeft: number; origTop: number; w: number; h: number; vw: number; vh: number;
  startX: number; startY: number;
  raf: number | null; dx: number; dy: number; moved: boolean;
  cleanup: () => void;
};

// Handles the floating widget's position: it docks to one of 8 fixed
// points on drop (see utils/snapPoints.ts) rather than free-floating, and
// persists which point via POS_KEY (shared parent-window localStorage, so
// it carries over between pages). Drag tracking itself is unchanged —
// still a live transform following the cursor in screen coordinates —
// only the *release* behavior now snaps instead of leaving it wherever
// the cursor let go.
export function useDragPosition() {
  const dragMeta = useRef<DragMeta | null>(null);
  const lastDragMoved = useRef(false);

  function applyPos(left: number, top: number) {
    const el = getContainer();
    if (!el) return;
    el.style.right = "auto";
    el.style.transform = "";
    el.style.left = `${left}px`;
    el.style.top = `${top}px`;
  }

  // Briefly enables a CSS transition on left/top so the final hop into a
  // dock point reads as a "snap", then removes it — every other position
  // change (drag tracking, resize) stays instant.
  function applyPosAnimated(left: number, top: number) {
    const el = getContainer();
    if (!el) return;
    el.classList.add("evol-snapping");
    applyPos(left, top);
    window.setTimeout(() => el.classList.remove("evol-snapping"), 220);
  }

  function saveSnap(id: SnapId) {
    try { window.parent.localStorage.setItem(POS_KEY, JSON.stringify({ snap: id })); } catch { }
  }

  function resetPos() {
    const el = getContainer();
    if (el) { el.style.transform = ""; el.style.left = ""; el.style.top = ""; el.style.right = ""; }
    try { window.parent.localStorage.removeItem(POS_KEY); } catch { }
  }

  // Re-derives pixel position for the currently-saved dock point using the
  // widget's *current* box size — call on mount, on window resize, and
  // after toggling pill <-> panel (their sizes differ).
  function applySavedPosition() {
    try {
      const raw = window.parent.localStorage.getItem(POS_KEY);
      if (!raw) return; // nothing docked yet — leave the CSS default in place
      const parsed = JSON.parse(raw);
      const snapId: SnapId = parsed && typeof parsed.snap === "string" ? parsed.snap : DEFAULT_SNAP;
      const el = getContainer();
      if (!el) return;
      const w = el.offsetWidth || PANEL_WIDTH, h = el.offsetHeight || 60;
      const vw = window.parent.innerWidth, vh = window.parent.innerHeight;
      const { left, top } = snapPixelPosition(snapId, w, h, vw, vh, EDGE_MARGIN);
      applyPos(left, top);
    } catch { }
  }

  useEffect(() => { applySavedPosition(); }, []);

  useEffect(() => {
    let parentWin: Window;
    try { parentWin = window.parent; } catch { return; }
    const onResize = () => applySavedPosition();
    try {
      parentWin.addEventListener("resize", onResize);
      return () => parentWin.removeEventListener("resize", onResize);
    } catch {
      return;
    }
  }, []);

  function startDrag(e: React.MouseEvent | React.TouchEvent, onTap: () => void) {
    if ((e.target as HTMLElement).closest("button, .header-view-toggle")) return;
    const el = getContainer();
    if (!el) return;

    const start = pointFromEvent(e.nativeEvent as MouseEvent | TouchEvent);
    if (!start) return;

    const rect = el.getBoundingClientRect();
    let vw = 9999, vh = 9999;
    try { vw = window.parent.innerWidth; vh = window.parent.innerHeight; } catch { }

    const onMove = (ev: MouseEvent | TouchEvent) => {
      const m = dragMeta.current;
      if (!m) return;
      const p = pointFromEvent(ev);
      if (!p) return;
      if ("touches" in ev) ev.preventDefault();
      const rawLeft = m.origLeft + (p.x - m.startX);
      const rawTop = m.origTop + (p.y - m.startY);
      const { left, top } = clampToViewport(rawLeft, rawTop, m.w, m.h, m.vw, m.vh);
      m.dx = left - m.origLeft;
      m.dy = top - m.origTop;
      if (Math.abs(m.dx) > DRAG_THRESHOLD || Math.abs(m.dy) > DRAG_THRESHOLD) m.moved = true;
      if (!m.raf) {
        m.raf = requestAnimationFrame(() => {
          if (!dragMeta.current) return;
          dragMeta.current.raf = null;
          dragMeta.current.el.style.transform =
            `translate3d(${dragMeta.current.dx}px, ${dragMeta.current.dy}px, 0)`;
        });
      }
    };

    const finishDrag = () => {
      const m = dragMeta.current;
      if (!m) return;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("touchmove", onMove);
      document.removeEventListener("mouseup", finishDrag);
      document.removeEventListener("touchend", finishDrag);
      try {
        window.parent.document.removeEventListener("mousemove", onMove);
        window.parent.document.removeEventListener("touchmove", onMove);
        window.parent.document.removeEventListener("mouseup", finishDrag);
        window.parent.document.removeEventListener("touchend", finishDrag);
      } catch { }
      if (m.raf) cancelAnimationFrame(m.raf);
      try { m.el.classList.remove("evol-dragging"); } catch { }
      try { window.parent.document.body.style.userSelect = ""; } catch { }
      if (m.moved) {
        m.el.style.transform = ""; // drop the drag-tracking transform; snap uses left/top instead
        const rawLeft = m.origLeft + m.dx, rawTop = m.origTop + m.dy;
        const snapId = nearestSnapId(rawLeft, rawTop, m.w, m.h, m.vw, m.vh, EDGE_MARGIN);
        const { left, top } = snapPixelPosition(snapId, m.w, m.h, m.vw, m.vh, EDGE_MARGIN);
        applyPosAnimated(left, top);
        saveSnap(snapId);
      }
      lastDragMoved.current = m.moved;
      dragMeta.current = null;
      if (!m.moved) onTap();
    };

    dragMeta.current = {
      el, origLeft: rect.left, origTop: rect.top, w: rect.width, h: rect.height, vw, vh,
      startX: start.x, startY: start.y,
      raf: null, dx: 0, dy: 0, moved: false,
      cleanup: finishDrag,
    };
    el.classList.add("evol-dragging");
    try { window.parent.document.body.style.userSelect = "none"; } catch { }

    document.addEventListener("mousemove", onMove);
    document.addEventListener("touchmove", onMove, { passive: false });
    document.addEventListener("mouseup", finishDrag);
    document.addEventListener("touchend", finishDrag);
    try {
      window.parent.document.addEventListener("mousemove", onMove);
      window.parent.document.addEventListener("touchmove", onMove, { passive: false });
      window.parent.document.addEventListener("mouseup", finishDrag);
      window.parent.document.addEventListener("touchend", finishDrag);
    } catch { }
  }

  useEffect(() => {
    return () => { dragMeta.current?.cleanup(); };
  }, []);

  return { startDrag, resetPos, applySavedPosition };
}