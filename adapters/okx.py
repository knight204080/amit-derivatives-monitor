"""OKX v5 public REST adapter. No API key required.

Confirmed live 2026-08-19: funding-rate response includes fundingTime and
prevFundingTime; the gap is 8h for BTC/ETH/SOL USDT-swap.
"""
import time
import urllib.request
import json

BASE = "https://www.okx.com"

# OKX's WAF returns 403 for Python's default urllib User-Agent
# ("Python-urllib/3.x") specifically -- confirmed live 2026-08-19 (curl with
# no UA override works fine; urllib with no UA override does not). A plain
# browser-style UA is enough to pass.
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; amit-derivatives-monitor/1.0)"}


def _get(url):
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.load(resp)
    if data.get("code") != "0":
        raise RuntimeError(f"okx error: {data.get('msg')}")
    return data["data"][0]


def fetch(symbol):
    inst = f"{symbol}-USDT-SWAP"
    spot_inst = f"{symbol}-USDT"

    funding = _get(f"{BASE}/api/v5/public/funding-rate?instId={inst}")
    oi = _get(f"{BASE}/api/v5/public/open-interest?instType=SWAP&instId={inst}")
    mark = _get(f"{BASE}/api/v5/public/mark-price?instType=SWAP&instId={inst}")
    index = _get(f"{BASE}/api/v5/market/index-tickers?instId={spot_inst}")

    funding_interval_hours = (
        int(funding["fundingTime"]) - int(funding["prevFundingTime"])
    ) / 1000 / 3600

    return {
        "venue": "okx",
        "symbol": symbol,
        "timestamp_utc": time.time(),
        "funding_rate": float(funding["fundingRate"]),
        "funding_interval_hours": funding_interval_hours,
        "next_funding_time": int(funding["fundingTime"]) / 1000,
        "mark_price": float(mark["markPx"]),
        "index_price": float(index["idxPx"]),
        "oi_contracts": float(oi["oiCcy"]),
        "oi_notional_usd": float(oi["oiUsd"]),
    }
