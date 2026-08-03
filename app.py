import streamlit as st

from config import APP_ICON, APP_TITLE
from services import auth_service
from ui.now_playing_widget import render_now_playing_drawer
from ui.pages import about, history, home, login, map_page, music, photobooth, relax, secret
from ui.styles import inject_global_css

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_global_css()

# If the browser has a valid "remember me" cookie, log the user back in
# before anything else renders — keeps you logged in across page reloads.
auth_service.restore_session()

pages = {
    "Home": [
        st.Page(home.render, title="Home", icon=":material/home:", url_path="home", default=True),
    ],
    "Account": [
        st.Page(login.render, title="Login", icon=":material/login:", url_path="login"),
        st.Page(music.render, title="Music", icon=":material/library_music:", url_path="music"),
    ],
    "Explore": [
        st.Page(about.render, title="About", icon=":material/info:", url_path="about"),
        st.Page(history.render, title="His-tory", icon=":material/history:", url_path="history"),
        st.Page(relax.render, title="Relax", icon=":material/self_improvement:", url_path="relax"),
        st.Page(map_page.render, title="Map", icon=":material/location_on:", url_path="map"),
        st.Page(photobooth.render, title="Photobooth", icon=":material/photo_camera:", url_path="photobooth"),
    ],
    "More": [
        st.Page(secret.render, title="???", icon=":material/lock:", url_path="secret"),
    ],
}

pg = st.navigation(pages)
render_now_playing_drawer()
pg.run()
