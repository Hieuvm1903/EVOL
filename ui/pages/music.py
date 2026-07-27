import random

import pandas as pd
import streamlit as st
from streamlit_player import st_player

from services import music_service

PLAY_MODES = ["Normal", "Shuffle", "Repeat Track", "Repeat All"]


def _current_user_id():
    user = st.session_state.get("user")
    return user["id"] if user else None


def _render_add_track(user_id: int) -> None:
    with st.expander("➕ Add music from a YouTube link", expanded=False):
        url = st.text_input("YouTube link", placeholder="https://www.youtube.com/watch?v=...")
        title_override = st.text_input("Title (optional — auto-detected if left blank)")
        if st.button("Fetch & add", key="add_track_btn"):
            if not url.strip():
                st.warning("Paste a YouTube link first.")
            else:
                ok, message = music_service.add_track(url.strip(), title_override.strip() or None, user_id)
                (st.success if ok else st.error)(message)
                if ok:
                    st.rerun()


def _render_playlists(user_id: int):
    """Returns (playlist_id, playlist_name, tracks_df) for the selected
    playlist, or None if the user has no playlists yet."""
    st.markdown("### 🎵 Playlists")
    col1, col2 = st.columns([1, 2])

    with col1:
        new_name = st.text_input("New playlist name", key="new_playlist_name")
        if st.button("➕ Create playlist"):
            if new_name.strip():
                music_service.create_playlist(user_id, new_name.strip())
                st.rerun()
            else:
                st.warning("Give it a name first.")

        playlists = music_service.get_playlists(user_id)
        if playlists.empty:
            st.info("No playlists yet — create one above.")
            return None

        options = {row["name"]: row["id"] for _, row in playlists.iterrows()}
        chosen_name = st.radio("Your playlists", list(options.keys()), key="playlist_choice")
        chosen_id = options[chosen_name]

        if st.button("🗑️ Delete this playlist"):
            music_service.delete_playlist(chosen_id)
            st.session_state.pop("music_queue", None)
            st.rerun()

    with col2:
        st.markdown(f"**{chosen_name}**")
        playlist_tracks = music_service.get_playlist_tracks(chosen_id)

        library = music_service.get_all_tracks()
        already_in = set(playlist_tracks["id"]) if not playlist_tracks.empty else set()
        addable = library[~library["id"].isin(already_in)] if not library.empty else library

        if addable is not None and not addable.empty:
            track_options = {row["title"]: row["id"] for _, row in addable.iterrows()}
            pick = st.selectbox("Add a track from your library", ["—"] + list(track_options.keys()))
            if pick != "—" and st.button("Add to playlist"):
                music_service.add_track_to_playlist(chosen_id, track_options[pick])
                st.rerun()
        elif library.empty:
            st.caption("Your library is empty — add a YouTube link above first.")

        if playlist_tracks.empty:
            st.caption("This playlist is empty — add tracks above.")
        else:
            for _, row in playlist_tracks.iterrows():
                c1, c2 = st.columns([5, 1])
                c1.write(f"🎵 {row['title']}")
                if c2.button("✖", key=f"rm_{chosen_id}_{row['id']}"):
                    music_service.remove_track_from_playlist(chosen_id, row["id"])
                    st.rerun()

    return chosen_id, chosen_name, playlist_tracks


def _load_queue(tracks: pd.DataFrame, mode: str) -> None:
    track_list = tracks.to_dict("records")
    order = list(range(len(track_list)))
    if mode == "Shuffle":
        random.shuffle(order)
    st.session_state["music_queue"] = track_list
    st.session_state["music_order"] = order
    st.session_state["music_pos"] = 0
    st.session_state["music_mode"] = mode


def _advance(step: int) -> None:
    order = st.session_state.get("music_order", [])
    if not order:
        return
    mode = st.session_state.get("music_mode", "Normal")
    pos = st.session_state.get("music_pos", 0) + step

    if pos < 0:
        pos = len(order) - 1 if mode == "Repeat All" else 0
    elif pos >= len(order):
        if mode in ("Repeat All", "Shuffle"):
            if mode == "Shuffle":
                random.shuffle(order)
                st.session_state["music_order"] = order
            pos = 0
        else:
            pos = len(order) - 1  # stay on the last track

    st.session_state["music_pos"] = pos


def _render_now_playing() -> None:
    st.markdown("### ▶️ Now Playing")
    queue = st.session_state.get("music_queue")
    if not queue:
        st.info("Pick a playlist above, choose a mode, and hit ▶️ Play to start listening.")
        return

    order = st.session_state["music_order"]
    pos = st.session_state["music_pos"]
    current = queue[order[pos]]
    mode = st.session_state["music_mode"]

    st.caption(f"Mode: {mode} · track {pos + 1} of {len(order)}")
    st.markdown(f"**🎵 {current['title']}**")

    col_prev, col_next = st.columns(2)
    if col_prev.button("⏮️ Previous"):
        _advance(-1)
        st.rerun()
    if col_next.button("⏭️ Next"):
        _advance(1)
        st.rerun()

    event = st_player(
        current["youtube_url"],
        playing=True,
        loop=(mode == "Repeat Track"),
        controls=True,
        events=["onEnded"],
        key=f"player_{current['id']}_{pos}",
    )
    if event and getattr(event, "name", None) == "onEnded" and mode != "Repeat Track":
        _advance(1)
        st.rerun()

    with st.expander("Queue"):
        for i, idx in enumerate(order):
            marker = "▶️ " if i == pos else "　"
            st.write(f"{marker}{i + 1}. {queue[idx]['title']}")


def render() -> None:
    st.markdown("## 🎧 Music")

    user_id = _current_user_id()
    if not user_id:
        st.warning("Log in first (see the Login tab) to build playlists and listen to music.")
        return

    _render_add_track(user_id)

    st.markdown("---")
    result = _render_playlists(user_id)

    st.markdown("---")
    if result is not None:
        _, _, playlist_tracks = result
        if not playlist_tracks.empty:
            mode = st.selectbox("Play mode", PLAY_MODES, key="play_mode_select")
            if st.button("▶️ Play this playlist"):
                _load_queue(playlist_tracks, mode)
                st.rerun()

    _render_now_playing()
