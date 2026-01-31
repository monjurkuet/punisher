import scrapetube
from youtube_transcript_api import YouTubeTranscriptApi
import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger("punisher.research.youtube")


class YouTubeMonitor:
    def __init__(self):
        self.channels = {
            "ChartChampions": "UC...",  # Needs actual channel ID or user
            "ECKrown": "UC...",  # Needs actual channel ID or user
        }
        self.db_path = "research.db"

    def fetch_latest_videos(self):
        # Implementation to check new videos
        pass

    def get_transcript(self, video_id):
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
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
