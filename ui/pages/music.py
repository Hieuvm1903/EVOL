import html as html_lib
import json

import streamlit as st

from services import music_service
from utils import ytmusic_search

_MODE_JS = {"Normal": "normal", "Shuffle": "shuffle", "Repeat All": "repeatAll"}

_BTN_STYLE = (
    "background:#161616;border:1px solid #02ab21;color:#02ab21;"
    "border-radius:8px;padding:6px 12px;font-size:1.05rem;cursor:pointer;"
)


def _current_user_id():
    user = st.session_state.get("user")
    return user["id"] if user else None


# ---------------------------------------------------------------------------
# Playlist list view
# ---------------------------------------------------------------------------

@st.dialog("Create a new playlist")
def _new_playlist_dialog(user_id: int) -> None:
    name = st.text_input("Playlist name", key="new_playlist_dialog_name")
    if st.button("Create", type="primary", use_container_width=True):
        if name.strip():
            music_service.create_playlist(user_id, name.strip())
            st.rerun()
        else:
            st.warning("Give it a name first.")


def _play_from_list(playlist_id: int, mode: str) -> None:
    tracks = music_service.get_playlist_tracks(playlist_id)
    if tracks.empty:
        st.warning("This playlist is empty.")
    else:
        _load_queue(tracks, mode)
        st.rerun()


def _render_playlist_row(row, all_playlists) -> None:
    pid = int(row["id"])
    c_name, c_play, c_shuffle, c_repeat, c_menu = st.columns([4, 0.6, 0.6, 0.6, 0.6])

    c_name.markdown(f"**🎵 {row['name']}**")

    if c_play.button("▶️", key=f"list_play_{pid}", help="Play"):
        _play_from_list(pid, "Normal")
    if c_shuffle.button("🔀", key=f"list_shuffle_{pid}", help="Shuffle"):
        _play_from_list(pid, "Shuffle")
    if c_repeat.button("🔁", key=f"list_repeat_{pid}", help="Repeat all"):
        _play_from_list(pid, "Repeat All")

    with c_menu:
        with st.popover("⋮"):
            if st.button("📂 Open", key=f"open_{pid}", use_container_width=True):
                st.session_state["music_view"] = "detail"
                st.session_state["music_selected_playlist_id"] = pid
                st.rerun()
            if st.button("🗑️ Delete", key=f"delete_{pid}", use_container_width=True):
                music_service.delete_playlist(pid)
                st.rerun()
            st.markdown("---")
            st.caption("Copy tracks from another playlist (duplicates skipped)")
            others = all_playlists[all_playlists["id"] != pid]
            if others.empty:
                st.caption("No other playlists yet.")
            else:
                opts = {r["name"]: int(r["id"]) for _, r in others.iterrows()}
                src_name = st.selectbox(
                    "Source", list(opts.keys()), key=f"copysrc_{pid}", label_visibility="collapsed"
                )
                if st.button("📋 Copy tracks", key=f"copybtn_{pid}", use_container_width=True):
                    added = music_service.copy_playlist_tracks(opts[src_name], pid)
                    st.success(f"Copied {added} new track(s).")
                    st.rerun()
    st.divider()


def _render_playlist_list(user_id: int) -> None:
    top_col1, top_col2 = st.columns([1, 3])
    with top_col1:
        if st.button("➕ New playlist", use_container_width=True):
            _new_playlist_dialog(user_id)
    with top_col2:
        search = st.text_input(
            "Find by name", label_visibility="collapsed", placeholder="🔍 Find playlist by name...",
        )

    playlists = music_service.get_playlists(user_id)
    if playlists.empty:
        st.info("No playlists yet — create one above.")
        return

    filtered = playlists
    if search.strip():
        filtered = playlists[playlists["name"].str.contains(search.strip(), case=False, na=False)]
        if filtered.empty:
            st.caption(f'No playlists match "{search.strip()}".')

    for _, row in filtered.iterrows():
        _render_playlist_row(row, playlists)


