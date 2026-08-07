import os
import io
import uuid
from datetime import datetime

import pandas as pd
from PIL import Image

from config import PHOTOS_DIR, TIMEZONE
from db import sheets_db
from services import remote_storage


def save_photo(image: Image.Image, caption: str, filter_name: str) -> None:
    """Upload a filtered photo to R2 (if configured) and record it in Sheets.

    Also writes a local copy to PHOTOS_DIR so the gallery has something to
    read immediately in the same session, without a round-trip download.
    """
    filename = f"{uuid.uuid4().hex}.jpg"

    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=90)
    photo_bytes = buf.getvalue()

    local_path = os.path.join(PHOTOS_DIR, filename)
    with open(local_path, "wb") as f:
        f.write(photo_bytes)

    remote_storage.upload_photo(filename, photo_bytes)

    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    sheets_db.insert("photos", {
        "filename": filename,
        "caption": caption,
        "filter": filter_name,
        "time": t,
    })


def get_photos() -> pd.DataFrame:
    df = sheets_db.read_all("photos")
    if not df.empty:
        df = df.sort_values("id", ascending=False)
    return df


def get_photo_source(filename: str):
    """Return something st.image() can render: a local path if cached,
    otherwise the raw bytes pulled from R2 (and cache them locally too)."""
    local_path = os.path.join(PHOTOS_DIR, filename)
    if os.path.exists(local_path):
        return local_path

    data = remote_storage.download_photo(filename)
    if data is not None:
        with open(local_path, "wb") as f:
            f.write(data)
        return local_path

    return None  # not found locally or remotely


def delete_photo(photo_id: int) -> None:
    photos = sheets_db.read_all("photos")
    match = photos[photos["id"] == photo_id] if not photos.empty else photos

    sheets_db.delete("photos", photo_id)

    if match is not None and not match.empty:
        filename = match.iloc[0]["filename"]
        local_path = os.path.join(PHOTOS_DIR, filename)
        if os.path.exists(local_path):
            os.remove(local_path)
        remote_storage.delete_photo(filename)
