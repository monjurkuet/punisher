from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx
import logging
import random
from punisher.config import settings

logger = logging.getLogger("punisher.research")


class ResearchScheduler:
    def __init__(self):
        self.search_url = settings.SEARCH_ENGINE_URL
        self.scheduler = AsyncIOScheduler()
        self.running = False

    async def fetch_updates(self):
        logger.info("Running scheduled research update...")
        try:
            # Randomly pick a topic to keep fresh
            topic = random.choice(
                ["bitcoin price", "bitcoin whale analysis", "crypto market sentiment"]
            )

            async with httpx.AsyncClient(timeout=10) as client:
                # Use correct SearXNG endpoint
                resp = await client.get(
                    f"{self.search_url}/search/text", params={"query": topic}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # In a real system, we'd ingest this into the Knowledge Base
                    # For MVP, just log it
                    logger.info(
                        f"Research update for '{topic}': Found {len(data.get('results', []))} results"
                    )
                else:
                    logger.warning(f"Search engine returned {resp.status_code}")

        except Exception as e:
            logger.error(f"Research update failed: {e}")

    def start(self):
        # 1-3 minutes interval
        self.scheduler.add_job(
            self.fetch_updates, "interval", seconds=random.randint(60, 180)
        )
        self.scheduler.start()
        self.running = True
        logger.info("Research scheduler started")

    def stop(self):
        self.scheduler.shutdown()
        self.running = False
