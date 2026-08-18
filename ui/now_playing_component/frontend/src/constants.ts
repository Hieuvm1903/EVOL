import type { Mode } from "./types";

export const MODE_MAP: Record<string, Mode> = { Normal: "normal", Shuffle: "shuffle", "Repeat All": "repeatAll" };
export const POS_KEY = "evol_player_pos";
export const SNAP_MODE_KEY = "evol_player_snap_mode"; // "1" | "0" — separate from POS_KEY so toggling doesn't wipe the saved position
export const EXPANDED_KEY = "evol_player_expanded";
export const DRAG_THRESHOLD = 4;
export const EDGE_MARGIN = 8;
export const PANEL_WIDTH = 300;