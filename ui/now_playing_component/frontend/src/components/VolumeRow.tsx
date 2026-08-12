import React from "react";
import { Slider } from "antd";
import { SoundOutlined } from "@ant-design/icons";

interface Props {
  volume: number;
  onChange: (v: number) => void;
}

export default function VolumeRow({ volume, onChange }: Props) {
  return (
    <div id="volume-row">
      <SoundOutlined style={{ color: "#9a9a9a" }} />
      <Slider
        className="volume-slider"
        min={0} max={100} value={volume}
        onChange={(v) => onChange(v as number)}
        tooltip={{ formatter: (v) => `${v}%` }}
      />
    </div>
  );
}