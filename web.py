import streamlit as st
from streamlit_option_menu import option_menu
import streamlit.components.v1 as html
import folium
from streamlit_folium import st_folium
import numpy as np
import pandas as pd
from image import *
from music import *
import music
from data import *
import pytz

st.set_page_config(
    page_title="EVOL Space",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global styling
# ---------------------------------------------------------------------------
hide_streamlit_style = """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

            html, body, [class*="css"]  {
                font-family: 'Poppins', sans-serif;
            }

            header {visibility: hidden;}
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
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
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

timezone = pytz.timezone("Asia/Ho_Chi_Minh")  # Replace with your desired timezone

# Icon choices for map markers: label shown in the UI -> Font Awesome icon name
ICON_CHOICES = {
    "📍 Marker": "map-marker",
    "🏠 Home": "home",
    "⭐ Star": "star",
    "❤️ Heart": "heart",
    "☕ Cafe": "coffee",
    "🌳 Park / Nature": "tree",
    "🍽️ Food": "cutlery",
    "🏨 Hotel": "bed",
    "🎓 School": "graduation-cap",
    "🎁 Gift": "gift",
    "🚩 Flag": "flag",
    "🎵 Music": "music",
}
ICON_COLORS = ["red", "blue", "green", "purple", "orange", "darkred", "cadetblue", "pink"]

with st.sidebar:
    choose = option_menu(
        "EVOL Space",
        ["Home", "About", "His-tory", "Relax", "Map", "???"],
        icons=['person-rolodex', 'lightbulb', 'menu-button', 'bell', 'geo-alt', 'door-open'],
        menu_icon="app-indicator", default_index=0,
        styles={
            "container": {"padding": "5!important", "background-color": "#0c0c0c"},
            "icon": {"color": "orange", "font-size": "25px"},
            "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#1f1f1f"},
            "nav-link-selected": {"background-color": "#02ab21"},
        }
    )

if choose == "Home":
    """
    Từng đau khổ mới biết thế nào là đau khổ.\n
    Từng chấp trước mới có thể rũ bỏ được chấp trước.\n
    Từng vấn vương mới có thể không còn vấn vương!"""
    html.html(
        """
  <iframe src="https://www.facebook.com/plugins/post.php?href=https%3A%2F%2Fwww.facebook.com%2Fphoto%2F%3Ffbid%3D1423943031364508%26set%3Da.167615383663952&width=750&show_text=true&height=499&appId"
  width="700" height="400" style="border:none;overflow:hidden" scrolling="no" frameborder="0" allowfullscreen="true" allow="autoplay; clipboard-write;
  encrypted-media; picture-in-picture; web-share"></iframe>
""",
        height=400, width=700
    )

    html.html("""
<div id="fb-root"></div>
<script async defer crossorigin="anonymous" src="https://connect.facebook.net/vi_VN/sdk.js#xfbml=1&version=v18.0" nonce="UhxLsFD4"></script><div class="fb-comments" data-href="https://www.facebook.com/photo/?fbid=1423943031364508&amp;set=a.167615383663952https://www.facebook.com/photo/?fbid=1423943031364508&amp;set=a.167615383663952" data-width="750" data-numposts="5"></div>
<div class="fb-comments" data-href="https://ev-l0-3.streamlit.app" data-width="750" data-numposts="5"></div>""",
                   height=300, width=900, scrolling=True)
    "---"

elif choose == "About":
    facebook_page_url = 'https://www.facebook.com/evbinl/'
    # (about content goes here)

elif choose == "His-tory":
    pop = music.music
    anime = music.anime
    bendy = music.bendy
    tab1, tab2, tab3 = st.tabs(["Linh tinh", "Anime", "Bendy"])
    with tab1:
        for m in pop:
            st.write(m[0])
            st_player(m[1])
    with tab2:
        for m in anime:
            st.write(m[0])
            st_player(m[1])
    with tab3:
        for m in bendy:
            st.write(m[0])
            st_player(m[1])

elif choose == "Relax":
    s = st.text_area('Tâm sự vào đây (Ẩn danh 100%)', '''

    ''')

    def onclick():
        write("{" + s + "}")
        st.rerun()

    st.button('Submit', key='submit', on_click=onclick)
    content = getwrite()
    if not content.empty:
        content['time'] = pd.to_datetime(content["time"])
        content['time'] = content.apply(lambda row: row['time'].astimezone(timezone), axis=1)
        df = content.sort_values(by='time', ascending=False)
        for _, row in df.iterrows():
            st.markdown(
                f"""
                <div class="evol-card">
                    <div class="evol-card-meta">{row['time'].strftime('%m/%d/%Y, %H:%M:%S')}</div>
                    <div class="evol-card-body">{row['content']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

elif choose == "Map":
    st.markdown("## 📍 Places")
    st.caption("Save spots you care about — paste coordinates, add a description, pick an icon.")

    with st.expander("➕ Add a new place", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            place_name = st.text_input("Place name", placeholder="e.g. Hồ Gươm")
            coord_str = st.text_input(
                "Paste coordinates (lat, lon)",
                placeholder="21.0285, 105.8542",
                help="Paste a 'lat, lon' pair — e.g. copied straight out of Google Maps."
            )
        with col2:
            icon_label = st.selectbox("Icon", list(ICON_CHOICES.keys()))
            icon_color = st.selectbox("Color", ICON_COLORS)
        place_desc = st.text_area("Description", placeholder="Why this place matters...")

        if st.button("Save place", key="save_place"):
            if not coord_str.strip():
                st.warning("Please paste coordinates first.")
            else:
                try:
                    lat_str, lon_str = coord_str.split(",")
                    lat, lon = float(lat_str.strip()), float(lon_str.strip())
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        raise ValueError("Latitude must be -90..90 and longitude -180..180")
                    add_place(
                        place_name.strip() or "Untitled place",
                        lat, lon,
                        place_desc.strip(),
                        f"{ICON_CHOICES[icon_label]}|{icon_color}",
                    )
                    st.success("Place saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't parse coordinates ({e}). Use the format: lat, lon")

    places_df = get_places()

    m = folium.Map(location=[16.0, 106.0], zoom_start=5, tiles="CartoDB positron")
    if not places_df.empty:
        for _, row in places_df.iterrows():
            icon_name, icon_color = (
                row['icon'].split("|") if row['icon'] and "|" in str(row['icon']) else ("map-marker", "blue")
            )
            popup_html = f"<b>{row['name']}</b><br>{row['description'] or ''}"
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=row['name'],
                icon=folium.Icon(color=icon_color, icon=icon_name, prefix="fa"),
            ).add_to(m)
        bounds = places_df[['lat', 'lon']].agg(['min', 'max'])
        m.fit_bounds([[bounds['lat']['min'], bounds['lon']['min']],
                      [bounds['lat']['max'], bounds['lon']['max']]])

    st_folium(m, width=None, height=520, key="places_map")

    if not places_df.empty:
        st.markdown("### Saved places")
        places_df['time'] = pd.to_datetime(places_df["time"])
        places_df['time'] = places_df.apply(lambda row: row['time'].astimezone(timezone), axis=1)
        for _, row in places_df.sort_values('time', ascending=False).iterrows():
            c1, c2 = st.columns([6, 1])
            with c1:
                st.markdown(
                    f"""
                    <div class="evol-card">
                        <div class="evol-card-title">{row['name']}</div>
                        <div class="evol-card-meta">{row['lat']:.5f}, {row['lon']:.5f} · {row['time'].strftime('%m/%d/%Y %H:%M')}</div>
                        <div class="evol-card-body">{row['description'] or ''}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c2:
                if st.button("🗑️", key=f"del_{row['id']}"):
                    delete_place(int(row['id']))
                    st.rerun()
    else:
        st.info("No places saved yet — add your first one above.")

elif choose == "???":
    col1, col2 = st.columns([1, 3])
    with col1:
        keys = st.text_input("Key???", "/Evolut??n")
    with col2:
        s = st.text_area('My thought', '''
    ''')
    btn = st.button('Submit', key='submit')
    if btn:
        if "/Evolut!0n" in keys:
            blog(s.strip())
            st.success("Posted!!!")
            st.rerun()
        else:
            st.warning("Don't ya remember it, EVOL?")
    content = getblog()
    if not content.empty:
        content['time'] = pd.to_datetime(content["time"])
        content['time'] = content.apply(lambda row: row['time'].astimezone(timezone), axis=1)
        df = content.sort_values(by='time', ascending=False)
        for _, row in df.iterrows():
            st.markdown(
                f"""
                <div class="evol-card">
                    <div class="evol-card-meta">{row['time'].strftime('%m/%d/%Y, %H:%M:%S')}</div>
                    <div class="evol-card-body">{row['content']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )