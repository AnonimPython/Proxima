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

from utils.access_checker import is_admin, find_user_by_identifier

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
    """
    with Session(engine) as session:
        # Находим user_id по telegram_id для банимого
        user = session.exec(select(UsersSchema).where(UsersSchema.telegram_id == user_id)).first()
        
        # Находим  telegram_id админа который будет банить
        banned_by_user = session.exec(select(UsersSchema).where(UsersSchema.telegram_id == banned_by_id)).first()
        
        if user and banned_by_user:
            # Вычисляем время разбана
            # Calculating the unban time
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
            
            # отправляем сообщение забаненному игроку
            # send a message to the banned player
            try:
                await bot.send_message(chat_id=user_id, text="бан")
            except:
                pass
#! TEST
@router.message(Command("make_me_admin"))
async def make_me_admin(message: Message):
    """
        Команда для выдачи прав администратора
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
                "• /unban - Разблокировать пользователя\n"
                "• /banlist - Список забаненных\n"
                "• /banhistory - История банов пользователя\n",
                parse_mode="HTML"
            )
        else:
            await message.answer("❗️ Пользователь не найден в базе данных ❗️")

@router.message(Command("permaban"))
async def permaban_command(message: Message):
    """Перманентный бан пользователя | Permanent user ban"""
    
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
    
    # Проверяем роль | Check role
    if user.role in ["admin", "moderator"]:
        await message.answer("❌ Нельзя забанить админа/модератора")
        return
    
    # Пермабан | Permanent ban
    ban_user(
        user.telegram_id,
        message.from_user.id,
        "permanent_ban",
        reason,
        0  # 0 minutes = permanent
    )
    
    await message.answer(
        f"🔴 <b>ПЕРМАНЕНТНЫЙ БАН</b>\n\n"
        f"👤 <b>Пользователь:</b> {identifier}\n"
        f"📝 <b>Причина:</b> {reason}\n"
        f"👮 <b>Забанил:</b> @{message.from_user.username or 'admin'}\n"
        f"🕒 <b>Тип:</b> Перманентный\n\n"
        f"❗️Пользователь забанен навсегда❗️",
        parse_mode="HTML"
    )

@router.message(Command("admin_ban"))
async def admin_ban_command(message: Message):
    """Временный бан (админ) | Temporary ban (admin)"""
    
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
    
    # Парсим время | Parse time
    time_match = re.match(r'^(\d+)([mhd])$', time_string)
    if not time_match:
        await message.answer(
            "❗️<b>Неправильный формат времени</b>❗️\n\n"
            "Используйте:\n"
            "• <code>30m</code> - 30 минут\n"
            "• <code>24h</code> -  24 часа\n" 
            "• <code>7d</code> - 7 дней",
            parse_mode="HTML"
        )
        return
    
    amount = int(time_match.group(1))
    unit = time_match.group(2)
    
    # Конвертируем в минуты | Convert to minutes
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
    
    if user.role in ["admin", "moderator"]:
        await message.answer("❗️Нельзя забанить админа/модератора❗️")
        return
    
    # Временный бан | Temporary ban
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
        f"👮 <b>Забанил:</b> @{message.from_user.username or 'admin'}\n"
        f"🕒 <b>До:</b> {ban_until.strftime('%d.%m.%Y %H:%M')}\n\n",
        parse_mode="HTML"
    )


@router.message(Command("unban"))
async def unmute_command(message: Message):
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для использования этой команды ❌")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "❌<b>Неправильный формат команды</b>❌\n\n"
            "<b>Использование:</b>\n"
            "<code>/unban @username</code>\n\n"
            "<b>Пример:</b>\n"
            "<code>/unban @username</code>",
            parse_mode="HTML"
        )
        return
    
    username = parts[1].replace('@', '')
    
    with Session(engine) as session:
        user_stmt = select(UsersSchema).where(UsersSchema.username == username)
        user = session.exec(user_stmt).first()
        
        if not user:
            await message.answer(f"❌ Пользователь @{username} не найден")
            return
        
        unbanned_by_stmt = select(UsersSchema).where(UsersSchema.telegram_id == message.from_user.id)
        unbanned_by_user = session.exec(unbanned_by_stmt).first()
        
        ban_stmt = select(UserBansSchema).where(
            UserBansSchema.user_id == user.user_id,
            UserBansSchema.is_active == True
        )
        active_bans = session.exec(ban_stmt).all()
        
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
            f"🕒 <b>Время:</b> {datetime.now(moscow_tz).strftime('%d.%m.%Y %H:%M')}\n\n",
            parse_mode="HTML"
        )
