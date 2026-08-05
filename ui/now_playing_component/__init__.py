import os
import streamlit.components.v1 as components

# Flip to True once you've run `npm run build` in frontend/ and want to
# ship the built assets instead of hitting the Vite dev server.
_RELEASE = True

if not _RELEASE:
    _component_func = components.declare_component(
        "now_playing",
        url="http://localhost:3001",  # `npm run dev` in frontend/
    )
else:
    _dir = os.path.dirname(os.path.abspath(__file__))
    _build_dir = os.path.join(_dir, "frontend", "dist")
    _component_func = components.declare_component("now_playing", path=_build_dir)


def now_playing_widget(queue: list[dict], mode: str = "Normal", key: str | None = None) -> None:
    """Render the floating now-playing widget.

    `queue` is a list of {"title", "video_id", "thumbnail_url"} dicts —
    same shape as before (see ui/now_playing_widget.py::load_queue).
    Fire-and-forget: the component doesn't send anything back to Python.
    """
    if not queue:
        return None
    return _component_func(queue=queue, mode=mode, key=key or "now_playing", default=None)
