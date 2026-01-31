"""
CoinGlass Hyperliquid Wallet Scraper
Scrapes leaderboard pages to find top trader wallet addresses
"""

import asyncio
import logging
import re
from playwright.async_api import async_playwright
from punisher.db.mongo import mongo

logger = logging.getLogger("punisher.scrapers.coinglass")


class CoinGlassScraper:
    def __init__(self):
        self.base_url = "https://www.coinglass.com/hl/range"

    async def start(self):
        """Scrape all ranges 1-16"""
        async with async_playwright() as p:
            # Launch browser with stealth args
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )

            # Create context with realistic User-Agent
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )

            page = await context.new_page()

            # Iterate through ranges 1 to 16
            for range_id in range(1, 17):
                try:
                    await self.scrape_range(page, range_id)
                    # Pause between ranges
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Failed range {range_id}: {e}")

            await browser.close()

    async def scrape_range(self, page, range_id):
        url = f"{self.base_url}/{range_id}"
        logger.info(f"Scraping {url}...")

        await page.goto(url, timeout=60000)

        # Wait for table to load
        try:
            await page.wait_for_selector("table", timeout=15000)
        except:
            logger.warning(f"No table found on range {range_id}")
            return

        # Pagination loop (attempt to go through pages if they exist)
        # For simplicity in V1, we just scrape the first visible page which usually has the top 20-50
        # To make it robust, we should scroll or click 'Next'

        # Logic to extract wallet links/addresses
        # CoinGlass usually links to /hl/address/{address} or displays it
        content = await page.content()

        # Regex to find 0x addresses (Hyperliquid uses Arbitrum-style 0x addresses)
        # Pattern: 0x followed by 40 hex chars
        wallets = set(re.findall(r"0x[a-fA-F0-9]{40}", content))

        logger.info(f"Found {len(wallets)} wallets on range {range_id}")

        if wallets:
            await self.save_wallets(list(wallets), range_id)

    async def save_wallets(self, wallets: list, range_id: int):
        """Save discovered wallets to MongoDB"""
        db = await mongo.get_db()

        count = 0
        for address in wallets:
            # Upsert into tracked_wallets
            res = await db.tracked_wallets.update_one(
                {"address": address},
                {
                    "$setOnInsert": {
                        "address": address,
                        "source": "coinglass",
                        "range_id": range_id,
                        "status": "discovered",  # discovered, scanned, ignored, monitoring
                        "discovered_at": datetime.utcnow(),
                    }
                },
                upsert=True,
            )
            if res.upserted_id:
                count += 1

        logger.info(f"Saved {count} new wallets from range {range_id}")


if __name__ == "__main__":
    from datetime import datetime

    logging.basicConfig(level=logging.INFO)

    # Run scraper
    scraper = CoinGlassScraper()
    asyncio.run(scraper.start())
