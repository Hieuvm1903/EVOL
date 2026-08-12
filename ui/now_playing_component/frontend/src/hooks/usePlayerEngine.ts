import { useEffect, useRef, useState } from "react";
import type { Track, Mode } from "../types";
import { MODE_MAP } from "../constants";
import { pickNextTrackIdx, pickPrevTrackIdx, shuffleQueue } from "../utils/queueOrder";

// Owns the YouTube player instances, playback state, and queue/shuffle
// order. #yt-main is always mounted by the caller (never unmounted, only
// hidden), so the player created here survives collapse/expand and the
// video/lyrics view toggle for the whole component's lifetime.
export function usePlayerEngine(queue: Track[], initialMode: string) {
  const [mode, setMode] = useState<Mode>(MODE_MAP[initialMode] || "normal");
  const [order, setOrder] = useState<number[]>(() => queue.map((_, i) => i));
  const [currentTrackIdx, setCurrentTrackIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [curTime, setCurTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolumeState] = useState(100);
  const [showUnmute, setShowUnmute] = useState(false);

  const playerMainRef = useRef<any>(null);
  const playerPreloadRef = useRef<any>(null);
  const preloadReady = useRef(false);
  const lastVideoIds = useRef<string>("");
  const prevModeRef = useRef(mode);
  const modeRef = useRef(mode);
  useEffect(() => { modeRef.current = mode; }, [mode]);

  const orderRef = useRef(order);
  useEffect(() => { orderRef.current = order; }, [order]);
  const currentTrackIdxRef = useRef(currentTrackIdx);
  useEffect(() => { currentTrackIdxRef.current = currentTrackIdx; }, [currentTrackIdx]);
  const queueRef = useRef(queue);
  useEffect(() => { queueRef.current = queue; }, [queue]);

  useEffect(() => {
    if (mode === "shuffle" && prevModeRef.current !== "shuffle") {
      setOrder(shuffleQueue(queueRef.current.length));
    }
    prevModeRef.current = mode;
  }, [mode]);

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

  // Load YouTube IFrame API once, create players exactly once for the
  // whole component's lifetime.
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

  // Reset when the tracks THEMSELVES change (not on every rerun — page
  // navigation re-invokes this component with the same queue).
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

  function seekToFraction(frac: number) {
    const p = playerMainRef.current;
    if (p?.getDuration) { try { p.seekTo(frac * p.getDuration(), true); } catch { } }
  }

  function seekToTime(seconds: number) {
    const p = playerMainRef.current;
    if (p?.seekTo) { try { p.seekTo(seconds, true); } catch { } }
  }

  function setVolume(v: number) {
    setVolumeState(v);
    try { playerMainRef.current?.setVolume(v); } catch { }
  }

  function unmuteNow() {
    try { playerMainRef.current?.unMute(); } catch { }
    setShowUnmute(false);
  }

  function stopVideo() {
    try { playerMainRef.current?.stopVideo?.(); } catch { }
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

  return {
    mode, setMode, order, setOrder, currentTrackIdx,
    playing, curTime, duration, volume, showUnmute,
    playTrackIdx, advance, togglePlayPause, seekToFraction, seekToTime, setVolume, unmuteNow, stopVideo,
    queueRef,
  };
}