#! not wokring at this time
@router.message(Command("banlist"))
async def banlist_command(message: Message):
    """Показывает список активных банов"""
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для использования этой команды")
        return
    
    with Session(engine) as session:
        from datetime import datetime
        
        # Получаем активные баны с информацией о пользователях
        ban_stmt = select(UserBansSchema, UsersSchema).join(
            UsersSchema, UserBansSchema.user_id == UsersSchema.user_id
        ).where(
            UserBansSchema.is_active == True
        )
        results = session.exec(ban_stmt).all()
        
        if not results:
            await message.answer("📋 <b>Список банов пуст</b>\n\nНет активных банов", parse_mode="HTML")
            return
        
        ban_list = "📋 <b>АКТИВНЫЕ БАНЫ</b>\n\n"
        current_time = datetime.now(moscow_tz)
        has_active_bans = False
        
        for ban, user in results:
            # Пропускаем истекшие баны и деактивируем их
            if ban.unbanned_at <= current_time:
                ban.is_active = False
                session.commit()
                continue
            
            # Вычисляем оставшееся время
            time_left = ban.unbanned_at - current_time
            minutes_left = int(time_left.total_seconds() / 60)
            hours_left = int(minutes_left / 60)
            
            if hours_left > 24:
                days = hours_left // 24
                hours = hours_left % 24
                time_display = f"{days}д {hours}ч"
            elif hours_left > 0:
                time_display = f"{hours_left}ч {minutes_left % 60}м"
            else:
                time_display = f"{minutes_left}м"
            
            ban_list += (
                f"👤 <b>@{user.username or user.first_name}</b>\n"
                f"⏰ Осталось: {time_display}\n"
                f"📝 Причина: {ban.reason}\n"
                f"🕒 Разбан: {ban.unbanned_at.strftime('%d.%m %H:%M')}\n"
                f"👮 Забанил: ID {ban.banned_by}\n"
                f"────────────────────\n"
            )
            has_active_bans = True
        
        if not has_active_bans:
            await message.answer("📋 <b>Список банов пуст</b>\n\nНет активных банов", parse_mode="HTML")
        else:
            await message.answer(ban_list, parse_mode="HTML")

@router.message(Command("banhistory"))
async def banhistory_command(message: Message):
    """Показывает историю банов пользователя"""
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для использования этой команды")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "❌ <b>Неправильный формат команды</b>\n\n"
            "<b>Использование:</b>\n"
            "<code>/banhistory @username</code>\n\n"
            "<b>Пример:</b>\n"
            "<code>/banhistory @username</code>",
            parse_mode="HTML"
        )
        return
    
    username = parts[1].replace('@', '')
    
    with Session(engine) as session:
        user_stmt = select(UsersSchema).where(UsersSchema.username == username)
        user = session.exec(user_stmt).first()
        
        if not user:
            await message.answer(f"❌ Пользователь @{username} не найден")
            return
        
        ban_stmt = select(UserBansSchema).where(
            UserBansSchema.user_id == user.user_id
        ).order_by(UserBansSchema.banned_at.desc()).limit(10)
        
        bans = session.exec(ban_stmt).all()
        
        if not bans:
            await message.answer(f"📋 <b>История банов @{username}</b>\n\nНет записей о банах", parse_mode="HTML")
            return
        
        history = f"📋 <b>ИСТОРИЯ БАНОВ @{username}</b>\n\n"
        
        for ban in bans:
            status = "🟢 Активен" if ban.is_active else "🔴 Снят"
            duration = f"{ban.duration_minutes}м"
            if ban.duration_minutes >= 1440:
                duration = f"{ban.duration_minutes // 1440}д"
            elif ban.duration_minutes >= 60:
                duration = f"{ban.duration_minutes // 60}ч"
            
            history += (
                f"📅 {ban.banned_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"⏰ Длительность: {duration}\n"
                f"📝 Причина: {ban.reason}\n"
                f"📊 Статус: {status}\n"
            )
            
            if not ban.is_active and ban.unbanned_at_time:
                history += f"Снят: {ban.unbanned_at_time.strftime('%d.%m.%Y %H:%M')}\n"
            
            history += "────────────────────\n"
        
        await message.answer(history, parse_mode="HTML")