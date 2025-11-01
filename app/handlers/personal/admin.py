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
from localization import translate

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
            
            # Отправляем сообщение забаненному игроку | Send message to banned player
            try:
                if minutes > 0:
                    ban_until = unbanned_at.strftime('%d.%m.%Y %H:%M')
                    ban_message = translate(
                        'user_banned', 
                        user_id, 
                        minutes=minutes, 
                        reason=reason, 
                        ban_until=ban_until
                    )
                else:
                    ban_message = translate('user_permanently_banned', user_id, reason=reason)
                await bot.send_message(chat_id=user_id, text=ban_message, parse_mode="HTML")
            except:
                pass  # Игрок заблокировал бота | User blocked the bot

#! TEST
@router.message(Command("make_me_admin"))
async def make_me_admin(message: Message):
    """
        Команда для выдачи прав администратора
        Command to grant administrator rights
    """
    admin_id = os.getenv('ADMIN_TELEGRAM_ID')
    
    if str(message.from_user.id) != admin_id:
        await message.answer(translate('admin.make_admin.no_rights', message.from_user.id))
        return
    
    with Session(engine) as session:
        user_stmt = select(UsersSchema).where(UsersSchema.telegram_id == message.from_user.id)
        user = session.exec(user_stmt).first()
        
        if user:
            user.role = "admin"
            session.commit()
            await message.answer(translate('admin.make_admin.success', message.from_user.id), parse_mode="HTML")
        else:
            await message.answer(translate('admin.make_admin.user_not_found', message.from_user.id))

@router.message(Command("make_moderator"))
async def make_moderator_command(message: Message):
    """
        Сделать пользователя модератором
        Make user a moderator
    """
    
    if not is_admin(message.from_user.id):
        await message.answer(translate('admin.only_admins', message.from_user.id))
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(translate('admin.make_moderator.wrong_format', message.from_user.id), parse_mode="HTML")
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
    
    admin_username = message.from_user.username or translate('admin.default_name', message.from_user.id)
    
    await message.answer(
        translate(
            'admin.make_moderator.success',
            message.from_user.id,
            identifier=identifier,
            admin_username=admin_username
        ),
        parse_mode="HTML"
    )

@router.message(Command("permaban"))
async def permaban_command(message: Message):
    """Перманентный бан пользователя | Permanent user ban"""
    
    if not is_admin(message.from_user.id):
        await message.answer(translate('admin.no_access', message.from_user.id))
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(translate('admin.permaban.wrong_format', message.from_user.id), parse_mode="HTML")
        return
    
    identifier = parts[1]
    reason = ' '.join(parts[2:])
    
    user, error = find_user_by_identifier(identifier)
    if error:
        await message.answer(error)
        return
    
    # Проверяем, может ли админ забанить этого пользователя | Check if admin can ban this user
    if not can_ban_user(message.from_user.id, user):
        await message.answer(translate('admin.permaban.cannot_ban', message.from_user.id))
        return
    
    # Пермабан | Permanent ban
    await ban_user(
        message.bot,
        user.telegram_id,
        message.from_user.id,
        "permanent_ban",
        reason,
        0
    )
    
    admin_username = message.from_user.username or translate('admin.default_name', message.from_user.id)
    
    await message.answer(
        translate(
            'admin.permaban.success',
            message.from_user.id,
            identifier=identifier,
            reason=reason,
            admin_username=admin_username
        ),
        parse_mode="HTML"
    )

@router.message(Command("admin_ban"))
async def admin_ban_command(message: Message):
    """Временный бан (админ) | Temporary ban (admin)"""
    
    if not is_admin(message.from_user.id):
        await message.answer(translate('admin.no_access', message.from_user.id))
        return
    
    parts = message.text.split()
    if len(parts) < 4:
        await message.answer(translate('admin.admin_ban.wrong_format', message.from_user.id), parse_mode="HTML")
        return
    
    identifier = parts[1]
    time_string = parts[2].lower()
    reason = ' '.join(parts[3:])
    
    time_match = re.match(r'^(\d+)([mhd])$', time_string)
    if not time_match:
        await message.answer(translate('admin.admin_ban.wrong_time_format', message.from_user.id), parse_mode="HTML")
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
    
    # Проверяем, может ли админ забанить этого пользователя | Check if admin can ban this user
    if not can_ban_user(message.from_user.id, user):
        await message.answer(translate('admin.permaban.cannot_ban', message.from_user.id))
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
    admin_username = message.from_user.username or translate('admin.default_name', message.from_user.id)
    
    await message.answer(
        translate(
            'admin.admin_ban.success',
            message.from_user.id,
            identifier=identifier,
            time_display=time_display,
            reason=reason,
            admin_username=admin_username,
            ban_until=ban_until.strftime('%d.%m.%Y %H:%M')
        ),
        parse_mode="HTML"
    )

