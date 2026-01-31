"""
Hyperliquid Market Data Monitor
Uses HTTP polling for trades and L2 book data
More reliable than WebSocket for high-frequency global market data
"""

import asyncio
import logging
import httpx
import time
from punisher.bus.queue import MessageQueue

logger = logging.getLogger("punisher.crypto.hyperliquid_market")


class HyperliquidMarketMonitor:
    """
    HTTP-based Market Data Monitor for Hyperliquid
    - Polls L2 order book for market sentiment
    - Tracks recent trades for whale detection
    - More reliable than WebSocket for global streams
    """

    def __init__(self, coin: str = "BTC"):
        self.api_url = "https://api.hyperliquid.xyz/info"
        self.coin = coin
        self.queue = MessageQueue()
        self.running = False

        # State tracking
        self.last_trades_hash = None
        self.last_sentiment_time = 0

    async def start(self):
        """Main polling loop"""
        self.running = True
        logger.info(f"Starting Hyperliquid Market Monitor for {self.coin}")

        async with httpx.AsyncClient(timeout=10) as client:
            while self.running:
                try:
                    # Parallel fetch of book and trades
                    book_task = self.fetch_l2_book(client)
                    trades_task = self.fetch_recent_trades(client)

                    book_data, trades_data = await asyncio.gather(
                        book_task, trades_task, return_exceptions=True
                    )

                    # Process L2 Book for sentiment
                    if isinstance(book_data, dict) and book_data:
                        await self.process_order_book(book_data)

                    # Process trades for whale detection
                    if isinstance(trades_data, list) and trades_data:
                        await self.process_trades(trades_data)

                    # Poll interval (2-5 seconds with jitter)
                    import random

                    await asyncio.sleep(random.uniform(2, 5))

                except Exception as e:
                    logger.error(f"Market monitor error: {e}")
                    await asyncio.sleep(10)

    async def fetch_l2_book(self, client: httpx.AsyncClient) -> dict:
        """Fetch L2 order book via HTTP"""
        try:
            payload = {"type": "l2Book", "coin": self.coin}
            resp = await client.post(self.api_url, json=payload)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.debug(f"L2 book fetch failed: {e}")
        return {}

    async def fetch_recent_trades(self, client: httpx.AsyncClient) -> list:
        """Fetch recent trades via HTTP"""
        try:
            payload = {"type": "recentTrades", "coin": self.coin}
            resp = await client.post(self.api_url, json=payload)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.debug(f"Trades fetch failed: {e}")
        return []

    async def process_order_book(self, book_data: dict):
        """Calculate and broadcast market sentiment from order book"""
        now = time.time()

        # Throttle sentiment updates to every 5 seconds
        if now - self.last_sentiment_time < 5:
            return

        try:
            levels = book_data.get("levels", [])
            if len(levels) >= 2:
                bids = levels[0]  # [[price, size], ...]
                asks = levels[1]

                # Sum volume of top 10 levels
                bid_vol = sum(
                    float(b.get("sz", b[1]) if isinstance(b, dict) else b[1])
                    for b in bids[:10]
                )
                ask_vol = sum(
                    float(a.get("sz", a[1]) if isinstance(a, dict) else a[1])
                    for a in asks[:10]
                )
                total_vol = bid_vol + ask_vol

                if total_vol > 0:
                    imbalance = (bid_vol - ask_vol) / total_vol

                    if imbalance > 0.2:
                        sentiment = "BULLISH 🟢"
                    elif imbalance < -0.2:
                        sentiment = "BEARISH 🔴"
                    else:
                        sentiment = "NEUTRAL ⚪"

                    self.queue.push(
                        "punisher:cli:out",
                        f"[MARKET] {self.coin} {sentiment} | Imbalance: {imbalance * 100:+.1f}%",
                    )
                    self.last_sentiment_time = now

        except Exception as e:
            logger.debug(f"Order book processing error: {e}")

    async def process_trades(self, trades: list):
        """Detect and broadcast whale trades"""
        try:
            # Create hash of trade IDs to detect new trades
            if not trades:
                return

            current_hash = hash(
                str([t.get("tid", t.get("time", "")) for t in trades[:5]])
            )

            if current_hash == self.last_trades_hash:
                return  # No new trades

            self.last_trades_hash = current_hash

            for trade in trades[:10]:  # Check last 10 trades
                # Handle different trade formats
                if isinstance(trade, dict):
                    size = float(trade.get("sz", trade.get("size", 0)))
                    price = float(trade.get("px", trade.get("price", 0)))
                    side = trade.get("side", "?")
                else:
                    continue

                usd_value = size * price

                # Whale threshold: > $50k
                if usd_value > 50000:
                    emoji = "🐋" if side in ["B", "buy"] else "🐻"
                    alert = f"[WHALE] {emoji} {side.upper()} {size:.4f} {self.coin} @ ${price:,.0f} (${usd_value / 1000:.1f}k)"
                    self.queue.push("punisher:cli:out", alert)

        except Exception as e:
            logger.debug(f"Trades processing error: {e}")

    def stop(self):
        self.running = False
