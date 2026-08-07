from datetime import datetime

import pandas as pd

from config import TIMEZONE
from db import sheets_db


def add_post(content: str) -> None:
    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    sheets_db.insert("blog", {"content": content, "time": t})


def get_posts() -> pd.DataFrame:
    df = sheets_db.read_all("blog")
    if not df.empty:
        df = df.sort_values("id", ascending=False)
    return df
