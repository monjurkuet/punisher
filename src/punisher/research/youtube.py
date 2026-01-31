"""
YouTube Intelligence Pipeline
Handles video discovery and transcript extraction for the knowledge base.
"""

import scrapetube
from youtube_transcript_api import YouTubeTranscriptApi
import logging
import sqlite3
import asyncio
from datetime import datetime

logger = logging.getLogger("punisher.research.youtube")


class YouTubeMonitor:
    def __init__(self):
        # High-signal trading channels
        self.channels = [
            "ChartChampions",
            "UC_InmS8U_T3O-S5x_1m4IeA",  # Example ID for ECKrown if known, using names for scrapetube
        ]
        self.db_path = "research.db"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS youtube_knowledge 
                     (video_id TEXT PRIMARY KEY, channel TEXT, title TEXT, 
                      published_at TIMESTAMP, transcript TEXT)""")
        conn.commit()
        conn.close()

    async def fetch_latest_videos(self, channel_handle, limit=3):
        """Fetch latest videos from a channel using scrapetube"""
        try:
            # scrapetube is synchronous, but we wrap in thread for async flow
            loop = asyncio.get_event_loop()
            videos = await loop.run_in_executor(
                None,
                lambda: list(
                    scrapetube.get_channel(
                        channel_url=f"https://www.youtube.com/@{channel_handle}"
                    )
                )[:limit],
            )
            return videos
        except Exception as e:
            logger.error(f"Failed to fetch videos for {channel_handle}: {e}")
            return []

    async def process_channel(self, channel_handle):
        """Monitor a channel and digest new videos"""
        videos = await self.fetch_latest_videos(channel_handle)
        processed_count = 0

        for vid in videos:
            video_id = vid["videoId"]
            title = vid["title"]["runs"][0]["text"]

            # Check if already processed
            if self._is_processed(video_id):
                continue

            logger.info(f"Processing new video: {title}")
            transcript = await self.get_transcript(video_id)

            if transcript:
                self.save_knowledge(
                    {
                        "id": video_id,
                        "channel": channel_handle,
                        "title": title,
                        "transcript": transcript,
                    }
                )
                processed_count += 1

        return processed_count

    def _is_processed(self, video_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT 1 FROM youtube_knowledge WHERE video_id=?", (video_id,))
        exists = c.fetchone()
        conn.close()
        return exists is not None

    async def get_transcript(self, video_id):
        try:
            # Wrap synchronous call
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(
                None, lambda: YouTubeTranscriptApi.get_transcript(video_id)
            )
            return " ".join([t["text"] for t in transcript])
        except Exception as e:
            logger.warning(f"No transcript for {video_id}: {e}")
            return None

    def save_knowledge(self, video_data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """INSERT OR IGNORE INTO youtube_knowledge 
                     (video_id, channel, title, published_at, transcript) 
                     VALUES (?, ?, ?, ?, ?)""",
            (
                video_data["id"],
                video_data["channel"],
                video_data["title"],
                datetime.now(),
                video_data["transcript"],
            ),
        )
        conn.commit()
        conn.close()
