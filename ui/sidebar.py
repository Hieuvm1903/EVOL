from streamlit_option_menu import option_menu

from config import MENU_OPTIONS, MENU_ICONS


def render_sidebar() -> str:
    """Render the sidebar nav and return the chosen tab label."""
    return option_menu(
        "EVOL Space",
        MENU_OPTIONS,
        icons=MENU_ICONS,
        menu_icon="app-indicator",
        default_index=0,
        styles={
            "container": {"padding": "5!important", "background-color": "#0c0c0c"},
            "icon": {"color": "orange", "font-size": "25px"},
            "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#1f1f1f"},
            "nav-link-selected": {"background-color": "#02ab21"},
        },
    )
