import sqlite3
import os

DB_PATH = os.path.join("data", "wb.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS advert_limits (
                campaign_id INTEGER PRIMARY KEY,
                campaign_name TEXT,
                daily_limit REAL DEFAULT 0,
                auto_pause BOOLEAN DEFAULT 1,
                last_paused_date TEXT
            )
        """)
        conn.commit()

def get_all_limits():
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT campaign_id, campaign_name, daily_limit, auto_pause, last_paused_date FROM advert_limits")
        return cursor.fetchall()

def update_limit(campaign_id, campaign_name, daily_limit, auto_pause):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO advert_limits (campaign_id, campaign_name, daily_limit, auto_pause)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(campaign_id) DO UPDATE SET
                campaign_name = excluded.campaign_name,
                daily_limit = excluded.daily_limit,
                auto_pause = excluded.auto_pause
        """, (campaign_id, campaign_name, daily_limit, auto_pause))
        conn.commit()

def set_paused_date(campaign_id, date_str: str):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE advert_limits SET last_paused_date = ? WHERE campaign_id = ?", (date_str, campaign_id))
        conn.commit()