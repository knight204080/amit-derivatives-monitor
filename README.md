# Cross-Venue Derivatives Monitor (Phase 1)

A read-only, keyless monitor of funding rates, spot-perp basis, and open
interest for BTC/ETH/SOL perpetuals across five venues. Built as a separate
project from the PFC momentum-carry signal system -- this is infrastructure,
not a trading strategy: no positions, no signals, no recommendations.

## Coverage matrix

| Venue | BTC | ETH | SOL | Funding interval |
|---|---|---|---|---|
| Binance USDT-M Futures | yes | yes | yes | 8h |
| Bybit v5 (linear) | yes | yes | yes | 8h |
| OKX v5 (USDT-swap) | yes | yes | yes | 8h |
| Deribit | yes | yes | **no** | 8h |
| Hyperliquid | yes | yes | yes | **1h** |

Deribit has no SOL perpetual (`get_instruments?currency=SOL&kind=future`
returns an empty list) -- this is a real venue gap, not a bug, and is logged
as `skipped` rather than faked.

## Data model

`funding_snapshots`: one row per venue/symbol/poll, with raw funding rate,
the venue's actual funding interval, an annualized funding percentage,
mark/index price, basis (perp vs. spot, in bps), and open interest in both
native contracts and USD notional.

`ingest_log`: one row per fetch attempt (ok/error/skipped), the basis for
the data-quality panel -- feed lag, error rate, and per-venue reliability
over time.

## Design choices, stated plainly

- **Spot reference for basis**: Binance spot price, not a cross-venue median
  index. Simple and defensible for Phase 1; a proper composite index is a
  Phase 2 improvement, not hidden as equivalent to one.
- **SQLite, not Postgres**: the RTX machine this currently runs on has
  Postgres installed but the service isn't active and there's no sudo access
  to start it without further setup. SQLite has zero ops overhead for a
  single-writer ingest process and is trivial to migrate once production
  hosting (TBD -- VPS vs. this machine) is decided.
- **Deribit OI is USD-denominated** in its own API (`open_interest` field),
  unlike the other four venues which report OI in contracts. `oi_contracts`
  is `None` for Deribit rather than a fabricated conversion.

## What this is not yet (Phase 2)

- No liquidation tracker
- No liquidity/slippage simulation
- No frontend or public API -- data currently lives in a local SQLite file
- No cron wiring yet -- `ingest.py` runs as a single pass, intended to be
  called every few minutes once scheduled
- No historical percentile/z-score display (the functions exist in
  `compute.py` but need accumulated history to be meaningful)

## Running it

```bash
python3 -m venv venv && source venv/bin/activate
# no third-party dependencies -- adapters use stdlib urllib.request only
python3 compute.py     # runs self-tests
python3 ingest.py      # single ingest pass, writes to data/monitor.db
```
