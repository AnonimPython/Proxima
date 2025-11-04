'''
FILE FOR WORK WITH SIMPLE COMMANDS | ФАЙЛ ДЛЯ РАБОТЫ С ПРОСТЫМИ КОМАНДАМИ
'''
#/ This file exists only for simple commands that do not require editing.
#/ Данный файл существует только для простых команд которые не требуют редактирования

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.handlers.matches import lobby_handler
#* Локализация | Localization
from app.localization import translate

#* Keyboards | Клавиатуры
from app.handlers.keyboards import get_main_keyboard, get_game_keyboard, get_start_keyboard
#* Database | База данных
from sqlmodel import Session, select
from app.database.models import (
    engine,
    UsersSchema,
    GameProfilesSchema,
    UserStatsSchema,
    MatchPlayersSchema,
    MatchesSchema,
    FoundMatchSchema,
)

router = Router()

def get_level_info(experience: int) -> tuple[int, int]:
    """
        Оределяем уровень и сколько нужно до следующего
        We determine the level and how much time is needed until the next one
    """
    if experience < 300:
        return 1, 300 - experience
    elif experience < 500:
        return 2, 500 - experience
    elif experience < 800:
        return 3, 800 - experience
    elif experience < 1200:
        return 4, 1200 - experience
    elif experience < 1500:
        return 5, 1500 - experience
    elif experience < 1900:
        return 6, 1900 - experience
    elif experience < 2300:
        return 7, 2300 - experience
    elif experience < 2600:
        return 8, 2600 - experience
    elif experience < 3000:
        return 9, 3000 - experience
    else:
        return 10, 0

@router.message(Command("help"))
async def help_handler(message: Message):
    """Обработчик команды помощи | Help command handler"""
    telegram_id = message.from_user.id
    
    await message.answer(
        f"{translate('help.title', telegram_id)}\n\n"
        
        f"{translate('help.profile_section', telegram_id)}\n"
        f"{translate('help.profile_command', telegram_id)}\n"
        f"{translate('help.stats_command', telegram_id)}\n\n"
        
        f"{translate('help.gameplay_section', telegram_id)}\n"
        f"{translate('help.lobby_command', telegram_id)}\n"
        f"{translate('help.top_command', telegram_id)}\n\n"
        
        f"{translate('help.links_section', telegram_id)}\n"
        f"{translate('help.rules_link', telegram_id)}\n"
        f"{translate('help.faq_link', telegram_id)}",
        disable_web_page_preview=True,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )

