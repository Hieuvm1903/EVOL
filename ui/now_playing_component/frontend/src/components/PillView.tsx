import React from "react";
import { Button, Typography } from "antd";
import { PlayCircleFilled, PauseCircleFilled } from "@ant-design/icons";
import type { Track } from "../types";

interface Props {
  track: Track;
  playing: boolean;
  pillRef: React.RefObject<HTMLDivElement>;
  visible: boolean;
  onStartDrag: (e: React.MouseEvent | React.TouchEvent, onTap: () => void) => void;
  onExpand: () => void;
  onTogglePlayPause: () => void;
}

export default function PillView({ track, playing, pillRef, visible, onStartDrag, onExpand, onTogglePlayPause }: Props) {
  return (
    <div id="pill-wrap" style={{ display: visible ? "block" : "none" }}>
      <div
        id="pill"
        ref={pillRef}
        title="Drag to move · tap to expand"
        onMouseDown={(e) => onStartDrag(e, onExpand)}
        onTouchStart={(e) => onStartDrag(e, onExpand)}
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
            onClick={(e) => { e.stopPropagation(); onTogglePlayPause(); }}
          />
        </span>
      </div>
    </div>
  );
}