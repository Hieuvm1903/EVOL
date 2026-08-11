import React, { useEffect, useRef, useState } from "react";
import { ConfigProvider, theme as antdTheme, Segmented, Button, Slider, Typography, Tooltip, Select, Input } from "antd";
import {
  StepBackwardOutlined, StepForwardOutlined, PlayCircleFilled, PauseCircleFilled,
  UnorderedListOutlined, SwapOutlined, RedoOutlined, RetweetOutlined, SoundOutlined, CloseOutlined,
  VideoCameraOutlined, FileTextOutlined, SearchOutlined,
} from "@ant-design/icons";
import { Streamlit } from "streamlit-component-lib";
import QueueList from "./QueueList";
import "./NowPlaying.css";
import { splitArtistTitle } from "./utils";
import { currentLineIndex, fetchLyrics, fetchLyricsCached, LyricsCandidate } from "./lyricsProvider";

export type Track = { title: string; video_id: string; thumbnail_url?: string };
type Mode = "normal" | "shuffle" | "repeatTrack" | "repeatAll";
type View = "video" | "lyrics";

const MODE_MAP: Record<string, Mode> = { Normal: "normal", Shuffle: "shuffle", "Repeat All": "repeatAll" };
const POS_KEY = "evol_player_pos";
const EXPANDED_KEY = "evol_player_expanded";
const DRAG_THRESHOLD = 4;
const EDGE_MARGIN = 8;
const PANEL_WIDTH = 300;

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
  const [lyricsCandidates, setLyricsCandidates] = useState<LyricsCandidate[] | undefined>(undefined);
  const [selectedCandidateIdx, setSelectedCandidateIdx] = useState(0);
  const [manualTitle, setManualTitle] = useState("");
  const [manualArtist, setManualArtist] = useState("");
  const [manualSearching, setManualSearching] = useState(false);

  const autoCandidatesRef = useRef<LyricsCandidate[]>([]);
  const playerMainRef = useRef<any>(null);
  const playerPreloadRef = useRef<any>(null);
  const preloadReady = useRef(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const pillNodeRef = useRef<HTMLDivElement>(null);
  const headerNodeRef = useRef<HTMLDivElement>(null);
  const lyricsViewportRef = useRef<HTMLDivElement>(null);
  const lyricsLinesRef = useRef<HTMLDivElement>(null);
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
    let lastHeight = 0;
    let raf: number | null = null;
    const report = () => {
      raf = null;
      // getBoundingClientRect is sub-pixel accurate, unlike scrollHeight
      // (integer, rounds down) — rounding scrollHeight down was clipping
      // the panel's bottom border by a fraction of a pixel in some layouts
      // (flex children can produce fractional heights), which is what made
      // the bottom outline disappear specifically in lyrics mode. +2px
      // buffer for extra safety margin against any remaining rounding.
      const h = Math.ceil(el.getBoundingClientRect().height) + 2;
      if (h !== lastHeight) { lastHeight = h; Streamlit.setFrameHeight(h); }
    };
    const scheduleReport = () => { if (!raf) raf = requestAnimationFrame(report); };
    const observer = new ResizeObserver(scheduleReport);
    observer.observe(el);
    scheduleReport();
    return () => { observer.disconnect(); if (raf) cancelAnimationFrame(raf); };
  }, []);
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

  useEffect(() => {
    applySavedPosition();
  }, []);

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

  const dragMeta = useRef<{
    el: HTMLElement; origLeft: number; origTop: number; w: number; h: number; vw: number; vh: number;
    startX: number; startY: number;
    raf: number | null; dx: number; dy: number; moved: boolean;
    cleanup: () => void;
  } | null>(null);

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

  // --- Lyrics: auto-fetch candidates whenever the current track changes -
  // Guarded by video_id, not just "did this effect fire" — `queue` is a
  // prop Streamlit re-sends as a fresh array on every rerun, even when its
  // content is unchanged, so depending on effect-firing alone would wipe
  // lyrics state (including manual search results) on any incidental
  // re-render, not just an actual track change. That was the "lyric state
  // lost when switching tabs" bug — switching view isn't the real trigger,
  // but any rerun that happened to land while on the lyrics tab looked
  // exactly like it.

  const lastLyricsFetchKeyRef = useRef<string>("");

  useEffect(() => {
    const track = queue[currentTrackIdx];
    const key = track ? track.video_id : "";
    if (key === lastLyricsFetchKeyRef.current) return;

    setLyricsCandidates(undefined);
    setSelectedCandidateIdx(0);
    autoCandidatesRef.current = [];
    if (!track) {
      lastLyricsFetchKeyRef.current = key;
      setManualTitle("");
      setManualArtist("");
      return;
    }

    let cancelled = false;
    const { artist: parsedArtist, title: parsedTitle } = splitArtistTitle(track.title);
    setManualTitle(parsedTitle);
    setManualArtist(parsedArtist ?? "");

    fetchLyricsCached({ ...track, artist: parsedArtist ?? undefined }).then((candidates) => {
      if (cancelled) return; // a rerun cancelled this one — don't mark `key`
      // as fetched, so the next effect run (even for
      // the same video_id) is free to retry instead
      // of silently skipping forever.
      lastLyricsFetchKeyRef.current = key; // only commit on real completion
      autoCandidatesRef.current = candidates;
      setLyricsCandidates(candidates);
    });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTrackIdx, queue]);

  // --- Manual search: user-provided title/artist, bypasses the cache and
  // the auto title-parsing entirely. -------------------------------------
  async function runManualSearch() {
    const title = manualTitle.trim();
    if (!title) return;
    const track = queue[currentTrackIdx];
    setManualSearching(true);
    try {
      const results = await fetchLyrics({
        title,
        artist: manualArtist.trim() || undefined,
        video_id: track?.video_id ?? "manual-search",
      });
      // Manual results go first — auto-detected candidates (if any) stay
      // available right after, as a fallback the user can still pick.
      setLyricsCandidates([...results, ...autoCandidatesRef.current]);
      setSelectedCandidateIdx(0);
    } finally {
      setManualSearching(false);
    }
  }

  const selectedCandidate = lyricsCandidates?.[selectedCandidateIdx];
  const activeLineIdx = selectedCandidate ? currentLineIndex(selectedCandidate.lines, curTime) : -1;

  function recenterLyrics() {
    const viewport = lyricsViewportRef.current;
    const linesEl = lyricsLinesRef.current;
    if (!viewport || !linesEl) return;
    const idx = activeLineIdx >= 0 ? activeLineIdx : 0;
    const activeEl = linesEl.querySelector(`[data-line-idx="${idx}"]`) as HTMLElement | null;
    if (!activeEl) { linesEl.style.transform = "translateY(0px)"; return; }
    const viewportHeight = viewport.offsetHeight;
    const offsetY = viewportHeight / 2 - (activeEl.offsetTop + activeEl.offsetHeight / 2);
    linesEl.style.transform = `translateY(${offsetY}px)`;
  }

  useEffect(() => {
    recenterLyrics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeLineIdx, selectedCandidate]);

  useEffect(() => {
    return () => { dragMeta.current?.cleanup(); };
  }, []);

  if (!queue.length) return null;
  const track = queue[currentTrackIdx];

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
            <div
              className="header-view-toggle"
              onMouseDown={(e) => e.stopPropagation()}
              onTouchStart={(e) => e.stopPropagation()}
            >
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
            <Button
              type="text" shape="circle" size="small" style={{ color: "#9a9a9a" }}
              icon={<CloseOutlined />}
              onClick={(e) => { e.stopPropagation(); closeWidget(); }}
              title="Close"
            />
          </div>

          {showUnmute && <div id="unmute-banner" onClick={unmuteNow}>Sound off — tap to unmute</div>}

          <div id="video-shell" style={{ display: view === "video" ? "block" : "none" }}>
            <div id="yt-main" />
          </div>

          <div className="lyrics-panel" style={{ display: view === "lyrics" ? "flex" : "none" }}>
            <div className="lyrics-search-row">
              <Input
                size="small"
                placeholder="Song name"
                value={manualTitle}
                onChange={(e) => setManualTitle(e.target.value)}
                onPressEnter={runManualSearch}
              />
              <Input
                size="small"
                placeholder="Artist (optional)"
                value={manualArtist}
                onChange={(e) => setManualArtist(e.target.value)}
                onPressEnter={runManualSearch}
              />
              <Button
                size="small"
                icon={<SearchOutlined />}
                loading={manualSearching}
                onClick={runManualSearch}
                disabled={!manualTitle.trim()}
              />
            </div>

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
              <div className="lyrics-empty">
                <div className="lyrics-spinner" />
                <p>Loading lyrics…</p>
              </div>
            )}

            {lyricsCandidates && lyricsCandidates.length === 0 && (
              <div className="lyrics-empty">
                <FileTextOutlined style={{ fontSize: 22, color: "#3a3a3a", marginBottom: 8 }} />
                <p>No lyrics found.</p>
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
              <div className="lyrics-viewport" ref={lyricsViewportRef}>
                <div className="lyrics-lines" ref={lyricsLinesRef}>
                  {selectedCandidate.lines.map((line, i) => {
                    const distance = activeLineIdx < 0 ? 0 : Math.abs(i - activeLineIdx);
                    return (
                      <div
                        key={i}
                        data-line-idx={i}
                        data-time={formatTime(line.time)}
                        className={`lyrics-line${i === activeLineIdx ? " lyrics-line-active" : ""}`}
                        style={{ opacity: Math.max(1 - distance * 0.18, 0.28) }}
                        onClick={() => { const p = playerMainRef.current; if (p?.seekTo) p.seekTo(line.time, true); }}
                      >
                        {line.text}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>


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
        </div>

        <div id="yt-preload" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", opacity: 0, pointerEvents: "none" }} />
      </div>
    </ConfigProvider>
  );
}