# ---------------------------------------------------------------------------
# Playlist detail view
# ---------------------------------------------------------------------------

def _render_play_controls(tracks, key_prefix: str) -> None:
    c1, c2, c3 = st.columns(3)
    if c1.button("▶️ Play", key=f"{key_prefix}_play", use_container_width=True):
        if tracks.empty:
            st.warning("This playlist is empty.")
        else:
            _load_queue(tracks, "Normal")
            st.rerun()
    if c2.button("🔀 Shuffle", key=f"{key_prefix}_shuffle", use_container_width=True):
        if tracks.empty:
            st.warning("This playlist is empty.")
        else:
            _load_queue(tracks, "Shuffle")
            st.rerun()
    if c3.button("🔁 Repeat all", key=f"{key_prefix}_repeat", use_container_width=True):
        if tracks.empty:
            st.warning("This playlist is empty.")
        else:
            _load_queue(tracks, "Repeat All")
            st.rerun()


def _render_add_track(playlist_id: int, user_id: int, existing_ids: set) -> None:
    with st.expander("➕ Add track", expanded=False):
        tab_search, tab_link = st.tabs(["🔍 Search", "🔗 Paste link"])

        with tab_search:
            query = st.text_input("Search songs", key=f"search_q_{playlist_id}",
                                   placeholder="song title or artist...")
            if st.button("Search", key=f"search_btn_{playlist_id}") and query.strip():
                with st.spinner("Searching..."):
                    st.session_state[f"search_results_{playlist_id}"] = ytmusic_search.search_songs(query.strip())

            results = st.session_state.get(f"search_results_{playlist_id}", [])
            if not results and query.strip():
                st.caption("Click Search to look it up.")
            for r in results:
                rc1, rc2, rc3 = st.columns([1, 4, 1])
                if r["thumbnail_url"]:
                    rc1.image(r["thumbnail_url"], width=56)
                rc2.markdown(f"**{r['title']}**  \n{r['artist']} · {r['duration']}")
                if rc3.button("➕", key=f"searchadd_{playlist_id}_{r['video_id']}"):
                    url = f"https://www.youtube.com/watch?v={r['video_id']}"
                    ok, msg, _ = music_service.add_track_and_attach(
                        playlist_id, url, user_id,
                        known_title=r["title"], known_thumbnail=r["thumbnail_url"],
                    )
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()

        with tab_link:
            url = st.text_input("YouTube link", key=f"add_url_{playlist_id}",
                                 placeholder="https://www.youtube.com/watch?v=...")
            title_override = st.text_input("Title (optional)", key=f"add_title_{playlist_id}")
            if st.button("Fetch & add", key=f"add_btn_{playlist_id}"):
                if not url.strip():
                    st.warning("Paste a YouTube link first.")
                else:
                    ok, msg, _ = music_service.add_track_and_attach(
                        playlist_id, url.strip(), user_id, known_title=title_override.strip() or None,
                    )
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()

        library = music_service.get_all_tracks()
        addable = library[~library["id"].isin(existing_ids)] if not library.empty else library
        if addable is not None and not addable.empty:
            st.markdown("**Or add from your library**")
            opts = {r["title"]: r["id"] for _, r in addable.iterrows()}
            pick = st.selectbox("Library track", ["—"] + list(opts.keys()),
                                 key=f"pick_{playlist_id}", label_visibility="collapsed")
            if pick != "—" and st.button("Add selected", key=f"add_lib_{playlist_id}"):
                music_service.add_track_to_playlist(playlist_id, opts[pick])
                st.rerun()


