import streamlit as st
from services import music_service
from .now_playing_component import now_playing_widget


def load_queue(tracks, mode: str) -> None:
    if mode.lower() == "shuffle":
        # shuffle track
        tracks = tracks.sample(frac=1).reset_index(drop=True)
    st.session_state["music_queue"] = tracks.to_dict("records")
    st.session_state["music_mode"] = mode


def render_now_playing_drawer() -> None:
    queue = st.session_state.get("music_queue")
    if not queue:
        return
    with st.container(key="now_playing_drawer"):
        result = now_playing_widget(queue, st.session_state.get("music_mode", "Normal"))

    if not isinstance(result, dict):
        return

    action = result.get("action")
    if action == "close":
        st.session_state["music_queue"] = None
        st.session_state.pop("music_mode", None)
        st.rerun()
    elif action == "save_lyrics_selection":
        track_id = result.get("track_id")
        if track_id is not None:
            music_service.update_track_details(
                track_id=int(track_id),
                artist=result.get("artist_name"),
                lyrics_url=result.get("lyrics_url"),
            )