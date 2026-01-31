"""
Hyperliquid Stealth Wallet Monitor
Based on the proven implementation from hyperliquid_ws_stealthy.py
Monitors specific wallets using webData2 subscription
"""

import asyncio
import logging
import json
import ssl
import base64
import os
import random
import time
import datetime
from websockets import connect
from punisher.bus.queue import MessageQueue
from punisher.config import settings
from punisher.crypto.hyperliquid_parser import parse_hyperliquid_data

logger = logging.getLogger("punisher.crypto.hyperliquid")

# Default wallets to monitor (can be overridden via config)
DEFAULT_WALLETS = [
    "0x1234567890abcdef1234567890abcdef12345678",  # Placeholder - replace with real wallets
]


class HyperliquidMonitor:
    """
    Stealth Hyperliquid WebSocket Monitor
    - Monitors specific wallet addresses using webData2 subscription
    - Mimics browser behavior to avoid detection
    - Rotates through multiple wallets
    """

    def __init__(self, wallets: list = None):
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        self.api_url = "https://api.hyperliquid.xyz/info"
        self.queue = MessageQueue()
        self.running = False

        # Static wallet list (if provided)
        self.static_wallets = wallets or []

        # Dynamic wallet tracking (from DB)
        self.current_wallet_index = 0

        # Connection state
        self.connection_count = 0
        self.last_activity = time.time()

    async def get_all_target_wallets(self):
        """Fetch both static and active dynamic wallets from DB"""
        wallets = set(self.static_wallets)

        # Fetch from DB: discovered or currently monitoring
        try:
            from punisher.db.mongo import mongo

            db = await mongo.get_db()
            cursor = db.tracked_wallets.find(
                {
                    "status": {
                        "$in": ["discovered", "monitoring", "initial_scan_complete"]
                    }
                }
            )
            async for w in cursor:
                wallets.add(w["address"])
        except Exception as e:
            logger.error(f"Failed to fetch wallets from DB: {e}")

        # Fallback to config if nothing else exists
        if not wallets and settings.HYPERLIQUID_WALLET_ADDRESS:
            wallets.add(settings.HYPERLIQUID_WALLET_ADDRESS)

        return list(wallets)

    async def update_wallet_status(self, address: str, status: str):
        """Update the scan/monitor status of a wallet in DB"""
        try:
            from punisher.db.mongo import mongo

            db = await mongo.get_db()
            await db.tracked_wallets.update_one(
                {"address": address},
                {
                    "$set": {
                        "status": status,
                        "last_scan_at": datetime.datetime.now(datetime.UTC),
                    }
                },
                upsert=True,  # In case it was a static wallet not in DB yet
            )
        except Exception as e:
            logger.error(f"Failed to update wallet status: {e}")

    def create_ssl_context(self):
        """Create SSL context that mimics Chrome's TLS fingerprint"""
        context = ssl.create_default_context()
        try:
            ciphers = [
                "TLS_AES_128_GCM_SHA256",
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
                "ECDHE-ECDSA-AES128-GCM-SHA256",
                "ECDHE-RSA-AES128-GCM-SHA256",
                "ECDHE-ECDSA-AES256-GCM-SHA384",
                "ECDHE-RSA-AES256-GCM-SHA384",
                "ECDHE-ECDSA-CHACHA20-POLY1305",
                "ECDHE-RSA-CHACHA20-POLY1305",
                "ECDHE-RSA-AES128-SHA",
                "ECDHE-RSA-AES256-SHA",
            ]
            context.set_ciphers(":".join(ciphers))
        except ssl.SSLError:
            context.set_ciphers(
                "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
            )
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        return context

    def get_headers(self):
        """Generate realistic browser headers matching the working implementation"""
        key = base64.b64encode(os.urandom(16)).decode()

        sec_ch_ua_versions = [
            '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            '"Google Chrome";v="120", "Chromium";v="120", "Not_A Brand";v="99"',
            '"Google Chrome";v="121", "Chromium";v="121", "Not A(Brand";v="99"',
        ]

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

        return [
            ("Host", "api.hyperliquid.xyz"),
            ("Connection", "Upgrade"),
            ("Pragma", "no-cache"),
            ("Cache-Control", "no-cache"),
            ("User-Agent", random.choice(user_agents)),
            ("Upgrade", "websocket"),
            ("Origin", "https://www.coinglass.com"),
            ("Sec-WebSocket-Version", "13"),
            ("Accept-Encoding", "gzip, deflate, br"),
            ("Accept-Language", "en-US,en;q=0.9"),
            ("Sec-Ch-Ua", random.choice(sec_ch_ua_versions)),
            ("Sec-Ch-Ua-Mobile", "?0"),
            ("Sec-Ch-Ua-Platform", '"Windows"'),
            ("Sec-WebSocket-Key", key),
            ("Sec-WebSocket-Extensions", "permessage-deflate; client_max_window_bits"),
            ("Sec-Fetch-Dest", "websocket"),
            ("Sec-Fetch-Mode", "websocket"),
            ("Sec-Fetch-Site", "cross-site"),
        ]

    async def human_delay(self):
        """Simulate human-like delays with weighted randomness"""
        delays = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.7, 1.0]
        weights = [20, 15, 15, 12, 10, 8, 6, 5, 4, 5]
        delay = random.choices(delays, weights=weights)[0]
        jitter = random.uniform(-0.05, 0.05)
        total_delay = max(0.05, delay + jitter)
        await asyncio.sleep(total_delay)

    def get_current_wallet(self):
        """Get current target wallet"""
        if not self.wallets:
            return None
        return self.wallets[self.current_wallet_index % len(self.wallets)]

    def advance_to_next_wallet(self, current_list_size: int):
        """Move to next wallet with human-like selection"""
        if current_list_size <= 1:
            return

        # Sometimes skip wallets or go back (human behavior)
        if random.random() < 0.1:  # 10% chance to skip
            self.current_wallet_index = (
                self.current_wallet_index + 2
            ) % current_list_size
        elif random.random() < 0.05:  # 5% chance to go back
            self.current_wallet_index = (
                self.current_wallet_index - 1
            ) % current_list_size
        else:
            self.current_wallet_index = (
                self.current_wallet_index + 1
            ) % current_list_size

    async def connect_with_stealth(self):
        """Establish connection with maximum stealth"""
        self.connection_count += 1

        if self.connection_count > 1:
            reconnect_delay = random.uniform(3, 12)
            logger.info(f"[⏳] Human-like pause: {reconnect_delay:.1f}s...")
            await asyncio.sleep(reconnect_delay)

        ssl_context = self.create_ssl_context()
        headers = self.get_headers()

        await self.human_delay()

        ws = await connect(
            self.ws_url,
            ssl=ssl_context,
            extra_headers=headers,
            ping_interval=30,
            ping_timeout=10,
            close_timeout=10,
        )

        logger.info("[✅] Stealth connection established")
        return ws

    async def subscribe_to_wallet(self, ws, wallet_address):
        """Subscribe to specific wallet with realistic timing"""
        # Human browsing simulation - wait before subscribing
        browse_delay = random.uniform(1.0, 4.0)
        logger.debug(f"[👀] Browsing simulation: {browse_delay:.1f}s...")
        await asyncio.sleep(browse_delay)

        subscribe_msg = {
            "method": "subscribe",
            "subscription": {"type": "webData2", "user": wallet_address},
        }

        message = json.dumps(subscribe_msg)

        # Typing simulation
        typing_delay = len(message) * random.uniform(0.002, 0.005)
        await asyncio.sleep(typing_delay)

        await ws.send(message)
        logger.info(f"[📡] Monitoring wallet: {wallet_address[:10]}...")

    async def start(self):
        """Main monitoring loop"""
        self.running = True
        logger.info("Starting Hyperliquid Stealth Monitor (Dynamic Mode)")

        while self.running:
            # Refresh wallet list on each loop iteration
            wallets = await self.get_all_target_wallets()
            if not wallets:
                logger.warning("No wallets to process yet...")
                await asyncio.sleep(10)
                continue

            # Get wallet to process
            current_wallet = wallets[self.current_wallet_index % len(wallets)]

            try:
                ws = await self.connect_with_stealth()
                await self.subscribe_to_wallet(ws, current_wallet)

                # Listen for data
                timeout_seconds = random.randint(3, 8) * 60  # 3-8 minutes per wallet
                start_time = time.time()

                while self.running and (time.time() - start_time < timeout_seconds):
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30)
                        self.last_activity = time.time()
                        data = json.loads(msg)

                        # Check for webData2 channel
                        if data.get("channel") == "webData2":
                            # Parse and broadcast wallet data
                            await self.process_wallet_data(current_wallet, data)

                    except asyncio.TimeoutError:
                        logger.debug("[⏰] Waiting for data...")
                        try:
                            await ws.ping()
                        except Exception:
                            break
                        continue

                # Graceful disconnect
                disconnect_delay = random.uniform(1, 3)
                await asyncio.sleep(disconnect_delay)
                await ws.close()

                # Move to next wallet
                self.advance_to_next_wallet(len(wallets))

            except Exception as e:
                logger.error(f"Hyperliquid WS Error: {e}")
                await asyncio.sleep(random.uniform(5, 15))

    async def process_wallet_data(self, wallet_address: str, raw_data: dict):
        """Process, store, and broadcast wallet data"""
        try:
            data = raw_data.get("data", {})
            parsed = parse_hyperliquid_data(data)

            # Save to MongoDB
            try:
                from punisher.db.mongo import mongo

                await mongo.save_wallet_snapshot(wallet_address, parsed)
                logger.debug(f"Saved snapshot to MongoDB for {wallet_address[:8]}...")

                # Update status to mark initial scan success
                await self.update_wallet_status(wallet_address, "initial_scan_complete")

            except Exception as db_err:
                logger.warning(f"MongoDB save failed: {db_err}")

            # Extract key metrics
            summary = parsed.get("summary", {})
            positions = parsed.get("asset_positions", [])

            account_value = float(summary.get("account_value", 0))

            # Only broadcast if meaningful data
            if account_value > 0:
                self.queue.push(
                    "punisher:cli:out",
                    f"[WALLET] {wallet_address[:8]}... Value: ${account_value:,.2f}",
                )

            # Broadcast significant positions
            for pos in positions:
                coin = pos.get("coin", "?")
                size = float(pos.get("size", 0))
                pnl = float(pos.get("unrealized_pnl", 0))

                if abs(size) > 0:
                    emoji = "🟢" if pnl >= 0 else "🔴"
                    self.queue.push(
                        "punisher:cli:out",
                        f"[POS] {emoji} {coin}: {size} | PnL: ${pnl:,.2f}",
                    )

        except Exception as e:
            logger.error(f"Error processing wallet data: {e}")

    def stop(self):
        self.running = False
