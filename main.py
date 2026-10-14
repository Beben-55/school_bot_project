import asyncio
import logging
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from config import settings
from handlers import router, scheduler

TIMEZONE = ZoneInfo(os.getenv("TZ", "Europe/Moscow"))

def tz_converter(*args):
    return datetime.now(TIMEZONE).timetuple()

async def main():
    logging.Formatter.converter = tz_converter
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )

    scheduler.load_schedule()

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    
    dp.include_router(router)

    logging.info("Бот успешно запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
