import React, { useEffect, useRef, useState } from "react";
import { ConfigProvider, theme as antdTheme, Segmented, Button, Slider, Typography, Tooltip } from "antd";
import {
  StepBackwardOutlined, StepForwardOutlined, PlayCircleFilled, PauseCircleFilled,
  UnorderedListOutlined, SwapOutlined, RedoOutlined, RetweetOutlined, SoundOutlined, CloseOutlined,
} from "@ant-design/icons";
import { Streamlit } from "streamlit-component-lib";
import QueueList from "./QueueList";
import "./NowPlaying.css";

export type Track = { title: string; video_id: string; thumbnail_url?: string };
type Mode = "normal" | "shuffle" | "repeatTrack" | "repeatAll";

const MODE_MAP: Record<string, Mode> = { Normal: "normal", Shuffle: "shuffle", "Repeat All": "repeatAll" };
const POS_KEY = "evol_player_pos";
const EXPANDED_KEY = "evol_player_expanded";
const DRAG_THRESHOLD = 4;

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

export default function NowPlaying({ queue, initialMode }: { queue: Track[]; initialMode: string }) {
  const [mode, setMode] = useState<Mode>(MODE_MAP[initialMode] || "normal");
  const [order, setOrder] = useState<number[]>(() => queue.map((_, i) => i));
  const [currentTrackIdx, setCurrentTrackIdx] = useState(0);
  const [expanded, setExpanded] = useState<boolean>(() => {
    try { return localStorage.getItem(EXPANDED_KEY) === "1"; } catch { return false; }
  });
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
  // mounted (see JSX below — no conditional rendering of the panel), so
  // this player is created exactly once for the whole component's
  // lifetime and survives collapse/expand. -------------------------------
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

  // Single source of truth for reacting to the queue prop changing (e.g.
  // the user picked a different playlist in the Streamlit app). Dedup'd
  // against lastVideoIds so it's a no-op on plain re-renders.
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

  // --- Drag-to-move ---------------------------------------------------
  //
  // The element that actually needs to move (.st-key-now_playing_drawer)
  // lives in the *parent* document, not inside this component's iframe.
  // A drag library bound to this iframe's own document (e.g.
  // react-draggable's DraggableCore) stops receiving mousemove/mouseup
  // the instant the cursor leaves the iframe's small bounding box —
  // which is almost immediately on any real drag — freezing the widget
  // mid-drag and leaving cleanup (the dragging class, body user-select)
  // stuck if the mouse is released outside the iframe.
  //
  // So instead: track the gesture with our own state, but attach the
  // move/up listeners directly to window.parent, where they'll keep
  // firing for the whole gesture regardless of where the cursor is on
  // the page. Supports both mouse and single-touch.
  const dragMeta = useRef<{
    el: HTMLElement; origLeft: number; origTop: number; w: number; h: number; vw: number; vh: number;
    startX: number; startY: number;
    raf: number | null; dx: number; dy: number; moved: boolean;
    cleanup: () => void;
  } | null>(null);

  function applyPos(left: number, top: number) {
    const el = getContainer();
    if (!el) return;
    el.style.right = "auto";
    el.style.transform = "";
    el.style.left = `${left}px`;
    el.style.top = `${top}px`;
  }
  function savePos(left: number, top: number) {
    try { window.parent.localStorage.setItem(POS_KEY, JSON.stringify({ left, top })); } catch { }
  }
  function resetPos() {
    const el = getContainer();
    if (el) { el.style.transform = ""; el.style.left = ""; el.style.top = ""; el.style.right = ""; }
    try { window.parent.localStorage.removeItem(POS_KEY); } catch { }
  }
  useEffect(() => {
    try {
      const raw = window.parent.localStorage.getItem(POS_KEY);
      if (!raw) return;
      const pos = JSON.parse(raw);
      const el = getContainer();
      const w = el?.offsetWidth ?? 300, h = el?.offsetHeight ?? 60;
      const vw = window.parent.innerWidth, vh = window.parent.innerHeight;
      applyPos(
        Math.min(Math.max(pos.left, 8), Math.max(8, vw - w - 8)),
        Math.min(Math.max(pos.top, 8), Math.max(8, vh - h - 8))
      );
    } catch { }
  }, []);
// Re-clamp whenever the parent viewport resizes — e.g. opening/closing
// DevTools, which shrinks/grows the actual page viewport without any
// drag happening. Without this, a position baked in as raw px at drag-end
// has no relationship to the viewport anymore, so it can end up
// off-screen or just visually "wrong" the moment the viewport changes.
useEffect(() => {
  let parentWin: Window;
  try { parentWin = window.parent; } catch { return; }

  function reclamp() {
    const el = getContainer();
    if (!el) return;
    // Only touch elements the user has actually dragged (i.e. left/top
    // were explicitly set) — leave the default CSS-pinned corner alone
    // otherwise, since that one already tracks the viewport via CSS.
    if (!el.style.left || el.style.left === "") return;
    const w = el.offsetWidth, h = el.offsetHeight;
    const vw = parentWin.innerWidth, vh = parentWin.innerHeight;
    const curLeft = parseFloat(el.style.left) || 0;
    const curTop = parseFloat(el.style.top) || 0;
    const clampedLeft = Math.min(Math.max(curLeft, 8), Math.max(8, vw - w - 8));
    const clampedTop = Math.min(Math.max(curTop, 8), Math.max(8, vh - h - 8));
    if (clampedLeft !== curLeft || clampedTop !== curTop) {
      el.style.left = `${clampedLeft}px`;
      el.style.top = `${clampedTop}px`;
      savePos(clampedLeft, clampedTop);
    }
  }

  try {
    parentWin.addEventListener("resize", reclamp);
    return () => parentWin.removeEventListener("resize", reclamp);
  } catch {
    return;
  }
}, []);
  // Track the raw mouse position purely within THIS document (the
  // component's own iframe) — that's the document mousemove/mouseup
  // reliably keeps firing on for the whole gesture, since the widget
  // follows the cursor and so the cursor stays over the iframe almost the
  // entire time. (Listening on window.parent instead only ever receives
  // events once the cursor leaves the iframe's box entirely — which barely
  // happens while tracking is working — and mixing a local-frame start
  // point with parent-frame move points corrupts the delta. That combo was
  // the actual cause of both the "only up/down" jank and positions not
  // sticking across collapse/expand.)
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
      const rawDx = p.x - m.startX;
      const rawDy = p.y - m.startY;
      const minDx = 8 - m.origLeft, maxDx = Math.max(minDx, m.vw - m.w - 8 - m.origLeft);
      const minDy = 8 - m.origTop, maxDy = Math.max(minDy, m.vh - m.h - 8 - m.origTop);
      m.dx = Math.min(Math.max(rawDx, minDx), maxDx);
      m.dy = Math.min(Math.max(rawDy, minDy), maxDy);
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
        applyPos(m.origLeft + m.dx, m.origTop + m.dy);
        savePos(m.origLeft + m.dx, m.origTop + m.dy);
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

    // Local document — primary source while the cursor is over the widget.
    document.addEventListener("mousemove", onMove);
    document.addEventListener("touchmove", onMove, { passive: false });
    document.addEventListener("mouseup", finishDrag);
    document.addEventListener("touchend", finishDrag);

    // Parent document too — now safe to use as a real (not just cleanup)
    // source since screenX/screenY don't care which frame fired them. This
    // covers fast drags where the cursor briefly outruns the widget and
    // ends up over the parent page for a frame or two.
    try {
      window.parent.document.addEventListener("mousemove", onMove);
      window.parent.document.addEventListener("touchmove", onMove, { passive: false });
      window.parent.document.addEventListener("mouseup", finishDrag);
      window.parent.document.addEventListener("touchend", finishDrag);
    } catch { }
  }

  // Belt-and-suspenders: if this component unmounts mid-drag (e.g. the
  // queue empties out), make sure listeners don't linger.
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
        {/* Both pill and panel stay mounted at all times — only CSS
            `display` toggles which is visible. That's what keeps #yt-main
            (and the YT player attached to it) alive across collapse. */}
       <div
            id="pill"
            ref={pillNodeRef}
            style={{ display: expanded ? "none" : "flex" }}
            title="Drag to move · tap to expand"
            onMouseDown={(e) => startDrag(e, () => toggleExpand(true))}
            onTouchStart={(e) => startDrag(e, () => toggleExpand(true))}
          >
            <img id="pill-thumb" src={track.thumbnail_url || ""} alt="" />
            <Typography.Text id="pill-title" ellipsis style={{ flex: 1, color: "#e6e6e6", fontSize: 12, fontWeight: 600 }}>
              {track.title}
            </Typography.Text>
            <Button
              type="text" shape="circle" size="small" style={{ color: "#02ab21" }}
              icon={playing ? <PauseCircleFilled /> : <PlayCircleFilled />}
              onClick={(e) => { e.stopPropagation(); togglePlayPause(); }}
            />
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

          <div id="video-shell"><div id="yt-main" /></div>

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
            <Button
              type="primary" shape="circle" size="large"
              icon={playing ? <PauseCircleFilled /> : <PlayCircleFilled />}
              onClick={togglePlayPause}
            />
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