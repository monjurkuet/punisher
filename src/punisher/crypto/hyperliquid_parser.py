import datetime
from typing import Dict, Any


def safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def parse_hyperliquid_data(data: dict) -> dict:
    """
    Parses webData2 snapshots into a clean, numeric format.
    Removes garbage fields and institutionalizes the data for MongoDB.
    """
    state = data.get("clearinghouseState", {})
    margin = state.get("marginSummary", {})

    snapshot_time = safe_int(
        state.get("time"), int(datetime.datetime.now().timestamp() * 1000)
    )

    summary = {
        "snapshot_time_ms": snapshot_time,
        "account_value": safe_float(margin.get("accountValue")),
        "total_ntl_pos": safe_float(margin.get("totalNtlPos")),
        "total_raw_usd": safe_float(margin.get("totalRawUsd")),
        "total_margin_used": safe_float(margin.get("totalMarginUsed")),
        "withdrawable": safe_float(state.get("withdrawable")),
    }

    asset_positions = []
    for asset in state.get("assetPositions", []):
        pos = asset.get("position", {})
        coin = pos.get("coin")
        size = safe_float(pos.get("szi"))

        if coin and size != 0:
            asset_positions.append(
                {
                    "coin": coin,
                    "size": size,
                    "entry_price": safe_float(pos.get("entryPx")),
                    "position_value": safe_float(pos.get("positionValue")),
                    "unrealized_pnl": safe_float(pos.get("unrealizedPnl")),
                    "roc": safe_float(pos.get("returnOnEquity")),
                    "leverage": safe_int(pos.get("leverage", {}).get("value"), 1),
                }
            )

    open_orders = []
    for order in data.get("openOrders", []):
        if order.get("oid") is not None:
            open_orders.append(
                {
                    "order_id": order.get("oid"),
                    "coin": order.get("coin", ""),
                    "side": order.get("side", ""),
                    "px": safe_float(order.get("limitPx")),
                    "sz": safe_float(order.get("sz")),
                    "order_type": order.get("orderType", "Limit"),
                }
            )

    return {
        "summary": summary,
        "positions": asset_positions,
        "orders": open_orders,
        "ts": snapshot_time,
    }


def parse_market_mids(data: dict) -> Dict[str, float]:
    """Cleans up allMids stream data"""
    raw_mids = data.get("mids", {})
    return {coin: safe_float(price) for coin, price in raw_mids.items()}


def parse_trade_data(trade: dict) -> dict:
    """Cleans up raw trade stream data"""
    px = safe_float(trade.get("px"))
    sz = safe_float(trade.get("sz"))
    return {
        "coin": trade.get("coin"),
        "side": trade.get("side"),
        "px": px,
        "sz": sz,
        "usd_val": px * sz,
        "ts": trade.get("time"),
        "hash": trade.get("hash"),
    }
