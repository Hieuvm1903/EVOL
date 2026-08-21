import io
import time
import uuid

import pandas as pd
import streamlit as st
from PIL import Image

from config import PHOTO_FILTERS, PHOTO_FRAMES, TIMEZONE
from services import photos_service
from utils.image_filters import apply_filter, apply_adjustments, DEFAULT_ADJUSTMENTS
from utils.photo_frames import apply_frame

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

# --- streamlit_extras: three separate optional widgets, each guarded on
# its own so a missing one just degrades that one feature, not the page. ---
try:
    from streamlit_extras.card_selector import card_selector
    CARD_SELECTOR_AVAILABLE = True
except ImportError:
    CARD_SELECTOR_AVAILABLE = False

try:
    from streamlit_extras.image_crop import image_crop
    CROP_AVAILABLE = True
except ImportError:
    CROP_AVAILABLE = False

try:
    from streamlit_extras.image_compare_slider import image_compare_slider
    COMPARISON_AVAILABLE = True
except ImportError:
    COMPARISON_AVAILABLE = False

TIMER_OPTIONS = [3, 5, 10]  # seconds
THUMB_WIDTH = 64

POSE_OPTIONS = {
    "🖐️ Open palm": "open_palm",
    "✌️ Peace sign": "peace",
    "👍 Thumbs up": "thumbs_up",
    "✊ Fist": "fist",
    "🤖 Any pose": "any",
}
POSE_LABELS = {v: k for k, v in POSE_OPTIONS.items()}


# ---------------------------------------------------------------------------
# Shot list — every capture (click/timer/gesture/upload) appends here.
# ---------------------------------------------------------------------------

def _add_shot(img: Image.Image) -> None:
    shots = st.session_state.setdefault("photobooth_shots", [])
    shots.append(img.convert("RGB"))
    st.session_state["photobooth_active_idx"] = len(shots) - 1
    st.session_state["photobooth_adjustments"] = dict(DEFAULT_ADJUSTMENTS)
    st.session_state.pop("photobooth_cropped", None)  # new shot -> discard any old crop


def _active_shot() -> Image.Image | None:
    shots = st.session_state.get("photobooth_shots", [])
    idx = st.session_state.get("photobooth_active_idx")
    if idx is None or idx >= len(shots):
        return None
    return shots[idx]


def _render_shot_picker() -> None:
    """Small thumbnails to pick which captured shot is being edited.
    Uses streamlit_extras.card_selector when available (a scrollable row
    of image cards, returns the selected index); falls back to a plain
    button-per-row list otherwise."""
    shots = st.session_state.get("photobooth_shots", [])
    if not shots:
        return
    st.caption(f"Shots ({len(shots)}) — tap to edit")

    if CARD_SELECTOR_AVAILABLE:
        items = [{"image": shot, "title": f"Shot {i + 1}"} for i, shot in enumerate(shots)]
        selected_idx = card_selector(
            items,
            key="photobooth_card_selector",
            default=st.session_state.get("photobooth_active_idx", 0),
        )
        if selected_idx is not None and selected_idx != st.session_state.get("photobooth_active_idx"):
            st.session_state["photobooth_active_idx"] = selected_idx
            st.session_state["photobooth_adjustments"] = dict(DEFAULT_ADJUSTMENTS)
            st.session_state.pop("photobooth_cropped", None)
            st.rerun()
        return

    active_idx = st.session_state.get("photobooth_active_idx")
    with st.container(height=180):
        for idx, shot in enumerate(shots):
            c1, c2 = st.columns([2, 1], vertical_alignment="center")
            with c1:
                st.image(shot, width=THUMB_WIDTH)
            with c2:
                if st.button(
                    "Edit", key=f"pick_shot_{idx}", use_container_width=True,
                    type="primary" if idx == active_idx else "secondary",
                ):
                    st.session_state["photobooth_active_idx"] = idx
                    st.session_state["photobooth_adjustments"] = dict(DEFAULT_ADJUSTMENTS)
                    st.session_state.pop("photobooth_cropped", None)
                    st.rerun()


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

