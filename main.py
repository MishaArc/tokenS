import logging
import sys
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
import aiocron
from config import TELEGRAM_TOKEN as TOKEN
from handlers.commands import router, prepare_week_statistics
from utils.asyncUtils import get_all_chat_ids, remove_chat_id

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))


async def scheduled_week_statistics():
    chat_ids = await get_all_chat_ids()
    message = await prepare_week_statistics()
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id, message, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Failed to send message to chat {chat_id}: {e}")
            if "chat not found" in str(e):
                await remove_chat_id(chat_id)


async def main() -> None:
    dp = Dispatcher()
    dp.include_router(router)
    aiocron.crontab('0 0 * * 0', func=scheduled_week_statistics)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