def _render_playlist_detail(user_id: int, playlist_id: int) -> None:
    if st.button("← Back to playlists"):
        st.session_state["music_view"] = "list"
        st.rerun()

    playlists = music_service.get_playlists(user_id)
    match = playlists[playlists["id"] == playlist_id]
    if match.empty:
        st.warning("Playlist not found.")
        st.session_state["music_view"] = "list"
        return
    current_name = match.iloc[0]["name"]

    new_name = st.text_input("Playlist name", value=current_name, key=f"rename_input_{playlist_id}")
    if st.button("💾 Save name", key=f"rename_save_{playlist_id}"):
        if new_name.strip() and new_name.strip() != current_name:
            music_service.rename_playlist(playlist_id, new_name.strip())
            st.rerun()

    tracks = music_service.get_playlist_tracks(playlist_id)

    st.markdown("#### Playback")
    _render_play_controls(tracks, key_prefix=f"detail_{playlist_id}")

    st.markdown("#### Tracks")
    if tracks.empty:
        st.caption("No tracks yet — add some below.")
    else:
        for _, t in tracks.iterrows():
            tc1, tc2 = st.columns([5, 1])
            tc1.write(f"🎵 {t['title']}")
            if tc2.button("✖", key=f"rm_{playlist_id}_{t['id']}"):
                music_service.remove_track_from_playlist(playlist_id, t["id"])
                st.rerun()

    existing_ids = set(tracks["id"]) if not tracks.empty else set()
    _render_add_track(playlist_id, user_id, existing_ids)


# ---------------------------------------------------------------------------
# Persistent, client-side-driven Now Playing player
#
# Everything below the initial "load a queue" click runs entirely in the
# browser (JS) rather than round-tripping through Streamlit reruns:
#   - Next/Previous/Play-Pause/mode-cycling are plain HTML buttons calling
#     JS functions, not Streamlit widgets — so they never trigger a script
#     rerun, and playback survives you clicking around the rest of the app.
#   - As long as st.session_state["music_queue"]/["music_mode"] don't
#     change, this function renders byte-identical HTML on every rerun,
#     which keeps the underlying iframe (and its YouTube player) from being
#     recreated/reloaded when unrelated parts of the page rerun.
#   - Playback starts muted (autoplay-with-sound is blocked by browsers
#     unless it's a direct continuation of a user gesture) with a one-click
#     "unmute" banner; once unmuted, track changes reuse the same player via
#     loadVideoById() rather than remounting the iframe, so sound keeps
#     working without needing to click again for every song.
#   - A second, hidden player pre-cues the next track ahead of time
#     (cueVideoById) so switching tracks is snappier.
# ---------------------------------------------------------------------------

def _load_queue(tracks, mode: str) -> None:
    st.session_state["music_queue"] = tracks.to_dict("records")
    st.session_state["music_mode"] = mode


