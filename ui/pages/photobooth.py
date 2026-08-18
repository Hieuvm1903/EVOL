import io
import time
import uuid

import pandas as pd
import streamlit as st
from PIL import Image

from config import PHOTO_FILTERS, TIMEZONE
from services import photos_service
from utils.image_filters import apply_filter

# streamlit-webrtc + av power both Timer and Gesture mode. These pull in
# compiled extensions that can be finicky on some local Windows setups, so
# they're imported lazily; the app falls back to plain click-to-capture if
# they're not importable rather than crashing.
try:
    from streamlit_webrtc import webrtc_streamer
    from utils.timer_capture import TimerCaptureProcessor, RTC_CONFIGURATION as TIMER_RTC_CONFIGURATION
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False

# Gesture mode additionally needs mediapipe + opencv on top of webrtc/av.
try:
    import cv2
    from utils.gesture_capture import GestureCaptureProcessor, RTC_CONFIGURATION
    GESTURE_CAPTURE_AVAILABLE = WEBRTC_AVAILABLE
except ImportError:
    GESTURE_CAPTURE_AVAILABLE = False

TIMER_OPTIONS = [3, 5, 10]  # seconds

POSE_OPTIONS = {
    "🖐️ Open palm": "open_palm",
    "✌️ Peace sign": "peace",
    "👍 Thumbs up": "thumbs_up",
    "✊ Fist": "fist",
    "🤖 Any recognized pose": "any",
}
POSE_LABELS = {v: k for k, v in POSE_OPTIONS.items()}


def _render_click_capture() -> None:
    camera_photo = st.camera_input("Take a photo")
    if camera_photo is not None:
        st.session_state["photobooth_raw_image"] = Image.open(camera_photo)


def _render_timer_capture() -> None:
    st.caption("⏱️ Live preview below — pick a countdown, hit start, strike your pose!")
    ctx = webrtc_streamer(
        key="timer-photobooth",
        video_processor_factory=TimerCaptureProcessor,
        rtc_configuration=TIMER_RTC_CONFIGURATION,
        media_stream_constraints={"video": True, "audio": False},
    )

    seconds = st.select_slider("Countdown (seconds)", options=TIMER_OPTIONS, value=3, key="timer_seconds")

    if not ctx.video_processor:
        st.caption("Waiting for the camera to connect…")
        return

    if st.button("Start countdown", key="start_timer", icon=":material/timer:"):
        countdown_ph = st.empty()
        for remaining in range(seconds, 0, -1):
            countdown_ph.markdown(f"## {remaining}…")
            time.sleep(1)
        countdown_ph.markdown("## 📸")

        with ctx.video_processor.lock:
            frame = ctx.video_processor.latest_frame  # already RGB

        countdown_ph.empty()
        if frame is not None:
            st.session_state["photobooth_raw_image"] = Image.fromarray(frame)
            st.toast("Captured! Scroll down to preview and edit.")
        else:
            st.warning("No frame captured yet — make sure the camera feed above is running, then try again.")


def _render_gesture_capture() -> None:
    pose_label = st.selectbox("Pose to trigger capture", list(POSE_OPTIONS.keys()), key="gesture_pose_choice")
    target_pose = POSE_OPTIONS[pose_label]
    st.caption(f"Hold **{pose_label}** steady for about a second to snap a photo.")

    ctx = webrtc_streamer(
        key="gesture-photobooth",
        video_processor_factory=GestureCaptureProcessor,
        rtc_configuration=RTC_CONFIGURATION,
        media_stream_constraints={"video": True, "audio": False},
    )

    if not ctx.video_processor:
        return

    ctx.video_processor.target_pose = target_pose  # may change between reruns

    with ctx.video_processor.lock:
        frame = ctx.video_processor.captured_frame
        detected = ctx.video_processor.detected_pose
        if frame is not None:
            ctx.video_processor.captured_frame = None  # consume it
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            st.session_state["photobooth_raw_image"] = Image.fromarray(rgb)
            st.toast("Captured! Scroll down to preview and edit.")

    if detected:
        st.caption(f"Currently detected: {POSE_LABELS.get(detected, detected)}")


def _render_capture_modes() -> None:
    mode_options = ["📷 Click to capture"]
    if WEBRTC_AVAILABLE:
        mode_options.append("⏱️ Timer capture")
    if GESTURE_CAPTURE_AVAILABLE:
        mode_options.append("🖐️ Gesture capture (pose match)")

    if len(mode_options) > 1:
        mode = st.radio("Capture mode", mode_options, horizontal=True)
    else:
        mode = mode_options[0]
        st.caption(
            "⏱️/🖐️ Timer and Gesture capture are disabled — the optional "
            "`streamlit-webrtc` / `mediapipe` packages aren't installed (or "
            "failed to import). See requirements-gesture.txt to enable them."
        )

    if mode == "📷 Click to capture":
        _render_click_capture()
    elif mode == "⏱️ Timer capture":
        _render_timer_capture()
    else:
        _render_gesture_capture()


def _render_edit_and_export(user) -> None:
    """Filter, preview, download — all anonymous. Saving to the gallery
    additionally requires being logged in."""
    filter_name = st.selectbox("Filter", PHOTO_FILTERS)
    caption = st.text_input("Caption (optional)")

    raw_image = st.session_state.get("photobooth_raw_image")
    if raw_image is None:
        return

    preview = apply_filter(raw_image, filter_name)
    st.image(preview, caption="Preview", use_container_width=True)

    buf = io.BytesIO()
    preview.convert("RGB").save(buf, format="JPEG", quality=90)
    download_col, save_col = st.columns(2)

    with download_col:
        st.download_button(
            "Download",
            data=buf.getvalue(),
            file_name=f"evol-photobooth-{uuid.uuid4().hex[:8]}.jpg",
            mime="image/jpeg",
            icon=":material/download:",
            use_container_width=True,
        )

    with save_col:
        if user:
            if st.button("Save to gallery", key="save_photo", icon=":material/save:", use_container_width=True):
                photos_service.save_photo(user["id"], preview, caption.strip(), filter_name)
                st.session_state["photobooth_raw_image"] = None
                st.success("Saved!")
                st.rerun()
        else:
            st.button(
                "Log in to save", key="save_photo_locked", icon=":material/lock:",
                use_container_width=True, disabled=True,
                help="Log in (see the Login tab) to save photos to a personal gallery.",
            )


def _render_gallery(user_id: int) -> None:
    st.markdown("### Gallery")
    photos_df = photos_service.get_photos(user_id)

    if photos_df.empty:
        st.info("No photos yet — take one above and save it!")
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
    if user:
        st.caption("Snap a pic — by clicking, on a timer, or with a gesture — add a filter, download it or save it to your gallery.")
    else:
        st.caption("Snap a pic, add a filter, and download it — no account needed. Log in (see the Login tab) if you want it saved to a personal gallery too.")

    col1, col2 = st.columns([1, 1])
    with col1:
        _render_capture_modes()
    with col2:
        _render_edit_and_export(user)

    st.markdown("---")
    if user:
        _render_gallery(user["id"])
    else:
        st.info(
            "Log in (see the Login tab) to see and manage a personal photo gallery.",
            icon=":material/lock:",
        )