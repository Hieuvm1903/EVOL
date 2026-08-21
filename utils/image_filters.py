import numpy as np
from PIL import Image, ImageOps, ImageFilter, ImageEnhance


def _sepia(img: Image.Image) -> Image.Image:
    arr = np.array(img.convert("RGB"), dtype=np.float64)
    matrix = np.array([
        [0.393, 0.769, 0.189],
        [0.349, 0.686, 0.168],
        [0.272, 0.534, 0.131],
    ])
    sepia_arr = np.clip(arr @ matrix.T, 0, 255).astype(np.uint8)
    return Image.fromarray(sepia_arr, "RGB")


def _vignette(img: Image.Image, strength: float) -> Image.Image:
    if strength <= 0:
        return img
    w, h = img.size
    y, x = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    max_dist = np.sqrt(cx ** 2 + cy ** 2)
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_dist
    mask = np.clip(1 - strength * (dist ** 2), 0, 1)
    arr = np.array(img.convert("RGB"), dtype=np.float64) * mask[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def _tint(img: Image.Image, warmth: float) -> Image.Image:
    """warmth in [-1, 1]: negative = cool (blue), positive = warm (orange).
    0 is a no-op."""
    if warmth == 0:
        return img
    color = (255, 150, 60) if warmth > 0 else (60, 150, 255)
    overlay = Image.new("RGB", img.size, color)
    return Image.blend(img.convert("RGB"), overlay, min(abs(warmth) * 0.3, 0.5))


# ---------------------------------------------------------------------------
# Base "style" filters — discrete looks, picked from a dropdown.
# ---------------------------------------------------------------------------

def apply_filter(img: Image.Image, filter_name: str) -> Image.Image:
    """Apply a named base style (see config.PHOTO_FILTERS) to a PIL image."""
    img = img.convert("RGB")

    if filter_name == "Grayscale":
        return ImageOps.grayscale(img).convert("RGB")
    if filter_name == "Sepia":
        return _sepia(img)
    if filter_name == "Invert":
        return ImageOps.invert(img)
    if filter_name == "Vintage":
        toned = _sepia(img)
        toned = ImageEnhance.Contrast(toned).enhance(0.9)
        toned = ImageEnhance.Color(toned).enhance(0.85)
        return _vignette(toned, 0.55)
    if filter_name == "Posterize":
        return ImageOps.posterize(img, bits=3)
    if filter_name == "Solarize":
        return ImageOps.solarize(img, threshold=128)
    if filter_name == "B&W (High Contrast)":
        gray = ImageOps.grayscale(img)
        gray = ImageEnhance.Contrast(gray).enhance(1.6)
        return gray.convert("RGB")

    return img  # "None" or unrecognized -> unchanged


# ---------------------------------------------------------------------------
# Continuous adjustments — all slider-driven, applied after the style filter.
# Every value defaults to a no-op so an untouched slider changes nothing.
# ---------------------------------------------------------------------------

DEFAULT_ADJUSTMENTS = {
    "brightness": 1.0,   # 0.5 .. 1.8
    "contrast": 1.0,     # 0.5 .. 1.8
    "saturation": 1.0,   # 0.0 .. 2.0
    "sharpness": 1.0,    # 0.0 .. 2.0
    "blur": 0.0,         # 0 .. 10 (px radius)
    "warmth": 0.0,       # -1 .. 1 (cool .. warm)
    "vignette": 0.0,     # 0 .. 1
}


def apply_adjustments(img: Image.Image, adjustments: dict) -> Image.Image:
    img = img.convert("RGB")
    a = {**DEFAULT_ADJUSTMENTS, **adjustments}

    if a["brightness"] != 1.0:
        img = ImageEnhance.Brightness(img).enhance(a["brightness"])
    if a["contrast"] != 1.0:
        img = ImageEnhance.Contrast(img).enhance(a["contrast"])
    if a["saturation"] != 1.0:
        img = ImageEnhance.Color(img).enhance(a["saturation"])
    if a["sharpness"] != 1.0:
        img = ImageEnhance.Sharpness(img).enhance(a["sharpness"])
    if a["blur"] > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=a["blur"]))
    if a["warmth"] != 0:
        img = _tint(img, a["warmth"])
    if a["vignette"] > 0:
        img = _vignette(img, a["vignette"])

    return img