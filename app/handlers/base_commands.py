'''
FILE FOR WORK WITH SIMPLE COMMANDS | ФАЙЛ ДЛЯ РАБОТЫ С ПРОСТЫМИ КОМАНДАМИ
'''
#/ This file exists only for simple commands that do not require editing.
#/ Данный файл существует только для простых команд которые не требуют редактирования

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from .matches import lobby_handler
#* Локализация | Localization
from localization import t

#* Keyboards | Клавиатуры
from .keyboards import get_main_keyboard, get_game_keyboard, get_start_keyboard
#* Database | База данных
from sqlmodel import Session, select
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

# Простая функция для получения языка | Simple function to get language
def get_lang(user_id: int) -> str:
    return 'ru'  # Пока всегда русский | For now always Russian

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
    lang = get_lang(message.from_user.id)
    
    await message.answer(
        f"{t('help.title', lang)}\n\n"
        
        f"{t('help.profile_section', lang)}\n"
        f"{t('help.profile_command', lang)}\n"
        f"{t('help.stats_command', lang)}\n\n"
        
        f"{t('help.gameplay_section', lang)}\n"
        f"{t('help.lobby_command', lang)}\n"
        f"{t('help.top_command', lang)}\n\n"
        
        f"{t('help.links_section', lang)}\n"
        f"{t('help.rules_link', lang)}\n"
        f"{t('help.faq_link', lang)}",
        disable_web_page_preview=True,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )

