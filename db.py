"""SQLite schema and access helpers. WAL mode for safe concurrent read/write."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "monitor.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS funding_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timestamp_utc REAL NOT NULL,
    funding_rate REAL,
    funding_interval_hours REAL,
    annualized_funding_pct REAL,
    next_funding_time REAL,
    mark_price REAL,
    index_price REAL,
    basis_bps REAL,
    oi_contracts REAL,
    oi_notional_usd REAL
);
CREATE INDEX IF NOT EXISTS idx_funding_venue_symbol_ts
    ON funding_snapshots (venue, symbol, timestamp_utc);

CREATE TABLE IF NOT EXISTS ingest_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc REAL NOT NULL,
    venue TEXT NOT NULL,
    symbol TEXT NOT NULL,
    status TEXT NOT NULL,       -- 'ok' or 'error'
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_ingest_log_ts ON ingest_log (timestamp_utc);
"""


def connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def insert_snapshot(conn, row):
    conn.execute(
        """INSERT INTO funding_snapshots
           (venue, symbol, timestamp_utc, funding_rate, funding_interval_hours,
            annualized_funding_pct, next_funding_time, mark_price, index_price,
            basis_bps, oi_contracts, oi_notional_usd)
           VALUES (:venue, :symbol, :timestamp_utc, :funding_rate,
                   :funding_interval_hours, :annualized_funding_pct,
                   :next_funding_time, :mark_price, :index_price, :basis_bps,
                   :oi_contracts, :oi_notional_usd)""",
        row,
    )


def log_ingest(conn, timestamp_utc, venue, symbol, status, error_message=None):
    conn.execute(
        """INSERT INTO ingest_log (timestamp_utc, venue, symbol, status, error_message)
           VALUES (?, ?, ?, ?, ?)""",
        (timestamp_utc, venue, symbol, status, error_message),
    )
