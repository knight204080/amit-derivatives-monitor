"""Deribit public REST adapter. No API key required.

Confirmed live 2026-08-19: Deribit lists BTC-PERPETUAL and ETH-PERPETUAL only.
No SOL perpetual exists (get_instruments?currency=SOL&kind=future returns
empty). fetch() raises ValueError for unsupported symbols rather than
fabricating data; callers must handle this and skip the combo.
"""
import time
import urllib.request
import json

BASE = "https://www.deribit.com"
SUPPORTED = {"BTC", "ETH"}


def _get(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.load(resp)["result"]


def fetch(symbol):
    if symbol not in SUPPORTED:
        raise ValueError(f"deribit has no perpetual for {symbol}")

    r = _get(f"{BASE}/api/v2/public/ticker?instrument_name={symbol}-PERPETUAL")

    return {
        "venue": "deribit",
        "symbol": symbol,
        "timestamp_utc": time.time(),
        "funding_rate": r["funding_8h"],
        "funding_interval_hours": 8,
        "next_funding_time": None,  # Deribit does not expose this directly
        "mark_price": r["mark_price"],
        "index_price": r["index_price"],
        "oi_contracts": None,  # Deribit reports OI in USD, not contracts
        "oi_notional_usd": r["open_interest"],
    }
