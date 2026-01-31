from playwright.async_api import async_playwright
import logging
import asyncio

logger = logging.getLogger("punisher.browser")


class BrowserClient:
    def __init__(self):
        self.playwright = None
        self.browser = None

    async def start(self):
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            logger.info("Browser started (Playwright)")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")

    async def search(self, query: str) -> str:
        if not self.browser:
            await self.start()

        try:
            # Use a realistic User-Agent to avoid simple bot detection
            page = await self.browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            # Direct navigation to search results is faster and more reliable
            import urllib.parse

            encoded_query = urllib.parse.quote(query)
            await page.goto(f"https://duckduckgo.com/?q={encoded_query}&t=h_&ia=web")

            # Wait for results - wait for network idle to ensure dynamic content loads
            try:
                await page.wait_for_selector("article", timeout=5000)
            except:
                # If article not found, maybe just wait a bit for body
                await asyncio.sleep(2)

            # Extract titles and snippets
            results = await page.evaluate("""() => {
                // Try multiple common selectors for DDG results
                let items = document.querySelectorAll('article');
                if (items.length === 0) {
                     // Fallback: Just return the body text if we can't find structured results
                     const bodyText = document.body.innerText.split('\\n').filter(line => line.trim().length > 50).slice(0, 5).join('\\n');
                     if (bodyText) {
                        return `FALLBACK TEXT CONTENT (Selectors failed):\n${bodyText}`;
                     }
                     return "";
                }
                
                return Array.from(items).slice(0, 3).map(item => {
                    const titleElement = item.querySelector('h2 a') || item.querySelector('.result__a');
                    const snippetElement = item.querySelector('[class*="snippet"]') || item.querySelector('.result__snippet');
                    
                    const title = titleElement ? titleElement.innerText : 'No Title';
                    const snippet = snippetElement ? snippetElement.innerText : 'No Snippet';
                    
                    return `TITLE: ${title}\nSNIPPET: ${snippet}\n---\n`;
                }).join('\\n');
            }""")

            await page.close()
            return results if results else "No results found (Empty page)."

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"Search failed: {str(e)}"

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
