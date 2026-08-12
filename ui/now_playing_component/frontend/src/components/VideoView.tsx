import React from "react";

// #yt-main must always be mounted — the YT.Player instance targets this
// DOM node directly, so unmounting it would destroy the player (which is
// exactly what caused "collapse restarts playback" in an earlier version).
// Visibility is controlled purely via CSS display, never conditional JSX.
export default function VideoView({ visible }: { visible: boolean }) {
  return (
    <div id="video-shell" style={{ display: visible ? "block" : "none" }}>
      <div id="yt-main" />
    </div>
  );
}