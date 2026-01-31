import logging
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from punisher.config import settings
from punisher.bus.queue import MessageQueue

logger = logging.getLogger("punisher.telegram")


class TelegramBot:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.queue = MessageQueue()
        self.app = None
        self.running = False

    async def start(self):
        if not self.token:
            logger.warning("No Telegram token provided. Skipping.")
            return

        self.app = ApplicationBuilder().token(self.token).build()

        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(
            MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message)
        )

        logger.info("Telegram Bot starting polling...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        self.running = True

        # Start listening for responses to send back to Telegram
        asyncio.create_task(self.response_listener())

    async def stop(self):
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        self.running = False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Punisher Online. I am watching.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        chat_id = update.effective_chat.id

        import json

        payload = {"source": f"telegram:{chat_id}", "content": text}
        self.queue.push("punisher:inbox", json.dumps(payload))

    async def response_listener(self):
        """Listen for outgoing messages addressed to telegram"""
        while self.running:
            try:
                # Poll for all keys starting with punisher:telegram:
                # For simplicity in this structure, we listen to a specific broadcast channel
                # Or handle specific chat responses

                # Check for responses specifically for telegram sources
                # The Orchestrator pushs to 'punisher:telegram:<chat_id>:out'

                # In this architecture, we'll monitor a generic 'punisher:telegram:out'
                # where the orchestrator puts JSON with {chat_id: ..., content: ...}
                msg_raw = self.queue.pop("punisher:telegram:out", timeout=0)
                if msg_raw:
                    import json

                    data = json.loads(msg_raw)
                    chat_id = data.get("chat_id")
                    content = data.get("content")
                    if chat_id and content:
                        await self.app.bot.send_message(chat_id=chat_id, text=content)

                # Also handle general broadcasts to a default channel if configured
                # broadcast_msg = self.queue.pop("punisher:cli:out", timeout=0)
                # if broadcast_msg:
                #     # Optional: send important broadcasts to a specialized telegram group
                #     pass

            except Exception as e:
                logger.error(f"Telegram listener error: {e}")

            await asyncio.sleep(0.5)