@router.message(Command("support"))
async def support_button_handler(message: Message):
    """Обработчик команды поддержки | Support command handler"""
    lang = get_lang(message.from_user.id)
    
    await message.answer(
        f"{t('support.title', lang)}\n\n"
        f"{t('support.contact_info', lang)}\n"
        f"{t('support.tech_support', lang)}\n"
        f"{t('support.main_admin', lang)}\n\n"
        f"{t('support.creator', lang)}\n\n"
        f"{t('support.ready_to_help', lang)}",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@router.message(Command("profile"))
async def profile_handler(message: Message):
    """Обработчик команды профиля | Profile command handler"""
    lang = get_lang(message.from_user.id)
    
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
            next_level_text = t('profile.max_level', lang)
        else:
            next_level_text = f"{exp_to_next} {t('profile.elo', lang)}"
        
        await message.answer(
            f"👤 <b>{nickname}</b>\n"
            f"🏆 <b>{t('profile.league', lang)}:</b> {league.capitalize()}\n"
            f"🔢 <b>{t('profile.id', lang)}:</b> {game_id}\n\n"
            
            f"⭐ <b>{t('profile.level', lang)}: {current_level}</b>\n"
            f"📊 {t('profile.elo', lang)}: {experience}\n"
            f"🎯 {t('profile.to_next_level', lang)} {current_level + 1 if current_level < 10 else 'MAX'}: {next_level_text}\n\n"
            
            f"⚔️ <b>{t('profile.kd_ratio', lang)}:</b> {kd_ratio:.2f}\n"
            f"🗡️ {t('profile.kills', lang)}: <b>{kills}</b>\n"
            f"💀 {t('profile.deaths', lang)}: <b>{deaths}</b>\n\n"
            
            f"🎯 <b>{t('profile.games_played', lang)}:</b> {total_games}\n"
            f"📊 <b>{t('profile.win_rate', lang)}:</b> {win_rate:.1f}%\n"
            f"✅ {t('profile.wins', lang)}: <b>{wins}</b> | ❌ {t('profile.losses', lang)}: <b>{losses}</b>\n\n"
            
            f"🏅 <b>{t('profile.mvp', lang)}:</b> 123 {t('profile.times', lang)}\n"
            f"📅 <b>{t('profile.on_project_since', lang)}:</b> {join_date.strftime('%d.%m.%Y')}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
    else:
        await message.answer(
            t('profile.not_found', lang),
            reply_markup=get_start_keyboard()
        )
        
@router.message(Command("stats"))
async def stats_handler(message: Message):
    """Обработчик команды статистики | Stats command handler"""
    lang = get_lang(message.from_user.id)
    
    await message.answer(
        f"{t('stats.title', lang)}\n\n"
        
        f"{t('stats.win_rate', lang)}: 58%\n"
        "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▱▱▱ 58%\n"
        f"✅ {t('stats.wins', lang)}: <b>203</b> | ❌ {t('stats.losses', lang)}: <b>147</b>\n\n"
        
        f"🏆 <b>{t('stats.best_map', lang)}:</b> Sandstone\n"
        f"🎯 {t('stats.win_rate', lang)}: <b>67%</b> | ⚔️ {t('stats.kd', lang)}: <b>1.8</b>\n\n"
        
        f"📊 <b>{t('stats.avg_per_game', lang)}:</b>\n"
        f"🗡️ 18.5 {t('stats.kills', lang)} | 💀 12.8 {t('stats.deaths', lang)}\n"
        f"🎯 45.3% {t('stats.headshots', lang)} | ⚡ 2.3 {t('stats.kdr', lang)}",
        parse_mode="HTML"
    )

@router.message(Command("top"))
async def top_handler(message: Message):
    """Обработчик команды топа | Top command handler"""
    lang = get_lang(message.from_user.id)
    
    await message.answer(
        f"{t('top.title', lang)}\n\n"
        
        f"🥇 <b>1. GodLike_SO2</b>\n"
        f"   ⭐ {t('top.elo', lang)}: <b>2450</b> | 📊 {t('top.win_rate', lang)}: <b>72%</b>\n"
        f"   🎯 2450 {t('top.kills', lang)} | 🏅 47 {t('top.mvp', lang)}\n\n"
        
        f"🥈 <b>2. ProPlayer_Elite</b>\n"  
        f"   ⭐ {t('top.elo', lang)}: <b>2380</b> | 📊 {t('top.win_rate', lang)}: <b>68%</b>\n"
        f"   🎯 2180 {t('top.kills', lang)} | 🏅 42 {t('top.mvp', lang)}\n\n"
        
        f"🥉 <b>3. KillerInstinct</b>\n"
        f"   ⭐ {t('top.elo', lang)}: <b>2340</b> | 📊 {t('top.win_rate', lang)}: <b>65%</b>\n"
        f"   🎯 1950 {t('top.kills', lang)} | 🏅 38 {t('top.mvp', lang)}\n\n"
        
        f"▫️ <b>245. ProPlayer_SO2</b>\n"
        f"   ⭐ {t('top.elo', lang)}: <b>1850</b> | 📊 {t('top.win_rate', lang)}: <b>58%</b>\n"
        f"   🎯 1450 {t('top.kills', lang)} | 🏅 12 {t('top.mvp', lang)}",
        parse_mode="HTML"
    )
    
@router.message(Command("history"))
async def history_handler(message: Message):
    """Обработчик команды истории | History command handler"""
    lang = get_lang(message.from_user.id)
    
    await message.answer(
        f"{t('history.title', lang)}\n\n"
        
        f"🟢 <b>{t('history.win', lang)}</b> | 🗺️ Sandstone\n"
        f"⚔️ {t('history.kd', lang)}: <b>1.8</b> | 🎯 18/10\n" 
        f"⭐ +15 {t('history.elo', lang)} | 📅 15.12.2023 20:45\n\n"
        
        f"🔴 <b>{t('history.loss', lang)}</b> | 🗺️ Downtown\n"
        f"⚔️ {t('history.kd', lang)}: <b>0.9</b> | 🎯 9/10\n"
        f"⭐ -12 {t('history.elo', lang)} | 📅 14.12.2023 19:30\n\n"
        
        f"🟢 <b>{t('history.win', lang)}</b> | 🗺️ Sandstone\n"
        f"⚔️ {t('history.kd', lang)}: <b>2.1</b> | 🎯 21/10\n"
        f"⭐ +18 {t('history.elo', lang)} | 📅 13.12.2023 22:15\n\n"
        
        f"🔵 <b>{t('history.draw', lang)}</b> | 🗺️ Factory\n"
        f"⚔️ {t('history.kd', lang)}: <b>1.2</b> | 🎯 12/10\n"
        f"⭐ +0 {t('history.elo', lang)} | 📅 12.12.2023 18:20",
        parse_mode="HTML"
    )

# Обработчики кнопок | Button handlers
@router.message(F.text == "📊 Мой профиль")
async def profile_button_handler(message: Message):
    """Обработчик кнопки профиля | Profile button handler"""
    await profile_handler(message)

@router.message(F.text == "🎮 Найти лобби")
async def lobby_button_handler(message: Message):
    """Обработчик кнопки поиска лобби | Lobby search button handler"""
    await lobby_handler(message)

@router.message(F.text == "📈 Статистика")
async def stats_button_handler(message: Message):
    """Обработчик кнопки статистики | Stats button handler"""
    await stats_handler(message)

@router.message(F.text == "🏆 Рейтинг")
async def top_button_handler(message: Message):
    """Обработчик кнопки рейтинга | Top button handler"""
    await top_handler(message)

@router.message(F.text == "📅 История")
async def history_button_handler(message: Message):
    """Обработчик кнопки истории | History button handler"""
    await history_handler(message)

@router.message(F.text == "❓ Помощь")
async def help_button_handler(message: Message):
    """Обработчик кнопки помощи | Help button handler"""
    await support_button_handler(message)