'''
FILE FOR WORK WITH COMMANDS
'''
from dotenv import load_dotenv
import os
load_dotenv()
from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from datetime import datetime
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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

#todo: replace / commands to keyboards Reply or Inline
router = Router()

class RegistrationStates(StatesGroup):
    waiting_for_game_id = State()
    waiting_for_nickname = State()

def get_user_league(telegram_id: int):
    with Session(engine) as session:
        user_league = session.exec(
            select(GameProfilesSchema.league)
            .join(UsersSchema, GameProfilesSchema.user_id == UsersSchema.user_id)
            .where(UsersSchema.telegram_id == telegram_id)
        ).first()
    return user_league 

#* commands
#? register user telegram
@router.message(Command("start"))
async def start_handler(message: Message):
    telegram_id = message.from_user.id
    username = message.from_user.username or "Без имени"
    first_name = message.from_user.first_name or "Без имени"
    last_name = message.from_user.last_name or "Без имени"
    
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
        #! test
        f"Привет! Твой Telegram ID: {telegram_id}\n"
        f"Твоё имя: {first_name}\n"
        f"Username: {username}\n"
        f"Полные данные: {last_name}"
    )
    
#? register game profile
#todo create exit button to stop register   
@router.message(Command("register"))
async def command_register_handler(message: Message, state: FSMContext) -> None:
    """Начало регистрации игрового профиля"""
    
    #* in /start we have this code
    with Session(engine) as session:
        user = session.exec(
            select(UsersSchema).where(UsersSchema.telegram_id == message.from_user.id)
        ).first()
        
        if not user:
            new_user = UsersSchema(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            user_id = new_user.user_id
        else:
            user_id = user.user_id
        
        # Проверяем, есть ли уже игровой профиль
        # Check have a user a game profile
        existing_profile = session.exec(
            select(GameProfilesSchema).where(GameProfilesSchema.user_id == user_id)
        ).first()
        league = get_user_league(message.from_user.id)
        if existing_profile:
            await message.answer(
                "🔹 У вас уже есть зарегистрированный игровой профиль!\n"
                #! test
                f"Ник: {existing_profile.nickname}\n"
                f"ID: {existing_profile.game_id}\n"
                f"Лига: {league.capitalize()}"
            )
            return
        
        # Сохраняем user_id в состоянии и переходим к вводу game_id
        # save in State() game_id
        await state.set_data({"user_id": user_id})
        await state.set_state(RegistrationStates.waiting_for_game_id)
        await message.answer(
            "🎮 Регистрация игрового профиля\n\n"
            "Введите ваш Game ID из Standoff 2:\n"
            "▫️ Это 8-значный цифровой идентификатор\n"
            "▫️ Пример: 12345678"
        )

@router.message(RegistrationStates.waiting_for_game_id)
async def process_game_id(message: Message, state: FSMContext) -> None:
    """Обработка ввода Game ID"""
    
    game_id = message.text.strip()
    
    # Валидация Game ID
    if not game_id.isdigit():
        await message.answer("❌ Game ID должен содержать только цифры! Попробуйте снова:")
        return
    
    if len(game_id) < 8:
        await message.answer("❌ Game ID должен содержать минимум 8 цифр! Попробуйте снова:")
        return
    
    # Проверяем, не занят ли этот game_id
    # checking game_id is used or not
    with Session(engine) as session:
        existing_game_id = session.exec(
            select(GameProfilesSchema).where(GameProfilesSchema.game_id == game_id)
        ).first()
        
        if existing_game_id:
            await message.answer("❌ Этот Game ID уже зарегистрирован! Введите другой:")
            return
    
    # Сохраняем game_id и переходим к вводу nickname
    # save in State game_id
    await state.update_data({"game_id": game_id})
    await state.set_state(RegistrationStates.waiting_for_nickname)
    
    await message.answer(
        "✅ Game ID принят!\n\n"
        "Теперь введите ваш игровой никнейм:\n"
        "▫️ Максимум 16 символов\n"
        "▫️ Может содержать буквы, цифры и символы"
    )

@router.message(RegistrationStates.waiting_for_nickname)
async def process_nickname(message: Message, state: FSMContext) -> None:
    """Обработка ввода никнейма и завершение регистрации"""
    
    nickname = message.text.strip()
    
    # Валидация никнейма
    # Validation nickename
    if len(nickname) > 16:
        await message.answer("❌ Никнейм не должен превышать 16 символов! Попробуйте снова:")
        return
    
    if len(nickname) < 2:
        await message.answer("❌ Никнейм должен содержать минимум 2 символа! Попробуйте снова:")
        return
    
    # Получаем данные из состояния
    # getting data from State()
    data = await state.get_data()
    user_id = data.get("user_id")
    game_id = data.get("game_id")
    
    # Создаем игровой профиль
    # create game profile
    with Session(engine) as session:
        new_profile = GameProfilesSchema(
            user_id=user_id,
            nickname=nickname,
            game_id=game_id
        )
        
        session.add(new_profile)
        session.commit()
        session.refresh(new_profile)
        
        new_stats = UserStatsSchema(
            user_id=user_id,
            profile_id=new_profile.game_profile_id
        )
        session.add(new_stats)
        session.commit()
    
    # Завершаем состояние
    # clear State()
    await state.clear()
    
    league = get_user_league(message.from_user.id)        
    await message.answer(
        "🎉 Регистрация завершена!\n\n"
        f"✅ Ваш игровой профиль:\n"
        f"▫️ Ник: {nickname}\n"
        f"▫️ Game ID: {game_id}\n"
        f"▫️ Лига: {league.capitalize()}\n\n"
        #todo: add buttons [✅ Подтвердить] [✏️ Изменить] | [✅ Accept] [✏️ Remake]
        f"Теперь вы можете использовать все функции бота!\n"
        f"Напишите /profile чтобы посмотреть статистику"
    )
#! testing how bot work in groups and supergroups 
CHAT_ID = os.getenv('CHAT_ID_SPEAKING')
@router.message()
async def handle_messages(message: Message):
    if message.chat.id == CHAT_ID and "test" in message.text.lower():
        await message.reply("🍎 I catch message test")
    else:
        return