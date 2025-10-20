'''
ADMIN COMMANDS - ONLY FOR ADMINS
'''

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime, timedelta
from sqlmodel import Session, select
from database.models import engine, UsersSchema, UserBansSchema
from zoneinfo import ZoneInfo
import re
import os
from dotenv import load_dotenv

from utils.access_checker import is_admin, find_user_by_identifier, can_ban_user

load_dotenv()

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
    """
    Банит пользователя и отправляет уведомление в ЛС
    Bans user and sends notification to DM
    """
    with Session(engine) as session:
        user = session.exec(select(UsersSchema).where(UsersSchema.telegram_id == user_id)).first()
        banned_by_user = session.exec(select(UsersSchema).where(UsersSchema.telegram_id == banned_by_id)).first()
        
        if user and banned_by_user:
            unbanned_at = datetime.now(moscow_tz) + timedelta(minutes=minutes) if minutes > 0 else None
            
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
            
            # Отправляем сообщение забаненному игроку
            try:
                if minutes > 0:
                    ban_until = unbanned_at.strftime('%d.%m.%Y %H:%M')
                    ban_message = (
                        f"🔴 <b>ВЫ ЗАБАНЕНЫ</b>\n\n"
                        f"⏰ <b>Срок:</b> {minutes} минут\n"
                        f"📝 <b>Причина:</b> {reason}\n"
                        f"🕒 <b>Разбан:</b> {ban_until}\n\n"
                        f"По вопросам обращайтесь к администрации"
                    )
                else:
                    ban_message = (
                        f"🔴 <b>ВЫ ЗАБАНЕНЫ НАВСЕГДА</b>\n\n"
                        f"📝 <b>Причина:</b> {reason}\n\n"
                        f"По вопросам обращайтесь к администрации"
                    )
                await bot.send_message(chat_id=user_id, text=ban_message, parse_mode="HTML")
            except:
                pass
#! TEST
@router.message(Command("make_me_admin"))
async def make_me_admin(message: Message):
    """
        Команда для выдачи прав администратора
        FOR TEST GIVE U ADMIN COMMANDS
    """
    admin_id = os.getenv('ADMIN_TELEGRAM_ID')
    
    if str(message.from_user.id) != admin_id:
        await message.answer("❌ У вас нет прав для использования этой команды ❌")
        return
    
    with Session(engine) as session:
        user_stmt = select(UsersSchema).where(UsersSchema.telegram_id == message.from_user.id)
        user = session.exec(user_stmt).first()
        
        if user:
            user.role = "admin"
            session.commit()
            await message.answer(
                "✅ <b>Вы стали администратором!</b>\n\n"
                "Теперь вам доступны команды:\n"
                "• /admin_ban - Заблокировать пользователя\n"
                "• /permaban - Перманентный бан\n"
                "• /unban - Разблокировать пользователя\n"
                "• /banlist - Список забаненных\n"
                "• /banhistory - История банов\n"
                "• /make_moderator - Сделать модератором",
                parse_mode="HTML"
            )
        else:
            await message.answer("❗️ Пользователь не найден в базе данных ❗️")

@router.message(Command("make_moderator"))
async def make_moderator_command(message: Message):
    """
    Сделать пользователя модератором
    Admin can make user moderator 
    """
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ Только для администраторов ❌")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "❗️ <b>Неправильный формат</b> ❗️\n\n"
            "<b>Использование:</b>\n"
            "<code>/make_moderator @username</code>\n"
            "<code>/make_moderator 123456789</code>",
            parse_mode="HTML"
        )
        return
    
    identifier = parts[1]
    
    user, error = find_user_by_identifier(identifier)
    if error:
        await message.answer(error)
        return
    
    with Session(engine) as session:
        user_to_promote = session.exec(select(UsersSchema).where(UsersSchema.user_id == user.user_id)).first()
        user_to_promote.role = "moderator"
        session.commit()
    
    await message.answer(
        f"✅ <b>Пользователь стал модератором</b>\n\n"
        f"👤 <b>Пользователь:</b> {identifier}\n"
        f"🎯 <b>Новая роль:</b> Модератор\n"
        f"👮 <b>Назначил:</b> @{message.from_user.username or 'администратор'}\n\n"
        f"Теперь пользователь может использовать команды модератора",
        parse_mode="HTML"
    )

