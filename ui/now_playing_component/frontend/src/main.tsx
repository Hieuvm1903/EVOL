import React from "react";
import ReactDOM from "react-dom/client";
import { Streamlit } from "streamlit-component-lib";
import "antd/dist/reset.css";
import NowPlaying, { Track } from "./NowPlaying";

const root = ReactDOM.createRoot(document.getElementById("root")!);

function onRender(event: Event) {
  const data = (event as CustomEvent).detail;
  const queue: Track[] = data.args["queue"] || [];
  const mode: string = data.args["mode"] || "Normal";
  root.render(
    <React.StrictMode>
      <NowPlaying queue={queue} initialMode={mode} />
    </React.StrictMode>
  );
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
Streamlit.setComponentReady();