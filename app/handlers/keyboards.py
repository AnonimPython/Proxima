from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardButton,InlineKeyboardMarkup)
#* Usings Bilders
from aiogram.utils.keyboard import ReplyKeyboardBuilder,InlineKeyboardBuilder

# Основные команды | Main commands
def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    
    # Добавляем кнопки
    builder.add(
        KeyboardButton(text="📊 Профиль"),
        KeyboardButton(text="🎮 Найти лобби"), 
        KeyboardButton(text="📈 Статистика"),
        KeyboardButton(text="🏆 Топ игроков"),
        KeyboardButton(text="📅 История"),
        KeyboardButton(text="❓ Помощь")
    )
    builder.adjust(2, 2, 2)
    
    return builder.as_markup(resize_keyboard=True)

# Клавиатура только для зарегистрированных пользователей
# Keyboard only for user who auth in project
def get_game_keyboard():
    builder = ReplyKeyboardBuilder()
    
    builder.add(
        KeyboardButton(text="🎮 Найти лобби"),
        KeyboardButton(text="📊 Мой профиль"),
        KeyboardButton(text="📈 Статистика"),
        #todo: take from CONFIG name of project
        KeyboardButton(text="🏆 Топ Proxima"),
    )
    
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)

# Клавиатура для незарегистрированных
# Keyboard for new users
def get_start_keyboard():
    builder = ReplyKeyboardBuilder()
    
    builder.add(
        KeyboardButton(text="🚀 Начать регистрацию"),
        KeyboardButton(text="❓ Помощь"),
        KeyboardButton(text="📞 Поддержка")
    )
    
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)