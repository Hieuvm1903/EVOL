"""Decorative frame/overlay PNGs applied on top of a photo (see
config.PHOTO_FRAMES). Frames are transparent PNGs shipped in assets/frames/
and resized to match the photo before compositing — they don't need to be
captured/photographed at any particular resolution ahead of time."""
import os

from PIL import Image

from config import FRAMES_DIR, PHOTO_FRAMES


def apply_frame(img: Image.Image, frame_name: str) -> Image.Image:
    """Composite the named frame over `img`. Returns `img` unchanged for
    "None", an unrecognized name, or if the file is missing on disk (so a
    bad/missing asset never crashes the page — just silently no-ops)."""
    filename = PHOTO_FRAMES.get(frame_name)
    if not filename:
        return img

    path = os.path.join(FRAMES_DIR, filename)
    if not os.path.exists(path):
        return img

    frame = Image.open(path).convert("RGBA").resize(img.size)
    base = img.convert("RGBA")
    composited = Image.alpha_composite(base, frame)
    return composited.convert("RGB")