@router.message(Command("support"))
async def support_button_handler(message: Message):
    """Обработчик команды поддержки | Support command handler"""
    telegram_id = message.from_user.id
    
    await message.answer(
        f"{translate('support.title', telegram_id)}\n\n"
        f"{translate('support.contact_info', telegram_id)}\n"
        f"{translate('support.tech_support', telegram_id)}\n"
        f"{translate('support.main_admin', telegram_id)}\n\n"
        f"{translate('support.creator', telegram_id)}\n\n"
        f"{translate('support.ready_to_help', telegram_id)}",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@router.message(Command("profile"))
async def profile_handler(message: Message):
    """Обработчик команды профиля | Profile command handler"""
    telegram_id = message.from_user.id
    
    with Session(engine) as session:
        result = session.exec(
            select(
                GameProfilesSchema.nickname,
                GameProfilesSchema.league,
                GameProfilesSchema.game_id,
                GameProfilesSchema.join_date,
                GameProfilesSchema.total_games,
                GameProfilesSchema.level,
                GameProfilesSchema.experience, 
                UserStatsSchema.kills,
                UserStatsSchema.deaths,
                UserStatsSchema.kd_ratio,
                UserStatsSchema.wins,
                UserStatsSchema.losses,
                UserStatsSchema.win_rate
            )
            .join(UsersSchema, GameProfilesSchema.user_id == UsersSchema.user_id)
            .join(UserStatsSchema, UserStatsSchema.user_id == UsersSchema.user_id)
            .where(UsersSchema.telegram_id == message.from_user.id)
        ).first()
    
    if result:
        nickname, league, game_id, join_date, total_games, level, experience, kills, deaths, kd_ratio, wins, losses, win_rate = result
        
        current_level, exp_to_next = get_level_info(experience)
        
        # Формируем текст для следующего уровня | Format text for next level
        if current_level == 10:
            next_level_text = translate('profile.max_level', telegram_id)
        else:
            next_level_text = f"{exp_to_next} {translate('profile.elo', telegram_id)}"
        #todo: сделать видимый id профиля, который выдает бот при регистрации, чтобы реализовать invite в клан
        await message.answer(
            f"👤 <b>{nickname}</b>\n"
            f"🏆 <b>{translate('profile.league', telegram_id)}:</b> {league.capitalize()}\n"
            f"🔢 <b>{translate('profile.id', telegram_id)}:</b> {game_id}\n\n"
            
            f"⭐ <b>{translate('profile.level', telegram_id)}: {current_level}</b>\n"
            f"📊 {translate('profile.elo', telegram_id)}: {experience}\n"
            f"🎯 {translate('profile.to_next_level', telegram_id)} {current_level + 1 if current_level < 10 else 'MAX'}: {next_level_text}\n\n"
            
            f"⚔️ <b>{translate('profile.kd_ratio', telegram_id)}:</b> {kd_ratio:.2f}\n"
            f"🗡️ {translate('profile.kills', telegram_id)}: <b>{kills}</b>\n"
            f"💀 {translate('profile.deaths', telegram_id)}: <b>{deaths}</b>\n\n"
            
            f"🎯 <b>{translate('profile.games_played', telegram_id)}:</b> {total_games}\n"
            f"📊 <b>{translate('profile.win_rate', telegram_id)}:</b> {win_rate:.1f}%\n"
            f"✅ {translate('profile.wins', telegram_id)}: <b>{wins}</b> | ❌ {translate('profile.losses', telegram_id)}: <b>{losses}</b>\n\n"
            
            f"🏅 <b>{translate('profile.mvp', telegram_id)}:</b> 123 {translate('profile.times', telegram_id)}\n"
            f"📅 <b>{translate('profile.on_project_since', telegram_id)}:</b> {join_date.strftime('%d.%m.%Y')}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
    else:
        await message.answer(
            translate('profile.not_found', telegram_id),
            reply_markup=get_start_keyboard()
        )
        
@router.message(Command("stats"))
async def stats_handler(message: Message):
    """Обработчик команды статистики | Stats command handler"""
    telegram_id = message.from_user.id
    
    await message.answer(
        f"{translate('stats.title', telegram_id)}\n\n"
        
        f"{translate('stats.win_rate', telegram_id)}: 58%\n"
        "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▱▱▱ 58%\n"
        f"✅ {translate('stats.wins', telegram_id)}: <b>203</b> | ❌ {translate('stats.losses', telegram_id)}: <b>147</b>\n\n"
        
        f"🏆 <b>{translate('stats.best_map', telegram_id)}:</b> Sandstone\n"
        f"🎯 {translate('stats.win_rate', telegram_id)}: <b>67%</b> | ⚔️ {translate('stats.kd', telegram_id)}: <b>1.8</b>\n\n"
        
        f"📊 <b>{translate('stats.avg_per_game', telegram_id)}:</b>\n"
        f"🗡️ 18.5 {translate('stats.kills', telegram_id)} | 💀 12.8 {translate('stats.deaths', telegram_id)}\n"
        f"🎯 45.3% {translate('stats.headshots', telegram_id)} | ⚡ 2.3 {translate('stats.kdr', telegram_id)}",
        parse_mode="HTML"
    )

@router.message(Command("top"))
async def top_handler(message: Message):
    """Обработчик команды топа | Top command handler"""
    telegram_id = message.from_user.id
    
    await message.answer(
        f"{translate('top.title', telegram_id)}\n\n"
        
        f"🥇 <b>1. GodLike_SO2</b>\n"
        f"   ⭐ {translate('top.elo', telegram_id)}: <b>2450</b> | 📊 {translate('top.win_rate', telegram_id)}: <b>72%</b>\n"
        f"   🎯 2450 {translate('top.kills', telegram_id)} | 🏅 47 {translate('top.mvp', telegram_id)}\n\n"
        
        f"🥈 <b>2. ProPlayer_Elite</b>\n"  
        f"   ⭐ {translate('top.elo', telegram_id)}: <b>2380</b> | 📊 {translate('top.win_rate', telegram_id)}: <b>68%</b>\n"
        f"   🎯 2180 {translate('top.kills', telegram_id)} | 🏅 42 {translate('top.mvp', telegram_id)}\n\n"
        
        f"🥉 <b>3. KillerInstinct</b>\n"
        f"   ⭐ {translate('top.elo', telegram_id)}: <b>2340</b> | 📊 {translate('top.win_rate', telegram_id)}: <b>65%</b>\n"
        f"   🎯 1950 {translate('top.kills', telegram_id)} | 🏅 38 {translate('top.mvp', telegram_id)}\n\n"
        
        f"▫️ <b>245. ProPlayer_SO2</b>\n"
        f"   ⭐ {translate('top.elo', telegram_id)}: <b>1850</b> | 📊 {translate('top.win_rate', telegram_id)}: <b>58%</b>\n"
        f"   🎯 1450 {translate('top.kills', telegram_id)} | 🏅 12 {translate('top.mvp', telegram_id)}",
        parse_mode="HTML"
    )
    
@router.message(Command("history"))
async def history_handler(message: Message):
    """Обработчик команды истории | History command handler"""
    telegram_id = message.from_user.id
    
    await message.answer(
        f"{translate('history.title', telegram_id)}\n\n"
        
        f"🟢 <b>{translate('history.win', telegram_id)}</b> | 🗺️ Sandstone\n"
        f"⚔️ {translate('history.kd', telegram_id)}: <b>1.8</b> | 🎯 18/10\n" 
        f"⭐ +15 {translate('history.elo', telegram_id)} | 📅 15.12.2023 20:45\n\n"
        
        f"🔴 <b>{translate('history.loss', telegram_id)}</b> | 🗺️ Downtown\n"
        f"⚔️ {translate('history.kd', telegram_id)}: <b>0.9</b> | 🎯 9/10\n"
        f"⭐ -12 {translate('history.elo', telegram_id)} | 📅 14.12.2023 19:30\n\n"
        
        f"🟢 <b>{translate('history.win', telegram_id)}</b> | 🗺️ Sandstone\n"
        f"⚔️ {translate('history.kd', telegram_id)}: <b>2.1</b> | 🎯 21/10\n"
        f"⭐ +18 {translate('history.elo', telegram_id)} | 📅 13.12.2023 22:15\n\n"
        
        f"🔵 <b>{translate('history.draw', telegram_id)}</b> | 🗺️ Factory\n"
        f"⚔️ {translate('history.kd', telegram_id)}: <b>1.2</b> | 🎯 12/10\n"
        f"⭐ +0 {translate('history.elo', telegram_id)} | 📅 12.12.2023 18:20",
        parse_mode="HTML"
    )

# Обработчики кнопок | Button handlers
@router.message(F.text.in_(["📊 Мой профиль", "📊 Profile"]))
async def profile_button_handler(message: Message):
    """Обработчик кнопки профиля | Profile button handler"""
    await profile_handler(message)

@router.message(F.text.in_(["🎮 Найти лобби", "🎮 Find lobby"]))
async def lobby_button_handler(message: Message):
    """Обработчик кнопки поиска лобби | Lobby search button handler"""
    await lobby_handler(message)

@router.message(F.text.in_(["📈 Статистика", "📈 Stats"]))
async def stats_button_handler(message: Message):
    """Обработчик кнопки статистики | Stats button handler"""
    await stats_handler(message)

@router.message(F.text.in_(["🏆 Рейтинг", "🏆 Raiting"]))
async def top_button_handler(message: Message):
    """Обработчик кнопки рейтинга | Top button handler"""
    await top_handler(message)

@router.message(F.text.in_([ "📅 История", "📅 History"]))
async def history_button_handler(message: Message):
    """Обработчик кнопки истории | History button handler"""
    await history_handler(message)

@router.message(F.text.in_(["❓ Помощь", "❓ Help"]))
async def help_button_handler(message: Message):
    """Обработчик кнопки помощи | Help button handler"""
    await support_button_handler(message)
    
@router.message(F.text.in_(["📞 Поддержка", "📞 Support"]))
async def support_button_handler(message: Message):
    """Обработчик кнопки поддержка | Support button handler"""
    await support_button_handler(message)