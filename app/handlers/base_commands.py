'''
FILE FOR WORK WITH SIMPLE COMMANDS
'''
#/ This file exists only for simple commands that do not require editing.
#/ Данный файл существует только для простых команд которые не требуют редактирования

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from .matches import lobby_handler
#* Keyboards
from .keyboards import get_main_keyboard, get_game_keyboard, get_start_keyboard
#* Database
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

# def get_user_data(telegram_id: int):
#     with Session(engine) as session:
#         user_league = session.exec(
#             select(GameProfilesSchema.league)
#             .join(UsersSchema, GameProfilesSchema.user_id == UsersSchema.user_id)
#             .where(UsersSchema.telegram_id == telegram_id)
#         ).first()
#     return user_league

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

# def create_level_progress_bar(percentage: float, length: int = 20) -> str:
#     """Создает прогресс-бар для уровня"""
#     filled = int((percentage / 100) * length)
#     return '▰' * filled + '▱' * (length - filled)



@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "🎮 <b>КОМАНДЫ БОТА</b>\n\n"
        
        "📊 <b>Профиль</b>\n"
        "• /profile - Ваша статистика\n"
        "• /stats - Детальная статистика\n\n"
        
        "🎯 <b>Игровой процесс</b>\n" 
        "• /lobby - Поиск игры\n"
        "• /top - Рейтинг игроков\n\n"
        
        "🔗 <b>Ссылки</b>\n"
        "• <a href='http://telegram.org/'>Правила</a>\n"
        "• <a href='http://telegram.org/'>FAQ</a>",
        disable_web_page_preview=True,
        reply_markup=get_main_keyboard(),
    )
