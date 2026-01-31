"""
YouTube Agent - Specialized in Video Intelligence and Media Alpha.
Digests trading content and provides a knowledge base for the Punisher.
"""

import asyncio
import logging
import sqlite3
from punisher.bus.queue import MessageQueue
from punisher.research.youtube import YouTubeMonitor
from punisher.llm.gateway import LLMGateway

logger = logging.getLogger("punisher.agents.youtube")


class Joker:
    def __init__(self):
        self.queue = MessageQueue()
        self.monitor = YouTubeMonitor()
        self.llm = LLMGateway()
        self.running = False
        # Specific high-signal channels to watch
        self.watchlist = ["ChartChampions", "ECKrown", "Glassnode"]

    async def start(self):
        """Start the media monitoring loop"""
        self.running = True
        logger.info("Joker initialized. Monitoring media alpha.")
        asyncio.create_task(self.background_digestion())
        await self.broadcast("Joker Online. Scanning the media tape.")

    async def broadcast(self, msg: str):
        self.queue.push("punisher:cli:out", f"[📺] {msg}")

    async def background_digestion(self):
        """Periodically check channels for new insights"""
        while self.running:
            try:
                for channel in self.watchlist:
                    new_vids = await self.monitor.process_channel(channel)
                    if new_vids > 0:
                        await self.broadcast(
                            f"Digested {new_vids} new insights from @{channel}."
                        )
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"Digestion error: {e}")
                await asyncio.sleep(600)

    async def get_intel_context(self) -> str:
        """Provide latest media context for the Punisher"""
        context = "--- MEDIA INTEL (YouTube) ---\n"
        try:
            conn = sqlite3.connect("research.db")
            c = conn.cursor()
            c.execute(
                "SELECT channel, title, transcript FROM youtube_knowledge ORDER BY published_at DESC LIMIT 2"
            )
            rows = c.fetchall()

            if rows:
                for r in rows:
                    source, title, text = r
                    if text:
                        # Perform LLM Deep Dive on the transcript
                        summary = await self.llm_summarize(title, text)
                        context += f"Source: @{source} | Title: {title}\nAlpha Extract: {summary}\n\n"
                    else:
                        context += f"Source: @{source} | Title: {title}\n[No Transcript Available]\n\n"
            else:
                context += "No recent media insights captured.\n"
            conn.close()
        except Exception as e:
            logger.error(f"Media intel context error: {e}")
            context += "[Media Intel Unavailable]\n"

        return context

    async def llm_summarize(self, title, transcript) -> str:
        """Use LLM to extract trading alpha from transcript"""
        try:
            # Truncate transcript to prevent context overflow (approx 2000 words)
            truncated = transcript[:8000]
            prompt = (
                f"Video Title: {title}\n\n"
                f"Transcript Content:\n{truncated}\n\n"
                "Extract the core trading alpha from this transcript. "
                "Focus on: Price levels (Support/Resistance), Bias (Long/Short), and specific indicators or strategies mentioned. "
                "Keep it under 100 words. Be institutional and precise."
            )

            response = await self.llm.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are 'Joker', the Narrative & Sentiment Analyst. "
                            "Your job is to identify retail euphoria and institutional traps in media transcripts. "
                            "Extract the 'why' and the 'how' of the current market cycle. Be cynical and precise."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ]
            )
            return response
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return transcript[:300] + "..."

    async def process_task(self, command: str) -> str:
        """Execute specific media tasks"""
        cmd = command.lower()
        if "sync" in cmd or "refresh" in cmd:
            asyncio.create_task(self.background_digestion())
            return "Manually triggering media refresh. Digesting new videos..."

        return "Acknowledged. Watching the feed."

    def stop(self):
        self.running = False
