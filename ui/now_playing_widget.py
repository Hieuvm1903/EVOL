import streamlit as st
from .now_playing_component import now_playing_widget


def load_queue(tracks, mode: str) -> None:
    st.session_state["music_queue"] = tracks.to_dict("records")
    st.session_state["music_mode"] = mode


def render_now_playing_drawer() -> None:
    queue = st.session_state.get("music_queue")
    if not queue:
        return
    with st.container(key="now_playing_drawer"):
        result = now_playing_widget(queue, st.session_state.get("music_mode", "Normal"))
    if result == "close":
        st.session_state["music_queue"] = None
        st.session_state.pop("music_mode", None)
        st.rerun()