@router.message(Command("support"))
async def support_button_handler(message: Message):
    await message.answer(
        "📞 <b>Поддержка</b>\n\n"
        #TODO: take info from CONFIG
        "По вопросам работы бота обращайтесь:\n"
        "• @username - Техническая поддержка ⭐\n"
        "• @username - Главный админ 🤩\n\n"
        "• @username - Создатель 👑\n\n"
        "Мы всегда готовы помочь 😃!",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@router.message(Command("profile"))
async def profile_handler(message: Message):
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
        
        # Формируем текст для следующего уровня
        # Write a new messasge about new lvl
        if current_level == 10:
            next_level_text = "MAХ LVL"
        else:
            next_level_text = f"{exp_to_next} ELO"
        
        await message.answer(
            f"👤 <b>{nickname}</b>\n"
            f"🏆 <b>Лига:</b> {league.capitalize()}\n"
            f"🔢 <b>ID:</b> {game_id}\n\n"
            
            f"⭐ <b>Уровень: {current_level}</b>\n"
            f"📊 ELO: {experience}\n"
            f"🎯 До уровня {current_level + 1 if current_level < 10 else 'MAX'}: {next_level_text}\n\n"
            
            f"⚔️ <b>KD Ratio:</b> {kd_ratio:.2f}\n"
            f"🗡️ Убийств: <b>{kills}</b>\n"
            f"💀 Смертей: <b>{deaths}</b>\n\n"
            
            f"🎯 <b>Игр сыграно:</b> {total_games}\n"
            f"📊 <b>Win Rate:</b> {win_rate:.1f}%\n"
            f"✅ Побед: <b>{wins}</b> | ❌ Поражений: <b>{losses}</b>\n\n"
            
            f"🏅 <b>MVP:</b> 123 раз\n"
            f"📅 <b>На проекте с:</b> {join_date.strftime('%d.%m.%Y')}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
    else:
        await message.answer(
            "❌ Профиль не найден. Введите команду /register для регистрации",
            reply_markup=get_start_keyboard()
        )
        
        
@router.message(Command("stats"))
async def stats_handler(message: Message):
    await message.answer(
        "📈 <b>Детальная статистика</b>\n\n"
        
        "🎯 <b>Win Rate:</b> 58%\n"
        "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▱▱▱ 58%\n"
        "✅ Побед: <b>203</b> | ❌ Поражений: <b>147</b>\n\n"
        
        "🏆 <b>Лучшая карта:</b> Sandstone\n"
        "🎯 Win Rate: <b>67%</b> | ⚔️ KD: <b>1.8</b>\n\n"
        
        "📊 <b>Средние показатели за игру:</b>\n"
        "🗡️ 18.5 убийств | 💀 12.8 смертей\n"
        "🎯 45.3% хедшотов | ⚡ 2.3 KDR",
        parse_mode="HTML"
    )
    
@router.message(Command("top"))
async def top_handler(message: Message):
    await message.answer(
        "🏆 <b>ГЛОБАЛЬНЫЙ РЕЙТИНГ</b>\n\n"
        
        "🥇 <b>1. GodLike_SO2</b>\n"
        "   ⭐ ELO: <b>2450</b> | 📊 Win Rate: <b>72%</b>\n"
        "   🎯 2450 убийств | 🏅 47 MVP\n\n"
        
        "🥈 <b>2. ProPlayer_Elite</b>\n"  
        "   ⭐ ELO: <b>2380</b> | 📊 Win Rate: <b>68%</b>\n"
        "   🎯 2180 убийств | 🏅 42 MVP\n\n"
        
        "🥉 <b>3. KillerInstinct</b>\n"
        "   ⭐ ELO: <b>2340</b> | 📊 Win Rate: <b>65%</b>\n"
        "   🎯 1950 убийств | 🏅 38 MVP\n\n"
        
        "▫️ <b>245. ProPlayer_SO2</b>\n"
        "   ⭐ ELO: <b>1850</b> | 📊 Win Rate: <b>58%</b>\n"
        "   🎯 1450 убийств | 🏅 12 MVP",
        parse_mode="HTML"
    )
    
@router.message(Command("history"))
async def history_handler(message: Message):
    await message.answer(
        "📅 <b>ИСТОРИЯ МАТЧЕЙ</b>\n\n"
        
        "🟢 <b>Победа</b> | 🗺️ Sandstone\n"
        "⚔️ K/D: <b>1.8</b> | 🎯 18/10\n" 
        "⭐ +15 ELO | 📅 15.12.2023 20:45\n\n"
        
        "🔴 <b>Поражение</b> | 🗺️ Downtown\n"
        "⚔️ K/D: <b>0.9</b> | 🎯 9/10\n"
        "⭐ -12 ELO | 📅 14.12.2023 19:30\n\n"
        
        "🟢 <b>Победа</b> | 🗺️ Sandstone\n"
        "⚔️ K/D: <b>2.1</b> | 🎯 21/10\n"
        "⭐ +18 ELO | 📅 13.12.2023 22:15\n\n"
        
        "🔵 <b>Ничья</b> | 🗺️ Factory\n"
        "⚔️ K/D: <b>1.2</b> | 🎯 12/10\n"
        "⭐ +0 ELO | 📅 12.12.2023 18:20",
        parse_mode="HTML"
    )

@router.message(F.text == "📊 Мой профиль")
async def profile_button_handler(message: Message):
    await profile_handler(message)

# @router.message(F.text == "🎮 Найти лобби")
# async def lobby_button_handler(message: Message):
#     await message.answer(
#         "🎯 <b>Поиск лобби</b>\n\n"
#         "Используйте команду /lobby для поиска игры\n",
#         parse_mode="HTML",
#         reply_markup=get_main_keyboard()
#     )
    
@router.message(F.text == "🎮 Найти лобби")
async def lobby_button_handler(message: Message):
    await lobby_handler(message)

@router.message(F.text == "📈 Статистика")
async def stats_button_handler(message: Message):
    await stats_handler(message)

@router.message(F.text == "🏆 Рейтинг")
async def top_button_handler(message: Message):
    await top_handler(message)

@router.message(F.text == "📅 История")
async def history_button_handler(message: Message):
    await history_handler(message)

@router.message(F.text == "❓ Помощь")
async def help_button_handler(message: Message):
    await support_button_handler(message)
