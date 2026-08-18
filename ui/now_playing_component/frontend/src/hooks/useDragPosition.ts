import { useEffect, useRef, useState } from "react";
import { POS_KEY, SNAP_MODE_KEY, DRAG_THRESHOLD, PANEL_WIDTH, EDGE_MARGIN } from "../constants";
import { getContainer, pointFromEvent, clampToViewport } from "../utils/dom";
import { DEFAULT_SNAP, nearestSnapId, snapPixelPosition, SnapId } from "../utils/snapPoints";

type DragMeta = {
  el: HTMLElement; origLeft: number; origTop: number; w: number; h: number; vw: number; vh: number;
  startX: number; startY: number;
  raf: number | null; dx: number; dy: number; moved: boolean;
  cleanup: () => void;
};

function readSnapModePref(): boolean {
  try {
    const raw = window.parent.localStorage.getItem(SNAP_MODE_KEY);
    return raw === null ? true : raw === "1"; // default: snap on
  } catch {
    return true;
  }
}

// Handles the floating widget's position. Two modes, toggled by the user
// (see the header switch): "snap" docks to one of 8 fixed points on
// drop (utils/snapPoints.ts); "free" is the original behavior — drop it
// anywhere, clamped to the viewport. Both persist under the same POS_KEY,
// distinguished by shape ({snap: id} vs {leftFrac, topFrac}), so
// applySavedPosition can restore either. The mode preference itself lives
// under a separate key so switching modes never discards the saved spot.
export function useDragPosition() {
  const dragMeta = useRef<DragMeta | null>(null);
  const lastDragMoved = useRef(false);

  const [snapEnabled, setSnapEnabled] = useState<boolean>(readSnapModePref);
  const snapEnabledRef = useRef(snapEnabled);
  useEffect(() => { snapEnabledRef.current = snapEnabled; }, [snapEnabled]);

  function applyPos(left: number, top: number) {
    const el = getContainer();
    if (!el) return;
    el.style.right = "auto";
    el.style.transform = "";
    el.style.left = `${left}px`;
    el.style.top = `${top}px`;
  }

  // Briefly enables a CSS transition on left/top so the hop into a dock
  // point reads as a "snap" — used only in snap mode.
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

  function saveFree(left: number, top: number, vw: number, vh: number) {
    try { window.parent.localStorage.setItem(POS_KEY, JSON.stringify({ leftFrac: left / vw, topFrac: top / vh })); } catch { }
  }

  function resetPos() {
    const el = getContainer();
    if (el) { el.style.transform = ""; el.style.left = ""; el.style.top = ""; el.style.right = ""; }
    try { window.parent.localStorage.removeItem(POS_KEY); } catch { }
  }

  // Re-derives pixel position from whatever's saved, using the widget's
  // *current* box size — call on mount, on window resize, and after
  // toggling pill <-> panel (their sizes differ).
  function applySavedPosition() {
    try {
      const raw = window.parent.localStorage.getItem(POS_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      const el = getContainer();
      if (!el) return;
      const w = el.offsetWidth || PANEL_WIDTH, h = el.offsetHeight || 60;
      const vw = window.parent.innerWidth, vh = window.parent.innerHeight;

      if (parsed && typeof parsed.snap === "string") {
        const { left, top } = snapPixelPosition(parsed.snap as SnapId, w, h, vw, vh, EDGE_MARGIN);
        applyPos(left, top);
      } else if (parsed && typeof parsed.leftFrac === "number") {
        const { left, top } = clampToViewport(parsed.leftFrac * vw, parsed.topFrac * vh, w, h, vw, vh);
        applyPos(left, top);
      }
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

  // Called from the header switch. In snap mode, immediately docks the
  // current position to its nearest point rather than waiting for the
  // next drag. In free mode, just converts the current pixel position to
  // a fraction and leaves it exactly where it is.
  function setSnapMode(enabled: boolean) {
    setSnapEnabled(enabled);
    try { window.parent.localStorage.setItem(SNAP_MODE_KEY, enabled ? "1" : "0"); } catch { }

    const el = getContainer();
    if (!el) return;
    const rect = el.getBoundingClientRect();
    let vw = 9999, vh = 9999;
    try { vw = window.parent.innerWidth; vh = window.parent.innerHeight; } catch { }

    if (enabled) {
      const id = nearestSnapId(rect.left, rect.top, rect.width, rect.height, vw, vh, EDGE_MARGIN);
      const { left, top } = snapPixelPosition(id, rect.width, rect.height, vw, vh, EDGE_MARGIN);
      applyPosAnimated(left, top);
      saveSnap(id);
    } else {
      saveFree(rect.left, rect.top, vw, vh);
    }
  }

  function startDrag(e: React.MouseEvent | React.TouchEvent, onTap: () => void) {
    if ((e.target as HTMLElement).closest("button, .header-view-toggle, .header-snap-toggle")) return;
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
        m.el.style.transform = "";
        const rawLeft = m.origLeft + m.dx, rawTop = m.origTop + m.dy;
        if (snapEnabledRef.current) {
          const snapId = nearestSnapId(rawLeft, rawTop, m.w, m.h, m.vw, m.vh, EDGE_MARGIN);
          const { left, top } = snapPixelPosition(snapId, m.w, m.h, m.vw, m.vh, EDGE_MARGIN);
          applyPosAnimated(left, top);
          saveSnap(snapId);
        } else {
          applyPos(rawLeft, rawTop);
          saveFree(rawLeft, rawTop, m.vw, m.vh);
        }
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

  return { startDrag, resetPos, applySavedPosition, snapEnabled, setSnapMode };
}