@router.message(Command("permaban"))
async def permaban_command(message: Message):
    """Перманентный бан пользователя"""
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав доступа ❌")
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "❗️ <b>Неправильный формат</b> ❗️\n\n"
            "<b>Использование:</b>\n"
            "<code>/permaban @username причина</code>\n"
            "<code>/permaban 123456789 причина</code>\n\n"
            "<b>Пример:</b>\n"
            "<code>/permaban @username Читы</code>\n"
            "<code>/permaban 123456789 Читы</code>",
            parse_mode="HTML"
        )
        return
    
    identifier = parts[1]
    reason = ' '.join(parts[2:])
    
    user, error = find_user_by_identifier(identifier)
    if error:
        await message.answer(error)
        return
    
    # Проверяем, может ли админ забанить этого пользователя
    if not can_ban_user(message.from_user.id, user):
        await message.answer("❌ Нельзя забанить этого пользователя")
        return
    
    # Пермабан
    await ban_user(
        message.bot,
        user.telegram_id,
        message.from_user.id,
        "permanent_ban",
        reason,
        0
    )
    
    await message.answer(
        f"🔴 <b>ПЕРМАНЕНТНЫЙ БАН</b>\n\n"
        f"👤 <b>Пользователь:</b> {identifier}\n"
        f"📝 <b>Причина:</b> {reason}\n"
        f"👮 <b>Забанил:</b> @{message.from_user.username or 'администратор'}\n"
        f"🕒 <b>Тип:</b> Перманентный\n\n"
        f"❗️Пользователь забанен навсегда❗️",
        parse_mode="HTML"
    )

@router.message(Command("admin_ban"))
async def admin_ban_command(message: Message):
    """Временный бан (админ)"""
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав доступа ❌")
        return
    
    parts = message.text.split()
    if len(parts) < 4:
        await message.answer(
            "❗️ <b>Неправильный формат</b>❗️\n\n"
            "<b>Использование:</b>\n"
            "<code>/admin_ban @username 7d причина</code>\n"
            "<code>/admin_ban 123456789 30d причина</code>\n\n"
            "<b>Единицы времени:</b>\n"
            "• <code>m</code> - минуты\n"
            "• <code>h</code> - часы\n"
            "• <code>d</code> - дни",
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
    elif unit == 'h':
        minutes = amount * 60
        time_display = f"{amount}ч"
    elif unit == 'd':
        minutes = amount * 24 * 60
        time_display = f"{amount}дн"
    
    user, error = find_user_by_identifier(identifier)
    if error:
        await message.answer(error)
        return
    
    # Проверяем, может ли админ забанить этого пользователя
    if not can_ban_user(message.from_user.id, user):
        await message.answer("❌ Нельзя забанить этого пользователя")
        return
    
    await ban_user(
        message.bot,
        user.telegram_id,
        message.from_user.id,
        "admin_temporary_ban",
        reason,
        minutes
    )
    
    ban_until = datetime.now(moscow_tz) + timedelta(minutes=minutes)
    
    await message.answer(
        f"🔴 <b>ВРЕМЕННЫЙ БАН</b>\n\n"
        f"👤 <b>Пользователь:</b> {identifier}\n"
        f"⏰ <b>Длительность:</b> {time_display}\n"
        f"📝 <b>Причина:</b> {reason}\n"
        f"👮 <b>Забанил:</b> @{message.from_user.username or 'администратор'}\n"
        f"🕒 <b>До:</b> {ban_until.strftime('%d.%m.%Y %H:%M')}\n\n",
        parse_mode="HTML"
    )

# Остальные команды (unban, banlist, banhistory) остаются без изменений
@router.message(Command("unban"))
async def unban_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для использования этой команды ❌")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌<b>Неправильный формат команды</b>❌")
        return
    
    username = parts[1].replace('@', '')
    
    with Session(engine) as session:
        user = session.exec(select(UsersSchema).where(UsersSchema.username == username)).first()
        if not user:
            await message.answer(f"❌ Пользователь @{username} не найден")
            return
        
        unbanned_by_user = session.exec(select(UsersSchema).where(UsersSchema.telegram_id == message.from_user.id)).first()
        active_bans = session.exec(select(UserBansSchema).where(
            UserBansSchema.user_id == user.user_id,
            UserBansSchema.is_active == True
        )).all()
        
        if not active_bans:
            await message.answer(f"ℹ️ У пользователя @{username} нет активных банов")
            return
        
        for ban in active_bans:
            ban.is_active = False
            if unbanned_by_user:
                ban.unbanned_by = unbanned_by_user.user_id
            ban.unbanned_at_time = datetime.now(moscow_tz)
        
        session.commit()
        
        await message.answer(
            f"✅ <b>Пользователь разбанен</b>\n\n"
            f"👤 <b>Пользователь:</b> @{username}\n"
            f"👮 <b>Разбанил:</b> @{message.from_user.username or 'администратор'}\n"
            f"🕒 <b>Время:</b> {datetime.now(moscow_tz).strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML"
        )

# banlist и banhistory команды остаются без изменений