# Остальные команды (unban, banlist, banhistory) остаются без изменений
# Other commands (unban, banlist, banhistory) remain unchanged
@router.message(Command("unban"))
async def unban_command(message: Message):
    """Разбан пользователя | Unban user"""
    
    if not is_admin(message.from_user.id):
        await message.answer(translate('admin.no_access', message.from_user.id))
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(translate('admin.unban.wrong_format', message.from_user.id), parse_mode="HTML")
        return
    
    username = parts[1].replace('@', '')
    
    with Session(engine) as session:
        user = session.exec(select(UsersSchema).where(UsersSchema.username == username)).first()
        if not user:
            await message.answer(translate('admin.unban.user_not_found', message.from_user.id, username=username))
            return
        
        unbanned_by_user = session.exec(select(UsersSchema).where(UsersSchema.telegram_id == message.from_user.id)).first()
        active_bans = session.exec(select(UserBansSchema).where(
            UserBansSchema.user_id == user.user_id,
            UserBansSchema.is_active == True
        )).all()
        
        if not active_bans:
            await message.answer(translate('admin.unban.no_bans', message.from_user.id, username=username))
            return
        
        for ban in active_bans:
            ban.is_active = False
            if unbanned_by_user:
                ban.unbanned_by = unbanned_by_user.user_id
            ban.unbanned_at_time = datetime.now(moscow_tz)
        
        session.commit()
        
        admin_username = message.from_user.username or translate('admin.default_name', message.from_user.id)
        current_time = datetime.now(moscow_tz).strftime('%d.%m.%Y %H:%M')
        
        await message.answer(
            translate(
                'admin.unban.success',
                message.from_user.id,
                username=username,
                admin_username=admin_username,
                time=current_time
            ),
            parse_mode="HTML"
        )
        
@router.message(Command("banlist"))
async def banlist_command(message: Message):
    """Показать список активных банов | Show active bans list"""
    
    if not is_admin(message.from_user.id):
        await message.answer(translate('admin.no_access', message.from_user.id))
        return
    
    with Session(engine) as session:
        # Получаем активные баны с информацией о пользователях | Get active bans with user info
        active_bans = session.exec(
            select(UserBansSchema, UsersSchema)
            .join(UsersSchema, UserBansSchema.user_id == UsersSchema.user_id)
            .where(UserBansSchema.is_active == True)
        ).all()
        
        if not active_bans:
            await message.answer("📋 <b>Список активных банов пуст</b>\n\n", parse_mode="HTML")
            return
        
        ban_list_text = "📋 <b>СПИСОК АКТИВНЫХ БАНОВ</b>\n\n"
        
        for ban, user in active_bans:
            ban_time = ban.banned_at.strftime('%d.%m.%Y %H:%M')
            ban_list_text += f"👤 {user.username or user.telegram_id}\n"
            ban_list_text += f"⏰ {ban_time} | {ban.ban_type}\n"
            ban_list_text += f"📝 {ban.reason}\n"
            if ban.duration_minutes > 0:
                unban_time = ban.unbanned_at.strftime('%d.%m.%Y %H:%M')
                ban_list_text += f"🕒 До: {unban_time}\n"
            else:
                ban_list_text += f"🕒 Пермабан | Permanent\n"
            ban_list_text += "─" * 30 + "\n"
        
        await message.answer(ban_list_text, parse_mode="HTML")

@router.message(Command("banhistory"))
async def banhistory_command(message: Message):
    """Показать историю банов пользователя | Show user ban history"""
    
    if not is_admin(message.from_user.id):
        await message.answer(translate('admin.no_access', message.from_user.id))
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "❗️ <b>Неправильный формат</b> ❗️\nWrong format\n\n"
            "<b>Использование | Usage:</b>\n"
            "<code>/banhistory @username</code>\n"
            "<code>/banhistory 123456789</code>",
            parse_mode="HTML"
        )
        return
    
    identifier = parts[1]
    
    user, error = find_user_by_identifier(identifier)
    if error:
        await message.answer(error)
        return
    
    with Session(engine) as session:
        # Получаем всю историю банов пользователя | Get all user ban history
        ban_history = session.exec(
            select(UserBansSchema)
            .where(UserBansSchema.user_id == user.user_id)
            .order_by(UserBansSchema.banned_at.desc())
        ).all()
        
        if not ban_history:
            await message.answer(
                f"📋 <b>История банов пользователя {identifier} пуста</b>\n\n"
                f"Ban history for user {identifier} is empty",
                parse_mode="HTML"
            )
            return
        
        history_text = f"📋 <b>ИСТОРИЯ БАНОВ | BAN HISTORY</b>\n👤 <b>Пользователь | User:</b> {identifier}\n\n"
        
        for i, ban in enumerate(ban_history[:10], 1):  # Ограничиваем 10 последними банами
            ban_time = ban.banned_at.strftime('%d.%m.%Y %H:%M')
            status = "🔴 АКТИВЕН | ACTIVE" if ban.is_active else "✅ СНЯТ | REMOVED"
            
            history_text += f"{i}. {ban.ban_type}\n"
            history_text += f"   ⏰ {ban_time} | {status}\n"
            history_text += f"   📝 {ban.reason}\n"
            if ban.unbanned_at_time:
                unban_time = ban.unbanned_at_time.strftime('%d.%m.%Y %H:%M')
                history_text += f"   ✅ Снят: {unban_time}\n"
            history_text += "   " + "─" * 20 + "\n"
        
        if len(ban_history) > 10:
            history_text += f"\n... и еще {len(ban_history) - 10} записей | and {len(ban_history) - 10} more records"
        
        await message.answer(history_text, parse_mode="HTML")