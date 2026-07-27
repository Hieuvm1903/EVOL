"""Hands-free photo capture: hold an open palm up to the camera for ~1s to
trigger a capture, instead of clicking a button.

Built on:
  - streamlit-webrtc: streams the browser webcam into Python frame-by-frame
    (st.camera_input can't do this — it only gives one shot per click).
  - MediaPipe Tasks HandLandmarker: fast, CPU-only hand-landmark detection
    per frame. (The older `mp.solutions.hands` API has been removed from
    recent mediapipe releases, so this uses the current Tasks API instead.)

The hand-landmark model (~8MB) is downloaded once, on first use, straight
from Google's model bucket and cached next to the project root — this needs
outbound internet access, which Streamlit Community Cloud has.

On Community Cloud, WebRTC needs a STUN server to establish the peer
connection (browser <-> server aren't on the same network). Google's public
STUN server below works for most home/office networks. If your network is
behind strict NAT/firewalls and the video never connects, swap in a free
TURN server (e.g. the Open Relay Project: https://www.metered.ca/tools/openrelay/).
"""
import os
import threading
import urllib.request

import av
import cv2
import numpy as np
from mediapipe import Image as MPImage, ImageFormat
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions
from streamlit_webrtc import RTCConfiguration, VideoProcessorBase

RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODEL_PATH = os.path.join(_ROOT_DIR, "hand_landmarker.task")
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)

# Landmark indices for the 4 non-thumb fingertips and their PIP joints
_FINGER_TIPS = [8, 12, 16, 20]
_FINGER_PIPS = [6, 10, 14, 18]

HOLD_FRAMES_TO_TRIGGER = 20  # ~1s at ~20fps


def _ensure_model() -> str:
    if not os.path.exists(_MODEL_PATH):
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
    return _MODEL_PATH


def _is_open_palm(landmarks) -> bool:
    """True if at least 3 of the 4 fingers are extended (tip above its own
    pip joint) — a little slack for imperfect tracking."""
    extended = 0
    for tip_idx, pip_idx in zip(_FINGER_TIPS, _FINGER_PIPS):
        if landmarks[tip_idx].y < landmarks[pip_idx].y:  # smaller y = higher in frame
            extended += 1
    return extended >= 3


class GestureCaptureProcessor(VideoProcessorBase):
    """Watches the video stream and stashes a frame once an open-palm hold
    is detected. Read `captured_frame` (under `lock`) from the main thread
    and clear it once consumed."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.captured_frame: np.ndarray | None = None
        self._hold_frames = 0
        self._armed = True  # must release the gesture before it can re-trigger
        self._timestamp_ms = 0

        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=_ensure_model()),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = MPImage(image_format=ImageFormat.SRGB, data=rgb)

        self._timestamp_ms += 33  # timestamps must be monotonically increasing
        result = self._landmarker.detect_for_video(mp_image, self._timestamp_ms)

        gesture_now = False
        if result.hand_landmarks:
            landmarks = result.hand_landmarks[0]
            gesture_now = _is_open_palm(landmarks)
            h, w = img.shape[:2]
            for lm in landmarks:
                cv2.circle(img, (int(lm.x * w), int(lm.y * h)), 3, (0, 220, 0), -1)

        with self.lock:
            if gesture_now and self._armed:
                self._hold_frames += 1
                progress = min(self._hold_frames / HOLD_FRAMES_TO_TRIGGER, 1.0)
                self._draw_progress(img, progress)
                if self._hold_frames >= HOLD_FRAMES_TO_TRIGGER:
                    self.captured_frame = img.copy()
                    self._armed = False
                    self._hold_frames = 0
            else:
                self._hold_frames = 0
                if not gesture_now:
                    self._armed = True  # gesture released, ready to trigger again

        return av.VideoFrame.from_ndarray(img, format="bgr24")

    @staticmethod
    def _draw_progress(img: np.ndarray, progress: float) -> None:
        h, w = img.shape[:2]
        bar_w = int(w * 0.6)
        x0, y0 = int(w * 0.2), h - 30
        cv2.rectangle(img, (x0, y0), (x0 + bar_w, y0 + 12), (60, 60, 60), -1)
        cv2.rectangle(img, (x0, y0), (x0 + int(bar_w * progress), y0 + 12), (0, 200, 0), -1)
        cv2.putText(img, "Hold open palm to capture", (x0, y0 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
