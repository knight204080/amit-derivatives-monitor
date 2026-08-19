"""Hyperliquid public info API adapter. No API key required.

Funding on Hyperliquid settles hourly (vs. 8h on the centralized venues here)
per Hyperliquid's documented perpetuals mechanics. The metaAndAssetCtxs
endpoint returns the current hourly rate directly, not annualized.
"""
import time
import urllib.request
import json

URL = "https://api.hyperliquid.xyz/info"
FUNDING_INTERVAL_HOURS = 1


def fetch(symbol):
    body = json.dumps({"type": "metaAndAssetCtxs"}).encode()
    req = urllib.request.Request(
        URL, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        meta, ctxs = json.load(resp)

    names = [u["name"] for u in meta["universe"]]
    if symbol not in names:
        raise ValueError(f"hyperliquid has no market for {symbol}")
    ctx = ctxs[names.index(symbol)]

    mark_price = float(ctx["markPx"])
    oi_contracts = float(ctx["openInterest"])

    return {
        "venue": "hyperliquid",
        "symbol": symbol,
        "timestamp_utc": time.time(),
        "funding_rate": float(ctx["funding"]),
        "funding_interval_hours": FUNDING_INTERVAL_HOURS,
        "next_funding_time": None,  # settles on the hour; not returned explicitly
        "mark_price": mark_price,
        "index_price": float(ctx["oraclePx"]),
        "oi_contracts": oi_contracts,
        "oi_notional_usd": oi_contracts * mark_price,
    }
