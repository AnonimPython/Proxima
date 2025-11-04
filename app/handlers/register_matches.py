'''
MATCH REGISTRATION HANDLER
'''

import os
import uuid
from aiogram import Router, F
from aiogram.types import Message, ContentType, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from sqlmodel import Session, select
from app.database.models import engine, MatchesSchema, MatchPlayersSchema, UsersSchema, MatchPhotosSchema, GameProfilesSchema
from zoneinfo import ZoneInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()
moscow_tz = ZoneInfo("Europe/Moscow")

# Создаем папку для фото если её нет | Create photos directory if not exists
PHOTOS_DIR = "app/photo_matches"
os.makedirs(PHOTOS_DIR, exist_ok=True)

# Состояния для FSM | States for FSM
class MatchRegistrationStates(StatesGroup):
    waiting_for_match_id = State()
    waiting_for_photo = State()

def get_cancel_keyboard():
    """Создает клавиатуру с кнопкой отмены | Creates keyboard with cancel button"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_registration")
    return builder.as_markup()

@router.message(Command("match_register"))
async def start_match_registration(message: Message, state: FSMContext):
    """Начало регистрации матча | Start match registration"""
    
    # Проверяем, есть ли у пользователя игровой профиль | Check if user has game profile
    with Session(engine) as session:
        user = session.exec(
            select(UsersSchema).where(UsersSchema.telegram_id == message.from_user.id)
        ).first()
        
        if not user:
            await message.answer(
                "❌<b>Сначала нужно зарегистрироваться!</b>❌\n\n"
                "Используйте команду /register чтобы создать профиль",
                parse_mode="HTML"
            )
            return
        
        game_profile = session.exec(
            select(GameProfilesSchema).where(GameProfilesSchema.user_id == user.user_id)
        ).first()
        
        if not game_profile:
            await message.answer(
                "❌<b>Сначала нужно создать игровой профиль!</b>❌\n\n"
                "Используйте команду /register чтобы создать профиль",
                parse_mode="HTML"
            )
            return
    
    await state.set_state(MatchRegistrationStates.waiting_for_match_id)
    await message.answer(
        "🎮 <b>РЕГИСТРАЦИЯ РЕЗУЛЬТАТА МАТЧА</b>\n"
        "Введите <b>номер матча</b>:\n"
        "▫️ Это цифровой ID матча\n"
        "▫️ Пример: 12345\n\n"
        "<i>Отправьте только цифры</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(MatchRegistrationStates.waiting_for_match_id)
async def process_match_id(message: Message, state: FSMContext):
    """Обработка ввода номера матча | Process match ID input"""
    
    match_id_text = message.text.strip()
    
    # Валидация ввода | Input validation
    if not match_id_text.isdigit():
        await message.answer(
            "❗️ <b>Неверный формат номера матча!</b>❗️\n\n"
            "Введите только цифры:\n"
            "<code>12345</code>\n\n",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    match_id = int(match_id_text)
    
    # Ищем матч в базе данных | Find match in database
    with Session(engine) as session:
        match = session.exec(
            select(MatchesSchema).where(MatchesSchema.match_id == match_id)
        ).first()
        
        if not match:
            await message.answer(
                f"❗️<b>Матч #{match_id} не найден!</b>❗️\n\n"
                f"Проверьте правильность номера матча",
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        # Проверяем, участвовал ли пользователь в этом матче | Check if user participated in this match
        user = session.exec(
            select(UsersSchema).where(UsersSchema.telegram_id == message.from_user.id)
        ).first()
        
        if user:
            player_in_match = session.exec(
                select(MatchPlayersSchema).where(
                    MatchPlayersSchema.match_id == match_id,
                    MatchPlayersSchema.user_id == user.user_id
                )
            ).first()
            
            if not player_in_match:
                await message.answer(
                    f"❌ <b>Вы не участвовали в матче #{match_id}!</b>❌\n\n"
                    f"Только участники матча могут загружать результаты",
                    parse_mode="HTML",
                    reply_markup=get_cancel_keyboard()
                )
                return
        
        # Сохраняем данные матча в состоянии | Save match data in state
        await state.update_data({
            "match_id": match_id,
            "map_name": match.map_name
        })
        
        # Получаем информацию об игроках для отображения | Get players info for display
        players = session.exec(
            select(MatchPlayersSchema, UsersSchema, GameProfilesSchema)
            .join(UsersSchema, MatchPlayersSchema.user_id == UsersSchema.user_id)
            .join(GameProfilesSchema, UsersSchema.user_id == GameProfilesSchema.user_id)
            .where(MatchPlayersSchema.match_id == match_id)
        ).all()
        
        # Формируем информацию о матче | Format match information
        match_info = (
            f"✅ <b>МАТЧ #{match_id} НАЙДЕН</b>\n"
            
            f"🗺️ <b>Карта </b> {match.map_name}\n"
            f"👥 <b>Участники </b> {len(players)}\n\n"
        )
        
        # Добавляем список игроков | Add players list
        match_info += "<b>Игроки</b>\n"
        for match_player, user, profile in players:
            match_info += f"▫️ {profile.nickname} | Убийств | Kills: {match_player.kills}\n"
        
        # Добавляем инструкцию по отправке фото | Add photo upload instructions
        match_info += (
            f"\n📸 <b>Теперь отправьте фото результата матча</b>\n"
            f"▫️ Сделайте скриншот итогового экрана\n"
            f"▫️ Отправьте его как фото (не файл)\n"
            f"▫️ Фото должно быть четким и читаемым\n\n"
            "❗️<b>За предоставление неверного результата - понесете наказание в соотетствуии с правилами сервера</b>❗️",
        )
        
        await state.set_state(MatchRegistrationStates.waiting_for_photo)
        await message.answer(match_info, parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(MatchRegistrationStates.waiting_for_photo, F.content_type == ContentType.PHOTO)
async def process_match_photo(message: Message, state: FSMContext):
    """Обработка фото результата матча | Process match result photo"""
    
    # Получаем данные из состояния | Get data from state
    data = await state.get_data()
    match_id = data.get("match_id")
    map_name = data.get("map_name")
    
    # Получаем информацию о пользователе | Get user information
    with Session(engine) as session:
        user = session.exec(
            select(UsersSchema).where(UsersSchema.telegram_id == message.from_user.id)
        ).first()
        
        if not user:
            await message.answer("❗️Ошибка: пользователь не найден❗️")
            await state.clear()
            return
    
    # Сохраняем фото | Save photo
    try:
        # Генерируем уникальное имя файла | Generate unique filename
        file_id = message.photo[-1].file_id
        file = await message.bot.get_file(file_id)
        file_extension = file.file_path.split('.')[-1] if '.' in file.file_path else 'jpg'
        
        unique_filename = f"match_{match_id}_{user.user_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
        file_path = os.path.join(PHOTOS_DIR, unique_filename)
        
        # Скачиваем фото | Download photo
        await message.bot.download_file(file.file_path, file_path)
        
        # Сохраняем информацию в базу данных | Save information to database
        with Session(engine) as session:
            new_photo = MatchPhotosSchema(
                match_id=match_id,
                user_id=user.user_id,
                photo_path=file_path,
                uploaded_at=datetime.now(moscow_tz),
                status="pending"
            )
            session.add(new_photo)
            session.commit()
        
        # Отправляем подтверждение | Send confirmation
        await message.answer(
            f"✅ <b>ФОТО РЕЗУЛЬТАТА СОХРАНЕНО!</b>\n"
            f"🎮 <b>Матч </b> #{match_id}\n"
            f"🗺️ <b>Карта </b> {map_name}\n"
            f"👤 <b>Загрузил </b> @{message.from_user.username or user.first_name}\n"
            f"🕒 <b>Время </b> {datetime.now(moscow_tz).strftime('%d.%m.%Y %H:%M')}\n\n"            
            f"Спасибо за регистрацию результата!\n"
            "❗️<b>За предоставление неверного результата - понесете наказание в соотетствуии с правилами сервера</b>❗️",
            parse_mode="HTML"
        )
        
        # Очищаем состояние | Clear state
        await state.clear()
        
    except Exception as e:
        await message.answer(
            f"❗️ <b>Ошибка при сохранении фото!</b>❗️\n\n"
            f"Попробуйте отправить фото еще раз\n\n"
            "❗️<b>За предоставление неверного результата - понесете наказание в соотетствуии с правилами сервера</b>❗️",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        print(f"Error saving photo: {e}")

@router.message(MatchRegistrationStates.waiting_for_photo)
async def wrong_content_type(message: Message):
    """Обработка неправильного типа контента | Wrong content type handler"""
    await message.answer(
        "❗️ <b>Пожалуйста, отправьте фото!</b>❗️\n\n"
        "▫️ Сделайте скриншот итогового экрана матча\n"
        "▫️ Отправьте его как <b>фото</b> (не файл)\n"
        "▫️ Фото должно быть четким и читаемым\n\n"
        "<i>Стикеры, GIF, документы и текст не принимаются</i>\n\n"
        "❗️<b>За предоставление неверного результата - понесете наказание в соотетствуии с правилами сервера</b>❗️",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.callback_query(F.data == "cancel_registration")
async def cancel_registration_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка отмены регистрации по кнопке | Cancel registration callback handler"""
    current_state = await state.get_state()
    if current_state is None:
        await callback.answer("❗️ Нет активной регистрации❗️")
        return
    
    await state.clear()
    await callback.message.edit_text(
        "❌ <b>Регистрация матча отменена</b>❌\n\n"
        "Вы можете начать заново командой /match_register\n\n",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(Command("cancel"))
async def cancel_registration_command(message: Message, state: FSMContext):
    """Отмена регистрации командой | Cancel registration by command"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("❗️ Нет активной регистрации ❗️")
        return
    
    await state.clear()
    await message.answer(
        "❌<b>Регистрация матча отменена</b>❌\n\n"
        "Вы можете начать заново командой /match_register\n\n",
        parse_mode="HTML"
    )