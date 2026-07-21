import sqlite3
import os
from datetime import datetime
import pandas as pd
import pytz

# Local SQLite database stored next to this module.
# No external service (e.g. Supabase) required — it's just a file on disk.
DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")

timezone = pytz.timezone("Asia/Ho_Chi_Minh")  # Replace with your desired timezone


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # Ensure tables exist
    conn.execute("""CREATE TABLE IF NOT EXISTS notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        time TEXT NOT NULL
                    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS blog (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        time TEXT NOT NULL
                    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS places (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        lat REAL NOT NULL,
                        lon REAL NOT NULL,
                        description TEXT,
                        icon TEXT,
                        time TEXT NOT NULL
                    )""")
    conn.commit()
    return conn


def write(s):
    t = datetime.now().astimezone(tz=timezone).strftime('%Y-%m-%d %H:%M:%S %z')
    conn = _get_conn()
    conn.execute("INSERT INTO notes (content, time) VALUES (?, ?)", (s, t))
    conn.commit()
    conn.close()


def getwrite():
    conn = _get_conn()
    df = pd.read_sql_query("SELECT * FROM notes ORDER BY id DESC", conn)
    conn.close()
    return df


def blog(s):
    t = datetime.now().astimezone(tz=timezone).strftime('%Y-%m-%d %H:%M:%S %z')
    conn = _get_conn()
    conn.execute("INSERT INTO blog (content, time) VALUES (?, ?)", (s, t))
    conn.commit()
    conn.close()


def getblog():
    conn = _get_conn()
    df = pd.read_sql_query("SELECT * FROM blog ORDER BY id DESC", conn)
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Places (map markers)
# ---------------------------------------------------------------------------

def add_place(name, lat, lon, description, icon):
    t = datetime.now().astimezone(tz=timezone).strftime('%Y-%m-%d %H:%M:%S %z')
    conn = _get_conn()
    conn.execute(
        "INSERT INTO places (name, lat, lon, description, icon, time) VALUES (?, ?, ?, ?, ?, ?)",
        (name, lat, lon, description, icon, t),
    )
    conn.commit()
    conn.close()


def get_places():
    conn = _get_conn()
    df = pd.read_sql_query("SELECT * FROM places ORDER BY id DESC", conn)
    conn.close()
    return df


def delete_place(place_id):
    conn = _get_conn()
    conn.execute("DELETE FROM places WHERE id = ?", (place_id,))
    conn.commit()
    conn.close()