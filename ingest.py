#!/usr/bin/env python3
"""Single-pass ingest: poll all 5 venues for BTC/ETH/SOL funding/basis/OI,
write to SQLite, log every attempt (success or failure) for the data-quality
panel. Designed to run from cron, matching the existing daily_run.sh pattern
in ~/amit-quant-system -- this one should run frequently (every few minutes),
not daily, since funding/basis/OI move continuously.
"""
import time
import urllib.request
import json

import db
from adapters import REGISTRY
from compute import annualize_funding, basis_bps

SYMBOLS = ["BTC", "ETH", "SOL"]
SPOT_INDEX_URL = "https://api.binance.com/api/v3/ticker/price?symbol={}USDT"


def get_spot_index(symbol):
    """Reference spot price for basis calculation. Uses Binance spot as a
    simple, defensible single reference -- not a cross-venue median (that's
    a documented simplification, see README)."""
    with urllib.request.urlopen(SPOT_INDEX_URL.format(symbol), timeout=10) as resp:
        return float(json.load(resp)["price"])


def run():
    conn = db.connect()
    ok_count = 0
    fail_count = 0
    failures = []

    spot_prices = {}
    for symbol in SYMBOLS:
        try:
            spot_prices[symbol] = get_spot_index(symbol)
        except Exception as e:
            print(f"FATAL: could not fetch spot index for {symbol}: {e}")
            return

    for venue_name, adapter in REGISTRY.items():
        for symbol in SYMBOLS:
            ts = time.time()
            try:
                data = adapter.fetch(symbol)
                annualized = None
                if data["funding_rate"] is not None and data["funding_interval_hours"]:
                    annualized = annualize_funding(
                        data["funding_rate"], data["funding_interval_hours"]
                    )
                basis = None
                if data["mark_price"] is not None:
                    basis = basis_bps(data["mark_price"], spot_prices[symbol])

                row = {
                    "venue": data["venue"],
                    "symbol": data["symbol"],
                    "timestamp_utc": data["timestamp_utc"],
                    "funding_rate": data["funding_rate"],
                    "funding_interval_hours": data["funding_interval_hours"],
                    "annualized_funding_pct": annualized,
                    "next_funding_time": data["next_funding_time"],
                    "mark_price": data["mark_price"],
                    "index_price": data["index_price"],
                    "basis_bps": basis,
                    "oi_contracts": data["oi_contracts"],
                    "oi_notional_usd": data["oi_notional_usd"],
                }
                db.insert_snapshot(conn, row)
                db.log_ingest(conn, ts, venue_name, symbol, "ok")
                ok_count += 1
            except ValueError as e:
                # expected gap (e.g. Deribit has no SOL) -- log, don't alarm
                db.log_ingest(conn, ts, venue_name, symbol, "skipped", str(e))
            except Exception as e:
                db.log_ingest(conn, ts, venue_name, symbol, "error", str(e))
                fail_count += 1
                failures.append(f"{venue_name}/{symbol}: {e}")

    conn.commit()
    conn.close()

    print(f"ingest complete: {ok_count} ok, {fail_count} failed")
    for f in failures:
        print(f"  FAILED: {f}")


if __name__ == "__main__":
    run()
