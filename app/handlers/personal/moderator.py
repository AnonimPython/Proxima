'''
MODERATOR COMMANDS - FOR MODERATORS
'''

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.database.models import engine, UsersSchema, UserBansSchema
from zoneinfo import ZoneInfo
import re

from app.utils.access_checker import is_moderator, find_user_by_identifier, can_ban_user
from app.localization import translate

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
        Bans the user and sends a notification via PM.
    """
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
                ban_message = translate(
                    'user_banned', 
                    user_id, 
                    minutes=minutes, 
                    reason=reason, 
                    ban_until=ban_until
                )
                await bot.send_message(chat_id=user_id, text=ban_message, parse_mode="HTML")
            except:
                pass

@router.message(Command("mod_ban"))
async def mod_ban_command(message: Message):
    """
        Временный бан (модератор) - максимум 7 дней
        Temporary ban (moderator) - max 7 days    
    """
    
    if not is_moderator(message.from_user.id):
        await message.answer(translate('moderator.no_access', message.from_user.id))
        return
    
    parts = message.text.split()
    if len(parts) < 4:
        await message.answer(translate('moderator.ban.wrong_format', message.from_user.id), parse_mode="HTML")
        return
    
    identifier = parts[1]
    time_string = parts[2].lower()
    reason = ' '.join(parts[3:])
    
    time_match = re.match(r'^(\d+)([mhd])$', time_string)
    if not time_match:
        await message.answer(translate('moderator.ban.wrong_time_format', message.from_user.id), parse_mode="HTML")
        return
    
    amount = int(time_match.group(1))
    unit = time_match.group(2)
    
    if unit == 'm':
        minutes = amount
        time_display = f"{amount}мин"
        max_minutes = 1440  # 24 часа | 24 hour
    elif unit == 'h':
        minutes = amount * 60
        time_display = f"{amount}ч"
        max_minutes = 10080  # 7 дней | 7 days
    elif unit == 'd':
        minutes = amount * 24 * 60
        time_display = f"{amount}дн"
        max_minutes = 10080  # 7 дней | 7 days
    
    # Проверяем лимиты модератора | Checking moderator limits
    if minutes > max_minutes:
        await message.answer(translate('moderator.ban.time_limit_exceeded', message.from_user.id, max_minutes=max_minutes))
        return
    
    user, error = find_user_by_identifier(identifier)
    if error:
        await message.answer(error)
        return
    
    # Проверяем, может ли модератор забанить этого пользователя
    # Check if the moderator can ban this user
    if not can_ban_user(message.from_user.id, user):
        await message.answer(translate('moderator.ban.cannot_ban', message.from_user.id))
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
    moderator_username = message.from_user.username or translate('moderator.default_name', message.from_user.id)
    
    await message.answer(
        translate(
            'moderator.ban.success', 
            message.from_user.id,
            identifier=identifier,
            time_display=time_display,
            reason=reason,
            moderator_username=moderator_username,
            ban_until=ban_until.strftime('%d.%m.%Y %H:%M')
        ),
        parse_mode="HTML"
    )

@router.message(Command("mod_warn"))
async def mod_warn_command(message: Message):
    """Предупреждение пользователю"""
    
    if not is_moderator(message.from_user.id):
        await message.answer(translate('moderator.no_access', message.from_user.id))
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(translate('moderator.warn.wrong_format', message.from_user.id), parse_mode="HTML")
        return
    
    identifier = parts[1]
    reason = ' '.join(parts[2:])
    
    user, error = find_user_by_identifier(identifier)
    if error:
        await message.answer(error)
        return
    
    # Проверяем, может ли модератор выдать предупреждение
    # Check if a moderator can issue a warning
    if not can_ban_user(message.from_user.id, user):
        await message.answer(translate('moderator.warn.cannot_warn', message.from_user.id))
        return
    
    # Создаем запись предупреждения в БД | create a warning message to DB
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
                is_active=False  # Предупреждение не активно как бан | send user a warning
            )
            session.add(new_warn)
            session.commit()
    
    # Отправляем уведомление пользователю в ЛС | Sent notification to user
    try:
        moderator_username = message.from_user.username or translate('moderator.default_name', message.from_user.id)
        current_time = datetime.now(moscow_tz).strftime('%d.%m.%Y %H:%M')
        
        warn_message = translate(
            'moderator.warn.user_message',
            user.telegram_id,
            reason=reason,
            moderator_username=moderator_username,
            time=current_time
        )
        await message.bot.send_message(
            chat_id=user.telegram_id, 
            text=warn_message, 
            parse_mode="HTML"
        )
        
        # Подтверждение модератору | Confirm to moderator
        await message.answer(
            translate(
                'moderator.warn.success',
                message.from_user.id,
                identifier=identifier,
                reason=reason,
                moderator_username=moderator_username
            ),
            parse_mode="HTML"
        )
        
    except Exception as e:
        # Если не удалось отправить сообщение в ЛС | If massage dont send to user
        await message.answer(
            translate(
                'moderator.warn.success',
                message.from_user.id,
                identifier=identifier,
                reason=reason,
                moderator_username=moderator_username
            ) + "\n\n" + translate('moderator.warn.failed_dm', message.from_user.id),
            parse_mode="HTML"
        )

@router.message(Command("mod_unban"))
async def mod_unban_command(message: Message):
    """
        Разбан пользователя (только свои баны)
        Unban users (only my moderator who ban)
    """
    
    if not is_moderator(message.from_user.id):
        await message.answer(translate('moderator.no_access', message.from_user.id))
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(translate('moderator.unban.wrong_format', message.from_user.id), parse_mode="HTML")
        return
    
    identifier = parts[1]
    
    with Session(engine) as session:
        user = session.exec(select(UsersSchema).where(UsersSchema.username == identifier)).first()
        if not user:
            # Пробуем найти по ID
            user = session.exec(select(UsersSchema).where(UsersSchema.telegram_id == int(identifier))).first()
            if not user:
                await message.answer(translate('moderator.unban.user_not_found', message.from_user.id, identifier=identifier))
                return
        
        # Находим модератора | Find a moderator
        moderator = session.exec(select(UsersSchema).where(UsersSchema.telegram_id == message.from_user.id)).first()
        
        # Находим только те баны, которые выдал этот модератор
        # We find only those bans issued by this moderator
        active_bans = session.exec(select(UserBansSchema).where(
            UserBansSchema.user_id == user.user_id,
            UserBansSchema.is_active == True,
            UserBansSchema.banned_by == moderator.user_id
        )).all()
        
        if not active_bans:
            await message.answer(translate('moderator.unban.no_bans', message.from_user.id, identifier=identifier))
            return
        
        for ban in active_bans:
            ban.is_active = False
            ban.unbanned_by = moderator.user_id
            ban.unbanned_at_time = datetime.now(moscow_tz)
        
        session.commit()
        
        moderator_username = message.from_user.username or translate('moderator.default_name', message.from_user.id)
        current_time = datetime.now(moscow_tz).strftime('%d.%m.%Y %H:%M')
        
        await message.answer(
            translate(
                'moderator.unban.success',
                message.from_user.id,
                identifier=identifier,
                moderator_username=moderator_username,
                time=current_time
            ),
            parse_mode="HTML"
        )