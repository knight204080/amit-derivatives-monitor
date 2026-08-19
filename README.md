# Cross-Venue Derivatives Monitor

A read-only, keyless monitor of funding rates, spot-perp basis, and open
interest for BTC/ETH/SOL perpetuals across five venues. Built as a separate
project from the PFC momentum-carry signal system: this is infrastructure,
not a trading strategy. No positions, no signals, no recommendations.

Live view: [amitrathore.io/derivatives](https://amitrathore.io/derivatives)

## Coverage matrix

| Venue | BTC | ETH | SOL | Funding interval | Funding history depth |
|---|---|---|---|---|---|
| Binance USDT-M Futures | yes | yes | yes | 8h | 30 days |
| Bybit v5 (linear) | yes | yes | yes | 8h | 30 days |
| OKX v5 (USDT-swap) | yes | yes | yes | 8h | 30 days |
| Deribit | yes | yes | **no** | 8h | 30 days |
| Hyperliquid | yes | yes | yes | **1h** | ~21 days (API page-size limit) |

Deribit has no SOL perpetual (`get_instruments?currency=SOL&kind=future`
returns an empty list): this is a real venue gap, not a bug, and is logged
as `skipped` rather than faked. Hyperliquid's shorter backfill window is a
consequence of its funding-history endpoint capping at 500 rows per call at
hourly resolution; a paginated backfill would close the gap but hasn't been
built yet.

## Data model

`funding_snapshots`: one row per venue/symbol/poll, with raw funding rate,
the venue's actual funding interval, an annualized funding percentage,
mark/index price, basis (perp vs. spot, in bps), and open interest in both
native contracts and USD notional.

`funding_history`: backfilled historical funding-rate observations per
venue/symbol, populated once via `backfill.py` from each venue's public
funding-history endpoint, no API keys. This is what makes the 30-day
percentile and z-score in the live view real numbers rather than dead code.

`ingest_log`: one row per fetch attempt (ok/error/skipped), the basis for
the data-quality panel: feed lag, error rate, and per-venue reliability
over time.

## Design choices, stated plainly

- **Spot reference for basis**: Binance spot price, not a cross-venue median
  index. Simple and defensible for Phase 1; a proper composite index is a
  Phase 2 improvement, not hidden as equivalent to one.
- **SQLite, not Postgres**: the RTX machine this runs on has Postgres
  installed but the service isn't active and there's no sudo access to
  start it without further setup. SQLite has zero ops overhead for a
  single-writer ingest process and is trivial to migrate later.
- **Deribit OI is USD-denominated** in its own API (`open_interest` field),
  unlike the other four venues which report OI in contracts. `oi_contracts`
  is `None` for Deribit rather than a fabricated conversion.
- **No liquidation panel.** Binance stopped publishing its public
  liquidation stream in 2021, and no free, reliable source exists for
  historical liquidation data across all five venues (Coinglass is the
  usual answer, and it's a paid vendor). Stating that plainly rather than
  faking a liquidation feed from an incomplete source.

## What this is not (by design, not oversight)

- No liquidity/slippage simulation
- No news/sentiment overlay (a real, verified option exists: `ElKulako/cryptobert`
  on public RSS headlines; parked as a later addition, not built yet)
- No wallet-connected or authenticated endpoints anywhere in this codebase

## Running it

```bash
python3 -m venv venv && source venv/bin/activate
# no third-party dependencies -- adapters use stdlib urllib.request only
python3 compute.py     # runs self-tests
python3 backfill.py    # one-time: populate funding_history for percentile/z-score
python3 ingest.py      # single ingest pass, writes to data/monitor.db
python3 export.py      # writes data/latest_snapshot.json for the public repo and site sync
```

In production this runs via cron every 15 minutes (`cron.sh`), pushing the
updated snapshot to this repo and syncing it into the live site.
