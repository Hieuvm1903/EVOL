import React, { useEffect, useRef, useState } from "react";
import { ConfigProvider, theme as antdTheme, Segmented, Button, Slider, Typography, Tooltip } from "antd";
import {
  StepBackwardOutlined, StepForwardOutlined, PlayCircleFilled, PauseCircleFilled,
  UnorderedListOutlined, SwapOutlined, RedoOutlined, RetweetOutlined, SoundOutlined, CloseOutlined,
} from "@ant-design/icons";
import Draggable, { DraggableCore, DraggableEventHandler } from "react-draggable";
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

  const modeRef = useRef(mode);
  useEffect(() => { modeRef.current = mode; }, [mode]);
  const orderRef = useRef(order);
  useEffect(() => { orderRef.current = order; }, [order]);
  const currentTrackIdxRef = useRef(currentTrackIdx);
  useEffect(() => { currentTrackIdxRef.current = currentTrackIdx; }, [currentTrackIdx]);
  const queueRef = useRef(queue);
  useEffect(() => { queueRef.current = queue; }, [queue]);

  function playTrackIdx(trackIdx: number) {
    const track = queueRef.current[trackIdx];
    if (!track) return;
    setCurrentTrackIdx(trackIdx);
    try { playerMainRef.current?.loadVideoById(track.video_id); } catch {}
    setTimeout(cuePreloadNext, 0);
  }

  function cuePreloadNext() {
    if (!preloadReady.current) return;
    const next = pickNextTrackIdx(orderRef.current, modeRef.current, currentTrackIdxRef.current);
    if (next === null) return;
    try { playerPreloadRef.current.cueVideoById(queueRef.current[next].video_id); } catch {}
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

  // --- Load YouTube IFrame API once, create players. #yt-main is now
  // *always* mounted (see JSX below — no more conditional rendering of
  // the panel), so this player is created exactly once for the whole
  // component's lifetime and survives collapse/expand. -------------------
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
              try { if (playerMainRef.current.isMuted()) setShowUnmute(true); } catch {}
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
    setOrder(queue.map((_, i) => i));
    if (isFirstRun || !queue.length) return;
    setCurrentTrackIdx(0);
    if (playerMainRef.current?.loadVideoById) {
      playerMainRef.current.loadVideoById(queue[0].video_id);
    }
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
    if (p?.getDuration) { try { p.seekTo(frac * p.getDuration(), true); } catch {} }
  }

  function setVolume(v: number) {
    setVolumeState(v);
    try { playerMainRef.current?.setVolume(v); } catch {}
  }

  function unmuteNow() {
    try { playerMainRef.current?.unMute(); } catch {}
    setShowUnmute(false);
  }

  function closeWidget() {
    try { playerMainRef.current?.stopVideo?.(); } catch {}
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
      } catch {}
    }, 500);
    return () => clearInterval(id);
  }, []);

  function toggleExpand(v: boolean) {
    setExpanded(v);
    try { localStorage.setItem(EXPANDED_KEY, v ? "1" : "0"); } catch {}
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

  // --- Drag-to-move, via react-draggable's DraggableCore. DraggableCore
  // deliberately does NOT move the DOM node itself — it just reports
  // pointer deltas through callbacks — which is exactly what we want,
  // since the thing that actually needs to move lives in the *parent*
  // document (the Streamlit container), not inside this iframe. -------
  const dragMeta = useRef<{
    el: HTMLElement; origLeft: number; origTop: number; w: number; h: number; vw: number; vh: number;
    raf: number | null; dx: number; dy: number;
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
    try { window.parent.localStorage.setItem(POS_KEY, JSON.stringify({ left, top })); } catch {}
  }
  function resetPos() {
    const el = getContainer();
    if (el) { el.style.transform = ""; el.style.left = ""; el.style.top = ""; el.style.right = ""; }
    try { window.parent.localStorage.removeItem(POS_KEY); } catch {}
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
    } catch {}
  }, []);

  const handleDragStart: DraggableEventHandler = () => {
    const el = getContainer();
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    let vw = 9999, vh = 9999;
    try { vw = window.parent.innerWidth; vh = window.parent.innerHeight; } catch {}
    dragMeta.current = {
      el, origLeft: rect.left, origTop: rect.top, w: rect.width, h: rect.height, vw, vh,
      raf: null, dx: 0, dy: 0,
    };
    try { el.classList.add("evol-dragging"); } catch {}
    try { window.parent.document.body.style.userSelect = "none"; } catch {}
  };

  const handleDragMove: DraggableEventHandler = (_e, data) => {
    const meta = dragMeta.current;
    if (!meta) return;
    const minDx = 8 - meta.origLeft, maxDx = Math.max(minDx, meta.vw - meta.w - 8 - meta.origLeft);
    const minDy = 8 - meta.origTop, maxDy = Math.max(minDy, meta.vh - meta.h - 8 - meta.origTop);
    meta.dx = Math.min(Math.max(data.x, minDx), maxDx);
    meta.dy = Math.min(Math.max(data.y, minDy), maxDy);
    if (!meta.raf) {
      meta.raf = requestAnimationFrame(() => {
        if (!dragMeta.current) return;
        dragMeta.current.raf = null;
        dragMeta.current.el.style.transform = `translate3d(${dragMeta.current.dx}px, ${dragMeta.current.dy}px, 0)`;
      });
    }
  };

  function handleDragStop() {
    const meta = dragMeta.current;
    if (!meta) { lastDragMoved.current = false; return; }
    if (meta.raf) cancelAnimationFrame(meta.raf);
    try { meta.el.classList.remove("evol-dragging"); } catch {}
    try { window.parent.document.body.style.userSelect = ""; } catch {}
    const moved = Math.abs(meta.dx) > DRAG_THRESHOLD || Math.abs(meta.dy) > DRAG_THRESHOLD;
    if (moved) {
      applyPos(meta.origLeft + meta.dx, meta.origTop + meta.dy);
      savePos(meta.origLeft + meta.dx, meta.origTop + meta.dy);
    }
    dragMeta.current = null;
    lastDragMoved.current = moved;
  }

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
        <DraggableCore
          nodeRef={pillNodeRef}
          cancel="button"
          onStart={handleDragStart}
          onDrag={handleDragMove}
          onStop={() => { handleDragStop(); if (!lastDragMoved.current) toggleExpand(true); }}
        >
          <div
            id="pill"
            ref={pillNodeRef}
            title="Drag to move · tap to expand"
            style={{ display: expanded ? "none" : "flex" }}
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
        </DraggableCore>

        <div id="panel" style={{ display: expanded ? "block" : "none" }}>
          <DraggableCore
            nodeRef={headerNodeRef}
            cancel="button"
            onStart={handleDragStart}
            onDrag={handleDragMove}
            onStop={() => { handleDragStop(); if (!lastDragMoved.current) toggleExpand(false); }}
          >
            <div className="panel-header" ref={headerNodeRef} title="Drag to move · tap to collapse">
              <span className="drag-grip" onDoubleClick={(e) => { e.stopPropagation(); resetPos(); }}>⠿</span>
              <span className="panel-title">Now Playing</span>
              <Button
                type="text" shape="circle" size="small" style={{ color: "#9a9a9a" }}
                icon={<CloseOutlined />}
                onClick={(e) => { e.stopPropagation(); closeWidget(); }}
                title="Close"
              />
            </div>
          </DraggableCore>

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