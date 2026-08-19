#!/usr/bin/env python3
"""Export the latest snapshot and recent ingest health to JSON, for the public
repo and the site sync. Reads only, never writes to the SQLite db."""
import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "monitor.db"
OUT_PATH = Path(__file__).parent / "data" / "latest_snapshot.json"


def export():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    latest_per_venue_symbol = conn.execute("""
        SELECT f.* FROM funding_snapshots f
        INNER JOIN (
            SELECT venue, symbol, MAX(timestamp_utc) AS max_ts
            FROM funding_snapshots GROUP BY venue, symbol
        ) latest
        ON f.venue = latest.venue AND f.symbol = latest.symbol AND f.timestamp_utc = latest.max_ts
        ORDER BY f.symbol, f.venue
    """).fetchall()

    snapshots = [dict(row) for row in latest_per_venue_symbol]

    since = time.time() - 24 * 3600
    ingest_stats = conn.execute("""
        SELECT status, COUNT(*) as n FROM ingest_log
        WHERE timestamp_utc > ? GROUP BY status
    """, (since,)).fetchall()
    health = {row["status"]: row["n"] for row in ingest_stats}

    last_ingest = conn.execute("SELECT MAX(timestamp_utc) as ts FROM ingest_log").fetchone()["ts"]

    conn.close()

    output = {
        "generated_at_utc": time.time(),
        "last_ingest_utc": last_ingest,
        "ingest_health_24h": health,
        "snapshots": snapshots,
    }
    OUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"exported {len(snapshots)} snapshots to {OUT_PATH}")


if __name__ == "__main__":
    export()
