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
                      published_at TIMESTAMP, transcript TEXT,
                      last_checked TIMESTAMP)""")

        # Migration: Ensure last_checked exists if the table was old
        try:
            c.execute("ALTER TABLE youtube_knowledge ADD COLUMN last_checked TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # Already exists

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

            # Check if already processed or recently checked
            if not self._should_process(video_id):
                continue

            logger.info(f"Processing video: {title} ({video_id})")
            transcript = await self.get_transcript(video_id)

            # Always save the result (even if transcript is None) to update last_checked
            self.save_knowledge(
                {
                    "id": video_id,
                    "channel": channel_handle,
                    "title": title,
                    "transcript": transcript,
                }
            )

            if transcript:
                processed_count += 1
                logger.info(f"Captured transcript for: {title}")
            else:
                logger.warning(
                    f"No transcript yet for: {title}. Will retry in 6+ hours."
                )

        return processed_count

    def _should_process(self, video_id):
        """Determine if we should try to get the transcript for this video."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT transcript, last_checked FROM youtube_knowledge WHERE video_id=?",
            (video_id,),
        )
        row = c.fetchone()
        conn.close()

        if not row:
            return True  # New video

        transcript, last_checked = row
        if transcript:
            return False  # Already have it

        if last_checked:
            # Re-check only if last checked > 6 hours ago
            last_dt = datetime.fromisoformat(last_checked)
            delta = datetime.now() - last_dt
            if delta.total_seconds() < (6 * 3600):
                return False

        return True

    async def get_transcript(self, video_id):
        """
        Main transcript engine.
        Attempts lightning-fast API fetch first (fixed for v1.2.4),
        falls back to nodriver 'human-mimic' scraping if needed.
        """
        try:
            # Try official API first (Fixed call for v1.2.4)
            api = YouTubeTranscriptApi()
            transcript = await asyncio.to_thread(api.fetch, video_id)
            if transcript and hasattr(transcript, "snippets"):
                content = " ".join([t.text for t in transcript.snippets])
                if content:
                    return content
        except Exception as e:
            logger.debug(f"API Transcript fetch failed for {video_id}: {e}")

        # Fallback to nodriver logic as requested (Standard for Gemini-level scrapers)
        return await self.get_transcript_nodriver(video_id)

    async def get_transcript_nodriver(self, video_id):
        """Scrapes transcript via nodriver using provided UserScript logic."""
        import nodriver as uc

        logger.info(f"Launching Stealth Browser for Transcript: {video_id}")

        browser = await uc.start()
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            tab = await browser.get(url)

            # 1. Expand Description
            try:
                # Wait for interaction
                await tab.sleep(4)
                expand = await tab.select("#expand")
                if expand:
                    await expand.click()
                    await tab.sleep(1)
            except Exception:
                pass

            # 2. Click "Show transcript"
            try:
                # Search for any button with transcript text
                await tab.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button, ytd-button-renderer'));
                    const target = btns.find(b => b.textContent.toLowerCase().includes('transcript'));
                    if (target) target.click();
                    else {
                        // Try specific renderer
                        const showBtn = document.querySelector('ytd-video-description-transcript-section-renderer button');
                        if (showBtn) showBtn.click();
                    }
                }""")
                await tab.sleep(5)
            except Exception:
                pass

            # 3. Extract using provided segments logic
            transcript_text = await tab.evaluate("""() => {
                const segmentSelectors = [
                    'ytd-transcript-segment-renderer',
                    'ytd-transcript-segment-list-renderer ytd-transcript-segment-renderer'
                ];

                let segments = [];
                for (const selector of segmentSelectors) {
                    segments = document.querySelectorAll(selector);
                    if (segments.length > 0) break;
                }

                if (segments.length === 0) return null;

                return Array.from(segments).map(s => {
                    const textEl = s.querySelector('.segment-text, #segment-text, yt-formatted-string.segment-text');
                    return textEl ? textEl.textContent.trim() : '';
                }).filter(t => t).join(' ');
            }""")

            if transcript_text:
                logger.info(f"Successfully scraped transcript via nodriver: {video_id}")
                return transcript_text

            logger.warning(f"No transcript segments found via nodriver for {video_id}")
            return None
        except Exception as e:
            logger.error(f"nodriver transcript error for {video_id}: {e}")
            return None
        finally:
            await browser.stop()

    def save_knowledge(self, video_data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # Using INSERT OR REPLACE to update last_checked even for videos we already know about
        c.execute(
            """INSERT OR REPLACE INTO youtube_knowledge 
                     (video_id, channel, title, published_at, transcript, last_checked) 
                     VALUES (?, ?, ?, ?, ?, ?)""",
            (
                video_data["id"],
                video_data["channel"],
                video_data["title"],
                datetime.now(),
                video_data["transcript"],
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        conn.close()
