import streamlit as st
from streamlit_option_menu import option_menu

DEFAULT_OPTIONS = ["Home", "Photobooth", "About", "His-tory", "Relax", "???"]
DEFAULT_ICONS = ['person-rolodex', 'camera', 'lightbulb', 'menu-button', 'bell','door-open']

DEFAULT_STYLES = {
    "container": {"padding": "5!important", "background-color": "#0c0c0c"},
    "icon": {"color": "orange", "font-size": "20px"},
    "nav-link": {"font-size": "14px", "text-align": "left", "margin":"6px", "--hover-color": "#eee"},
    "nav-link-selected": {"background-color": "#02ab21"},
}


def ensure_state():
    """Ensure required session state keys exist."""
    if 'choose' not in st.session_state:
        st.session_state.choose = DEFAULT_OPTIONS[0]


def render_menu():
    """Always render a horizontal top menu and return the selected choice."""
    options = DEFAULT_OPTIONS
    icons = DEFAULT_ICONS

    # Determine start index
    try:
        start_index = options.index(st.session_state.get('choose', options[0]))
    except ValueError:
        start_index = 0

    # horizontal menu fixed at top
    choice = option_menu(None, options, icons=icons, default_index=start_index, orientation='horizontal', styles=DEFAULT_STYLES)
    st.session_state.choose = choice
    return st.session_state.choose