def _render_capture_controls() -> str:
    mode_options = ["Click", "Upload (test)"]
    if WEBRTC_AVAILABLE:
        mode_options.insert(1, "Timer")
    if GESTURE_CAPTURE_AVAILABLE:
        mode_options.insert(2 if WEBRTC_AVAILABLE else 1, "Gesture")

    mode = st.radio("Capture mode", mode_options, horizontal=True, label_visibility="collapsed")

    if not WEBRTC_AVAILABLE:
        st.caption("Timer/Gesture need `streamlit-webrtc`/`mediapipe` — see requirements-gesture.txt.")

    if mode == "Timer":
        st.session_state["timer_seconds"] = st.select_slider(
            "Countdown (s)", options=TIMER_OPTIONS, value=st.session_state.get("timer_seconds", 3),
        )
    elif mode == "Gesture":
        st.session_state["gesture_pose_choice"] = st.selectbox(
            "Trigger pose", list(POSE_OPTIONS.keys()),
            index=list(POSE_OPTIONS.keys()).index(
                st.session_state.get("gesture_pose_choice", "🖐️ Open palm")
            ),
        )

    return mode


def _render_capture_widget(mode: str) -> None:
    if mode == "Click":
        camera_photo = st.camera_input("Take a photo", label_visibility="collapsed")
        if camera_photo is not None:
            sig = camera_photo.file_id if hasattr(camera_photo, "file_id") else camera_photo.name
            if st.session_state.get("photobooth_click_sig") != sig:
                st.session_state["photobooth_click_sig"] = sig
                _add_shot(Image.open(camera_photo))

    elif mode == "Timer":
        ctx = webrtc_streamer(
            key="timer-photobooth",
            video_processor_factory=TimerCaptureProcessor,
            rtc_configuration=TIMER_RTC_CONFIGURATION,
            media_stream_constraints={"video": True, "audio": False},
        )
        if not ctx.video_processor:
            st.caption("Waiting for the camera to connect…")
            return
        if st.button("Start countdown", key="start_timer", icon=":material/timer:"):
            countdown_ph = st.empty()
            seconds = st.session_state.get("timer_seconds", 3)
            for remaining in range(seconds, 0, -1):
                countdown_ph.markdown(f"## {remaining}…")
                time.sleep(1)
            countdown_ph.markdown("## 📸")
            with ctx.video_processor.lock:
                frame = ctx.video_processor.latest_frame
            countdown_ph.empty()
            if frame is not None:
                _add_shot(Image.fromarray(frame))
                st.toast("Captured! Pick it from the shot list to edit.")
            else:
                st.warning("No frame yet — make sure the feed above is running.")

    elif mode == "Gesture":
        target_pose = POSE_OPTIONS[st.session_state.get("gesture_pose_choice", "🖐️ Open palm")]
        ctx = webrtc_streamer(
            key="gesture-photobooth",
            video_processor_factory=GestureCaptureProcessor,
            rtc_configuration=RTC_CONFIGURATION,
            media_stream_constraints={"video": True, "audio": False},
        )
        if not ctx.video_processor:
            return
        ctx.video_processor.target_pose = target_pose
        with ctx.video_processor.lock:
            frame = ctx.video_processor.captured_frame
            detected = ctx.video_processor.detected_pose
            if frame is not None:
                ctx.video_processor.captured_frame = None
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                _add_shot(Image.fromarray(rgb))
                st.toast("Captured! Pick it from the shot list to edit.")
        if detected:
            st.caption(f"Detected: {POSE_LABELS.get(detected, detected)}")

    else:  # Upload (test)
        uploaded = st.file_uploader(
            "Upload an image", type=["png", "jpg", "jpeg", "webp"],
            label_visibility="collapsed",
        )
        if uploaded is not None:
            sig = (uploaded.name, uploaded.size)
            if st.session_state.get("photobooth_upload_sig") != sig:
                st.session_state["photobooth_upload_sig"] = sig
                _add_shot(Image.open(uploaded))


# ---------------------------------------------------------------------------
# Crop — streamlit_extras.image_crop, applied to the raw shot before any
# style/adjustments/frame. Result cached per-shot in session_state so
# re-running the page doesn't reset the crop on every interaction.
# ---------------------------------------------------------------------------

def _render_crop(raw: Image.Image) -> Image.Image:
    if not CROP_AVAILABLE:
        return raw

    idx = st.session_state.get("photobooth_active_idx", 0)
    cropped = image_crop(raw, key=f"photobooth_image_crop_{idx}")
    if cropped is not None:
        st.session_state["photobooth_cropped"] = cropped
        return cropped
    return st.session_state.get("photobooth_cropped", raw)


