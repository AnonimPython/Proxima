'''
MODERATOR COMMANDS - FOR MODERATORS
'''

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime, timedelta
from sqlmodel import Session, select
from database.models import engine, UsersSchema, UserBansSchema
from zoneinfo import ZoneInfo
import re

from utils.access_checker import is_moderator, find_user_by_identifier, can_ban_user

router = Router()
moscow_tz = ZoneInfo("Europe/Moscow")

async def ban_user(
        bot,
        user_id: int,
        banned_by_id: int,
        ban_type: str,
        reason: str,
        minutes: int,
    ):
    """Банит пользователя и отправляет уведомление в ЛС"""
    with Session(engine) as session:
        user = session.exec(select(UsersSchema).where(UsersSchema.telegram_id == user_id)).first()
        banned_by_user = session.exec(select(UsersSchema).where(UsersSchema.telegram_id == banned_by_id)).first()
        
        if user and banned_by_user:
            unbanned_at = datetime.now(moscow_tz) + timedelta(minutes=minutes)
            
            new_ban = UserBansSchema(
                user_id=user.user_id,
                banned_by=banned_by_user.user_id,
                ban_type=ban_type,
                reason=reason,
                duration_minutes=minutes,
                banned_at=datetime.now(moscow_tz),
                unbanned_at=unbanned_at,
                is_active=True
            )
            session.add(new_ban)
            session.commit()
            
            try:
                ban_until = unbanned_at.strftime('%d.%m.%Y %H:%M')
                ban_message = (
                    f"🔴 <b>ВЫ ЗАБАНЕНЫ</b>\n\n"
                    f"⏰ <b>Срок:</b> {minutes} минут\n"
                    f"📝 <b>Причина:</b> {reason}\n"
                    f"🕒 <b>Разбан:</b> {ban_until}\n\n"
                    f"По вопросам обращайтесь к администрации"
                )
                await bot.send_message(chat_id=user_id, text=ban_message, parse_mode="HTML")
            except:
                pass

@router.message(Command("mod_ban"))
async def mod_ban_command(message: Message):
    """Временный бан (модератор) - максимум 7 дней"""
    
    if not is_moderator(message.from_user.id):
        await message.answer("❌ Нет прав доступа ❌")
        return
    
    parts = message.text.split()
    if len(parts) < 4:
        await message.answer(
            "❗️ <b>Неправильный формат</b>❗️\n\n"
            "<b>Использование:</b>\n"
            "<code>/mod_ban @username 24h причина</code>\n"
            "<code>/mod_ban 123456789 3d причина</code>\n\n"
            "<b>Максимальное время:</b> 7 дней\n"
            "<b>Единицы времени:</b>\n"
            "• <code>m</code> - минуты (макс 1440)\n"
            "• <code>h</code> - часы (макс 168)\n"
            "• <code>d</code> - дни (макс 7)",
            parse_mode="HTML"
        )
        return
    
    identifier = parts[1]
    time_string = parts[2].lower()
    reason = ' '.join(parts[3:])
    
    time_match = re.match(r'^(\d+)([mhd])$', time_string)
    if not time_match:
        await message.answer(
            "❗️<b>Неправильный формат времени</b>❗️\n\n"
            "Используйте:\n"
            "• <code>30m</code> - 30 минут\n"
            "• <code>24h</code> - 24 часа\n" 
            "• <code>7d</code> - 7 дней",
            parse_mode="HTML"
        )
        return
    
    amount = int(time_match.group(1))
    unit = time_match.group(2)
    
    if unit == 'm':
        minutes = amount
        time_display = f"{amount}мин"
        max_minutes = 1440  # 24 часа
    elif unit == 'h':
        minutes = amount * 60
        time_display = f"{amount}ч"
        max_minutes = 10080  # 7 дней
    elif unit == 'd':
        minutes = amount * 24 * 60
        time_display = f"{amount}дн"
        max_minutes = 10080  # 7 дней
    
    # Проверяем лимиты модератора
    if minutes > max_minutes:
        await message.answer(f"❌ Превышен лимит времени для модератора\nМаксимум: {max_minutes} минут")
        return
    
    user, error = find_user_by_identifier(identifier)
    if error:
        await message.answer(error)
        return
    
    # Проверяем, может ли модератор забанить этого пользователя
    if not can_ban_user(message.from_user.id, user):
        await message.answer("❌ Нельзя забанить этого пользователя")
        return
    
    await ban_user(
        message.bot,
        user.telegram_id,
        message.from_user.id,
        "moderator_ban",
        reason,
        minutes
    )
    
    ban_until = datetime.now(moscow_tz) + timedelta(minutes=minutes)
    
    await message.answer(
        f"🔴 <b>ВРЕМЕННЫЙ БАН (МОДЕРАТОР)</b>\n\n"
        f"👤 <b>Пользователь:</b> {identifier}\n"
        f"⏰ <b>Длительность:</b> {time_display}\n"
        f"📝 <b>Причина:</b> {reason}\n"
        f"👮 <b>Забанил:</b> @{message.from_user.username or 'модератор'}\n"
        f"🕒 <b>До:</b> {ban_until.strftime('%d.%m.%Y %H:%M')}\n\n",
        parse_mode="HTML"
    )

