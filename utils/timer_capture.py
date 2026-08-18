"""Lightweight webrtc processor for Timer mode.

Deliberately has no mediapipe/opencv dependency — Timer mode just needs a
live preview plus "grab whatever frame is showing right now", so it stays
usable even on setups where requirements-gesture.txt (mediapipe, opencv)
isn't installed but streamlit-webrtc/av are.
"""
import threading

import av
import numpy as np
from streamlit_webrtc import RTCConfiguration, VideoProcessorBase

RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)


class TimerCaptureProcessor(VideoProcessorBase):
    """Passes the video stream through unmodified, stashing the most recent
    frame (as RGB) under `lock` so the countdown loop in the main thread can
    read it once it finishes."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.latest_frame: np.ndarray | None = None  # RGB, HxWx3

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        rgb = frame.to_ndarray(format="rgb24")
        with self.lock:
            self.latest_frame = rgb
        return frame