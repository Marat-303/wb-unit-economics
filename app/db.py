import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "wb.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS cost_prices (
    nm_id       INTEGER PRIMARY KEY,
    sa_name     TEXT,
    cost_rub    REAL NOT NULL,
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    nm_id       INTEGER PRIMARY KEY,
    vendor_code TEXT,
    title       TEXT,
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sales (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date           TEXT NOT NULL,
    nm_id                 INTEGER NOT NULL,
    sa_name               TEXT,
    quantity              INTEGER NOT NULL DEFAULT 0,
    return_qty            INTEGER NOT NULL DEFAULT 0,
    retail_amount         REAL NOT NULL DEFAULT 0,
    ppvz_sales_commission REAL NOT NULL DEFAULT 0,
    ppvz_for_pay          REAL NOT NULL DEFAULT 0,
    
    delivery_rub          REAL NOT NULL DEFAULT 0,
    storage_fee           REAL NOT NULL DEFAULT 0,
    processing_fee        REAL NOT NULL DEFAULT 0,
    other_deductions      REAL NOT NULL DEFAULT 0,
    penalty_fee           REAL NOT NULL DEFAULT 0,
    wb_correction         REAL NOT NULL DEFAULT 0,
    
    UNIQUE (report_date, nm_id)
);

CREATE TABLE IF NOT EXISTS ads (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date   TEXT NOT NULL,
    campaign_id   INTEGER,
    campaign_name TEXT,
    nm_id         INTEGER,
    sum_rub       REAL NOT NULL DEFAULT 0,
    sum_price     REAL NOT NULL DEFAULT 0,
    UNIQUE (report_date, campaign_id, nm_id)
);

CREATE TABLE IF NOT EXISTS taxes (
    month_str       TEXT PRIMARY KEY,
    tax_amount      REAL NOT NULL DEFAULT 0,
    premiums_amount REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sync_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type  TEXT NOT NULL,
    status     TEXT NOT NULL,
    message    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        
        # Миграция для sales
        cursor = conn.execute("PRAGMA table_info(sales)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "return_qty" not in columns:
            conn.execute("ALTER TABLE sales ADD COLUMN return_qty INTEGER NOT NULL DEFAULT 0")
            
        # Миграция для taxes (добавляем premiums_amount)
        cursor = conn.execute("PRAGMA table_info(taxes)")
        tax_cols = [row["name"] for row in cursor.fetchall()]
        if "premiums_amount" not in tax_cols:
            conn.execute("ALTER TABLE taxes ADD COLUMN premiums_amount REAL NOT NULL DEFAULT 0")
        
        conn.commit()