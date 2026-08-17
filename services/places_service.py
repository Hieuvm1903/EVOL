from datetime import datetime

import pandas as pd

from config import TIMEZONE
from db import sheets_db


def add_place(
    user_id: int, name: str, lat: float, lon: float,
    description: str, icon: str, tags: str = "",
) -> None:
    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    sheets_db.insert("places", {
        "user_id": user_id,
        "name": name,
        "lat": lat,
        "lon": lon,
        "description": description,
        "icon": icon,
        "tags": tags,
        "time": t,
    })


def update_place(
    place_id: int, name: str, lat: float, lon: float,
    description: str, icon: str, tags: str = "",
) -> None:
    """Used by the map page's edit flow (reuses the same add/edit dialog)."""
    sheets_db.update("places", place_id, {
        "name": name,
        "lat": lat,
        "lon": lon,
        "description": description,
        "icon": icon,
        "tags": tags,
    })


def get_places(user_id: int) -> pd.DataFrame:
    """Only this user's places — each account has its own map."""
    df = sheets_db.read_all("places")
    if df.empty:
        return df
    df = df[df["user_id"] == user_id]
    return df.sort_values("id", ascending=False)


def get_all_tags(user_id: int) -> list[str]:
    """Distinct tags this user has used so far — for filter dropdowns and
    autocomplete-style hints in the add/edit form."""
    df = get_places(user_id)
    if df.empty or "tags" not in df.columns:
        return []
    tags: set[str] = set()
    for val in df["tags"].dropna():
        tags.update(t.strip() for t in str(val).split(",") if t.strip())
    return sorted(tags)


def delete_place(place_id: int, user_id: int) -> None:
    """Only deletes if the place actually belongs to this user."""
    places = sheets_db.read_all("places")
    match = places[(places["id"] == place_id) & (places["user_id"] == user_id)]
    if match.empty:
        return
    sheets_db.delete("places", place_id)