import asyncio
from punisher.browser.client import BrowserClient


async def test_search():
    client = BrowserClient()
    print("Starting search for 'bitcoin news'...")
    results = await client.search("bitcoin news")
    print(f"Results:\n{results}")
    await client.stop()


if __name__ == "__main__":
    asyncio.run(test_search())
