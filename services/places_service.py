from datetime import datetime

import pandas as pd

from config import TIMEZONE
from db import sheets_db


def add_place(name: str, lat: float, lon: float, description: str, icon: str) -> None:
    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    sheets_db.insert("places", {
        "name": name,
        "lat": lat,
        "lon": lon,
        "description": description,
        "icon": icon,
        "time": t,
    })


def get_places() -> pd.DataFrame:
    df = sheets_db.read_all("places")
    if not df.empty:
        df = df.sort_values("id", ascending=False)
    return df


def delete_place(place_id: int) -> None:
    sheets_db.delete("places", place_id)
