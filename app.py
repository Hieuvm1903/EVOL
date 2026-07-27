import streamlit as st

from config import APP_ICON, APP_TITLE
from ui.pages import about, history, home, login, map_page, music, photobooth, relax, secret
from ui.sidebar import render_sidebar
from ui.styles import inject_global_css

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_global_css()

PAGES = {
    "Home": home.render,
    "Login": login.render,
    "Music": music.render,
    "About": about.render,
    "His-tory": history.render,
    "Relax": relax.render,
    "Map": map_page.render,
    "Photobooth": photobooth.render,
    "???": secret.render,
}

with st.sidebar:
    choice = render_sidebar()

PAGES[choice]()
