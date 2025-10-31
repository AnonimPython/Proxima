'''
FILE FOR WORK WITH COMMANDS | ФАЙЛ ДЛЯ РАБОТЫ С КОМАНДАМИ
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
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Локализация | Localization
from localization import translate

#* Keyboards | Клавиатуры
from .keyboards import get_main_keyboard, get_game_keyboard, get_start_keyboard
#* Database | База данных
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

class RegistrationStates(StatesGroup):
    waiting_for_game_id = State()
    waiting_for_nickname = State()
    waiting_for_confirmation = State()  # Новое состояние для подтверждения

def get_user_league(telegram_id: int):
    """Получает лигу пользователя | Get user league"""
    with Session(engine) as session:
        user_league = session.exec(
            select(GameProfilesSchema.league)
            .join(UsersSchema, GameProfilesSchema.user_id == UsersSchema.user_id)
            .where(UsersSchema.telegram_id == telegram_id)
        ).first()
    return user_league 

def get_confirmation_keyboard():
    """Создает клавиатуру подтверждения | Creates confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_registration")
    builder.button(text="✏️ Изменить", callback_data="edit_registration")
    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()

#* commands | команды
@router.message(CommandStart())
async def start_handler(message: Message):
    telegram_id = message.from_user.id
    username = message.from_user.username or "Игрок"
    first_name = message.from_user.first_name or "Игрок"
    last_name = message.from_user.last_name or ""
    
    with Session(engine) as session:
        statement = select(UsersSchema).where(UsersSchema.telegram_id == telegram_id)
        user = session.exec(statement).first()
        
        if not user:
            # Если нет, создаём нового | If not exists, create new one
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
                f"{translate('start.welcome', telegram_id)}\n\n"
                f"{translate('start.register_prompt', telegram_id)}\n\n"
                f"Привет! Твой Telegram ID: {telegram_id}\n"
                f"Твоё имя: {first_name}\n"
                f"Username: {username}",
                reply_markup=get_start_keyboard()
            )
        else:
            await message.answer(
                f"{translate('start.welcome_back', telegram_id, username=username)}\n\n"
                "Доступные команды:\n"
                "/profile - Профиль\n"
                "/lobby - Найти лобби\n" 
                "/stats - Статистика\n"
                "/top - Топ игроков\n\n",
                parse_mode="HTML",
                reply_markup=get_game_keyboard()
            )
    
@router.message(Command("register"))
async def command_register_handler(message: Message, state: FSMContext) -> None:
    """Начало регистрации игрового профиля | Start game profile registration"""
    telegram_id = message.from_user.id
    
    with Session(engine) as session:
        user = session.exec(
            select(UsersSchema).where(UsersSchema.telegram_id == telegram_id)
        ).first()
        
        if not user:
            # Создаем пользователя если нет | Create user if not exists
            new_user = UsersSchema(
                telegram_id=telegram_id,
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
        
        # Проверяем, есть ли уже игровой профиль | Check if game profile already exists
        existing_profile = session.exec(
            select(GameProfilesSchema).where(GameProfilesSchema.user_id == user_id)
        ).first()
        league = get_user_league(telegram_id)
        
        if existing_profile:
            await message.answer(
                f"{translate('register.already_exists', telegram_id)}\n\n"
                f"Ник: {existing_profile.nickname}\n"
                f"ID: {existing_profile.game_id}\n"
                f"Лига: {league.capitalize() if league else 'Starter'}"
            )
            return
        
        # Сохраняем user_id в состоянии и переходим к вводу game_id
        # Save user_id in state and proceed to game_id input
        await state.set_data({"user_id": user_id})
        await state.set_state(RegistrationStates.waiting_for_game_id)
        await message.answer(
            f"{translate('register.enter_game_id', telegram_id)}\n"
            f"{translate('register.game_id_rules', telegram_id)}"
        )

@router.message(RegistrationStates.waiting_for_game_id)
async def process_game_id(message: Message, state: FSMContext) -> None:
    """Обработка ввода Game ID | Process Game ID input"""
    telegram_id = message.from_user.id
    game_id = message.text.strip()
    
    # Валидация Game ID | Game ID validation
    if not game_id.isdigit():
        await message.answer(translate('register.invalid_game_id', telegram_id))
        return
    
    if len(game_id) < 8:
        await message.answer(translate('register.invalid_game_id', telegram_id))
        return
    
    # Проверяем, не занят ли этот game_id | Check if game_id is already taken
    with Session(engine) as session:
        existing_game_id = session.exec(
            select(GameProfilesSchema).where(GameProfilesSchema.game_id == game_id)
        ).first()
        
        if existing_game_id:
            await message.answer(translate('register.game_id_taken', telegram_id))
            return
    
    # Сохраняем game_id и переходим к вводу nickname
    # Save game_id and proceed to nickname input
    await state.update_data({"game_id": game_id})
    await state.set_state(RegistrationStates.waiting_for_nickname)
    
    await message.answer(
        f"{translate('register.enter_nickname', telegram_id)}\n"
        f"{translate('register.nickname_rules', telegram_id)}"
    )

@router.message(RegistrationStates.waiting_for_nickname)
async def process_nickname(message: Message, state: FSMContext) -> None:
    """Обработка ввода никнейма | Process nickname input"""
    telegram_id = message.from_user.id
    nickname = message.text.strip()
    
    # Валидация никнейма | Nickname validation
    if len(nickname) > 16:
        await message.answer(translate('register.invalid_nickname', telegram_id))
        return
    
    if len(nickname) < 2:
        await message.answer(translate('register.invalid_nickname', telegram_id))
        return
    
    # Сохраняем nickname и переходим к подтверждению
    # Save nickname and proceed to confirmation
    await state.update_data({"nickname": nickname})
    await state.set_state(RegistrationStates.waiting_for_confirmation)
    
    # Получаем все данные для отображения | Get all data for display
    data = await state.get_data()
    game_id = data.get("game_id")
    
    await message.answer(
        f"📋 <b>ПОДТВЕРЖДЕНИЕ РЕГИСТРАЦИИ</b>\n\n"
        f"✅ <b>Ваш профиль:</b>\n"
        f"▫️ Ник: <b>{nickname}</b>\n"
        f"▫️ Game ID: <b>{game_id}</b>\n"
        f"▫️ Лига: <b>Starter</b>\n\n"
        f"<i>Всё верно?</i>",
        parse_mode="HTML",
        reply_markup=get_confirmation_keyboard()
    )

@router.callback_query(F.data == "confirm_registration")
async def confirm_registration(callback: CallbackQuery, state: FSMContext):
    """Подтверждение регистрации | Confirm registration"""
    telegram_id = callback.from_user.id
    
    # Получаем данные из состояния | Get data from state
    data = await state.get_data()
    user_id = data.get("user_id")
    game_id = data.get("game_id")
    nickname = data.get("nickname")
    
    # Создаем игровой профиль | Create game profile
    with Session(engine) as session:
        new_profile = GameProfilesSchema(
            user_id=user_id,
            nickname=nickname,
            game_id=game_id
        )
        
        session.add(new_profile)
        session.commit()
        session.refresh(new_profile)
        
        # Создаем запись статистики для профиля | Create statistics record for profile
        new_stats = UserStatsSchema(
            user_id=user_id,
            profile_id=new_profile.game_profile_id
        )
        session.add(new_stats)
        session.commit()
    
    # Завершаем состояние | Clear state
    await state.clear()
    
    league = get_user_league(telegram_id)        
    await callback.message.edit_text(
        f"{translate('register.complete', telegram_id)}\n\n"
        f"✅ <b>Ваш игровой профиль:</b>\n"
        f"▫️ Ник: <b>{nickname}</b>\n"
        f"▫️ Game ID: <b>{game_id}</b>\n"
        f"▫️ Лига: <b>{league.capitalize() if league else 'Starter'}</b>\n\n"
        f"Теперь вы можете использовать все функции бота!\n\n"
        f"Напишите /profile чтобы посмотреть статистику",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "edit_registration")
async def edit_registration(callback: CallbackQuery, state: FSMContext):
    """Редактирование регистрации | Edit registration"""
    telegram_id = callback.from_user.id
    
    # Возвращаемся к вводу nickname | Return to nickname input
    await state.set_state(RegistrationStates.waiting_for_nickname)
    
    await callback.message.edit_text(
        f"{translate('register.enter_nickname', telegram_id)}\n"
        f"{translate('register.nickname_rules', telegram_id)}"
    )
    await callback.answer("✏️ Введите новый никнейм")

#! testing how bot work in groups and supergroups | тестирование работы бота в группах
CHAT_ID = os.getenv('CHAT_ID_SPEAKING')
@router.message()
async def handle_messages(message: Message):
    """Обработчик всех сообщений | All messages handler"""
    if message.chat.id == CHAT_ID and "test" in message.text.lower():
        await message.reply("🍎 I catch message test | Я поймал сообщение test")
    else:
        return