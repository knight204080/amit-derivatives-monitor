from . import binance, bybit, okx, deribit, hyperliquid

REGISTRY = {
    "binance": binance,
    "bybit": bybit,
    "okx": okx,
    "deribit": deribit,
    "hyperliquid": hyperliquid,
}
