import { useEffect, useRef } from "react";
import { POS_KEY, DRAG_THRESHOLD, PANEL_WIDTH } from "../constants";
import { getContainer, pointFromEvent, clampToViewport } from "../utils/dom";

type DragMeta = {
  el: HTMLElement; origLeft: number; origTop: number; w: number; h: number; vw: number; vh: number;
  startX: number; startY: number;
  raf: number | null; dx: number; dy: number; moved: boolean;
  cleanup: () => void;
};

// Handles both the floating widget's position persistence (as a fraction
// of the viewport, so it rescales symmetrically on resize instead of only
// ever clamping inward) and the drag gesture itself. Listens on THIS
// document (reliably receives the whole gesture, since the box tracks the
// cursor) plus the parent's as a fast-drag safety net — safe to mix
// sources since everything uses screen coordinates.
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

  function savePosFraction(left: number, top: number, vw: number, vh: number) {
    try { window.parent.localStorage.setItem(POS_KEY, JSON.stringify({ leftFrac: left / vw, topFrac: top / vh })); } catch { }
  }

  function resetPos() {
    const el = getContainer();
    if (el) { el.style.transform = ""; el.style.left = ""; el.style.top = ""; el.style.right = ""; }
    try { window.parent.localStorage.removeItem(POS_KEY); } catch { }
  }

  function applySavedPosition() {
    try {
      const raw = window.parent.localStorage.getItem(POS_KEY);
      if (!raw) return;
      const { leftFrac, topFrac } = JSON.parse(raw);
      const el = getContainer();
      if (!el) return;
      const w = el.offsetWidth || PANEL_WIDTH, h = el.offsetHeight || 60;
      const vw = window.parent.innerWidth, vh = window.parent.innerHeight;
      const { left, top } = clampToViewport(leftFrac * vw, topFrac * vh, w, h, vw, vh);
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
        const left = m.origLeft + m.dx, top = m.origTop + m.dy;
        applyPos(left, top);
        savePosFraction(left, top, m.vw, m.vh);
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

  return { startDrag, resetPos };
}