@router.message(Command("mod_warn"))
async def mod_warn_command(message: Message):
    """Предупреждение пользователю"""
    
    if not is_moderator(message.from_user.id):
        await message.answer("❌ Нет прав доступа ❌")
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "❗️<b>Неправильный формат</b>❗️\n\n"
            "<b>Использование:</b>\n"
            "<code>/mod_warn @username причина</code>\n"
            "<code>/mod_warn 123456789 причина</code>",
            parse_mode="HTML"
        )
        return
    
    identifier = parts[1]
    reason = ' '.join(parts[2:])
    
    user, error = find_user_by_identifier(identifier)
    if error:
        await message.answer(error)
        return
    
    # Проверяем, может ли модератор выдать предупреждение
    if not can_ban_user(message.from_user.id, user):
        await message.answer("❌ Нельзя выдать предупреждение этому пользователю")
        return
    
    # Создаем запись предупреждения в БД
    with Session(engine) as session:
        moderator = session.exec(select(UsersSchema).where(UsersSchema.telegram_id == message.from_user.id)).first()
        
        if user and moderator:
            new_warn = UserBansSchema(
                user_id=user.user_id,
                banned_by=moderator.user_id,
                ban_type="warning",
                reason=reason,
                duration_minutes=0,
                banned_at=datetime.now(moscow_tz),
                unbanned_at=None,
                is_active=False  # Предупреждение не активно как бан
            )
            session.add(new_warn)
            session.commit()
    
    # Отправляем уведомление пользователю в ЛС
    try:
        warn_message = (
            f"⚠️ <b>ВЫ ПОЛУЧИЛИ ПРЕДУПРЕЖДЕНИЕ</b>\n\n"
            f"📝 <b>Причина:</b> {reason}\n"
            f"👮 <b>Выдал модератор:</b> @{message.from_user.username or 'модератор'}\n"
            f"🕒 <b>Время:</b> {datetime.now(moscow_tz).strftime('%d.%m.%Y %H:%M')}\n\n"
            f"<i>При повторных нарушениях возможна блокировка</i>"
        )
        await message.bot.send_message(
            chat_id=user.telegram_id, 
            text=warn_message, 
            parse_mode="HTML"
        )
        
        # Подтверждение модератору
        await message.answer(
            f"⚠️ <b>ВЫДАНО ПРЕДУПРЕЖДЕНИЕ</b>\n\n"
            f"👤 <b>Пользователь:</b> {identifier}\n"
            f"📝 <b>Причина:</b> {reason}\n"
            f"👮 <b>Выдал:</b> @{message.from_user.username or 'модератор'}\n\n",
            # f"✅ Пользователь уведомлен в ЛС",
            parse_mode="HTML"
        )
        
    except Exception as e:
        # Если не удалось отправить сообщение в ЛС | If massage dont send to user
        await message.answer(
            f"⚠️ <b>ВЫДАНО ПРЕДУПРЕЖДЕНИЕ</b>\n\n"
            f"👤 <b>Пользователь:</b> {identifier}\n"
            f"📝 <b>Причина:</b> {reason}\n"
            f"👮 <b>Выдал:</b> @{message.from_user.username or 'модератор'}\n\n"
            f"❌ <b>Не удалось отправить уведомление в ЛС (Пользователь заблокировал бота)</b>\n",
            parse_mode="HTML"
        )

@router.message(Command("mod_unban"))
async def mod_unban_command(message: Message):
    """Разбан пользователя (только свои баны)"""
    
    if not is_moderator(message.from_user.id):
        await message.answer("❌ Нет прав доступа ❌")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "❗️ <b>Неправильный формат</b>❗️\n\n"
            "<b>Использование:</b>\n"
            "<code>/mod_unban @username</code>\n"
            "<code>/mod_unban 123456789</code>",
            parse_mode="HTML"
        )
        return
    
    identifier = parts[1]
    
    with Session(engine) as session:
        user = session.exec(select(UsersSchema).where(UsersSchema.username == identifier)).first()
        if not user:
            # Пробуем найти по ID
            user = session.exec(select(UsersSchema).where(UsersSchema.telegram_id == int(identifier))).first()
            if not user:
                await message.answer(f"❌ Пользователь {identifier} не найден")
                return
        
        # Находим модератора
        moderator = session.exec(select(UsersSchema).where(UsersSchema.telegram_id == message.from_user.id)).first()
        
        # Находим только те баны, которые выдал этот модератор
        active_bans = session.exec(select(UserBansSchema).where(
            UserBansSchema.user_id == user.user_id,
            UserBansSchema.is_active == True,
            UserBansSchema.banned_by == moderator.user_id
        )).all()
        
        if not active_bans:
            await message.answer(f"У пользователя {identifier} нет активных банов от вас")
            return
        
        for ban in active_bans:
            ban.is_active = False
            ban.unbanned_by = moderator.user_id
            ban.unbanned_at_time = datetime.now(moscow_tz)
        
        session.commit()
        
        await message.answer(
            f"✅ <b>Пользователь разбанен</b>\n\n"
            f"👤 <b>Пользователь:</b> {identifier}\n"
            f"👮 <b>Разбанил:</b> @{message.from_user.username or 'модератор'}\n"
            f"🕒 <b>Время:</b> {datetime.now(moscow_tz).strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML"
        )