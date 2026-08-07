from datetime import datetime

import pandas as pd

from config import TIMEZONE
from db import sheets_db


def add_note(content: str) -> None:
    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    sheets_db.insert("notes", {"content": content, "time": t})


def get_notes() -> pd.DataFrame:
    df = sheets_db.read_all("notes")
    if not df.empty:
        df = df.sort_values("id", ascending=False)
    return df
