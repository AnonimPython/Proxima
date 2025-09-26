'''
FILE FOR WORK WITH STANDART COMMANDS
'''

from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

router = Router()

# Обработчик команды /start
@router.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "🚀 <b>Добро пожаловать в Proxima!</b>\n\n"
        "Присоединяйся к элитному сообществу\n"
        "<i>Для начала пройди регистрацию</i>\n\n"
        "📋 <b>Доступные команды:</b>\n"
        "/help - Помощь\n\n"
        "/register"
        "🎯 <b>Начни прямо сейчас!</b>"
    )


    
