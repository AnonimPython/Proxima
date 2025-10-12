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
from handlers.base_commands import router as bs_router
from handlers.matches import router as matches_router
from handlers.clans import router as clans_router
from handlers.personal.admin import router as admin_router


BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Инициализация бота
#* Initial Bot
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


# Запуск бота
#* Start Bot
async def main():
    dp.include_routers(admin_router)
    dp.include_routers(clans_router)
    dp.include_routers(matches_router)
    dp.include_router(bs_router)
    dp.include_routers(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Бот остановлен")