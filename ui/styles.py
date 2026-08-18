import streamlit as st

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

html, body, [class*="css"]  {
    font-family: 'Be Vietnam Pro', sans-serif;
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
/* ---------------------------------------------------------------------
   Sidebar redesign
--------------------------------------------------------------------- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0f0f 0%, #0a0a0a 100%);
    border-right: 1px solid #1f1f1f;
}

.evol-sidebar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 4px 22px;
    margin-bottom: 6px;
    border-bottom: 1px solid #232323;
}
.evol-sidebar-brand-icon {
    font-size: 1.5rem;
    filter: drop-shadow(0 0 6px rgba(2, 171, 33, 0.55));
}
.evol-sidebar-brand-text {
    font-family: 'Be Vietnam Pro', sans-serif;
    font-weight: 700;
    font-size: 1.15rem;
    letter-spacing: 0.02em;
    background: linear-gradient(90deg, #ffffff, #9be8a8);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}

/* Section headers ("Home", "Account", "Explore") */
[data-testid="stSidebarNav"] [data-testid="stSidebarNavSectionHeader"],
section[data-testid="stSidebar"] .st-emotion-cache-1cypcdb,
section[data-testid="stSidebar"] p:has(+ ul) {
    font-family: 'Be Vietnam Pro', sans-serif;
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #6f6f6f !important;
    padding: 14px 8px 6px !important;
}

/* Nav links */
[data-testid="stSidebarNav"] a,
section[data-testid="stSidebar"] li a {
    display: flex;
    align-items: center;
    gap: 10px;
    border-radius: 10px;
    padding: 9px 12px !important;
    margin: 2px 4px;
    font-family: 'Be Vietnam Pro', sans-serif;
    font-size: 0.92rem;
    font-weight: 500;
    color: #b8b8b8 !important;
    transition: background 0.15s ease, color 0.15s ease, transform 0.1s ease;
}
[data-testid="stSidebarNav"] a:hover,
section[data-testid="stSidebar"] li a:hover {
    background: #1a1a1a;
    color: #ffffff !important;
    transform: translateX(2px);
}

/* Active/current page */
[data-testid="stSidebarNav"] a[aria-current="page"],
section[data-testid="stSidebar"] li a[aria-current="page"] {
    background: linear-gradient(90deg, #02ab21, #029a1d);
    color: #ffffff !important;
    font-weight: 600;
    box-shadow: 0 2px 10px rgba(2, 171, 33, 0.35);
}
[data-testid="stSidebarNav"] a[aria-current="page"] span,
[data-testid="stSidebarNav"] a[aria-current="page"] [data-testid="stIconMaterial"] {
    color: #ffffff !important;
}

/* Icons */
[data-testid="stSidebarNav"] [data-testid="stIconMaterial"] {
    font-size: 1.1rem !important;
    color: #7a7a7a;
}
[data-testid="stSidebarNav"] a:hover [data-testid="stIconMaterial"] {
    color: #3ddc57;
}

/* Thin scrollbar for long nav lists, matches queue-list styling elsewhere */
section[data-testid="stSidebar"] ::-webkit-scrollbar { width: 6px; }
section[data-testid="stSidebar"] ::-webkit-scrollbar-track { background: #141414; }
section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #02ab21, #017a17);
    border-radius: 4px;
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
.evol-hero {
    text-align: center;
    padding: 24px 12px 32px;
}
.evol-hero-title {
    font-family: 'Be Vietnam Pro', sans-serif;
    font-size: 3.2rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    background: linear-gradient(90deg, #02ab21, #3ddc57 45%, #02ab21);
    background-size: 200% auto;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    animation: evol-shine 6s linear infinite;
    margin-bottom: 18px;
}
@keyframes evol-shine {
    to { background-position: 200% center; }
}
.evol-hero-quote p {
    font-family: 'Be Vietnam Pro', sans-serif;
    font-style: italic;
    font-weight: 400;
    font-size: 1.45rem;
    line-height: 1.9;
    color: #d8d8d8;
    margin: 0 0 6px;
    letter-spacing: 0.01em;
}
.evol-hero-quote p:last-child {
    color: #02ab21;
    font-weight: 600;
    font-style: normal;
}

/* Facebook embed — cropped to just the photo, no like/comment/share bar
   or comment box underneath. The iframe renders at its natural full
   height (so the photo itself lays out correctly); the wrapper below it
   just clips everything past FB_EMBED_VISIBLE_HEIGHT. */
.evol-fb-embed {
    max-width: 750px;
    height: var(--fb-visible-height, 420px);
    margin: 0 auto 20px;
    overflow: hidden;
    border-radius: 14px;
    border: 1px solid #2a2a2a;
    background: #161616;
    box-shadow: 0 2px 10px rgba(0,0,0,0.25);
    position: relative;
}
.evol-fb-embed iframe {
    max-width: 100%;
    position: absolute;
    top: 0;
    left: 0;
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



div[class*="st-key-pl_row_"] div[data-testid="stHorizontalBlock"],
div[class*="st-key-trk_row_"] div[data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    gap: 6px !important;
}
div[class*="st-key-pl_row_"] div[data-testid="stColumn"],
div[class*="st-key-trk_row_"] div[data-testid="stColumn"] {
    min-width: 0 !important;
}
/* Name/title button: truncate instead of wrapping to a 2nd line */
div[class*="st-key-pl_row_"] .stButton>button p {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
 
/* Tighter playlist "cards" — the default bordered container has a
   lot of built-in padding/margin, which was the main source of the
   "too much space" feel. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    padding: 4px 14px !important;
    margin-bottom: 6px !important;
}
 
/* Popover sizing: wider and shorter, and left anchored to its
   trigger button (not pinned to a fixed spot on screen) so it opens
   right next to whatever "⋮" you clicked.
 
   Note: this trades away the earlier fix for popovers that flip to
   open *upward* near the bottom of the screen — if one opens up and
   there isn't enough room above the trigger, its top can still end
   up clipped above the viewport. Shortening max-height (below)
   reduces how often that happens, since a shorter panel needs less
   room to fully fit above the button. */
div[data-testid="stPopoverBody"] {
    width: 380px !important;
    max-width: 92vw !important;
    max-height: 320px !important;
    overflow-y: auto !important;
}
 
/* Icon-only buttons in these tight rows: keep them compact and
   vertically centered instead of stretching to match the name
   button's height. */
div[class*="st-key-pl_row_"] .stButton>button,
div[class*="st-key-trk_row_"] .stButton>button {
    padding: 4px 10px;
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