def _build_player_html(queue: list[dict], mode: str) -> str:
    js_queue = [{"title": t["title"], "video_id": t["video_id"]} for t in queue]
    queue_json = json.dumps(js_queue)
    initial_mode = _MODE_JS.get(mode, "normal")

    list_items = "".join(
        f'<div class="queue-item" data-idx="{i}" onclick="jumpTo({i})">'
        f'{i + 1}. {html_lib.escape(t["title"])}</div>'
        for i, t in enumerate(js_queue)
    )

    return f"""
<div id="evol-player" style="font-family:Poppins,sans-serif;color:#e6e6e6;">
  <div id="unmute-banner" style="display:none;background:#02ab21;color:#fff;padding:8px 12px;
       border-radius:8px;margin-bottom:8px;cursor:pointer;text-align:center;font-weight:600;"
       onclick="unmuteNow()">
    🔇 Started muted (browser autoplay rules) — click here to turn sound on
  </div>

  <div id="yt-main" style="border-radius:12px;overflow:hidden;"></div>
  <div id="yt-preload" style="position:absolute;width:1px;height:1px;overflow:hidden;opacity:0;pointer-events:none;"></div>

  <div style="display:flex;align-items:center;gap:10px;margin-top:10px;flex-wrap:wrap;">
    <button onclick="advance(-1)" style="{_BTN_STYLE}">⏮️</button>
    <button id="playpause-btn" onclick="togglePlayPause()" style="{_BTN_STYLE}">⏸️</button>
    <button onclick="advance(1)" style="{_BTN_STYLE}">⏭️</button>
    <button onclick="toggleMode()" style="{_BTN_STYLE}"><span id="mode-label"></span></button>
  </div>

  <div id="now-title" style="margin-top:8px;font-weight:600;font-size:1.05rem;"></div>

  <div style="margin-top:10px;max-height:200px;overflow-y:auto;border-top:1px solid #2a2a2a;padding-top:8px;">
    {list_items}
  </div>
</div>

<style>
  .queue-item {{ padding:6px 8px;border-radius:6px;cursor:pointer;font-size:0.9rem; }}
  .queue-item:hover {{ background:#1f1f1f; }}
  .queue-item.active {{ background:#02ab21; color:#fff; font-weight:600; }}
</style>

<script src="https://www.youtube.com/iframe_api"></script>
<script>
  const QUEUE = {queue_json};
  let mode = "{initial_mode}";
  let order = buildOrder(QUEUE.length, mode);
  let orderPos = 0;
  let playerMain, playerPreload;
  let preloadReady = false;
  let unmuted = false;

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
      videoId: currentTrack().video_id,
      playerVars: {{ autoplay: 1, mute: 1, playsinline: 1, rel: 0 }},
      events: {{ onReady: onMainReady, onStateChange: onMainStateChange }}
    }});
    playerPreload = new YT.Player('yt-preload', {{
      videoId: '',
      playerVars: {{ mute: 1, controls: 0 }},
      events: {{ onReady: function() {{ preloadReady = true; cueNext(); }} }}
    }});
  }}

  function onMainReady() {{
    document.getElementById('unmute-banner').style.display = 'block';
    updateUI();
  }}

  function onMainStateChange(e) {{
    if (e.data === YT.PlayerState.ENDED) {{
      if (mode === "repeatTrack") {{
        playerMain.seekTo(0); playerMain.playVideo();
      }} else {{
        advance(1);
      }}
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
    if (unmuted) playerMain.unMute();
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
    unmuted = true;
    document.getElementById('unmute-banner').style.display = 'none';
  }}

  function jumpTo(i) {{
    const p = order.indexOf(i);
    orderPos = (p >= 0) ? p : 0;
    loadCurrent();
  }}

  function modeLabel(m) {{
    return {{normal: "➡️ Normal", shuffle: "🔀 Shuffle",
             repeatTrack: "🔂 Repeat Track", repeatAll: "🔁 Repeat All"}}[m];
  }}
  function setPlayingUI(isPlaying) {{
    document.getElementById('playpause-btn').innerText = isPlaying ? "⏸️" : "▶️";
  }}
  function updateUI() {{
    const track = currentTrack();
    document.getElementById('now-title').innerText = "🎵 " + track.title;
    document.getElementById('mode-label').innerText = modeLabel(mode);
    document.querySelectorAll('.queue-item').forEach(function(el) {{
      el.classList.toggle('active', parseInt(el.dataset.idx) === currentIndex());
    }});
  }}
</script>
"""


def _render_now_playing() -> None:
    queue = st.session_state.get("music_queue")
    mode = st.session_state.get("music_mode", "Normal")
    if not queue:
        st.info("Pick a playlist above and hit ▶️, 🔀, or 🔁 to start listening.")
        return

    st.markdown("### ▶️ Now Playing")
    st.iframe(_build_player_html(queue, mode), height=560)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render() -> None:
    st.markdown("## 🎧 Music")

    user_id = _current_user_id()
    if not user_id:
        st.warning("Log in first (see the Login tab) to build playlists and listen to music.")
        return

    view = st.session_state.get("music_view", "list")
    if view == "detail" and st.session_state.get("music_selected_playlist_id"):
        _render_playlist_detail(user_id, st.session_state["music_selected_playlist_id"])
    else:
        _render_playlist_list(user_id)

    st.markdown("---")
    _render_now_playing()
