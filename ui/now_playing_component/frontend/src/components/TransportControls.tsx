import React from "react";
import { Button } from "antd";
import { StepBackwardOutlined, StepForwardOutlined, PlayCircleFilled, PauseCircleFilled } from "@ant-design/icons";
import type { Track } from "../types";

interface Props {
  track: Track;
  playing: boolean;
  onPrev: () => void;
  onNext: () => void;
  onTogglePlayPause: () => void;
}

export default function TransportControls({ track, playing, onPrev, onNext, onTogglePlayPause }: Props) {
  return (
    <div id="controls-row">
      <Button shape="circle" icon={<StepBackwardOutlined />} onClick={onPrev} />
      <span className="spin-disk-wrap spin-disk-lg">
        <span
          className={`spin-disk${playing ? " spin-disk-playing" : ""}`}
          style={track.thumbnail_url ? { backgroundImage: `url(${track.thumbnail_url})` } : undefined}
        />
        <Button
          type="primary" shape="circle" size="large"
          style={{ position: "relative", zIndex: 1 }}
          icon={playing ? <PauseCircleFilled /> : <PlayCircleFilled />}
          onClick={onTogglePlayPause}
        />
      </span>
      <Button shape="circle" icon={<StepForwardOutlined />} onClick={onNext} />
    </div>
  );
}