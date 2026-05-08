import structlog
import asyncio
import sys
import os
from typing import Optional

# Ensure the project root is on sys.path so we can import the backend module
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from telegram import Update
from telegram.ext import Application, ApplicationBuilder
from telegram.error import TelegramError

from backend.config.settings import settings
from backend.database.db import init_db

from telegram_bot.handlers import register_handlers

logger = structlog.get_logger(__name__)


class BotRunner:
    """Manages the Telegram bot lifecycle: init, run, and graceful shutdown."""

    def __init__(self, token: str | None = None, chat_id: str | None = None):
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self.application: Application | None = None
        self._running = False

    async def initialize(self) -> None:
        """Initialize the database and build the Application with all handlers."""
        await init_db()

        if not self.token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is not set. "
                "Configure it via environment variable or settings."
            )

        self.application = (
            ApplicationBuilder()
            .token(self.token)
            .concurrent_updates(True)
            .get_updates_connection_pool_size(4)
            .build()
        )

        register_handlers(self.application)

        logger.info(
            "telegram bot initialized",
            chat_id=self.chat_id,
            has_token=bool(self.token),
        )

    def run(self) -> None:
        """Start polling. Blocking call — runs until the process is stopped."""
        if self._running:
            logger.warning("bot is already running")
            return

        if self.application is None:
            raise RuntimeError(
                "Bot not initialized. Call initialize() before run()."
            )

        self._running = True
        logger.info(
            "telegram bot starting polling",
            chat_id=self.chat_id,
        )

        if not self.chat_id:
            logger.warning(
                "TELEGRAM_CHAT_ID not set — the bot will not authorize any user."
            )

        try:
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                close_loop=False,
            )
        except TelegramError as e:
            logger.error("telegram polling error", error=str(e))
            raise
        finally:
            self._running = False

    async def run_async(self) -> None:
        """Start polling in an async context. Useful when embedding in another app."""
        if self._running:
            logger.warning("bot is already running")
            return
        if self.application is None:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        self._running = True
        logger.info(
            "telegram bot starting async polling",
            chat_id=self.chat_id,
        )

        try:
            await self.application.initialize()
            await self.application.start()
            if self.chat_id:
                try:
                    await self.application.bot.send_message(
                        chat_id=self.chat_id,
                        text="🤖 <b>Bot Online</b>\nPortfolio monitoring is active.",
                        parse_mode="HTML",
                    )
                except TelegramError as e:
                    logger.warning("failed to send startup message", error=str(e))
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
            )
            # Keep running
            while self._running:
                await asyncio.sleep(1)
        except TelegramError as e:
            logger.error("telegram async polling error", error=str(e))
            raise
        finally:
            self._running = False
            await self._shutdown()

    async def stop(self) -> None:
        """Signal the bot to stop gracefully."""
        logger.info("telegram bot stopping")
        self._running = False

    async def _shutdown(self) -> None:
        """Perform cleanup of application resources."""
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                logger.warning("error during bot shutdown", error=str(e))
        logger.info("telegram bot shut down")


def main():
    """CLI entry point: run the bot standalone."""
    import argparse

    parser = argparse.ArgumentParser(description="eToro Portfolio Telegram Bot")
    parser.add_argument(
        "--token",
        help="Telegram bot token (overrides settings)",
        default=None,
    )
    parser.add_argument(
        "--chat-id",
        help="Authorized chat ID (overrides settings)",
        default=None,
    )
    args = parser.parse_args()

    runner = BotRunner(token=args.token, chat_id=args.chat_id)

    async def startup():
        await runner.initialize()
        await runner.run_async()

    try:
        asyncio.run(startup())
    except KeyboardInterrupt:
        logger.info("bot stopped by user")
    except Exception as e:
        logger.error("bot failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
