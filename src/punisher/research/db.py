from datetime import datetime
from punisher.config import settings


def init_research_db():
    import sqlite3

    conn = sqlite3.connect("research.db")
    c = conn.cursor()

    # YouTube Knowledge Base
    c.execute("""CREATE TABLE IF NOT EXISTS youtube_knowledge (
        video_id TEXT PRIMARY KEY,
        channel TEXT,
        title TEXT,
        published_at DATE,
        transcript TEXT,
        summary TEXT,
        key_levels TEXT,
        sentiment TEXT
    )""")

    # Market Metrics (CoinGlass, CBBI)
    c.execute("""CREATE TABLE IF NOT EXISTS market_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        source TEXT,
        metric_name TEXT,
        value REAL,
        meta JSON
    )""")

    # Hyperliquid Wallet Snapshots
    c.execute("""CREATE TABLE IF NOT EXISTS hyperliquid_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wallet_address TEXT NOT NULL,
        snapshot_time_ms INTEGER,
        account_value TEXT,
        total_ntl_pos TEXT,
        total_raw_usd TEXT,
        total_margin_used TEXT,
        withdrawable TEXT,
        cross_maintenance_margin_used TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # Hyperliquid Positions
    c.execute("""CREATE TABLE IF NOT EXISTS hyperliquid_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id INTEGER,
        wallet_address TEXT NOT NULL,
        coin TEXT NOT NULL,
        type TEXT,
        size TEXT,
        leverage_type TEXT,
        leverage_value INTEGER,
        entry_price TEXT,
        position_value TEXT,
        unrealized_pnl TEXT,
        return_on_equity TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (snapshot_id) REFERENCES hyperliquid_snapshots(id)
    )""")

    # Hyperliquid Open Orders
    c.execute("""CREATE TABLE IF NOT EXISTS hyperliquid_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id INTEGER,
        wallet_address TEXT NOT NULL,
        order_id TEXT,
        coin TEXT,
        side TEXT,
        limit_price TEXT,
        quantity TEXT,
        timestamp_ms INTEGER,
        order_type TEXT,
        reduce_only INTEGER,
        time_in_force TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (snapshot_id) REFERENCES hyperliquid_snapshots(id)
    )""")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_research_db()
