"""A floating "Now Playing" drawer pinned to the right edge of the viewport,
rendered from app.py (outside pg.run()) so it survives page navigation —
see the module-level note in app.py for why that matters.

Streamlit doesn't have a built-in right sidebar, so this is a single
st.iframe whose *outer* box is pinned with `position: fixed` via a CSS rule
targeting st.container(key=...)'s generated class (see ui/styles.py). The
iframe's own content then implements collapse/expand as a pure CSS/JS
toggle between a small pill and a full panel — collapsing doesn't shrink
the outer iframe box (Streamlit doesn't support that), so the empty space
around the pill is made click-through (`pointer-events: none`) so it never
blocks the page underneath.
"""
import json

import streamlit as st

_MODE_JS = {"Normal": "normal", "Shuffle": "shuffle", "Repeat All": "repeatAll"}


def load_queue(tracks, mode: str) -> None:
    st.session_state["music_queue"] = tracks.to_dict("records")
    st.session_state["music_mode"] = mode


def _build_player_html(queue: list[dict], mode: str) -> str:
    js_queue = [
        {"title": t["title"], "video_id": t["video_id"], "thumbnail_url": t.get("thumbnail_url") or ""}
        for t in queue
    ]
    queue_json = json.dumps(js_queue)
    initial_mode = _MODE_JS.get(mode, "normal")

    return f"""
<style>
  html, body {{
    margin: 0; padding: 0; background: transparent;
    font-family: Poppins, sans-serif; color: #e6e6e6;
    pointer-events: none; /* let clicks pass through the empty parts of the box */
  }}
  #pill, #panel {{ pointer-events: auto; }}

  #pill {{
    position: absolute; top: 0; right: 0; width: 260px;
    display: flex; align-items: center; gap: 8px;
    background: #161616; border: 1px solid #02ab21; border-radius: 999px;
    padding: 6px 10px; cursor: pointer; box-shadow: 0 4px 14px rgba(0,0,0,0.4);
  }}
  #pill img {{ width: 32px; height: 32px; border-radius: 6px; object-fit: cover; background: #000; flex-shrink: 0; }}
  #pill-title {{ flex: 1; font-size: 0.78rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  #pill button {{ background: none; border: none; color: #02ab21; font-size: 1rem; cursor: pointer; padding: 2px 4px; }}

  #panel {{
    position: absolute; top: 0; right: 0; width: 300px; display: none;
    background: #161616; border: 1px solid #02ab21; border-radius: 14px;
    padding: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  }}
  .panel-header {{ display: flex; justify-content: space-between; align-items: center;
    font-size: 0.75rem; color: #9a9a9a; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.03em; }}
  .panel-header button {{ background: none; border: none; color: #9a9a9a; font-size: 0.9rem; cursor: pointer; }}

  #unmute-banner {{ display:none; background:#02ab21; color:#fff; padding:5px 8px; border-radius:6px;
    margin-bottom:8px; cursor:pointer; text-align:center; font-weight:600; font-size:0.72rem; }}

  #video-shell {{ position: relative; width: 100%; padding-top: 56.25%; border-radius: 10px;
    overflow: hidden; background: #000; }}
  #yt-main {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; }}

  #now-title {{ margin-top: 8px; font-weight: 600; font-size: 0.85rem;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

  #progress-row {{ display: flex; align-items: center; gap: 6px; margin-top: 8px; font-size: 0.68rem; color: #9a9a9a; }}
  #progress-bar {{ flex: 1; height: 5px; background: #2a2a2a; border-radius: 3px; cursor: pointer; position: relative; }}
  #progress-fill {{ position: absolute; left: 0; top: 0; height: 100%; width: 0%; background: #02ab21; border-radius: 3px; }}

  #controls-row {{ display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 10px; }}
  .ctrl-btn {{ background:#0c0c0c; border:1px solid #02ab21; color:#02ab21;
    border-radius:8px; padding:5px 11px; font-size:1rem; cursor:pointer; }}
  .ctrl-btn-small {{ background:#0c0c0c; border:1px solid #2a2a2a; color:#9a9a9a;
    border-radius:8px; padding:5px 9px; font-size:0.68rem; cursor:pointer; }}

  #volume-row {{ display: flex; align-items: center; gap: 6px; margin-top: 10px; font-size: 0.85rem; }}
  #volume-slider {{ flex: 1; accent-color: #02ab21; }}
</style>

<div id="pill" onclick="toggleExpand(true)">
  <img id="pill-thumb" src="">
  <div id="pill-title"></div>
  <button onclick="event.stopPropagation(); togglePlayPause()" id="pill-playpause">⏸</button>
</div>

<div id="panel">
  <div class="panel-header">
    <span>Now Playing</span>
    <button onclick="toggleExpand(false)" title="Collapse">▾</button>
  </div>
  <div id="unmute-banner" onclick="unmuteNow()">Sound off — tap to unmute</div>
  <div id="video-shell"><div id="yt-main"></div></div>
  <div id="now-title"></div>
  <div id="progress-row">
    <span id="cur-time">0:00</span>
    <div id="progress-bar" onclick="seek(event)"><div id="progress-fill"></div></div>
    <span id="dur-time">0:00</span>
  </div>
  <div id="controls-row">
    <button class="ctrl-btn" onclick="advance(-1)" title="Previous">⏮</button>
    <button class="ctrl-btn" id="playpause-btn" onclick="togglePlayPause()" title="Play/Pause">⏸</button>
    <button class="ctrl-btn" onclick="advance(1)" title="Next">⏭</button>
    <button class="ctrl-btn-small" onclick="toggleMode()" title="Playback mode"><span id="mode-label"></span></button>
  </div>
  <div id="volume-row">
    🔊 <input type="range" id="volume-slider" min="0" max="100" value="100" oninput="setVolume(this.value)">
  </div>
</div>

<div id="yt-preload" style="position:absolute;width:1px;height:1px;overflow:hidden;opacity:0;pointer-events:none;"></div>

<script src="https://www.youtube.com/iframe_api"></script>
<script>
  const QUEUE = {queue_json};
  let mode = "{initial_mode}";
  let order = buildOrder(QUEUE.length, mode);
  let orderPos = 0;
  let playerMain, playerPreload;
  let preloadReady = false;
  let expanded = false;
  try {{ expanded = localStorage.getItem('evol_player_expanded') === '1'; }} catch (e) {{}}

  function buildOrder(n, m) {{
    let arr = Array.from({{length: n}}, (_, i) => i);
    if (m === "shuffle") shuffleArr(arr);
    return arr;
  }}
  function shuffleArr(arr) {{
    for (let i = arr.length - 1; i > 0; i--) {{
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }}
  }}
  function currentIndex() {{ return order[orderPos]; }}
  function currentTrack() {{ return QUEUE[currentIndex()]; }}

  function onYouTubeIframeAPIReady() {{
    playerMain = new YT.Player('yt-main', {{
      width: '100%', height: '100%',
      videoId: currentTrack().video_id,
      playerVars: {{ autoplay: 1, mute: 0, playsinline: 1, rel: 0 }},
      events: {{ onReady: onMainReady, onStateChange: onMainStateChange }}
    }});
    playerPreload = new YT.Player('yt-preload', {{
      videoId: '',
      playerVars: {{ mute: 1, controls: 0 }},
      events: {{ onReady: function() {{ preloadReady = true; cueNext(); }} }}
    }});
  }}

  function onMainReady() {{
    updateUI();
    toggleExpand(expanded);
    setInterval(updateProgress, 500);
    setTimeout(function() {{
      try {{
        if (playerMain.isMuted()) document.getElementById('unmute-banner').style.display = 'block';
      }} catch (e) {{}}
    }}, 500);
  }}

  function onMainStateChange(e) {{
    if (e.data === YT.PlayerState.ENDED) {{
      if (mode === "repeatTrack") {{ playerMain.seekTo(0); playerMain.playVideo(); }}
      else {{ advance(1); }}
    }}
    if (e.data === YT.PlayerState.PLAYING) setPlayingUI(true);
    if (e.data === YT.PlayerState.PAUSED) setPlayingUI(false);
  }}

  function computeNextOrderPos() {{
    let p = orderPos + 1;
    if (p >= order.length) {{
      if (mode === "repeatAll" || mode === "shuffle") return 0;
      return null;
    }}
    return p;
  }}

  function cueNext() {{
    if (!preloadReady) return;
    const p = computeNextOrderPos();
    if (p === null) return;
    try {{ playerPreload.cueVideoById(QUEUE[order[p]].video_id); }} catch (e) {{}}
  }}

  function advance(step) {{
    if (step > 0) {{
      orderPos += 1;
      if (orderPos >= order.length) {{
        if (mode === "repeatAll") {{ orderPos = 0; }}
        else if (mode === "shuffle") {{ order = buildOrder(QUEUE.length, mode); orderPos = 0; }}
        else {{ orderPos = order.length - 1; setPlayingUI(false); updateUI(); return; }}
      }}
    }} else {{
      orderPos -= 1;
      if (orderPos < 0) {{ orderPos = (mode === "repeatAll") ? order.length - 1 : 0; }}
    }}
    loadCurrent();
  }}

  function loadCurrent() {{
    const track = currentTrack();
    playerMain.loadVideoById(track.video_id);
    updateUI();
    cueNext();
  }}

  function togglePlayPause() {{
    if (!playerMain || !playerMain.getPlayerState) return;
    const state = playerMain.getPlayerState();
    if (state === YT.PlayerState.PLAYING) playerMain.pauseVideo();
    else playerMain.playVideo();
  }}

  function toggleMode() {{
    const modes = ["normal", "shuffle", "repeatTrack", "repeatAll"];
    mode = modes[(modes.indexOf(mode) + 1) % modes.length];
    if (mode === "shuffle") {{ order = buildOrder(QUEUE.length, mode); orderPos = 0; loadCurrent(); }}
    updateUI();
  }}

  function unmuteNow() {{
    if (playerMain && playerMain.unMute) playerMain.unMute();
    document.getElementById('unmute-banner').style.display = 'none';
  }}

  function toggleExpand(v) {{
    expanded = v;
    document.getElementById('pill').style.display = expanded ? 'none' : 'flex';
    document.getElementById('panel').style.display = expanded ? 'block' : 'none';
    try {{ localStorage.setItem('evol_player_expanded', expanded ? '1' : '0'); }} catch (e) {{}}
  }}

  function seek(e) {{
    const bar = document.getElementById('progress-bar');
    const rect = bar.getBoundingClientRect();
    const frac = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
    if (playerMain && playerMain.getDuration) {{
      try {{ playerMain.seekTo(frac * playerMain.getDuration(), true); }} catch (err) {{}}
    }}
  }}

  function setVolume(v) {{
    if (playerMain && playerMain.setVolume) {{ try {{ playerMain.setVolume(v); }} catch (e) {{}} }}
  }}

  function formatTime(s) {{
    s = Math.max(0, Math.floor(s));
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m + ':' + (sec < 10 ? '0' : '') + sec;
  }}

  function updateProgress() {{
    if (!playerMain || !playerMain.getCurrentTime) return;
    try {{
      const cur = playerMain.getCurrentTime();
      const dur = playerMain.getDuration();
      if (dur > 0) {{
        document.getElementById('progress-fill').style.width = (cur / dur * 100) + '%';
        document.getElementById('cur-time').innerText = formatTime(cur);
        document.getElementById('dur-time').innerText = formatTime(dur);
      }}
    }} catch (e) {{}}
  }}

  function modeLabel(m) {{
    return {{normal: "Normal", shuffle: "Shuffle", repeatTrack: "Repeat 1", repeatAll: "Repeat all"}}[m];
  }}
  function setPlayingUI(isPlaying) {{
    const icon = isPlaying ? "⏸" : "▶";
    document.getElementById('playpause-btn').innerText = icon;
    document.getElementById('pill-playpause').innerText = icon;
  }}
  function updateUI() {{
    const track = currentTrack();
    document.getElementById('now-title').innerText = track.title;
    document.getElementById('pill-title').innerText = track.title;
    document.getElementById('mode-label').innerText = modeLabel(mode);
    const thumb = track.thumbnail_url || '';
    document.getElementById('pill-thumb').src = thumb;
  }}
</script>
"""


def render_now_playing_drawer() -> None:
    queue = st.session_state.get("music_queue")
    mode = st.session_state.get("music_mode", "Normal")
    if not queue:
        return  # nothing playing — take up zero space until something is
    with st.container(key="now_playing_drawer"):
        st.iframe(_build_player_html(queue, mode), height=460)
