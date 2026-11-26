"""Render Web Service entry point for UzbAI Telegram bot."""
import asyncio
import logging
from uzbeai import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger("uzbai").info("Bot stopped.")
