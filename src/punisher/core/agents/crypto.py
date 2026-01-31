"""
Crypto Agent - Specialized in Hyperliquid and CoinGlass intelligence.
Handles wallet discovery, monitoring, and alpha extraction.
"""

import asyncio
import logging
from punisher.bus.queue import MessageQueue
from punisher.crypto.hyperliquid import HyperliquidMonitor
from punisher.scrapers.coinglass import CoinGlassScraper
from punisher.llm.gateway import LLMGateway

logger = logging.getLogger("punisher.agents.crypto")


class Satoshi:
    def __init__(self):
        self.queue = MessageQueue()
        self.hl_monitor = HyperliquidMonitor()
        self.cg_scraper = CoinGlassScraper()
        self.llm = LLMGateway()
        self.running = False

    async def start(self):
        """Start the crypto-dedicated subsystems"""
        self.running = True
        logger.info("Satoshi initialized. Managing Hyperliquid and CoinGlass.")
        asyncio.create_task(self.hl_monitor.start())
        await self.broadcast("Satoshi Online. Tracking institutional flows.")

    async def broadcast(self, msg: str):
        self.queue.push("punisher:cli:out", f"[💎] {msg}")

    async def get_alpha_context(self) -> str:
        """Fetch and synthesize crypto alpha for the Punisher"""
        raw_data = ""
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
                raw_data += "New High-Conviction Wallets:\n"
                for w in wallets:
                    raw_data += (
                        f"- {w['address'][:10]}... (PnL: {w.get('pnl_str', 'N/A')})\n"
                    )

            # 2. Significant Active Positions (Whales)
            snapshots = (
                await db.hyperliquid_snapshots.find()
                .sort("created_at", -1)
                .limit(2)
                .to_list(length=2)
            )
            if snapshots:
                raw_data += "\nActive Whale Clips:\n"
                for s in snapshots:
                    raw_data += f"- Wallet {s['wallet_address'][:8]}: Value ${float(s.get('account_value', 0)):,.0f}\n"
                    for p in s.get("positions", []):
                        if abs(float(p.get("size", 0))) > 0:
                            raw_data += f"  > {p.get('coin')} {p.get('side')} (${float(p.get('unrealized_pnl', 0)):,.0f} uPNL)\n"

            if not raw_data:
                return "--- CRYPTO ALPHA ---\nNo significant on-chain shifts detected in current cycle."

            # 3. SYNTHESIS: Use LLM to condense and identify trends
            alpha_intel = await self.synthesize_alpha(raw_data)
            return f"--- CRYPTO ALPHA (Synthesized) ---\n{alpha_intel}\n"

        except Exception as e:
            logger.error(f"Alpha context synthesis error: {e}")
            return "[Crypto Alpha Synthesis Failed]\n"

    async def synthesize_alpha(self, raw_data: str) -> str:
        """Satoshi's internal intelligence layer"""
        try:
            prompt = (
                f"ON-CHAIN RAW DATA:\n{raw_data}\n\n"
                "You are 'Satoshi', an expert on-chain detective. Synthesize this raw data into a concise alpha report. "
                "Identify any aggressive accumulation, recurring coin themes, or significant risk shifts. "
                "Keep it under 80 words. Be sharp and institutional."
            )
            response = await self.llm.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are 'Satoshi', the Lead On-chain Intelligence Officer. "
                            "You analyze institutional footprints on Hyperliquid and CoinGlass. "
                            "You speak in cold, technical terms. You hate fluff. You only care about where the 'Whales' are positioning."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ]
            )
            return response
        except Exception as e:
            logger.error(f"Synthesis fallback error: {e}")
            return raw_data[:500]

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

    async def get_live_btc_price(self) -> float:
        """Fetch BTC price from the internal HL stream"""
        return self.hl_monitor.get_mid_price("BTC")

    def stop(self):
        self.running = False
        self.hl_monitor.stop()
