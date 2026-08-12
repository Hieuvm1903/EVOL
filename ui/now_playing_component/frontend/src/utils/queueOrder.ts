import type { Mode } from "../types";

export function shuffleArray<T>(arr: T[]): T[] {
  const result = [...arr];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

export function shuffleQueue(queueLen: number): number[] {
  return shuffleArray(Array.from({ length: queueLen }, (_, i) => i));
}

export function pickNextTrackIdx(order: number[], mode: Mode, currentTrackIdx: number): number | null {
  const len = order.length;
  if (len <= 1) return mode === "shuffle" || mode === "repeatAll" ? currentTrackIdx : null;
  const pos = order.indexOf(currentTrackIdx);
  if (mode === "shuffle") {
    let candidate = currentTrackIdx;
    while (candidate === currentTrackIdx) candidate = order[Math.floor(Math.random() * len)];
    return candidate;
  }
  const nextPos = pos + 1;
  if (nextPos < len) return order[nextPos];
  return mode === "repeatAll" ? order[0] : null;
}

export function pickPrevTrackIdx(order: number[], mode: Mode, currentTrackIdx: number): number {
  const len = order.length;
  const pos = order.indexOf(currentTrackIdx);
  const prevPos = pos - 1;
  if (prevPos >= 0) return order[prevPos];
  return mode === "repeatAll" ? order[len - 1] : order[0];
}