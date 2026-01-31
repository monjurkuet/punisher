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
                const results = [];
                // 1. Try DuckDuckGo primary selectors
                const items = document.querySelectorAll('article, .result, .links_main');
                
                items.forEach(item => {
                    const titleEl = item.querySelector('h2, .result__title, a.result__a');
                    const snippetEl = item.querySelector('.result__snippet, [data-testid="result-snippet"]');
                    
                    if (titleEl && titleEl.innerText.trim()) {
                        results.push(`TITLE: ${titleEl.innerText.trim()}\nSNIPPET: ${snippetEl ? snippetEl.innerText.trim() : "No snippet"}\n---`);
                    }
                });

                if (results.length > 0) return results.slice(0, 5).join('\\n');

                // 2. Fallback: Extract meaningful paragraph text
                const paragraphs = Array.from(document.querySelectorAll('p, span'))
                    .map(p => p.innerText.trim())
                    .filter(t => t.length > 60)
                    .slice(0, 5);
                
                if (paragraphs.length > 0) {
                    return "FALLBACK CONTEXT:\\n" + paragraphs.join('\\n');
                }

                return "No structured results found.";
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
