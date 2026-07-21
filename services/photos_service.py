import os
import uuid
from datetime import datetime

import pandas as pd
from PIL import Image

from config import TIMEZONE
from db.database import get_connection, PHOTOS_DIR


def save_photo(image: Image.Image, caption: str, filter_name: str) -> None:
    """Persist an already-filtered PIL image to disk and record it in the DB."""
    filename = f"{uuid.uuid4().hex}.jpg"
    path = os.path.join(PHOTOS_DIR, filename)
    image.convert("RGB").save(path, format="JPEG", quality=90)

    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    conn = get_connection()
    conn.execute(
        "INSERT INTO photos (filename, caption, filter, time) VALUES (?, ?, ?, ?)",
        (filename, caption, filter_name, t),
    )
    conn.commit()
    conn.close()


def get_photos() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM photos ORDER BY id DESC", conn)
    conn.close()
    return df


def photo_path(filename: str) -> str:
    return os.path.join(PHOTOS_DIR, filename)


def delete_photo(photo_id: int) -> None:
    conn = get_connection()
    row = conn.execute("SELECT filename FROM photos WHERE id = ?", (photo_id,)).fetchone()
    conn.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
    conn.commit()
    conn.close()
    if row:
        path = photo_path(row[0])
        if os.path.exists(path):
            os.remove(path)