# ---------------------------------------------------------------------------
# Edit panel — style + frame dropdowns, sliders, short toggle, caption.
# ---------------------------------------------------------------------------

def _render_edit_controls() -> tuple[str, str, dict, str, bool]:
    filter_name = st.selectbox("Style", PHOTO_FILTERS)
    frame_name = st.selectbox("Frame", list(PHOTO_FRAMES.keys()))

    st.caption("Adjust")
    saved = st.session_state.get("photobooth_adjustments", dict(DEFAULT_ADJUSTMENTS))
    adjustments = {
        "brightness": st.slider("Brightness", 0.5, 1.8, saved["brightness"], 0.05),
        "contrast": st.slider("Contrast", 0.5, 1.8, saved["contrast"], 0.05),
        "saturation": st.slider("Saturation", 0.0, 2.0, saved["saturation"], 0.05),
        "sharpness": st.slider("Sharpness", 0.0, 2.0, saved["sharpness"], 0.05),
        "blur": st.slider("Blur", 0.0, 10.0, saved["blur"], 0.5),
        "warmth": st.slider("Warmth", -1.0, 1.0, saved["warmth"], 0.05),
        "vignette": st.slider("Vignette", 0.0, 1.0, saved["vignette"], 0.05),
    }
    st.session_state["photobooth_adjustments"] = adjustments

    if st.button("Reset sliders", use_container_width=True, icon=":material/restart_alt:"):
        st.session_state["photobooth_adjustments"] = dict(DEFAULT_ADJUSTMENTS)
        st.rerun()

    compare = st.toggle("Compare", value=False) if COMPARISON_AVAILABLE else False
    caption = st.text_input("Caption")

    return filter_name, frame_name, adjustments, caption, compare


def _render_actions(user, edited: Image.Image, filter_name: str, caption: str) -> None:
    buf = io.BytesIO()
    edited.convert("RGB").save(buf, format="JPEG", quality=90)

    st.download_button(
        "Download", data=buf.getvalue(),
        file_name=f"evol-photobooth-{uuid.uuid4().hex[:8]}.jpg",
        mime="image/jpeg", icon=":material/download:", use_container_width=True,
    )

    if user:
        if st.button("Save to gallery", key="save_photo", icon=":material/save:", use_container_width=True):
            photos_service.save_photo(user["id"], edited, caption.strip(), filter_name)
            st.success("Saved!")
    else:
        st.button(
            "Log in to save", key="save_photo_locked", icon=":material/lock:",
            use_container_width=True, disabled=True,
            help="Log in to save photos to a personal gallery.",
        )


# ---------------------------------------------------------------------------
# Right side — images only.
# ---------------------------------------------------------------------------

def _render_right_panel(mode: str, cropped, edited, compare: bool, filter_name: str) -> None:
    if cropped is None:
        _render_capture_widget(mode)
        return

    if compare and COMPARISON_AVAILABLE:
        image_compare_slider(
            img1=cropped.convert("RGB"), img2=edited,
            label1="Original", label2=filter_name if filter_name != "None" else "Edited",
            key="photobooth_compare_slider",
        )
    else:
        st.image(edited, use_container_width=True)


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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render() -> None:
    st.markdown("## :material/photo_camera: Photobooth")

    user = st.session_state.get("user")
    st.caption(
        "Capture, style, and download for free — log in to also save to your gallery."
        if not user else
        "Capture, style, crop, compare, download, or save to your gallery."
    )

    left, right = st.columns([1, 2.2], gap="medium")

    original = _active_shot()

    with left:
        mode = _render_capture_controls()
        _render_shot_picker()
        st.markdown("---")

        if original is not None:
            cropped = _render_crop(original)
            filter_name, frame_name, adjustments, caption, compare = _render_edit_controls()
            styled = apply_filter(cropped, filter_name)
            styled = apply_adjustments(styled, adjustments)
            edited = apply_frame(styled, frame_name)
        else:
            cropped, filter_name, edited, caption, compare = None, "None", None, "", False

    with right:
        _render_right_panel(mode, cropped, edited, compare, filter_name)

    if original is not None:
        st.markdown("---")
        _render_actions(user, edited, filter_name, caption)

    st.markdown("---")
    if user:
        _render_gallery(user["id"])
    else:
        st.info("Log in to see and manage a personal photo gallery.", icon=":material/lock:")