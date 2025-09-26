'''
 ▗▄▖ ▗▖  ▗▖ ▗▄▖ ▗▖  ▗▖▗▄▄▄▖▗▖  ▗▖▗▄▄▖ ▗▖  ▗▖▗▄▄▄▖▗▖ ▗▖ ▗▄▖ ▗▖  ▗▖
▐▌ ▐▌▐▛▚▖▐▌▐▌ ▐▌▐▛▚▖▐▌  █  ▐▛▚▞▜▌▐▌ ▐▌ ▝▚▞▘   █  ▐▌ ▐▌▐▌ ▐▌▐▛▚▖▐▌
▐▛▀▜▌▐▌ ▝▜▌▐▌ ▐▌▐▌ ▝▜▌  █  ▐▌  ▐▌▐▛▀▘   ▐▌    █  ▐▛▀▜▌▐▌ ▐▌▐▌ ▝▜▌
▐▌ ▐▌▐▌  ▐▌▝▚▄▞▘▐▌  ▐▌▗▄█▄▖▐▌  ▐▌▐▌     ▐▌    █  ▐▌ ▐▌▝▚▄▞▘▐▌  ▐▌
'''

from dotenv import load_dotenv
import os
load_dotenv()

import asyncio
from aiogram import Bot, Dispatcher
#* for HTML messages format
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from handlers.start import router


BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Инициализация бота
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


# Запуск бота
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Бот остановлен")