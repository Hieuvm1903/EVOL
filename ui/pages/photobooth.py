import pandas as pd
import streamlit as st
from PIL import Image

from config import PHOTO_FILTERS, TIMEZONE
from services import photos_service
from utils.image_filters import apply_filter

# Gesture capture needs streamlit-webrtc + mediapipe (+ opencv, av). These
# pull in compiled/Rust extensions that can be finicky on some local Windows
# setups. Import them lazily and fall back to click-only capture if they're
# not importable, rather than crashing the whole app.
try:
    import cv2
    from streamlit_webrtc import webrtc_streamer
    from utils.gesture_capture import GestureCaptureProcessor, RTC_CONFIGURATION
    GESTURE_CAPTURE_AVAILABLE = True
except ImportError:
    GESTURE_CAPTURE_AVAILABLE = False


def _render_click_capture() -> None:
    camera_photo = st.camera_input("Take a photo")
    if camera_photo is not None:
        st.session_state["photobooth_raw_image"] = Image.open(camera_photo)


def _render_gesture_capture() -> None:
    st.caption("🖐️ Hold an open palm up to the camera and keep it steady for about a second.")
    ctx = webrtc_streamer(
        key="gesture-photobooth",
        video_processor_factory=GestureCaptureProcessor,
        rtc_configuration=RTC_CONFIGURATION,
        media_stream_constraints={"video": True, "audio": False},
    )

    if ctx.video_processor:
        with ctx.video_processor.lock:
            frame = ctx.video_processor.captured_frame
            if frame is not None:
                ctx.video_processor.captured_frame = None  # consume it
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                st.session_state["photobooth_raw_image"] = Image.fromarray(rgb)
                st.toast("Captured! Scroll down to preview and save.")


def _render_capture(user_id: int) -> None:
    if GESTURE_CAPTURE_AVAILABLE:
        mode = st.radio(
            "Capture mode",
            ["📷 Click to capture", "🖐️ Gesture capture (open palm)"],
            horizontal=True,
        )
    else:
        mode = "📷 Click to capture"
        st.caption(
            "🖐️ Gesture capture is disabled — the optional `streamlit-webrtc` / "
            "`mediapipe` packages aren't installed (or failed to import). "
            "See requirements-gesture.txt to enable it."
        )

    col1, col2 = st.columns([1, 1])
    with col1:
        if mode == "📷 Click to capture":
            _render_click_capture()
        else:
            _render_gesture_capture()

    with col2:
        filter_name = st.selectbox("Filter", PHOTO_FILTERS)
        caption = st.text_input("Caption (optional)")

        raw_image = st.session_state.get("photobooth_raw_image")
        if raw_image is not None:
            preview = apply_filter(raw_image, filter_name)
            st.image(preview, caption="Preview", use_container_width=True)

            if st.button("Save to gallery", key="save_photo", icon=":material/save:"):
                photos_service.save_photo(user_id, preview, caption.strip(), filter_name)
                st.session_state["photobooth_raw_image"] = None
                st.success("Saved!")
                st.rerun()


def _render_gallery(user_id: int) -> None:
    st.markdown("### Gallery")
    photos_df = photos_service.get_photos(user_id)

    if photos_df.empty:
        st.info("No photos yet — take one above!")
        return

    photos_df["time"] = pd.to_datetime(photos_df["time"])
    photos_df["time"] = photos_df.apply(lambda row: row["time"].astimezone(TIMEZONE), axis=1)
    photos_df = photos_df.sort_values("time", ascending=False)

    cols = st.columns(3)
    for i, (_, row) in enumerate(photos_df.iterrows()):
        with cols[i % 3]:
            source = photos_service.get_photo_source(row["filename"])
            if source is not None:
                st.image(source, use_container_width=True)
            else:
                st.warning("Photo file missing.")
            st.markdown(
                f'<div class="evol-card-meta">{row["time"].strftime("%m/%d/%Y %H:%M")} · {row["filter"]}</div>',
                unsafe_allow_html=True,
            )
            if row["caption"]:
                st.markdown(f'<div class="evol-card-body">{row["caption"]}</div>', unsafe_allow_html=True)
            if st.button("Delete", key=f"del_photo_{row['id']}", icon=":material/delete:"):
                photos_service.delete_photo(int(row["id"]), user_id)
                st.rerun()


def render() -> None:
    st.markdown("## :material/photo_camera: Photobooth")

    user = st.session_state.get("user")
    if not user:
        st.warning(
            "Log in first (see the Login tab) — your gallery is personal to your account.",
            icon=":material/lock:",
        )
        return

    st.caption("Snap a pic — by clicking or with a gesture — add a filter, save it to your gallery.")

    _render_capture(user["id"])
    st.markdown("---")
    _render_gallery(user["id"])