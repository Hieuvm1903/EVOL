from datetime import datetime

import pandas as pd

from config import TIMEZONE
from db import sheets_db


def add_place(user_id: int, name: str, lat: float, lon: float, description: str, icon: str) -> None:
    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    sheets_db.insert("places", {
        "user_id": user_id,
        "name": name,
        "lat": lat,
        "lon": lon,
        "description": description,
        "icon": icon,
        "time": t,
    })


def get_places(user_id: int) -> pd.DataFrame:
    """Only this user's places — each account has its own map."""
    df = sheets_db.read_all("places")
    if df.empty:
        return df
    df = df[df["user_id"] == user_id]
    return df.sort_values("id", ascending=False)


def delete_place(place_id: int, user_id: int) -> None:
    """Only deletes if the place actually belongs to this user."""
    places = sheets_db.read_all("places")
    match = places[(places["id"] == place_id) & (places["user_id"] == user_id)]
    if match.empty:
        return
    sheets_db.delete("places", place_id)