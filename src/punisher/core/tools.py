import httpx
import logging
import nodriver as uc
from punisher.config import settings

logger = logging.getLogger("punisher.core.tools")


class AgentTools:
    """Unified toolset for all Punisher agents."""

    def __init__(self):
        self.search_base_url = settings.SEARCH_ENGINE_URL  # http://localhost:9345

    async def web_search(self, query: str, category: str = "text") -> str:
        """Search the local intelligence engine (SearXNG)."""
        try:
            url = f"{self.search_base_url}/search/{category}"
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, params={"query": query})
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    if not results:
                        return f"Search for '{query}' returned no results."

                    output = [f"Search Results for '{query}':"]
                    for r in results[:5]:
                        output.append(f"- {r.get('title')}: {r.get('body')}")
                    return "\n".join(output)
                return f"Search engine error: {resp.status_code}"
        except Exception as e:
            logger.error(f"Web search tool failed: {e}")
            return f"Search failed: {str(e)}"

    async def browse_page(self, url: str) -> str:
        """Browse a webpage using nodriver (stealth) and extract text."""
        try:
            logger.info(f"Stealth browsing: {url}")
            browser = await uc.start()
            tab = await browser.get(url)
            await tab.sleep(3)  # Wait for JS

            # Extract main content content
            content = await tab.evaluate("""(() => {
                // Remove noise
                const noise = document.querySelectorAll('script, style, nav, footer, header');
                noise.forEach(el => el.remove());
                return document.body.innerText.split('\\n')
                    .filter(line => line.trim().length > 30)
                    .slice(0, 20)
                    .join('\\n');
            })()""")

            await browser.stop()
            return f"Content from {url}:\n{content}"
        except Exception as e:
            logger.error(f"Stealth browsing failed: {e}")
            return f"Browsing failed: {str(e)}"
