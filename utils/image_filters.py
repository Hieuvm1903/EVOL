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


def _tint(img: Image.Image, color: tuple[int, int, int], alpha: float = 0.14) -> Image.Image:
    """Blend a flat color overlay over the image — cheap warm/cool grading
    without needing per-channel curve math."""
    overlay = Image.new("RGB", img.size, color)
    return Image.blend(img.convert("RGB"), overlay, alpha)


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

    if filter_name == "Brightness+":
        return ImageEnhance.Brightness(img).enhance(1.35)

    if filter_name == "Contrast+":
        return ImageEnhance.Contrast(img).enhance(1.35)

    if filter_name == "Sharpen":
        return img.filter(ImageFilter.SHARPEN)

    if filter_name == "Warm":
        return _tint(img, (255, 150, 60), alpha=0.14)

    if filter_name == "Cool":
        return _tint(img, (60, 150, 255), alpha=0.14)

    if filter_name == "Posterize":
        return ImageOps.posterize(img, bits=3)

    if filter_name == "Solarize":
        return ImageOps.solarize(img, threshold=128)

    if filter_name == "Edge Enhance":
        return img.filter(ImageFilter.EDGE_ENHANCE_MORE)

    if filter_name == "B&W (High Contrast)":
        gray = ImageOps.grayscale(img)
        gray = ImageEnhance.Contrast(gray).enhance(1.6)
        return gray.convert("RGB")

    return img  # "None" or unrecognized -> unchanged