'''
FILE FOR WORK WITH STANDART COMMANDS
'''

from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from datetime import datetime
#* Database
from sqlmodel import Session, select
from typing import Optional
from database.models import (
    engine,
    UsersSchema,
    GameProfilesSchema,
    UserStatsSchema,
    MatchPlayersSchema,
    MatchesSchema,
    FoundMatchSchema,
)

router = Router()

# Обработчик команды /start
@router.message(Command("start"))
async def start_handler(message: Message):
    telegram_id = message.from_user.id
    username = message.from_user.username or "Без имени"
    first_name = message.from_user.first_name or "Без имени"
    first_name = message.from_user.first_name or "Без имени"
    first_name = message.from_user.first_name or "Без имени"
    first_name = message.from_user.first_name or "Без имени"
    
    # Проверка существования пользователя в БД
    # check user in db
    with Session(engine) as session:
        # Получаем пользователя по telegram_id
        # we take telegram_id to check user in system/DB
        statement = select(UsersSchema).where(UsersSchema.telegram_id == telegram_id)
        user = session.exec(statement).first()
        
        if not user:
            # Если нет, создаём нового
            # if user not exists we are adding him for DB
            user = UsersSchema(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                created_at=datetime.now(),
            )
            session.add(user)
            session.commit()
            session.refresh(user)

    await message.answer(
        "🚀 <b>Добро пожаловать в Proxima!</b>\n\n"
        "Присоединяйся к элитному сообществу\n"
        "<i>Для начала пройди регистрацию</i>\n\n"
        "/register\n\n"
        "📋 <b>Доступные команды:</b>\n"
        "/help - Помощь\n\n"
        f"Привет! Твой Telegram ID: {telegram_id}\n"
        f"Твоё имя: {first_name}\n"
        f"Username: {username}\n"
        f"Полные данные: {message.from_user}"
    )

    
