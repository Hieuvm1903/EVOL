import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from config import PLACE_ICON_CHOICES, PLACE_ICON_COLORS, TIMEZONE
from services import places_service
from ui.styles import render_card


def _render_add_form() -> None:
    with st.expander("Add a new place", icon=":material/add_location:", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            place_name = st.text_input("Place name", placeholder="e.g. Hồ Gươm")
            coord_str = st.text_input(
                "Paste coordinates (lat, lon)",
                placeholder="21.0285, 105.8542",
                help="Paste a 'lat, lon' pair — e.g. copied straight out of Google Maps.",
            )
        with col2:
            icon_label = st.selectbox("Icon", list(PLACE_ICON_CHOICES.keys()))
            icon_color = st.selectbox("Color", PLACE_ICON_COLORS)
        place_desc = st.text_area("Description", placeholder="Why this place matters...")

        if st.button("Save place", key="save_place", icon=":material/save:"):
            if not coord_str.strip():
                st.warning("Please paste coordinates first.")
                return
            try:
                lat_str, lon_str = coord_str.split(",")
                lat, lon = float(lat_str.strip()), float(lon_str.strip())
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    raise ValueError("Latitude must be -90..90 and longitude -180..180")
                places_service.add_place(
                    place_name.strip() or "Untitled place",
                    lat, lon,
                    place_desc.strip(),
                    f"{PLACE_ICON_CHOICES[icon_label]}|{icon_color}",
                )
                st.success("Place saved!")
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't parse coordinates ({e}). Use the format: lat, lon")


def _render_map(places_df: pd.DataFrame) -> None:
    m = folium.Map(location=[16.0, 106.0], zoom_start=5, tiles="CartoDB positron")
    if not places_df.empty:
        for _, row in places_df.iterrows():
            icon_name, icon_color = (
                row["icon"].split("|") if row["icon"] and "|" in str(row["icon"]) else ("map-marker", "blue")
            )
            popup_html = f"<b>{row['name']}</b><br>{row['description'] or ''}"
            folium.Marker(
                location=[row["lat"], row["lon"]],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=row["name"],
                icon=folium.Icon(color=icon_color, icon=icon_name, prefix="fa"),
            ).add_to(m)
        bounds = places_df[["lat", "lon"]].agg(["min", "max"])
        m.fit_bounds([[bounds["lat"]["min"], bounds["lon"]["min"]],
                      [bounds["lat"]["max"], bounds["lon"]["max"]]])
    st_folium(m, width=None, height=520, key="places_map")


def _render_list(places_df: pd.DataFrame) -> None:
    if places_df.empty:
        st.info("No places saved yet — add your first one above.")
        return

    st.markdown("### Saved places")
    places_df["time"] = pd.to_datetime(places_df["time"])
    places_df["time"] = places_df.apply(lambda row: row["time"].astimezone(TIMEZONE), axis=1)
    for _, row in places_df.sort_values("time", ascending=False).iterrows():
        c1, c2 = st.columns([6, 1])
        with c1:
            render_card(
                title=row["name"],
                meta=f"{row['lat']:.5f}, {row['lon']:.5f} · {row['time'].strftime('%m/%d/%Y %H:%M')}",
                body=row["description"] or "",
            )
        with c2:
            if st.button("", key=f"del_{row['id']}", icon=":material/delete:", help="Delete this place"):
                places_service.delete_place(int(row["id"]))
                st.rerun()


def render() -> None:
    st.markdown("## :material/location_on: Places")
    st.caption("Save spots you care about — paste coordinates, add a description, pick an icon.")

    _render_add_form()
    places_df = places_service.get_places()
    _render_map(places_df)
    _render_list(places_df)
