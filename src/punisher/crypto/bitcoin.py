import httpx
import logging

logger = logging.getLogger("punisher.crypto.bitcoin")


class BitcoinData:
    """Free Bitcoin Data Provider"""

    @staticmethod
    async def get_price() -> dict:
        """
        Get current BTC price from CoinDesk BPI
        """
        url = "https://api.coindesk.com/v1/bpi/currentprice.json"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10)
                data = resp.json()
                price = data["bpi"]["USD"]["rate_float"]
                return {
                    "source": "CoinDesk",
                    "price_usd": price,
                    "updated": data["time"]["updated"],
                }
        except Exception as e:
            logger.error(f"Failed to fetch BTC price: {e}")
            # Mock fallback for demo/offline
            return {
                "source": "MOCK_FALLBACK",
                "price_usd": 94520.00,
                "updated": "2026-01-31T12:00:00+00:00",
                "warning": str(e),
            }

    @staticmethod
    async def get_market_data() -> dict:
        """
        Get market data from CoinCap
        """
        url = "https://api.coincap.io/v2/assets/bitcoin"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10)
                data = resp.json()["data"]
                return {
                    "source": "CoinCap",
                    "rank": data["rank"],
                    "market_cap": float(data["marketCapUsd"]),
                    "volume_24h": float(data["volumeUsd24Hr"]),
                    "change_24h": float(data["changePercent24Hr"]),
                }
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            return {"error": str(e)}
