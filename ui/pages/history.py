import streamlit as st
from streamlit_player import st_player

from content import music_library


def _render_playlist(playlist) -> None:
    for title, url in playlist:
        st.write(title)
        st_player(url)


def render() -> None:
    tab1, tab2, tab3 = st.tabs(["Linh tinh", "Anime", "Bendy"])
    with tab1:
        _render_playlist(music_library.POP)
    with tab2:
        _render_playlist(music_library.ANIME)
    with tab3:
        _render_playlist(music_library.BENDY)
