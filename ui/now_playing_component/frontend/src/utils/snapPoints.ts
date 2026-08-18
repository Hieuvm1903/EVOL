// 8 dock points the floating widget can snap to on drop — 4 corners plus
// the 4 edge midpoints. Same set is used whether the widget is collapsed
// (pill) or expanded (panel); each snap position is computed from the
// widget's *current* box size, so switching between pill <-> panel (or a
// window resize) re-derives the correct pixel offset for whichever corner
// it's docked to, instead of storing a fixed x/y that would drift.
export type SnapId =
  | "top-left" | "top-center" | "top-right"
  | "middle-left" | "middle-right"
  | "bottom-left" | "bottom-center" | "bottom-right";

export const SNAP_IDS: SnapId[] = [
  "top-left", "top-center", "top-right",
  "middle-left", "middle-right",
  "bottom-left", "bottom-center", "bottom-right",
];

export const DEFAULT_SNAP: SnapId = "top-right";

export function snapPixelPosition(
  id: SnapId, w: number, h: number, vw: number, vh: number, margin: number
): { left: number; top: number } {
  const [vSide, hSide] = id.split("-") as ["top" | "middle" | "bottom", "left" | "center" | "right"];
  const left = hSide === "left" ? margin : hSide === "center" ? (vw - w) / 2 : vw - w - margin;
  const top = vSide === "top" ? margin : vSide === "middle" ? (vh - h) / 2 : vh - h - margin;
  return { left: Math.max(margin, left), top: Math.max(margin, top) };
}

export function nearestSnapId(
  left: number, top: number, w: number, h: number, vw: number, vh: number, margin: number
): SnapId {
  let best: SnapId = DEFAULT_SNAP;
  let bestDist = Infinity;
  for (const id of SNAP_IDS) {
    const p = snapPixelPosition(id, w, h, vw, vh, margin);
    const d = Math.hypot(p.left - left, p.top - top);
    if (d < bestDist) { bestDist = d; best = id; }
  }
  return best;
}