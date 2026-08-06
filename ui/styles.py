import streamlit as st

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"]  {
    font-family: 'Poppins', sans-serif;
}

header[data-testid="stHeader"] {
    background: transparent;
    z-index: 100; /* keep it below the drawer, which now sits above it */
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Sidebar collapse/expand toggle — kept visible, styled to match the theme */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"] {
    visibility: visible !important;
    background: #161616;
    border: 1px solid #02ab21;
    border-radius: 8px;
    padding: 4px;
}
[data-testid="stExpandSidebarButton"] svg,
[data-testid="stSidebarCollapseButton"] svg {
    fill: #02ab21;
}
footer:after {
    content:'Made by EVOL';
    visibility: visible;
    display: block;
    position: relative;
    padding: 5px;
    top: 2px;
}

.main .block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1100px;
}

h1, h2, h3 {
    font-weight: 600;
}

.evol-card {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 14px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.25);
    transition: transform 0.15s ease, border-color 0.15s ease;
}
.evol-card:hover {
    transform: translateY(-2px);
    border-color: #02ab21;
}
.evol-card-title {
    font-size: 1.05rem;
    font-weight: 600;
    margin-bottom: 4px;
}
.evol-card-meta {
    font-size: 0.78rem;
    color: #9a9a9a;
    margin-bottom: 8px;
}
.evol-card-body {
    font-size: 0.95rem;
    color: #e6e6e6;
    white-space: pre-wrap;
}

.stButton>button {
    border-radius: 10px;
    font-weight: 500;
    border: 1px solid #02ab21;
}
.stButton>button:hover {
    background-color: #02ab21;
    color: white;
    border-color: #02ab21;
}

div[data-testid="stExpander"] {
    border-radius: 12px;
    border: 1px solid #2a2a2a;
}



.st-key-now_playing_drawer {
    position: fixed;
    top: 4.5rem;
    right: 1.25rem;
    z-index: 999999; /* must clear Streamlit's own header/toolbar layer */
    width: 300px;
    will-change: transform;
    transition: box-shadow 0.15s ease;
}

.st-key-now_playing_drawer iframe {
    width: 100% !important;
    border: none !important;
    background: transparent !important;
}
.st-key-now_playing_drawer.evol-dragging {
    transition: none !important;
    will-change: transform;
    filter: drop-shadow(0 10px 26px rgba(0,0,0,0.55));
}

</style>
"""


def inject_global_css() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def render_card(title: str | None, meta: str, body: str) -> None:
    """Reusable dark 'card' block used by Relax, the secret blog, and Places."""
    title_html = f'<div class="evol-card-title">{title}</div>' if title else ""
    st.markdown(
        f"""
        <div class="evol-card">
            {title_html}
            <div class="evol-card-meta">{meta}</div>
            <div class="evol-card-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
