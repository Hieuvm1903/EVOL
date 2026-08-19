import streamlit as st
from services import music_service
from .now_playing_component import now_playing_widget


def load_queue(tracks, mode: str) -> None:
    if mode.lower() == "shuffle":
        # shuffle track. (Was comparing to "shuffle" lower-case against
        # callers passing "Shuffle" — never actually matched, so this was
        # silently a no-op; harmless since the frontend does its own
        # client-side shuffle too, but fixed while in here.)
        tracks = tracks.sample(frac=1).reset_index(drop=True)
    st.session_state["music_queue"] = tracks.to_dict("records")
    st.session_state["music_mode"] = mode
    # Every Play click bumps this. It's folded into the widget's `key`
    # below, which forces Streamlit to treat each new queue as a BRAND
    # NEW component instance rather than trying to hand updated props to
    # the same already-mounted one. That in-place handoff was unreliable
    # enough to visually drop the widget the first time you hit Play on a
    # different list while one was already playing, requiring a second
    # click to actually reopen it. A fresh instance always starts clean
    # (fresh YouTube player, fresh default return value — no stale action
    # from the previous playlist can leak in), which is also exactly the
    # "replace what's playing" behavior wanted here rather than a
    # seamless in-place swap.
    st.session_state["music_queue_version"] = st.session_state.get("music_queue_version", 0) + 1


def render_now_playing_drawer() -> None:
    queue = st.session_state.get("music_queue")
    if not queue:
        return
    version = st.session_state.get("music_queue_version", 0)
    with st.container(key="now_playing_drawer"):
        result = now_playing_widget(
            queue, st.session_state.get("music_mode", "Normal"),
            key=f"now_playing_{version}",
        )

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