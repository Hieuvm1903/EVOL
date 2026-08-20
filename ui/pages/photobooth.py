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

# Crop + before/after compare are both optional extras — page still works
# (just without those two widgets) if either package isn't installed.
try:
    from streamlit_cropper import st_cropper
    CROPPER_AVAILABLE = True
except ImportError:
    CROPPER_AVAILABLE = False

try:
    from streamlit_image_comparison import image_comparison
    COMPARISON_AVAILABLE = True
except ImportError:
    COMPARISON_AVAILABLE = False

TIMER_OPTIONS = [3, 5, 10]  # seconds

POSE_OPTIONS = {
    "🖐️ Open palm": "open_palm",
    "✌️ Peace sign": "peace",
    "👍 Thumbs up": "thumbs_up",
    "✊ Fist": "fist",
    "🤖 Any recognized pose": "any",
}
POSE_LABELS = {v: k for k, v in POSE_OPTIONS.items()}


def _set_raw_image(img: Image.Image) -> None:
    """Every capture path (click/timer/gesture/upload) funnels through
    here. Bumping the version counter forces a brand-new st_cropper
    widget instance below (its key includes the version) — without this,
    a fresh photo would still show the *previous* photo's crop box/region
    until manually reset, since st_cropper otherwise keeps its own state
    keyed only by widget key."""
    st.session_state["photobooth_raw_image"] = img.convert("RGB")
    st.session_state["photobooth_image_version"] = st.session_state.get("photobooth_image_version", 0) + 1


def _render_click_capture() -> None:
    camera_photo = st.camera_input("Take a photo")
    if camera_photo is not None:
        _set_raw_image(Image.open(camera_photo))


def _render_upload_capture() -> None:
    st.caption("🧪 Temporary: upload any image to test crop/filters/compare without a camera.")
    uploaded = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg", "webp"], key="photobooth_upload")
    if uploaded is not None:
        # Only re-set (and bump the crop version) when it's actually a new
        # upload, not on every rerun the uploader widget survives.
        upload_sig = (uploaded.name, uploaded.size)
        if st.session_state.get("photobooth_upload_sig") != upload_sig:
            st.session_state["photobooth_upload_sig"] = upload_sig
            _set_raw_image(Image.open(uploaded))


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
            _set_raw_image(Image.fromarray(frame))
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
            _set_raw_image(Image.fromarray(rgb))
            st.toast("Captured! Scroll down to preview and edit.")

    if detected:
        st.caption(f"Currently detected: {POSE_LABELS.get(detected, detected)}")


def _render_capture_modes() -> None:
    mode_options = ["📷 Click to capture"]
    if WEBRTC_AVAILABLE:
        mode_options.append("⏱️ Timer capture")
    if GESTURE_CAPTURE_AVAILABLE:
        mode_options.append("🖐️ Gesture capture (pose match)")
    mode_options.append("🧪 Upload (test)")  # temporary — see docstring on _render_upload_capture

    mode = st.radio("Capture mode", mode_options, horizontal=True)

    if not WEBRTC_AVAILABLE:
        st.caption(
            "⏱️/🖐️ Timer and Gesture capture are disabled — the optional "
            "`streamlit-webrtc` / `mediapipe` packages aren't installed (or "
            "failed to import). See requirements-gesture.txt to enable them."
        )

    if mode == "📷 Click to capture":
        _render_click_capture()
    elif mode == "⏱️ Timer capture":
        _render_timer_capture()
    elif mode == "🖐️ Gesture capture (pose match)":
        _render_gesture_capture()
    else:
        _render_upload_capture()


def _render_crop(raw_image: Image.Image) -> Image.Image:
    """Optional crop step. Returns the cropped image, or the original if
    the cropper package isn't installed or the user hasn't touched the
    crop box yet."""
    if not CROPPER_AVAILABLE:
        return raw_image

    version = st.session_state.get("photobooth_image_version", 0)
    with st.expander("✂️ Crop", expanded=False):
        st.caption("Drag the box's edges/corners to crop. Leave it as-is to keep the full photo.")
        cropped = st_cropper(
            raw_image,
            realtime_update=True,
            box_color="#02ab21",
            aspect_ratio=None,
            return_type="image",
            key=f"photobooth_cropper_{version}",  # forces a fresh box per new photo
        )
    return cropped if cropped is not None else raw_image


def _render_edit_and_export(user) -> None:
    """Crop, filter, preview/compare, download — all anonymous. Saving to
    the gallery additionally requires being logged in."""
    raw_image = st.session_state.get("photobooth_raw_image")
    if raw_image is None:
        st.info("Capture or upload a photo to start editing.")
        return

    working_image = _render_crop(raw_image)

    filter_name = st.selectbox("Filter", PHOTO_FILTERS)
    caption = st.text_input("Caption (optional)")

    filtered = apply_filter(working_image, filter_name)

    if COMPARISON_AVAILABLE:
        show_compare = st.toggle("Compare before / after", value=(filter_name != "None"))
    else:
        show_compare = False

    if show_compare:
        image_comparison(
            img1=working_image.convert("RGB"),
            img2=filtered,
            label1="Original",
            label2=filter_name if filter_name != "None" else "Filtered",
        )
    else:
        st.image(filtered, caption="Preview", use_container_width=True)

    buf = io.BytesIO()
    filtered.convert("RGB").save(buf, format="JPEG", quality=90)
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
                photos_service.save_photo(user["id"], filtered, caption.strip(), filter_name)
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
        st.caption("Snap a pic — by clicking, on a timer, or with a gesture — crop it, add a filter, compare, download or save it to your gallery.")
    else:
        st.caption("Snap a pic, crop, add a filter, and download it — no account needed. Log in (see the Login tab) if you want it saved to a personal gallery too.")

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