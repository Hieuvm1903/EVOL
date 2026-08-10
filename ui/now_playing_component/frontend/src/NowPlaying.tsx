import React, { useEffect, useRef, useState } from "react";
import { ConfigProvider, theme as antdTheme, Segmented, Button, Slider, Typography, Tooltip, Select } from "antd";
import {
  StepBackwardOutlined, StepForwardOutlined, PlayCircleFilled, PauseCircleFilled,
  UnorderedListOutlined, SwapOutlined, RedoOutlined, RetweetOutlined, SoundOutlined, CloseOutlined,
  VideoCameraOutlined, FileTextOutlined,
} from "@ant-design/icons";
import { Streamlit } from "streamlit-component-lib";
import QueueList from "./QueueList";
import "./NowPlaying.css";
import { splitArtistTitle } from "./utils";
import { currentLineIndex, LyricLine, fetchLyricsCached, LyricsCandidate } from "./lyricsProvider";
export type Track = { title: string; video_id: string; thumbnail_url?: string };
type Mode = "normal" | "shuffle" | "repeatTrack" | "repeatAll";
type View = "video" | "lyrics";

const MODE_MAP: Record<string, Mode> = { Normal: "normal", Shuffle: "shuffle", "Repeat All": "repeatAll" };
const POS_KEY = "evol_player_pos";
const WIDTH_KEY = "evol_player_width";
const EXPANDED_KEY = "evol_player_expanded";
const DRAG_THRESHOLD = 4;
const EDGE_MARGIN = 8;
const MIN_WIDTH = 260;
const MAX_WIDTH = 480;
const DEFAULT_WIDTH = 300;

