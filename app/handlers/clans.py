'''
FILE FOR WORK WITH CLANS
'''
#! NOT WORKING AT THE MOMENT
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

router = Router()

@router.message(Command("invite"))
async def invite_handler(message: Message):
    # Получаем аргументы команды: /invite 123456789
    args = message.text.split()[1:]  # Разбиваем и берём всё после /invite
    if not args:
        #todo: переделать под игровой профиль, его id игровой который выдает после регистрации.
        #todo: после реализации сделать ТОП КЛАНОВ
        await message.answer("Использование: /invite <telegram_id>")
        return
    
    target_chat_id = args[0]  # Первый аргумент — ID
    
    # Проверяем, что это число (telegram_id)
    if not target_chat_id.isdigit():
        await message.answer("Telegram ID должен быть числом.")
        return
    
    target_chat_id = int(target_chat_id)
    
    try:
        # Отправляем сообщение
        await message.bot.send_message(
            chat_id=target_chat_id,
            text="тест для инвайта в клан"
        )
        await message.answer(f"✅ Сообщение отправлено пользователю с ID {target_chat_id}!")
    except TelegramBadRequest as e:
        # Обрабатываем ошибки (например, пользователь заблокировал бота или не начал чат)
        if "bot was blocked" in str(e).lower():
            await message.answer(f"❌ Пользователь с ID {target_chat_id} заблокировал бота.")
        else:
            await message.answer(f"❌ Не удалось отправить: {e}. Убедитесь, что пользователь стартовал с ботом.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
