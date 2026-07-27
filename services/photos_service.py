import io
import os
import uuid
from datetime import datetime

import pandas as pd
from PIL import Image

from config import TIMEZONE
from db.database import get_connection, push_db, PHOTOS_DIR
from services import remote_storage


def save_photo(image: Image.Image, caption: str, filter_name: str) -> None:
    """Upload a filtered photo to R2 (if configured) and record it in the DB.

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
    conn = get_connection()
    conn.execute(
        "INSERT INTO photos (filename, caption, filter, time) VALUES (?, ?, ?, ?)",
        (filename, caption, filter_name, t),
    )
    conn.commit()
    conn.close()
    push_db()


def get_photos() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM photos ORDER BY id DESC", conn)
    conn.close()
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
    conn = get_connection()
    row = conn.execute("SELECT filename FROM photos WHERE id = ?", (photo_id,)).fetchone()
    conn.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
    conn.commit()
    conn.close()
    push_db()

    if row:
        filename = row[0]
        local_path = os.path.join(PHOTOS_DIR, filename)
        if os.path.exists(local_path):
            os.remove(local_path)
        remote_storage.delete_photo(filename)
