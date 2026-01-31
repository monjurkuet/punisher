"""
CoinGlass Hyperliquid Wallet Scraper (nodriver Page Version)
Extracts wallet addresses directly from the DOM for maximum reliability.
"""

import asyncio
import logging
import random
import nodriver as uc
from datetime import datetime, UTC
from punisher.db.mongo import mongo
from punisher.bus.queue import MessageQueue

logger = logging.getLogger("punisher.scrapers.coinglass")


class CoinGlassScraper:
    def __init__(self):
        self.base_url = "https://www.coinglass.com/hl/range/{group_id}"
        self.queue = MessageQueue()
        self.target_total = 10000
        self.discovered_total = 0
        self.browsing_speed_range = (3, 6)

    async def broadcast(self, msg: str):
        self.queue.push("punisher:cli:out", f"[🕵️] {msg}")
        logger.info(msg)

    async def start(self):
        """Scrape groups 1-16 with pagination until target reached"""
        await self.broadcast("Launching DOM-Based Scraper (nodriver)...")

        # Start nodriver
        browser = await uc.start()

        try:
            for group_id in range(1, 17):
                if self.discovered_total >= self.target_total:
                    break
                await self.scrape_group(browser, group_id)
                await asyncio.sleep(random.uniform(5, 10))
        finally:
            await self.broadcast(
                f"Scrape Complete. Total Discovered: {self.discovered_total}"
            )
            await browser.stop()

    async def scrape_group(self, browser, group_id):
        url = self.base_url.format(group_id=group_id)
        await self.broadcast(f"Entering Group {group_id}...")

        tab = await browser.get(url)
        await tab.sleep(5)

        page_num = 1
        while self.discovered_total < self.target_total:
            # Extract wallets from current page DOM
            wallets_data = await self.extract_wallets(tab)

            if wallets_data:
                new_count = await self.save_wallets(wallets_data, group_id)
                self.discovered_total += new_count
                await self.broadcast(
                    f"Group {group_id} | Page {page_num} | Found {len(wallets_data)} (New: {new_count}) | Total: {self.discovered_total}"
                )
            else:
                # Retry once after a bit of scrolling
                await tab.scroll_down(500)
                await tab.sleep(3)
                wallets_data = await self.extract_wallets(tab)
                if not wallets_data:
                    await self.broadcast(
                        f"No wallets found on Group {group_id} Page {page_num}. Ending group."
                    )
                    break
                else:
                    new_count = await self.save_wallets(wallets_data, group_id)
                    self.discovered_total += new_count
                    await self.broadcast(
                        f"Group {group_id} | Page {page_num} (Retry) | Found {len(wallets_data)} (New: {new_count}) | Total: {self.discovered_total}"
                    )

            # Click Next Page
            if not await self.go_to_next_page(tab):
                await self.broadcast(f"Reached end of pagination for Group {group_id}")
                break

            page_num += 1
            await tab.sleep(random.uniform(*self.browsing_speed_range))

    async def extract_wallets(self, tab):
        """Extract wallets with metadata using JS execution on the DOM"""
        try:
            # Wait for any table rows to appear
            await tab.sleep(5)

            # Simple check
            title = await tab.evaluate("document.title")
            logger.info(f"Extracting from page: {title}")

            # nodriver's evaluate to pull data from table rows
            res = await tab.evaluate("""(() => {
                try {
                    const results = [];
                    // Look for rows specifically
                    let rows = Array.from(document.querySelectorAll("tr.ant-table-row"));
                    if (rows.length === 0) rows = Array.from(document.querySelectorAll("tbody tr"));
                    if (rows.length === 0) rows = Array.from(document.querySelectorAll("tr[data-row-key]"));
                    
                    rows.forEach(row => {
                        const cells = row.querySelectorAll("td");
                        if (cells.length < 2) return;
                        
                        const anchor = row.querySelector("a[href*='/hyperliquid/']");
                        if (!anchor) return;
                        
                        const href = anchor.getAttribute('href');
                        const match = href.match(/0x[a-fA-F0-9]{40}/);
                        if (!match) return;
                        const address = match[0];
                        
                        const pnl = cells[4] ? cells[4].innerText.trim() : "";
                        const bias = cells[2] ? cells[2].innerText.trim() : "";
                        
                        results.push({
                            address,
                            pnl,
                            win_rate: bias,
                            meta: {
                                margin: cells[1] ? cells[1].innerText.trim() : "",
                                bias: bias,
                                in_position: cells[3] ? cells[3].innerText.trim() : "",
                                upnl: pnl,
                                risk: cells[5] ? cells[5].innerText.trim() : "",
                                group: cells[6] ? cells[6].innerText.trim() : ""
                            }
                        });
                    });
                    return {
                        success: true, 
                        count: results.length, 
                        data: results, 
                        rowCount: rows.length
                    };
                } catch (e) {
                    return {success: false, error: e.toString()};
                }
            })()""")

            if res is None:
                logger.warning("Extraction result is None (evaluate failed)")
                return []

            if isinstance(res, dict) and not res.get("success"):
                logger.warning(f"JS Extraction Error: {res.get('error')}")
                return []

            logger.info(
                f"Extraction Attempt: Rows found: {res.get('rowCount', 0)}, Valid Wallets: {res.get('count', 0)}"
            )
            return res.get("data", [])
        except Exception as e:
            logger.warning(f"DOM extraction python error: {e}")
            return []

    async def go_to_next_page(self, tab):
        """Find and click the next pagination button"""
        try:
            # Try multiple selectors for Ant Design and RC pagination
            next_btn = await tab.select(
                "li.ant-pagination-next:not(.ant-pagination-disabled), li.rc-pagination-next:not(.rc-pagination-disabled)"
            )
            if next_btn:
                await next_btn.scroll_into_view()
                await tab.sleep(0.5)
                await next_btn.click()
                return True
            return False
        except:
            return False

    async def save_wallets(self, wallets_data, range_id):
        """Save unique wallets to MongoDB"""
        db = await mongo.get_db()
        count = 0
        for item in wallets_data:
            address = item["address"]
            res = await db.tracked_wallets.update_one(
                {"address": address},
                {
                    "$set": {
                        "pnl_str": item.get("pnl"),
                        "win_rate_str": item.get("win_rate"),
                        "meta": item.get("meta"),
                        "last_seen_at": datetime.now(UTC),
                    },
                    "$setOnInsert": {
                        "address": address,
                        "source": "coinglass_dom_v2",
                        "range_id": range_id,
                        "status": "discovered",
                        "discovered_at": datetime.now(UTC),
                    },
                },
                upsert=True,
            )
            if res.upserted_id:
                count += 1
        return count


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    scraper = CoinGlassScraper()
    asyncio.run(scraper.start())
