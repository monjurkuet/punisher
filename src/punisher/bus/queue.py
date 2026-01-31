import sqlite3
import json
import os
import time
from typing import Any, Optional


class MessageQueue:
    """
    SQLite-based Message Queue replacing hirlite (rlite) due to Python 3.14 build failures.
    Implements a similar interface: push, pop, publish (simulated).
    """

    def __init__(self, path: str = "data/queue.db"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT DEFAULT 'new',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_channel_status ON queue(channel, status);"
            )
            conn.commit()

    def push(self, channel: str, message: dict | str) -> None:
        if isinstance(message, dict):
            message = json.dumps(message)

        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO queue (channel, payload, status) VALUES (?, ?, 'new')",
                (channel, message),
            )
            conn.commit()

    def pop(self, channel: str, timeout: int = 0) -> str | None:
        """
        Simulates BRPOP. Simple polling with timeout.
        """
        start_time = time.time()
        while True:
            with sqlite3.connect(self.path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Transaction to pop the oldest 'new' message
                try:
                    cursor.execute("BEGIN IMMEDIATE")
                    cursor.execute(
                        """
                        SELECT id, payload FROM queue 
                        WHERE channel = ? AND status = 'new' 
                        ORDER BY id ASC LIMIT 1
                    """,
                        (channel,),
                    )
                    row = cursor.fetchone()

                    if row:
                        msg_id, payload = row["id"], row["payload"]
                        cursor.execute("DELETE FROM queue WHERE id = ?", (msg_id,))
                        conn.commit()
                        return payload
                    else:
                        conn.rollback()
                except sqlite3.OperationalError:
                    conn.rollback()

            if timeout > 0 and (time.time() - start_time) >= timeout:
                return None

            # Non-blocking check for instant return if timeout=0?
            # Redis BRPOP blocks, but RPOP doesn't.
            # If timeout=0 in Redis BRPOP it blocks indefinitely.
            # Here if timeout=0 we act like RPOP (non-blocking).
            if timeout == 0:
                return None

            time.sleep(0.1)

    def publish(self, channel: str, message: dict | str) -> None:
        # For our purposes, publish is same as push (pub/sub vs queue is blurred here)
        self.push(channel, message)
