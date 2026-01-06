
import sqlite3
import os
import time
import pandas as pd
from datetime import datetime
import pytz

# Local SQLite database stored next to this module
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