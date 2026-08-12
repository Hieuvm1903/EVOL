import React from "react";
import { Button, Segmented, Tooltip } from "antd";
import { CloseOutlined, VideoCameraOutlined, FileTextOutlined } from "@ant-design/icons";
import type { View } from "../types";

interface Props {
  headerRef: React.RefObject<HTMLDivElement>;
  view: View;
  onViewChange: (v: View) => void;
  onStartDrag: (e: React.MouseEvent | React.TouchEvent, onTap: () => void) => void;
  onCollapse: () => void;
  onResetPos: () => void;
  onClose: () => void;
}

export default function PanelHeader({ headerRef, view, onViewChange, onStartDrag, onCollapse, onResetPos, onClose }: Props) {
  return (
    <div
      className="panel-header"
      ref={headerRef}
      title="Drag to move · tap to collapse"
      onMouseDown={(e) => onStartDrag(e, onCollapse)}
      onTouchStart={(e) => onStartDrag(e, onCollapse)}
    >
      <span className="drag-grip" onDoubleClick={(e) => { e.stopPropagation(); onResetPos(); }}>⠿</span>
      <span className="panel-title">Now Playing</span>
      <div
        className="header-view-toggle"
        onMouseDown={(e) => e.stopPropagation()}
        onTouchStart={(e) => e.stopPropagation()}
      >
        <Segmented
          size="small"
          value={view}
          onChange={(v) => onViewChange(v as View)}
          options={[
            { value: "video", label: <Tooltip title="Video"><VideoCameraOutlined /></Tooltip> },
            { value: "lyrics", label: <Tooltip title="Lyrics"><FileTextOutlined /></Tooltip> },
          ]}
        />
      </div>
      <Button
        type="text" shape="circle" size="small" style={{ color: "#9a9a9a" }}
        icon={<CloseOutlined />}
        onClick={(e) => { e.stopPropagation(); onClose(); }}
        title="Close"
      />
    </div>
  );
}