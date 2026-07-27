from datetime import datetime

import pandas as pd

from config import TIMEZONE
from db.database import get_connection, push_db


def add_post(content: str) -> None:
    t = datetime.now().astimezone(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    conn = get_connection()
    conn.execute("INSERT INTO blog (content, time) VALUES (?, ?)", (content, t))
    conn.commit()
    conn.close()
    push_db()


def get_posts() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM blog ORDER BY id DESC", conn)
    conn.close()
    return df
