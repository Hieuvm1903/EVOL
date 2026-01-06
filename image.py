from PIL import Image, ImageOps, ImageDraw
import os


def ensure_frames_dir(frames_dir):
    """Create frames dir and a sample frame if none are present."""
    os.makedirs(frames_dir, exist_ok=True)
    files = [f for f in os.listdir(frames_dir) if f.lower().endswith(('png','jpg','jpeg'))]
    if not files:
        # create a sample frame (transparent center with colored border)
        size = (800, 800)
        frame = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)
        border = 60
        draw.rectangle([0, 0, size[0], size[1]], outline=(255, 0, 0, 255), width=border)
        frame_path = os.path.join(frames_dir, "sample_frame.png")
        frame.save(frame_path)


def list_frames(frames_dir):
    """Return list of frame file paths (creates sample if needed)."""
    ensure_frames_dir(frames_dir)
    files = sorted([os.path.join(frames_dir, f) for f in os.listdir(frames_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    return files


def merge_with_frame(user_img, frame_path):
    """Composite the user image with the selected frame and return a PIL Image."""
    frame = Image.open(frame_path).convert("RGBA")
    target_size = frame.size
    user_img = ImageOps.fit(user_img.convert("RGBA"), target_size, method=Image.LANCZOS)
    composed = Image.alpha_composite(user_img, frame)
    return composed

