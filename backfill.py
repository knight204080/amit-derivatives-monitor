#!/usr/bin/env python3
"""One-time backfill of ~30 days of funding-rate history per venue/symbol,
from free public endpoints, no API keys. Populates funding_history so the
percentile_rank/z_score functions in compute.py (already written, previously
unusable with zero history) have real data to work against.

Deribit has no SOL perpetual (documented, consistent gap, not a bug).
Endpoint response shapes verified live on 2026-08-19 before writing this.
"""
import json
import sqlite3
import time
import urllib.request
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from compute import annualize_funding

DB_PATH = Path(__file__).parent / "data" / "monitor.db"
DAYS = 30
SYMBOLS = ["BTC", "ETH", "SOL"]


def _get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def backfill_binance(symbol):
    pair = f"{symbol}USDT"
    since_ms = int((time.time() - DAYS * 86400) * 1000)
    rows = _get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={pair}&startTime={since_ms}&limit=1000")
    return [
        {"funding_time": r["fundingTime"] / 1000, "funding_rate": float(r["fundingRate"]), "interval_hours": 8}
        for r in rows
    ]


def backfill_bybit(symbol):
    pair = f"{symbol}USDT"
    since_ms = int((time.time() - DAYS * 86400) * 1000)
    out = []
    end_ms = int(time.time() * 1000)
    for _ in range(3):  # paginate backward, 200/page, covers 30d of 8h funding easily
        r = _get(f"https://api.bybit.com/v5/market/funding/history?category=linear&symbol={pair}&endTime={end_ms}&limit=200")
        batch = r["result"]["list"]
        if not batch:
            break
        for row in batch:
            out.append({
                "funding_time": int(row["fundingRateTimestamp"]) / 1000,
                "funding_rate": float(row["fundingRate"]),
                "interval_hours": 8,
            })
        oldest = min(int(x["fundingRateTimestamp"]) for x in batch)
        if oldest <= since_ms:
            break
        end_ms = oldest - 1
    return [r for r in out if r["funding_time"] * 1000 >= since_ms]


_OKX_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; amit-derivatives-monitor/1.0)"}


def backfill_okx(symbol):
    inst = f"{symbol}-USDT-SWAP"
    since_ms = int((time.time() - DAYS * 86400) * 1000)
    out = []
    before = None
    for _ in range(5):  # 100/page
        url = f"https://www.okx.com/api/v5/public/funding-rate-history?instId={inst}&limit=100"
        if before:
            url += f"&before={before}"
        r = _get(url, headers=_OKX_HEADERS)
        batch = r["data"]
        if not batch:
            break
        for row in batch:
            out.append({
                "funding_time": int(row["fundingTime"]) / 1000,
                "funding_rate": float(row["fundingRate"]),
                "interval_hours": 8,
            })
        oldest = min(int(x["fundingTime"]) for x in batch)
        before = oldest
        if oldest <= since_ms:
            break
    return [r for r in out if r["funding_time"] * 1000 >= since_ms]


def backfill_deribit(symbol):
    if symbol not in {"BTC", "ETH"}:
        return []  # no SOL perpetual, documented gap
    now_ms = int(time.time() * 1000)
    start_ms = int((time.time() - DAYS * 86400) * 1000)
    r = _get(f"https://www.deribit.com/api/v2/public/get_funding_rate_history?instrument_name={symbol}-PERPETUAL&start_timestamp={start_ms}&end_timestamp={now_ms}")
    return [
        {"funding_time": row["timestamp"] / 1000, "funding_rate": row["interest_8h"], "interval_hours": 8}
        for row in r["result"]
    ]


def backfill_hyperliquid(symbol):
    start_ms = int((time.time() - DAYS * 86400) * 1000)
    body = json.dumps({"type": "fundingHistory", "coin": symbol, "startTime": start_ms}).encode()
    req = urllib.request.Request("https://api.hyperliquid.xyz/info", data=body,
                                  headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        rows = json.load(resp)
    return [
        {"funding_time": row["time"] / 1000, "funding_rate": float(row["fundingRate"]), "interval_hours": 1}
        for row in rows
    ]


BACKFILL_FNS = {
    "binance": backfill_binance,
    "bybit": backfill_bybit,
    "okx": backfill_okx,
    "deribit": backfill_deribit,
    "hyperliquid": backfill_hyperliquid,
}


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS funding_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venue TEXT NOT NULL,
            symbol TEXT NOT NULL,
            funding_time REAL NOT NULL,
            funding_rate REAL NOT NULL,
            annualized_funding_pct REAL NOT NULL,
            UNIQUE(venue, symbol, funding_time)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_funding_history_vs ON funding_history (venue, symbol, funding_time)")

    total_inserted = 0
    for venue, fn in BACKFILL_FNS.items():
        for symbol in SYMBOLS:
            try:
                rows = fn(symbol)
            except Exception as e:
                print(f"  {venue}/{symbol}: FAILED - {e}")
                continue
            inserted = 0
            for r in rows:
                ann = annualize_funding(r["funding_rate"], r["interval_hours"])
                try:
                    conn.execute(
                        "INSERT INTO funding_history (venue, symbol, funding_time, funding_rate, annualized_funding_pct) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (venue, symbol, r["funding_time"], r["funding_rate"], ann),
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    pass  # already backfilled this point, idempotent re-run
            conn.commit()
            total_inserted += inserted
            print(f"  {venue}/{symbol}: {inserted} rows ({len(rows)} fetched)")

    print(f"\nbackfill complete: {total_inserted} new rows inserted")
    conn.close()


if __name__ == "__main__":
    run()
