import React, { useRef, useState } from "react";
import { ConfigProvider, theme as antdTheme, Typography } from "antd";
import { Streamlit } from "streamlit-component-lib";

import type { Track, View } from "./types";
import { EXPANDED_KEY } from "./constants";
import { formatTime } from "./utils/time";
import { shuffleQueue } from "./utils/queueOrder";

import { useFrameHeight } from "./hooks/useFrameHeight";
import { useDragPosition } from "./hooks/useDragPosition";
import { usePlayerEngine } from "./hooks/usePlayerEngine";
import { useLyrics } from "./hooks/useLyrics";

import QueueList from "./QueueList";
import PanelHeader from "./components/PanelHeader";
import VideoView from "./components/VideoView";
import LyricsView from "./components/LyricsView";
import TransportControls from "./components/TransportControls";
import ModeRow from "./components/ModeRow";
import VolumeRow from "./components/VolumeRow";

import "./NowPlaying.css";
import PillView from "./components/PillView";

export type { Track };

export default function NowPlaying({ queue, initialMode }: { queue: Track[]; initialMode: string }) {
  const [expanded, setExpanded] = useState<boolean>(() => {
    try { return localStorage.getItem(EXPANDED_KEY) === "1"; } catch { return false; }
  });
  const [view, setView] = useState<View>("video");
  const rootRef = useRef<HTMLDivElement>(null);
  const pillRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);

  const engine = usePlayerEngine(queue, initialMode);
  const { startDrag, resetPos } = useDragPosition();
  const lyrics = useLyrics(queue, engine.currentTrackIdx, engine.curTime);

  useFrameHeight(rootRef);

  function toggleExpand(v: boolean) {
    setExpanded(v);
    try { localStorage.setItem(EXPANDED_KEY, v ? "1" : "0"); } catch { }
  }

  function closeWidget() {
    engine.stopVideo();
    Streamlit.setComponentValue({ action: "close" });
  }

  function handleSeekFromLyrics(time: number) {
    engine.seekToTime(time);
  }

  function handleProgressBarClick(e: React.MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const frac = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
    engine.seekToFraction(frac);
  }

  if (!queue.length) return null;
  const track = queue[engine.currentTrackIdx];

  return (
    <ConfigProvider
      theme={{
        algorithm: antdTheme.darkAlgorithm,
        token: { colorPrimary: "#02ab21", colorBgContainer: "#161616", borderRadius: 10 },
      }}
    >
      <div ref={rootRef}>
        <PillView
          track={track}
          playing={engine.playing}
          pillRef={pillRef}
          visible={!expanded}
          onStartDrag={startDrag}
          onExpand={() => toggleExpand(true)}
          onTogglePlayPause={engine.togglePlayPause}
        />

        <div id="panel" style={{ display: expanded ? "block" : "none" }}>
          <PanelHeader
            headerRef={headerRef}
            view={view}
            onViewChange={setView}
            onStartDrag={startDrag}
            onCollapse={() => toggleExpand(false)}
            onResetPos={resetPos}
            onClose={closeWidget}
          />

          {engine.showUnmute && (
            <div id="unmute-banner" onClick={engine.unmuteNow}>Sound off — tap to unmute</div>
          )}

          <VideoView visible={view === "video"} />
          <LyricsView visible={view === "lyrics"} track={track} lyrics={lyrics} onSeek={handleSeekFromLyrics} />

          <Typography.Text ellipsis style={{ display: "block", marginTop: 8, fontWeight: 600, fontSize: 13.5, color: "#e6e6e6" }}>
            {track.title}
          </Typography.Text>

          <div id="progress-row">
            <span>{formatTime(engine.curTime)}</span>
            <div id="progress-bar" onClick={handleProgressBarClick}>
              <div id="progress-fill" style={{ width: engine.duration ? `${(engine.curTime / engine.duration) * 100}%` : "0%" }} />
            </div>
            <span>{formatTime(engine.duration)}</span>
          </div>

          <TransportControls
            track={track}
            playing={engine.playing}
            onPrev={() => engine.advance(-1)}
            onNext={() => engine.advance(1)}
            onTogglePlayPause={engine.togglePlayPause}
          />

          <ModeRow
            mode={engine.mode}
            onModeChange={engine.setMode}
            onReshuffle={() => engine.setOrder(shuffleQueue(engine.queueRef.current.length))}
          />

          <VolumeRow volume={engine.volume} onChange={engine.setVolume} />

          <QueueList
            order={engine.order}
            queue={queue}
            currentTrackIdx={engine.currentTrackIdx}
            onReorder={engine.setOrder}
            onPlay={engine.playTrackIdx}
          />
        </div>

        <div id="yt-preload" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", opacity: 0, pointerEvents: "none" }} />
      </div>
    </ConfigProvider>
  );
}