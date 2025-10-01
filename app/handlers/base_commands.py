'''
FILE FOR WORK WITH SIMPLE COMMANDS
'''
#/ This file exists only for simple commands that do not require editing.
#/ Данный файл существует только для простых команд которые не требуют редактирования

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "🎮 <b>КОМАНДЫ БОТА</b>\n\n"
        
        "📊 <b>Профиль</b>\n"
        "• /profile - Ваша статистика\n"
        "• /stats - Детальная статистика\n\n"
        
        "🎯 <b>Игровой процесс</b>\n" 
        "• /find_match - Поиск игры\n"
        "• /top - Рейтинг игроков\n\n"
        
        "⚙️ <b>Настройки</b>\n"
        "• /settings - Настройки бота\n"
        "• /help - Помощь\n\n"
        
        "🔗 <b>Ссылки</b>\n"
        "• <a href='http://telegram.org/'>Правила</a>\n"
        "• <a href='http://telegram.org/'>FAQ</a>",
        disable_web_page_preview=True
    )

@router.message(Command("commands"))
async def commands_handler(message: Message):
    await message.answer(
        "🚀 <b>Доступные команды:</b>\n\n"
        "/start - Начало работы\n"
        "/help - Помощь\n" 
        "/register - Регистрация\n"
        "/commands - Список команд\n\n"
        "✅ Base commands работает!"
    )

# Простой тест - реагирует на любое сообщение "test"
@router.message(lambda message: message.text and message.text.lower() == "test")
async def test_handler(message: Message):
    await message.answer("✅ Base commands router работает!")
