"""
MongoDB Client for Hyperliquid WebSocket data storage
"""

import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from punisher.config import settings

logger = logging.getLogger("punisher.db.mongo")

# MongoDB URI from settings
MONGO_URI = settings.MONGODB_URI
DATABASE_NAME = "punisher"


class MongoStorage:
    """Async MongoDB storage for Hyperliquid data"""

    _instance = None
    _client = None
    _db = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._client = None
        self._db = None

    async def connect(self):
        """Initialize async MongoDB connection"""
        if self._client is None:
            self._client = AsyncIOMotorClient(MONGO_URI)
            self._db = self._client[DATABASE_NAME]
            logger.info(f"Connected to MongoDB: {DATABASE_NAME}")
        return self._db

    async def get_db(self):
        if self._db is None:
            await self.connect()
        return self._db

    async def save_wallet_snapshot(self, wallet_address: str, parsed_data: dict):
        """Save wallet snapshot - Only new unique states (Limit 20 unique per wallet)"""
        db = await self.get_db()

        summary = parsed_data.get("summary", {})
        positions = parsed_data.get("positions", [])
        orders = parsed_data.get("orders", [])
        snapshot_time_ms = parsed_data.get("ts")

        # Helper to generate state hash
        def get_state_hash(s, p, o):
            # Sort lists to ensure consistent order
            p_sorted = sorted(p, key=lambda x: x.get("coin"))
            o_sorted = sorted(o, key=lambda x: x.get("order_id", x.get("oid", "")))

            # Key state components
            state = {
                "account_value": s.get("account_value"),
                "total_ntl_pos": s.get("total_ntl_pos"),
                "positions_hash": str(p_sorted),
                "orders_hash": str(o_sorted),
            }
            return str(state)

        current_hash = get_state_hash(summary, positions, orders)

        # Check latest snapshot for this wallet
        latest_cursor = (
            db.hyperliquid_snapshots.find({"wallet_address": wallet_address})
            .sort("updated_at", -1)
            .limit(1)
        )

        latest_snapshot = await latest_cursor.to_list(length=1)

        if latest_snapshot:
            latest = latest_snapshot[0]
            # Compare hashes (or reconstruct state if hash not stored)
            latest_hash = latest.get("state_hash")

            # Backward compatibility or direct check
            if not latest_hash:
                latest_hash = get_state_hash(
                    {
                        "account_value": latest.get("account_value"),
                        "total_ntl_pos": latest.get("total_ntl_pos"),
                    },
                    latest.get("positions", []),
                    latest.get("open_orders", []),
                )

            if current_hash == latest_hash:
                # Just update the timestamp of the existing record to verify aliveness
                await db.hyperliquid_snapshots.update_one(
                    {"_id": latest["_id"]},
                    {
                        "$set": {
                            "updated_at": datetime.utcnow(),
                            "snapshot_time_ms": snapshot_time_ms,
                        }
                    },
                )
                return "updated_timestamp"

        # If not duplicate (or no previous history), insert new unique record
        doc = {
            "wallet_address": wallet_address,
            "snapshot_time_ms": snapshot_time_ms,
            "account_value": summary.get("account_value"),
            "total_ntl_pos": summary.get("total_ntl_pos"),
            "total_raw_usd": summary.get("total_raw_usd"),
            "total_margin_used": summary.get("total_margin_used"),
            "withdrawable": summary.get("withdrawable"),
            "positions": positions,
            "open_orders": orders,
            "state_hash": current_hash,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await db.hyperliquid_snapshots.insert_one(doc)

        # Prune old unique states (Keep last 20)
        cursor = (
            db.hyperliquid_snapshots.find(
                {"wallet_address": wallet_address}, {"_id": 1}
            )
            .sort("updated_at", -1)
            .skip(20)
        )

        ids_to_delete = []
        async for old_doc in cursor:
            ids_to_delete.append(old_doc["_id"])

        if ids_to_delete:
            await db.hyperliquid_snapshots.delete_many({"_id": {"$in": ids_to_delete}})
            logger.debug(
                f"Pruned {len(ids_to_delete)} old states for {wallet_address[:8]}..."
            )

        return result.inserted_id

    async def save_trade(self, coin: str, trade_data: dict):
        """Save whale trade to MongoDB"""
        db = await self.get_db()

        doc = {
            "coin": coin,
            "sz": trade_data.get("sz"),
            "px": trade_data.get("px"),
            "side": trade_data.get("side"),
            "usd_val": trade_data.get("usd_val"),
            "ts": trade_data.get("ts"),
            "hash": trade_data.get("hash"),
            "created_at": datetime.utcnow(),
        }

        result = await db.whale_trades.insert_one(doc)
        return result.inserted_id

    async def save_market_mids(self, mids: dict):
        """Save mid-price snapshot for key assets"""
        db = await self.get_db()

        # We only care about major ones for history, keep the collection lean
        subset = {k: v for k, v in mids.items() if k in ["BTC", "ETH", "SOL", "HYPE"]}
        if not subset:
            return None

        doc = {
            "mids": subset,
            "ts": datetime.utcnow(),
        }

        # Update latest record instead of spawning thousands of small docs
        # Or insert one per hour? Let's insert new for historical analysis
        result = await db.market_prices.insert_one(doc)

        # Prune: keep last 1000 snapshots (~1 week of 10-min snapshots)
        count = await db.market_prices.count_documents({})
        if count > 1000:
            oldest = await db.market_prices.find().sort("ts", 1).limit(1).to_list(1)
            if oldest:
                await db.market_prices.delete_many({"ts": {"$lte": oldest[0]["ts"]}})

        return result.inserted_id

    async def save_market_sentiment(self, coin: str, imbalance: float, sentiment: str):
        """Save market sentiment snapshot"""
        db = await self.get_db()

        doc = {
            "coin": coin,
            "imbalance": imbalance,
            "sentiment": sentiment,
            "created_at": datetime.utcnow(),
        }

        result = await db.market_sentiment.insert_one(doc)
        return result.inserted_id

    async def get_latest_snapshots(self, wallet_address: str, limit: int = 10):
        """Get latest snapshots for a wallet"""
        db = await self.get_db()

        cursor = (
            db.hyperliquid_snapshots.find({"wallet_address": wallet_address})
            .sort("created_at", -1)
            .limit(limit)
        )

        return await cursor.to_list(length=limit)

    async def close(self):
        if self._client:
            self._client.close()
            self._client = None
            self._db = None


# Singleton instance
mongo = MongoStorage.get_instance()
