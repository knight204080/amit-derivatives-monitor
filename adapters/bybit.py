"""Bybit v5 public REST adapter. No API key required.

Confirmed live 2026-08-19: /v5/market/tickers returns fundingIntervalHour
directly per symbol (8 for BTCUSDT/ETHUSDT/SOLUSDT).
"""
import time
import urllib.request
import json

BASE = "https://api.bybit.com"


def _get(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.load(resp)


def fetch(symbol):
    pair = f"{symbol}USDT"
    data = _get(f"{BASE}/v5/market/tickers?category=linear&symbol={pair}")
    if data.get("retCode") != 0:
        raise RuntimeError(f"bybit error: {data.get('retMsg')}")
    row = data["result"]["list"][0]

    return {
        "venue": "bybit",
        "symbol": symbol,
        "timestamp_utc": time.time(),
        "funding_rate": float(row["fundingRate"]),
        "funding_interval_hours": int(row["fundingIntervalHour"]),
        "next_funding_time": int(row["nextFundingTime"]) / 1000,
        "mark_price": float(row["markPrice"]),
        "index_price": float(row["indexPrice"]),
        "oi_contracts": float(row["openInterest"]),
        "oi_notional_usd": float(row["openInterestValue"]),
    }
