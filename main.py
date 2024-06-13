import logging
import sys
import asyncio
from aiogram import Bot, Dispatcher
from fastapi import FastAPI
from aiogram.client.default import DefaultBotProperties
from config import TELEGRAM_TOKEN as TOKEN
import uvicorn
from aiogram.client.session.aiohttp import AiohttpSession
import aiocron
import os
from aiogram.fsm.storage.memory import MemoryStorage
from handlers.commands import router, prepare_week_statistics
from utils.asyncUtils import get_all_chat_ids, remove_chat_id

app = FastAPI()
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
session = AiohttpSession()


@app.get("/")
async def read_root():
    return {"Hello": "World"}


async def scheduled_week_statistics():
    chat_ids = await get_all_chat_ids()
    message = await prepare_week_statistics()
    for chat_id in chat_ids:
        try:
            await bot.send_photo(
                chat_id=chat_id,
                photo="AgACAgIAAxkBAAICNmZBDDMHwAsaQ-HklZlQLX_tatwdAALl3TEbaU8ISkKOB1wyeJOOAQADAgADeQADNQQ",
                caption=message, parse_mode="HTML")

        except Exception as e:
            logging.error(f"Failed to send message to chat {chat_id}: {e}")
            if "chat not found" in str(e):
                await remove_chat_id(chat_id)


async def main() -> None:
    dp = Dispatcher()
    dp.include_router(router)
    loop = asyncio.get_event_loop()
    loop.create_task(dp.start_polling(bot))

    aiocron.crontab('25 13 * * 0', func=scheduled_week_statistics)
    config = uvicorn.Config(app=app, host="0.0.0.0", port=int(os.environ.get('PORT', 5001)), loop="auto")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
