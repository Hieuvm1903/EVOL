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


def _vignette(img: Image.Image, strength: float = 0.55) -> Image.Image:
    w, h = img.size
    y, x = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    max_dist = np.sqrt(cx ** 2 + cy ** 2)
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_dist
    mask = np.clip(1 - strength * (dist ** 2), 0, 1)
    arr = np.array(img.convert("RGB"), dtype=np.float64) * mask[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def apply_filter(img: Image.Image, filter_name: str) -> Image.Image:
    """Apply a named filter (see config.PHOTO_FILTERS) to a PIL image."""
    img = img.convert("RGB")

    if filter_name == "Grayscale":
        return ImageOps.grayscale(img).convert("RGB")

    if filter_name == "Sepia":
        return _sepia(img)

    if filter_name == "Invert":
        return ImageOps.invert(img)

    if filter_name == "Blur":
        return img.filter(ImageFilter.GaussianBlur(radius=4))

    if filter_name == "Vintage":
        toned = _sepia(img)
        toned = ImageEnhance.Contrast(toned).enhance(0.9)
        toned = ImageEnhance.Color(toned).enhance(0.85)
        return _vignette(toned)

    return img  # "None" or unrecognized -> unchanged
