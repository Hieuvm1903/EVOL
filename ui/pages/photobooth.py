import pandas as pd
import streamlit as st
from PIL import Image

from config import PHOTO_FILTERS, TIMEZONE
from services import photos_service
from utils.image_filters import apply_filter


def _render_capture() -> None:
    col1, col2 = st.columns([1, 1])

    with col1:
        camera_photo = st.camera_input("Take a photo")

    with col2:
        filter_name = st.selectbox("Filter", PHOTO_FILTERS)
        caption = st.text_input("Caption (optional)")

        if camera_photo is not None:
            original = Image.open(camera_photo)
            preview = apply_filter(original, filter_name)
            st.image(preview, caption="Preview", use_container_width=True)

            if st.button("💾 Save to gallery", key="save_photo"):
                photos_service.save_photo(preview, caption.strip(), filter_name)
                st.success("Saved!")
                st.rerun()


def _render_gallery() -> None:
    st.markdown("### Gallery")
    photos_df = photos_service.get_photos()

    if photos_df.empty:
        st.info("No photos yet — take one above!")
        return

    photos_df["time"] = pd.to_datetime(photos_df["time"])
    photos_df["time"] = photos_df.apply(lambda row: row["time"].astimezone(TIMEZONE), axis=1)
    photos_df = photos_df.sort_values("time", ascending=False)

    cols = st.columns(3)
    for i, (_, row) in enumerate(photos_df.iterrows()):
        with cols[i % 3]:
            path = photos_service.photo_path(row["filename"])
            st.image(path, use_container_width=True)
            st.markdown(
                f'<div class="evol-card-meta">{row["time"].strftime("%m/%d/%Y %H:%M")} · {row["filter"]}</div>',
                unsafe_allow_html=True,
            )
            if row["caption"]:
                st.markdown(f'<div class="evol-card-body">{row["caption"]}</div>', unsafe_allow_html=True)
            if st.button("🗑️ Delete", key=f"del_photo_{row['id']}"):
                photos_service.delete_photo(int(row["id"]))
                st.rerun()


def render() -> None:
    st.markdown("## 📸 Photobooth")
    st.caption("Snap a pic, add a filter, save it to your gallery.")

    _render_capture()
    st.markdown("---")
    _render_gallery()
