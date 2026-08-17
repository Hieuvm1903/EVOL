import React from "react";
import { Button, Segmented, Tooltip } from "antd";
import { UnorderedListOutlined, SwapOutlined, RedoOutlined, RetweetOutlined } from "@ant-design/icons";
import type { Mode } from "../types";

interface Props {
  mode: Mode;
  onModeChange: (m: Mode) => void;
  onReshuffle: () => void;
}

export default function ModeRow({ mode, onModeChange, onReshuffle }: Props) {
  return (
    <div id="mode-row">
      <Segmented
        size="small"
        value={mode}
        onChange={(v) => onModeChange(v as Mode)}
        options={[
          { value: "normal", label: <Tooltip title="Normal"><UnorderedListOutlined /></Tooltip> },
          { value: "shuffle", label: <Tooltip title="Shuffle"><SwapOutlined /></Tooltip> },
          { value: "repeatTrack", label: <Tooltip title="Repeat one"><RedoOutlined /></Tooltip> },
          { value: "repeatAll", label: <Tooltip title="Repeat all"><RetweetOutlined /></Tooltip> },
        ]}
      />
      {/* {mode === "shuffle" && (
        <Tooltip title="Shuffle again">
          <Button
            type="text" size="small" icon={<SwapOutlined />}
            onClick={onReshuffle}
            style={{ marginLeft: 6, color: "#02ab21" }}
          />
        </Tooltip>
      )} */}
    </div>
  );
}