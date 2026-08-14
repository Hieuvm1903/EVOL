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

// `order` already holds the play sequence — in shuffle mode that sequence
// is a random permutation (built once, when shuffle mode is entered, or
// again via "shuffle again"), but advancing through it is now always
// sequential, same as normal mode. Re-randomizing on every single
// "next" call (the old behavior) meant the Queue list's visible order —
// which IS `order` — never actually matched what played next, which
// looked like a bug: the list said one thing, playback did another.
export function pickNextTrackIdx(order: number[], mode: Mode, currentTrackIdx: number): number | null {
  const len = order.length;
  if (len <= 1) return mode === "repeatAll" ? currentTrackIdx : null;
  const pos = order.indexOf(currentTrackIdx);
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