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
        user_id = update.effective_user.id

        # Push to queue
        payload = {"source": "telegram", "user_id": user_id, "content": text}
        self.queue.push("punisher:inbox", payload)

    async def response_listener(self):
        """Listen for outgoing messages addressed to telegram"""
        while self.running:
            # In a real impl, payload should contain target chat_id
            # For MVP, we stick to CLI or need to store state mapping msg_id -> chat_id
            # This is a placeholder for the reverse flow
            await asyncio.sleep(1)
