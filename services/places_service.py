from datetime import datetime

import pandas as pd

from config import TIMEZONE
from db.database import get_connection


def add_place(name: str, lat: float, lon: float, description: str, icon: str) -> None:
    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    conn = get_connection()
    conn.execute(
        "INSERT INTO places (name, lat, lon, description, icon, time) VALUES (?, ?, ?, ?, ?, ?)",
        (name, lat, lon, description, icon, t),
    )
    conn.commit()
    conn.close()


def get_places() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM places ORDER BY id DESC", conn)
    conn.close()
    return df


def delete_place(place_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM places WHERE id = ?", (place_id,))
    conn.commit()
    conn.close()
