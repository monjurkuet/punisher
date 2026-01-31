"""
Crypto Agent - Specialized in Hyperliquid and CoinGlass intelligence.
Handles wallet discovery, monitoring, and alpha extraction.
"""

import asyncio
import logging
import json
from datetime import datetime, UTC
from punisher.bus.queue import MessageQueue
from punisher.crypto.hyperliquid import HyperliquidMonitor
from punisher.scrapers.coinglass import CoinGlassScraper

logger = logging.getLogger("punisher.agents.crypto")


class Satoshi:
    def __init__(self):
        self.queue = MessageQueue()
        self.hl_monitor = HyperliquidMonitor()
        self.cg_scraper = CoinGlassScraper()
        self.running = False

    async def start(self):
        """Start the crypto-dedicated subsystems"""
        self.running = True
        logger.info("Satoshi initialized. Managing Hyperliquid and CoinGlass.")

        # Start Hyperliquid WebSocket Monitor in background
        asyncio.create_task(self.hl_monitor.start())

        # Periodic CoinGlass Scraper (can be manually triggered or scheduled)
        # For now, we'll keep it as a triggerable task to manage discovery volume
        await self.broadcast("Satoshi Online. Tracking institutional flows.")

    async def broadcast(self, msg: str):
        self.queue.push("punisher:cli:out", f"[💎] {msg}")

    async def get_alpha_context(self) -> str:
        """Fetch latest alpha data for the Punisher's decision making"""
        context = "--- CRYPTO ALPHA (HL + CG) ---\n"
        try:
            from punisher.db.mongo import mongo

            db = await mongo.get_db()

            # 1. Newest Discoveries
            wallets = (
                await db.tracked_wallets.find()
                .sort("discovered_at", -1)
                .limit(3)
                .to_list(length=3)
            )
            if wallets:
                context += "Latest Discoveries:\n"
                for w in wallets:
                    context += f"- {w['address'][:10]}... (Group: {w.get('range_id')}, PnL: {w.get('pnl_str')})\n"

            # 2. Significant Active Positions (Whales)
            snapshots = (
                await db.hyperliquid_snapshots.find()
                .sort("created_at", -1)
                .limit(3)
                .to_list(length=3)
            )
            if snapshots:
                context += "\nActive Whale Movements:\n"
                for s in snapshots:
                    value = float(s.get("account_value", 0))
                    context += f"- {s['wallet_address'][:8]} Account: ${value:,.0f}\n"
                    for p in s.get("positions", []):
                        if abs(float(p.get("size", 0))) > 0:
                            coin = p.get("coin", "Unknown")
                            side = p.get("side", "N/A")
                            pnl = float(p.get("unrealized_pnl", 0))
                            context += f"  > {coin} {side} (PnL: ${pnl:,.0f})\n"

        except Exception as e:
            logger.error(f"Alpha context error: {e}")
            context += "[Alpha Data Temporarily Unavailable]\n"

        return context

    async def process_task(self, command: str) -> str:
        """Execute specific crypto commands"""
        cmd = command.lower()
        if "scrape" in cmd or "discover" in cmd:
            asyncio.create_task(self.cg_scraper.start())
            return "Scheduled deep scrape of CoinGlass. Discovery in progress."

        if "wallets" in cmd:
            from punisher.db.mongo import mongo

            db = await mongo.get_db()
            count = await db.tracked_wallets.count_documents({})
            return f"Currently tracking {count} high-conviction wallets across Hyperliquid."

        return "Acknowledged. Monitoring the tape."

    def stop(self):
        self.running = False
        self.hl_monitor.stop()