function formatTime(s: number): string {
  s = Math.max(0, Math.floor(s));
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec < 10 ? "0" : ""}${sec}`;
}

function pickNextTrackIdx(order: number[], mode: Mode, currentTrackIdx: number): number | null {
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

function pickPrevTrackIdx(order: number[], mode: Mode, currentTrackIdx: number): number {
  const len = order.length;
  const pos = order.indexOf(currentTrackIdx);
  const prevPos = pos - 1;
  if (prevPos >= 0) return order[prevPos];
  return mode === "repeatAll" ? order[len - 1] : order[0];
}

function getContainer(): HTMLElement | null {
  try {
    return window.parent.document.querySelector(".st-key-now_playing_drawer");
  } catch {
    return null;
  }
}

// screenX/screenY (not clientX/clientY) — relative to the physical
// display, not whichever viewport fired the event. Needed because the
// element being dragged/resized IS this iframe's own container: using
// viewport-local coordinates while that viewport itself moves creates a
// feedback loop where the delta shrinks toward zero as tracking "catches
// up", causing stutter. Screen coordinates have no such dependency.
function pointFromEvent(e: MouseEvent | TouchEvent): { x: number; y: number } | null {
  if ("touches" in e) {
    const t = e.touches[0] ?? e.changedTouches[0];
    if (!t) return null;
    return { x: t.screenX, y: t.screenY };
  }
  return { x: e.screenX, y: e.screenY };
}
function clampToViewport(left: number, top: number, w: number, h: number, vw: number, vh: number) {
  return {
    left: Math.min(Math.max(left, EDGE_MARGIN), Math.max(EDGE_MARGIN, vw - w - EDGE_MARGIN)),
    top: Math.min(Math.max(top, EDGE_MARGIN), Math.max(EDGE_MARGIN, vh - h - EDGE_MARGIN)),
  };
}
function clampWidth(px: number, vw: number) {
  return Math.min(Math.max(px, MIN_WIDTH), Math.min(MAX_WIDTH, vw - EDGE_MARGIN * 2));
}

export default function NowPlaying({ queue, initialMode }: { queue: Track[]; initialMode: string }) {
  const [mode, setMode] = useState<Mode>(MODE_MAP[initialMode] || "normal");
  const [order, setOrder] = useState<number[]>(() => queue.map((_, i) => i));
  const [currentTrackIdx, setCurrentTrackIdx] = useState(0);
  const [expanded, setExpanded] = useState<boolean>(() => {
    try { return localStorage.getItem(EXPANDED_KEY) === "1"; } catch { return false; }
  });
  const [view, setView] = useState<View>("video");
  const [playing, setPlaying] = useState(false);
  const [curTime, setCurTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolumeState] = useState(100);
  const [showUnmute, setShowUnmute] = useState(false);

  const playerMainRef = useRef<any>(null);
  const playerPreloadRef = useRef<any>(null);
  const preloadReady = useRef(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const pillNodeRef = useRef<HTMLDivElement>(null);
  const headerNodeRef = useRef<HTMLDivElement>(null);
  const lastVideoIds = useRef<string>("");
  const lastDragMoved = useRef(false);
  const prevModeRef = useRef(mode);
  const modeRef = useRef(mode);
  useEffect(() => { modeRef.current = mode; }, [mode]);
  useEffect(() => {
    if (mode === "shuffle" && prevModeRef.current !== "shuffle") {
      setOrder(shuffleQueue(queueRef.current.length));
    }
    prevModeRef.current = mode;
  }, [mode]);
  const orderRef = useRef(order);
  useEffect(() => { orderRef.current = order; }, [order]);
  const currentTrackIdxRef = useRef(currentTrackIdx);
  useEffect(() => { currentTrackIdxRef.current = currentTrackIdx; }, [currentTrackIdx]);
  const queueRef = useRef(queue);
  useEffect(() => { queueRef.current = queue; }, [queue]);

  function shuffleArray<T>(arr: T[]): T[] {
    const result = [...arr];
    for (let i = result.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
  }
  function shuffleQueue(queueLen: number): number[] {
    return shuffleArray(Array.from({ length: queueLen }, (_, i) => i));
  }

  function playTrackIdx(trackIdx: number) {
    const track = queueRef.current[trackIdx];
    if (!track) return;
    setCurrentTrackIdx(trackIdx);
    try { playerMainRef.current?.loadVideoById(track.video_id); } catch { }
    setTimeout(cuePreloadNext, 0);
  }

  function cuePreloadNext() {
    if (!preloadReady.current) return;
    const next = pickNextTrackIdx(orderRef.current, modeRef.current, currentTrackIdxRef.current);
    if (next === null) return;
    try { playerPreloadRef.current.cueVideoById(queueRef.current[next].video_id); } catch { }
  }

  function advance(step: number) {
    if (!orderRef.current.length) return;
    const next = step > 0
      ? pickNextTrackIdx(orderRef.current, modeRef.current, currentTrackIdxRef.current)
      : pickPrevTrackIdx(orderRef.current, modeRef.current, currentTrackIdxRef.current);
    if (next === null) { setPlaying(false); return; }
    playTrackIdx(next);
  }

  function handleEnded() {
    if (modeRef.current === "repeatTrack") {
      playerMainRef.current?.seekTo(0);
      playerMainRef.current?.playVideo();
    } else {
      advance(1);
    }
  }

  // --- Load YouTube IFrame API once, create players. #yt-main is always
  // mounted (see JSX below — no conditional rendering of the panel, and
  // the video/lyrics toggle only hides it via CSS), so this player is
  // created exactly once for the whole component's lifetime and survives
  // collapse/expand AND switching to the lyrics view. -------------------
  useEffect(() => {
    function ensureApi(): Promise<void> {
      return new Promise((resolve) => {
        if ((window as any).YT && (window as any).YT.Player) return resolve();
        const prev = (window as any).onYouTubeIframeAPIReady;
        (window as any).onYouTubeIframeAPIReady = () => { prev?.(); resolve(); };
        if (!document.getElementById("yt-iframe-api")) {
          const tag = document.createElement("script");
          tag.id = "yt-iframe-api";
          tag.src = "https://www.youtube.com/iframe_api";
          document.body.appendChild(tag);
        }
      });
    }

    let cancelled = false;
    ensureApi().then(() => {
      if (cancelled || !queueRef.current.length) return;
      const YT = (window as any).YT;
      playerMainRef.current = new YT.Player("yt-main", {
        width: "100%", height: "100%",
        videoId: queueRef.current[currentTrackIdxRef.current].video_id,
        playerVars: { autoplay: 1, mute: 0, playsinline: 1, rel: 0 },
        events: {
          onReady: () => {
            setTimeout(() => {
              try { if (playerMainRef.current.isMuted()) setShowUnmute(true); } catch { }
            }, 500);
          },
          onStateChange: (e: any) => {
            if (e.data === YT.PlayerState.ENDED) handleEnded();
            if (e.data === YT.PlayerState.PLAYING) setPlaying(true);
            if (e.data === YT.PlayerState.PAUSED) setPlaying(false);
          },
        },
      });
      playerPreloadRef.current = new YT.Player("yt-preload", {
        videoId: "",
        playerVars: { mute: 1, controls: 0 },
        events: { onReady: () => { preloadReady.current = true; cuePreloadNext(); } },
      });
    });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const ids = queue.map((t) => t.video_id).join(",");
    if (ids === lastVideoIds.current) return;
    const isFirstRun = lastVideoIds.current === "";
    lastVideoIds.current = ids;
    const freshOrder = modeRef.current === "shuffle"
      ? shuffleQueue(queue.length)
      : queue.map((_, i) => i);
    setOrder(freshOrder);
    if (isFirstRun || !queue.length) return;
    setCurrentTrackIdx(0);
    if (playerMainRef.current?.loadVideoById) {
      playerMainRef.current.loadVideoById(queue[0].video_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queue]);

  function togglePlayPause() {
    const p = playerMainRef.current;
    if (!p?.getPlayerState) return;
    const YT = (window as any).YT;
    if (p.getPlayerState() === YT.PlayerState.PLAYING) p.pauseVideo();
    else p.playVideo();
  }

  function seek(e: React.MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const frac = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
    const p = playerMainRef.current;
    if (p?.getDuration) { try { p.seekTo(frac * p.getDuration(), true); } catch { } }
  }

  function setVolume(v: number) {
    setVolumeState(v);
    try { playerMainRef.current?.setVolume(v); } catch { }
  }

  function unmuteNow() {
    try { playerMainRef.current?.unMute(); } catch { }
    setShowUnmute(false);
  }

  function closeWidget() {
    try { playerMainRef.current?.stopVideo?.(); } catch { }
    Streamlit.setComponentValue("close");
  }

  useEffect(() => {
    const id = setInterval(() => {
      const p = playerMainRef.current;
      if (!p?.getCurrentTime) return;
      try {
        const cur = p.getCurrentTime();
        const dur = p.getDuration();
        if (dur > 0) { setCurTime(cur); setDuration(dur); }
      } catch { }
    }, 500);
    return () => clearInterval(id);
  }, []);

  function toggleExpand(v: boolean) {
    setExpanded(v);
    try { localStorage.setItem(EXPANDED_KEY, v ? "1" : "0"); } catch { }
  }
  useEffect(() => {
    if (!rootRef.current) return;
    const el = rootRef.current;
    const report = () => Streamlit.setFrameHeight(el.scrollHeight);
    const observer = new ResizeObserver(report);
    observer.observe(el);
    report();
    return () => observer.disconnect();
  }, []);

  // --- Position (drag-to-move) -----------------------------------------
  function applyPos(left: number, top: number) {
    const el = getContainer();
    if (!el) return;
    el.style.right = "auto";
    el.style.transform = "";
    el.style.left = `${left}px`;
    el.style.top = `${top}px`;
  }
  // Persisted as a FRACTION of the viewport (0..1), not raw pixels — a
  // fraction naturally rescales in both directions as the viewport
  // resizes (e.g. opening/closing DevTools), where raw pixels only ever
  // clamp inward and never restore back out.
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
      const w = el.offsetWidth || DEFAULT_WIDTH, h = el.offsetHeight || 60;
      const vw = window.parent.innerWidth, vh = window.parent.innerHeight;
      const { left, top } = clampToViewport(leftFrac * vw, topFrac * vh, w, h, vw, vh);
      applyPos(left, top);
    } catch { }
  }

  // --- Width (resize) -----------------------------------------------
  function applyWidth(px: number) {
    const el = getContainer();
    if (el) el.style.width = `${px}px`;
  }
  function saveWidth(px: number) {
    try { window.parent.localStorage.setItem(WIDTH_KEY, String(px)); } catch { }
  }
  function applySavedWidth() {
    try {
      const raw = window.parent.localStorage.getItem(WIDTH_KEY);
      const vw = window.parent.innerWidth;
      const px = raw ? clampWidth(parseFloat(raw), vw) : clampWidth(DEFAULT_WIDTH, vw);
      applyWidth(px);
    } catch { }
  }

  useEffect(() => {
    applySavedPosition();
    applySavedWidth();
  }, []);

  // Re-derive position AND width fresh from saved fraction/value whenever
  // the parent viewport resizes (DevTools open/close, window resize) —
  // always recomputing from the source of truth rather than nudging
  // whatever's currently applied, so it tracks the viewport symmetrically
  // in both directions.
  useEffect(() => {
    let parentWin: Window;
    try { parentWin = window.parent; } catch { return; }
    const onResize = () => { applySavedPosition(); applySavedWidth(); };
    try {
      parentWin.addEventListener("resize", onResize);
      return () => parentWin.removeEventListener("resize", onResize);
    } catch {
      return;
    }
  }, []);

  // --- Drag-to-move. Listens on THIS document (reliably receives the
  // whole gesture, since the box tracks the cursor) plus the parent's, as
  // a safety net / fast-drag catch-all — safe to mix sources since we use
  // screen coordinates throughout. ---------------------------------------
  const dragMeta = useRef<{
    el: HTMLElement; origLeft: number; origTop: number; w: number; h: number; vw: number; vh: number;
    startX: number; startY: number;
    raf: number | null; dx: number; dy: number; moved: boolean;
    cleanup: () => void;
  } | null>(null);

  function startDrag(e: React.MouseEvent | React.TouchEvent, onTap: () => void) {
    if ((e.target as HTMLElement).closest("button")) return;
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

  // --- Resize (bottom-right handle, width only — height follows content
  // naturally via ResizeObserver, and the video keeps its 16:9 ratio via
  // the #video-shell padding trick regardless of width). Same
  // screen-coordinate + dual-document-listener approach as drag. --------
  const resizeMeta = useRef<{
    startX: number; startWidth: number; vw: number;
    cleanup: () => void;
  } | null>(null);

  function startResize(e: React.MouseEvent | React.TouchEvent) {
    e.stopPropagation(); // don't let this bubble into the header's drag handler
    const el = getContainer();
    if (!el) return;
    const start = pointFromEvent(e.nativeEvent as MouseEvent | TouchEvent);
    if (!start) return;
    const startWidth = el.offsetWidth;
    let vw = 9999;
    try { vw = window.parent.innerWidth; } catch { }

    const onMove = (ev: MouseEvent | TouchEvent) => {
      const m = resizeMeta.current;
      if (!m) return;
      const p = pointFromEvent(ev);
      if (!p) return;
      if ("touches" in ev) ev.preventDefault();
      applyWidth(clampWidth(m.startWidth + (p.x - m.startX), m.vw));
    };
    const finishResize = () => {
      const m = resizeMeta.current;
      if (!m) return;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("touchmove", onMove);
      document.removeEventListener("mouseup", finishResize);
      document.removeEventListener("touchend", finishResize);
      try {
        window.parent.document.removeEventListener("mousemove", onMove);
        window.parent.document.removeEventListener("touchmove", onMove);
        window.parent.document.removeEventListener("mouseup", finishResize);
        window.parent.document.removeEventListener("touchend", finishResize);
      } catch { }
      const el2 = getContainer();
      if (el2) saveWidth(el2.offsetWidth);
      resizeMeta.current = null;
    };

    resizeMeta.current = { startX: start.x, startWidth, vw, cleanup: finishResize };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("touchmove", onMove, { passive: false });
    document.addEventListener("mouseup", finishResize);
    document.addEventListener("touchend", finishResize);
    try {
      window.parent.document.addEventListener("mousemove", onMove);
      window.parent.document.addEventListener("touchmove", onMove, { passive: false });
      window.parent.document.addEventListener("mouseup", finishResize);
      window.parent.document.addEventListener("touchend", finishResize);
    } catch { }
  }
const videoShellRef = useRef<HTMLDivElement>(null);

// Keep --video-height in sync with the video's actual rendered height
// (which changes with panel width, since it's a 16:9 box) so the lyrics
// panel can match it exactly via CSS, even before any lyrics have loaded.
useEffect(() => {
  if (!videoShellRef.current) return;
  const el = videoShellRef.current;
  const report = () => {
    if (rootRef.current) rootRef.current.style.setProperty("--video-height", `${el.offsetHeight}px`);
  };
  const observer = new ResizeObserver(report);
  observer.observe(el);
  report();
  return () => observer.disconnect();
}, []);
  // Belt-and-suspenders cleanup if this component unmounts mid-gesture.
  useEffect(() => {
    return () => { dragMeta.current?.cleanup(); resizeMeta.current?.cleanup(); };
  }, []);

  if (!queue.length) return null;
  const track = queue[currentTrackIdx];
  const [lyricsCandidates, setLyricsCandidates] = useState<LyricsCandidate[] | undefined>(undefined); // undefined = loading
  const [selectedCandidateIdx, setSelectedCandidateIdx] = useState(0);
  const lyricsListRef = useRef<HTMLDivElement>(null);

  // Fetch all candidates (lines included) once per track change.
  useEffect(() => {
    const track = queue[currentTrackIdx];

    setLyricsCandidates(undefined);
    setSelectedCandidateIdx(0);
    if (!track) return;
    let cancelled = false;
    const { artist: parsedArtist } = splitArtistTitle(track.title);
    fetchLyricsCached({ ...track, artist: parsedArtist ?? undefined }).then((candidates) => {
      if (!cancelled) setLyricsCandidates(candidates);
    });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTrackIdx, queue]);

  const selectedCandidate = lyricsCandidates?.[selectedCandidateIdx];
  const activeLineIdx = selectedCandidate ? currentLineIndex(selectedCandidate.lines, curTime) : -1;

  useEffect(() => {
    if (!lyricsListRef.current || activeLineIdx < 0) return;
    const container = lyricsListRef.current;
    const activeEl = container.querySelector(`[data-line-idx="${activeLineIdx}"]`) as HTMLElement | null;
    if (!activeEl) return;
    const containerRect = container.getBoundingClientRect();
    const activeRect = activeEl.getBoundingClientRect();
    const alreadyVisible = activeRect.top >= containerRect.top && activeRect.bottom <= containerRect.bottom;
    if (!alreadyVisible) activeEl.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeLineIdx]);
  return (
    <ConfigProvider
      theme={{
        algorithm: antdTheme.darkAlgorithm,
        token: { colorPrimary: "#02ab21", colorBgContainer: "#161616", borderRadius: 10 },
      }}
    >
      <div ref={rootRef}>
        <div id="pill-wrap" style={{ display: expanded ? "none" : "block" }}>
          <div
            id="pill"
            ref={pillNodeRef}
            title="Drag to move · tap to expand"
            onMouseDown={(e) => startDrag(e, () => toggleExpand(true))}
            onTouchStart={(e) => startDrag(e, () => toggleExpand(true))}
          >
            <span className={`pill-eq${playing ? " pill-eq-playing" : ""}`} aria-hidden="true">
              <span className="pill-eq-bar" />
              <span className="pill-eq-bar" />
              <span className="pill-eq-bar" />
              <span className="pill-eq-bar" />
            </span>
            <Typography.Text id="pill-title" ellipsis style={{ flex: 1, color: "#e6e6e6", fontSize: 12, fontWeight: 600 }}>
              {track.title}
            </Typography.Text>
            <span className="spin-disk-wrap spin-disk-sm">
              <span
                className={`spin-disk${playing ? " spin-disk-playing" : ""}`}
                style={track.thumbnail_url ? { backgroundImage: `url(${track.thumbnail_url})` } : undefined}
              />
              <Button
                type="text" shape="circle" size="small"
                style={{ color: "#02ab21", position: "relative", zIndex: 1 }}
                icon={playing ? <PauseCircleFilled /> : <PlayCircleFilled />}
                onClick={(e) => { e.stopPropagation(); togglePlayPause(); }}
              />
            </span>
          </div>
        </div>

        <div id="panel" style={{ display: expanded ? "block" : "none" }}>
          <div
            className="panel-header"
            ref={headerNodeRef}
            title="Drag to move · tap to collapse"
            onMouseDown={(e) => startDrag(e, () => toggleExpand(false))}
            onTouchStart={(e) => startDrag(e, () => toggleExpand(false))}
          >
            <span className="drag-grip" onDoubleClick={(e) => { e.stopPropagation(); resetPos(); }}>⠿</span>
            <span className="panel-title">Now Playing</span>
            <Button
              type="text" shape="circle" size="small" style={{ color: "#9a9a9a" }}
              icon={<CloseOutlined />}
              onClick={(e) => { e.stopPropagation(); closeWidget(); }}
              title="Close"
            />
          </div>

          {showUnmute && <div id="unmute-banner" onClick={unmuteNow}>Sound off — tap to unmute</div>}

          <div id="view-toggle-row">
            <Segmented
              size="small"
              value={view}
              onChange={(v) => setView(v as View)}
              options={[
                { value: "video", label: <Tooltip title="Video"><VideoCameraOutlined /></Tooltip> },
                { value: "lyrics", label: <Tooltip title="Lyrics"><FileTextOutlined /></Tooltip> },
              ]}
            />
          </div>

          {/* #video-shell (and the YT player inside it) is never
              unmounted — only hidden via display:none — so switching to
              the lyrics view never interrupts playback. */}
          <div ref={videoShellRef} id="video-shell" style={{ display: view === "video" ? "block" : "none" }}>
            <div id="yt-main" />
          </div>

          {view === "lyrics" && (
            <div className="lyrics-panel">
              {lyricsCandidates && lyricsCandidates.length > 1 && (
                <Select
                  size="small"
                  className="lyrics-candidate-select"
                  value={selectedCandidateIdx}
                  onChange={(idx) => setSelectedCandidateIdx(idx)}
                  options={lyricsCandidates.map((c, idx) => ({
                    value: idx,
                    label: c.artistName ? `${c.trackName} — ${c.artistName}` : c.trackName,
                  }))}
                />
              )}

              {lyricsCandidates === undefined && (
                <div className="lyrics-empty"><p>Loading lyrics…</p></div>
              )}

              {lyricsCandidates && lyricsCandidates.length === 0 && (
                <div className="lyrics-empty">
                  <p>Lyrics aren't shown in-app to respect copyright.</p>
                  <p className="lyrics-track-title">{track.title}</p>
                  <div className="lyrics-links">
                    <a href={`https://genius.com/search?q=${encodeURIComponent(track.title)}`} target="_blank" rel="noreferrer">
                      Search Genius ↗
                    </a>
                    <a href={`https://www.musixmatch.com/search?query=${encodeURIComponent(track.title)}`} target="_blank" rel="noreferrer">
                      Search Musixmatch ↗
                    </a>
                  </div>
                </div>
              )}

              {selectedCandidate && selectedCandidate.lines.length > 0 && (
                <div className="lyrics-synced" ref={lyricsListRef}>
                  {selectedCandidate.lines.map((line, i) => (
                    <div
                      key={i}
                      data-line-idx={i}
                      className={`lyrics-line${i === activeLineIdx ? " lyrics-line-active" : ""}`}
                      onClick={() => { const p = playerMainRef.current; if (p?.seekTo) p.seekTo(line.time, true); }}
                    >
                      {line.text}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <Typography.Text ellipsis style={{ display: "block", marginTop: 8, fontWeight: 600, fontSize: 13.5, color: "#e6e6e6" }}>
            {track.title}
          </Typography.Text>

          <div id="progress-row">
            <span>{formatTime(curTime)}</span>
            <div id="progress-bar" onClick={seek}>
              <div id="progress-fill" style={{ width: duration ? `${(curTime / duration) * 100}%` : "0%" }} />
            </div>
            <span>{formatTime(duration)}</span>
          </div>

          <div id="controls-row">
            <Button shape="circle" icon={<StepBackwardOutlined />} onClick={() => advance(-1)} />
            <span className="spin-disk-wrap spin-disk-lg">
              <span
                className={`spin-disk${playing ? " spin-disk-playing" : ""}`}
                style={track.thumbnail_url ? { backgroundImage: `url(${track.thumbnail_url})` } : undefined}
              />
              <Button
                type="primary" shape="circle" size="large"
                style={{ position: "relative", zIndex: 1 }}
                icon={playing ? <PauseCircleFilled /> : <PlayCircleFilled />}
                onClick={togglePlayPause}
              />
            </span>
            <Button shape="circle" icon={<StepForwardOutlined />} onClick={() => advance(1)} />
          </div>

          <div id="mode-row">
            <Segmented
              size="small"
              value={mode}
              onChange={(v) => setMode(v as Mode)}
              options={[
                { value: "normal", label: <Tooltip title="Normal"><UnorderedListOutlined /></Tooltip> },
                { value: "shuffle", label: <Tooltip title="Shuffle"><SwapOutlined /></Tooltip> },
                { value: "repeatTrack", label: <Tooltip title="Repeat one"><RedoOutlined /></Tooltip> },
                { value: "repeatAll", label: <Tooltip title="Repeat all"><RetweetOutlined /></Tooltip> },
              ]}
            />
            {mode === "shuffle" && (
              <Tooltip title="Shuffle again">
                <Button
                  type="text" size="small" icon={<SwapOutlined />}
                  onClick={() => setOrder(shuffleQueue(queueRef.current.length))}
                  style={{ marginLeft: 6, color: "#02ab21" }}
                />
              </Tooltip>
            )}
          </div>

          <div id="volume-row">
            <SoundOutlined style={{ color: "#9a9a9a" }} />
            <Slider
              className="volume-slider"
              min={0} max={100} value={volume}
              onChange={(v) => setVolume(v as number)}
              tooltip={{ formatter: (v) => `${v}%` }}
            />
          </div>

          <QueueList
            order={order}
            queue={queue}
            currentTrackIdx={currentTrackIdx}
            onReorder={setOrder}
            onPlay={playTrackIdx}
          />

          <div
            className="resize-handle"
            onMouseDown={startResize}
            onTouchStart={startResize}
            title="Drag to resize"
          />
        </div>

        <div id="yt-preload" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", opacity: 0, pointerEvents: "none" }} />
      </div>
    </ConfigProvider>
  );
}