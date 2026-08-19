"""Binance USDT-M Futures public REST adapter. No API key required.

Confirmed live 2026-08-19: funding interval is 8h for BTCUSDT/ETHUSDT/SOLUSDT
via GET /fapi/v1/fundingInfo.
"""
import time
import urllib.request
import json

BASE = "https://fapi.binance.com"
SPOT_BASE = "https://api.binance.com"

FUNDING_INTERVAL_HOURS = 8


def _get(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.load(resp)


def fetch(symbol):
    pair = f"{symbol}USDT"
    premium = _get(f"{BASE}/fapi/v1/premiumIndex?symbol={pair}")
    oi = _get(f"{BASE}/fapi/v1/openInterest?symbol={pair}")

    mark_price = float(premium["markPrice"])
    oi_contracts = float(oi["openInterest"])

    return {
        "venue": "binance",
        "symbol": symbol,
        "timestamp_utc": time.time(),
        "funding_rate": float(premium["lastFundingRate"]),
        "funding_interval_hours": FUNDING_INTERVAL_HOURS,
        "next_funding_time": int(premium["nextFundingTime"]) / 1000,
        "mark_price": mark_price,
        "index_price": float(premium["indexPrice"]),
        "oi_contracts": oi_contracts,
        "oi_notional_usd": oi_contracts * mark_price,
    }
