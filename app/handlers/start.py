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
from localization import t

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
    builder.button(text="✅ Подтвердить | Confirm", callback_data="confirm_registration")
    builder.button(text="✏️ Изменить | Edit", callback_data="edit_registration")
    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()

# Простая функция для получения языка | Simple function to get language
def get_lang(user_id: int) -> str:
    return 'ru'  # Пока всегда русский | For now always Russian

#* commands | команды
@router.message(Command("start"))
async def start_handler(message: Message):
    telegram_id = message.from_user.id
    username = message.from_user.username or "Игрок | Player"
    first_name = message.from_user.first_name or "Игрок | Player"
    last_name = message.from_user.last_name or ""
    lang = get_lang(telegram_id)
    
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
                f"{t('start.welcome', lang)}\n\n"
                f"{t('start.register_prompt', lang)}\n\n"
                f"Привет! Твой Telegram ID: {telegram_id}\n"
                f"Твоё имя: {first_name}\n"
                f"Username: {username}",
                reply_markup=get_start_keyboard()
            )
        else:
            await message.answer(
                f"{t('start.welcome_back', lang, username=username)}\n\n"
                "Доступные команды | Available commands:\n"
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
    lang = get_lang(message.from_user.id)
    
    with Session(engine) as session:
        user = session.exec(
            select(UsersSchema).where(UsersSchema.telegram_id == message.from_user.id)
        ).first()
        
        if not user:
            # Создаем пользователя если нет | Create user if not exists
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
        
        # Проверяем, есть ли уже игровой профиль | Check if game profile already exists
        existing_profile = session.exec(
            select(GameProfilesSchema).where(GameProfilesSchema.user_id == user_id)
        ).first()
        league = get_user_league(message.from_user.id)
        
        if existing_profile:
            await message.answer(
                f"{t('register.already_exists', lang)}\n\n"
                f"Ник | Nick: {existing_profile.nickname}\n"
                f"ID: {existing_profile.game_id}\n"
                f"Лига | League: {league.capitalize() if league else 'Starter'}"
            )
            return
        
        # Сохраняем user_id в состоянии и переходим к вводу game_id
        # Save user_id in state and proceed to game_id input
        await state.set_data({"user_id": user_id})
        await state.set_state(RegistrationStates.waiting_for_game_id)
        await message.answer(
            f"{t('register.enter_game_id', lang)}\n"
            f"{t('register.game_id_rules', lang)}"
        )

@router.message(RegistrationStates.waiting_for_game_id)
async def process_game_id(message: Message, state: FSMContext) -> None:
    """Обработка ввода Game ID | Process Game ID input"""
    lang = get_lang(message.from_user.id)
    game_id = message.text.strip()
    
    # Валидация Game ID | Game ID validation
    if not game_id.isdigit():
        await message.answer(t('register.invalid_game_id', lang))
        return
    
    if len(game_id) < 8:
        await message.answer(t('register.invalid_game_id', lang))
        return
    
    # Проверяем, не занят ли этот game_id | Check if game_id is already taken
    with Session(engine) as session:
        existing_game_id = session.exec(
            select(GameProfilesSchema).where(GameProfilesSchema.game_id == game_id)
        ).first()
        
        if existing_game_id:
            await message.answer(t('register.game_id_taken', lang))
            return
    
    # Сохраняем game_id и переходим к вводу nickname
    # Save game_id and proceed to nickname input
    await state.update_data({"game_id": game_id})
    await state.set_state(RegistrationStates.waiting_for_nickname)
    
    await message.answer(
        f"{t('register.enter_nickname', lang)}\n"
        f"{t('register.nickname_rules', lang)}"
    )

@router.message(RegistrationStates.waiting_for_nickname)
async def process_nickname(message: Message, state: FSMContext) -> None:
    """Обработка ввода никнейма | Process nickname input"""
    lang = get_lang(message.from_user.id)
    nickname = message.text.strip()
    
    # Валидация никнейма | Nickname validation
    if len(nickname) > 16:
        await message.answer(t('register.invalid_nickname', lang))
        return
    
    if len(nickname) < 2:
        await message.answer(t('register.invalid_nickname', lang))
        return
    
    # Сохраняем nickname и переходим к подтверждению
    # Save nickname and proceed to confirmation
    await state.update_data({"nickname": nickname})
    await state.set_state(RegistrationStates.waiting_for_confirmation)
    
    # Получаем все данные для отображения | Get all data for display
    data = await state.get_data()
    game_id = data.get("game_id")
    
    await message.answer(
        f"📋 <b>ПОДТВЕРЖДЕНИЕ РЕГИСТРАЦИИ | REGISTRATION CONFIRMATION</b>\n\n"
        f"✅ <b>Ваш профиль | Your profile:</b>\n"
        f"▫️ Ник | Nick: <b>{nickname}</b>\n"
        f"▫️ Game ID: <b>{game_id}</b>\n"
        f"▫️ Лига | League: <b>Starter</b>\n\n"
        f"<i>Всё верно? | Is everything correct?</i>",
        parse_mode="HTML",
        reply_markup=get_confirmation_keyboard()
    )

@router.callback_query(F.data == "confirm_registration")
async def confirm_registration(callback: CallbackQuery, state: FSMContext):
    """Подтверждение регистрации | Confirm registration"""
    lang = get_lang(callback.from_user.id)
    
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
    
    league = get_user_league(callback.from_user.id)        
    await callback.message.edit_text(
        f"{t('register.complete', lang)}\n\n"
        f"✅ <b>Ваш игровой профиль | Your game profile:</b>\n"
        f"▫️ Ник | Nick: <b>{nickname}</b>\n"
        f"▫️ Game ID: <b>{game_id}</b>\n"
        f"▫️ Лига | League: <b>{league.capitalize() if league else 'Starter'}</b>\n\n"
        f"Теперь вы можете использовать все функции бота!\n"
        f"Now you can use all bot features!\n\n"
        f"Напишите /profile чтобы посмотреть статистику\n"
        f"Write /profile to view statistics",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "edit_registration")
async def edit_registration(callback: CallbackQuery, state: FSMContext):
    """Редактирование регистрации | Edit registration"""
    lang = get_lang(callback.from_user.id)
    
    # Возвращаемся к вводу nickname | Return to nickname input
    await state.set_state(RegistrationStates.waiting_for_nickname)
    
    await callback.message.edit_text(
        f"{t('register.enter_nickname', lang)}\n"
        f"{t('register.nickname_rules', lang)}"
    )
    await callback.answer("✏️ Введите новый никнейм | Enter new nickname")

#! testing how bot work in groups and supergroups | тестирование работы бота в группах
CHAT_ID = os.getenv('CHAT_ID_SPEAKING')
@router.message()
async def handle_messages(message: Message):
    """Обработчик всех сообщений | All messages handler"""
    if message.chat.id == CHAT_ID and "test" in message.text.lower():
        await message.reply("🍎 I catch message test | Я поймал сообщение test")
    else:
        return