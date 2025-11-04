'''
FILE FOR WORK WITH CREATING MATCHES AND REGISTER THEM
'''

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
import random
import asyncio
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlmodel import Session, select
from app.database.models import engine, UsersSchema, GameProfilesSchema, MatchesSchema, FoundMatchSchema, UserBansSchema
from app.localization import translate

router = Router()
moscow_tz = ZoneInfo("Europe/Moscow")

# Хранилище для активных лобби
active_lobbies = {}
'''
# Пример структуры одного лобби | Example of one lobby structure:
# active_lobbies["1"] = {
#     'players': ["Player1", "Player2", "Player3"],  # Ники игроков | Player nicknames
#     'player_ids': [123, 456, 789],                 # Telegram ID игроков | Player Telegram IDs
#     'player_profiles': {                           # Профили игроков из БД | Player profiles from DB
#         123: GameProfilesSchema_object,
#         456: GameProfilesSchema_object
#     },
#     'status': 'waiting',                           # Статус лобби | Lobby status
#     'captains': [123, 456],                        # ID капитанов | Captain IDs
#     'messages': [                                  # Сообщения у каждого игрока | Messages for each player
#         {
#             'user_id': 123,
#             'message_id': 1001,
#             'chat_id': 123456789
#         },
#         {
#             'user_id': 456, 
#             'message_id': 1002,
#             'chat_id': 987654321
#         }
#     ]
# }
'''


map_selections = {}


# Проверка - забанен ли пользователь или нет
# Bot check have a user ban or not
def is_user_banned(user_id: int) -> bool:
    try:
        # открываем сессию с базой данных
        # opening a session with the database
        with Session(engine) as session:
            # формируем запрос к таблице пользователей с условием по telegram_id
            # creating a query to UsersSchema filtered by telegram_id
            user_stmt = select(UsersSchema).where(UsersSchema.telegram_id == user_id)
            # выполняем запрос, получаем первого пользователя, если он найден
            # executing the query and fetching the first user if found
            user = session.exec(user_stmt).first()
            
            # если пользователь не найден, возвращаем False (не забанен)
            # if user is not found, return False (not banned)
            if not user:
                return False
                
            # формируем запрос к таблице банов с условием по user_id и активному статусу
            # creating a query to UserBansSchema filtering by user_id and active status
            ban_stmt = select(UserBansSchema).where(
                # находим пользователя в базе данных отведенную под баны
                # find the user in the database reserved for bans
                UserBansSchema.user_id == user.user_id,
                # и если мы нашли игрока у которого бан True, то ему автоматически запрещается играть
                # and if we find a player with a True ban, then he is automatically banned from playing
                UserBansSchema.is_active == True
            )
            # выполняем запрос, получаем самую первую запись бана, если есть
            # executing the query and fetching the first active ban record if exists
            active_ban = session.exec(ban_stmt).first()
            
            # проверяем, есть ли активный бан и не истёк ли срок бана
            # checking if there is an active ban and if ban period has not expired
            if active_ban and active_ban.unbanned_at > datetime.now(moscow_tz):
                # если бан активен по дате, возвращаем True
                # if ban is active by expiration date, return True
                return True
            # если бан отсутствует или закончился, возвращаем False
            # if ban is absent or expired, return False
            return False
    except Exception as e:
        print(f"Ошибка проверки бана: {e}")
        return False

def ban_user(user_id: int, ban_type: str = "lobby_leave", reason: str = "Выход из заполненного лобби", minutes: int = 1): #! for test set 1 minute ban
    # открываем сессию с базой данных
    # opening a session with the database
    with Session(engine) as session:
        user_stmt = select(UsersSchema).where(UsersSchema.telegram_id == user_id)
        user = session.exec(user_stmt).first()
        
        if user:
            # для автоматических банов (типа lobby_leave) banned_by устанавливается как ID самого пользователя
            # for automatic bans (like lobby_leave) banned_by is set as the user's own ID
            
            # присваиваем banned_by ID текущего пользователя
            # assigning banned_by the ID of the current user
            banned_by = user.user_id
            
            # создаём новый объект в базе данных UserBansSchema
            # creating a new object in UserBansSchema
            new_ban = UserBansSchema(
                user_id=user.user_id,
                banned_by=banned_by,
                ban_type=ban_type,
                reason=reason,
                duration_minutes=minutes,
                unbanned_at=datetime.now(moscow_tz) + timedelta(minutes=minutes)
            )
            session.add(new_ban)
            session.commit()

def get_lobby_player_count(lobby_number: str) -> int:
    """
        Получает реальное количество игроков в лобби
        Gets the actual number of players in the lobby
    """
    lobby_data = active_lobbies.get(lobby_number, {})
    return len(lobby_data.get('players', []))

async def update_lobby_messages(
        bot,
        lobby_number: str,
        is_full: bool = False,
        captain_nicknames: list = None,
    ):
    # Текущее количество игроков | Current player count
    lobby_data = active_lobbies.get(lobby_number)
    if not lobby_data:
        return
    
    current_players = len(lobby_data['players'])
    
    # Создаем клавиатуру с кнопкой Выйти
    cancel_builder = InlineKeyboardBuilder()
    cancel_builder.button(
        text=translate('buttons.leave_lobby', 0),  # 0 для системных сообщений
        callback_data=f"leave_lobby_{lobby_number}"
    )
    
    # СОЗДАЕМ ТЕКСТ СООБЩЕНИЯ
    # CREATE MESSAGE TEXT
    if is_full and captain_nicknames:
        # Текст для заполненного лобби
        # Text for full lobby
        message_text = (
            f"{translate('matches.lobby_full.title', 0, lobby_number=lobby_number)}\n\n"
            f"{translate('matches.lobby_full.players_full', 0)}\n"
            + "\n".join([f"• {player}" for player in lobby_data['players']]) +
            f"\n\n{translate('matches.lobby_full.captains_selected', 0)}\n"
            f"• {captain_nicknames[0]} (Команда А)\n"
            f"• {captain_nicknames[1]} (Команда Б)\n\n"
            f"{translate('matches.lobby_full.map_selection', 0)}"
        )
    else:
        # Текст для лобби в ожидании
        # Text for waiting lobby
        message_text = (
            f"{translate('matches.lobby_waiting.selected', 0, lobby_number=lobby_number)}\n\n"
            f"{translate('matches.lobby_waiting.players_count', 0, current_players=current_players)}\n"
            + "\n".join([f"• {player}" for player in lobby_data['players']]) +
            f"\n\n{translate('matches.lobby_waiting.waiting', 0)}"
        )
    
    # ОБНОВЛЯЕМ СООБЩЕНИЯ У КАЖДОГО ИГРОКА
    # UPDATE MESSAGES FOR EACH PLAYER
    for message_info in lobby_data.get('messages', []):
        try:
            # Редактируем сообщение каждого игрока
            # Edit each player's message
            await bot.edit_message_text(
                # Куда отправлять
                # Where to send
                chat_id=message_info['chat_id'], 
                # Какое сообщение редактировать
                # Which message to edit
                message_id=message_info['message_id'], 
                text=message_text, # Новый текст | New text
                reply_markup=cancel_builder.as_markup(), # Клавиатура | Keyboard
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка обновления сообщения для user_id {message_info['user_id']}: {e}")

async def update_lobby_list(bot):
    """
        Обновляет список лобби для всех пользователей
        Refreshes the lobby list for all users.
    """

    #! TEST
    # Для теста просто логируем
    # For test use logging 
    print("🔄 Обновлен список лобби:")
    for lobby_num in range(1, 5):
        count = get_lobby_player_count(str(lobby_num))
        print(f"Lobby {lobby_num}: {count}/10 игроков")

@router.message(Command("lobby"))
async def lobby_handler(message: Message):
    """
        Показ доступных лобби с реальным подсчетом игроков
        Showing available lobbies with real player counts
    """
    
    user_id = message.from_user.id
    
    # ПРОВЕРЯЕМ ВСЕ ЛОББИ - в каком находится пользователь
    # CHECK ALL LOBBIES - which one the user is in
    user_current_lobby = None
    for lobby_number, lobby_data in active_lobbies.items():
        # Ищем user_id в списке player_ids лобби
        # Search for user_id in lobby's player_ids list
        if user_id in lobby_data.get('player_ids', []):
            user_current_lobby = lobby_number
            break
    
    # ЕСЛИ ПОЛЬЗОВАТЕЛЬ УЖЕ В ЛОББИ - выходим из него
    # IF USER IS ALREADY IN LOBBY - leave it
    if user_current_lobby:
        lobby_data = active_lobbies[user_current_lobby]
        
        # УДАЛЯЕМ ПОЛЬЗОВАТЕЛЯ ИЗ СПИСКА ИГРОКОВ
        # REMOVE USER FROM PLAYER LIST
        if user_id in lobby_data['player_ids']:
            # Находим индекс пользователя в списке
            # Find user index in the list
            index = lobby_data['player_ids'].index(user_id)
            
            # Удаляем из обоих списков по одинаковому индексу
            # Remove from both lists by same index
            lobby_data['players'].pop(index)    # Удаляем ник | Remove nickname
            lobby_data['player_ids'].pop(index) # Удаляем ID | Remove ID
            
            # Удаляем сообщение пользователя из списка сообщений
            # Remove user's message from messages list
            lobby_data['messages'] = [msg for msg in lobby_data.get('messages', []) if msg['user_id'] != user_id]
            
            # Если пользователь был капитаном, выбираем нового
            if user_id in lobby_data.get('captains', []):
                available_players = [pid for pid in lobby_data['player_ids'] if pid != user_id]
                if available_players:
                    lobby_data['captains'] = random.sample(available_players, min(2, len(available_players)))
            
            # Очищаем данные выбора карт если лобби пустое
            if len(lobby_data.get('players', [])) == 0:
                if user_current_lobby in active_lobbies:
                    del active_lobbies[user_current_lobby]
                if user_current_lobby in map_selections:
                    del map_selections[user_current_lobby]
            else:
                # Обновляем сообщения у оставшихся игроков
                await update_lobby_messages(message.bot, user_current_lobby)
        
        await message.answer(
            translate('matches.already_in_lobby', user_id, lobby_number=user_current_lobby),
            parse_mode="HTML"
        )
    
    # ПРОВЕРЯЕМ БАН (после выхода из лобби)
    # check ban user or not
    if is_user_banned(user_id):
        await message.answer(
            translate('matches.banned', user_id),
            parse_mode="HTML"
        )
        return
    
    # ПОЛУЧАЕМ РЕАЛЬНЫЕ СЧЕТЧИКИ ИГРОКОВ ДЛЯ КАЖДОГО ЛОББИ
    # GET REAL PLAYER COUNTS FOR EACH LOBBY
    builder = InlineKeyboardBuilder()
    
    # Реальные счетчики игроков
    lobby_1_count = get_lobby_player_count("1") # Считает игроков в лобби 1 | Counts players in lobby 1
    lobby_2_count = get_lobby_player_count("2")
    lobby_3_count = get_lobby_player_count("3") 
    lobby_4_count = get_lobby_player_count("4")
    
    # СОЗДАЕМ КНОПКИ ДЛЯ КАЖДОГО ЛОББИ
    # CREATE BUTTONS FOR EACH LOBBY
    for lobby_num, count in [
        (1, lobby_1_count), 
        (2, lobby_2_count),
        (3, lobby_3_count),
        (4, lobby_4_count),
    ]:
        # Если в лобби более 10 человек - мы блокируем лобби и отправляем уведомление игроку
        # if lobby take 10 players in - we are block lobby and send notification about it
        if count >= 10:
            builder.button(
                text=f"🎮 Lobby {lobby_num} • 10/10 🔒",
                callback_data=f"lobby_full_{lobby_num}",
            )
        # Если же лобби не заполнено, оставляем открытым
        # if lobby are not full - player can connect in
        else:
            builder.button(
                text=f"🎮 Lobby {lobby_num} • {count}/10",
                callback_data=f"join_lobby_{lobby_num}",
            )
    
    builder.adjust(2)
    
    # Описания лобби
    lobby_descriptions = {
        1: translate('matches.lobby_list.ranked_match', user_id),
        2: translate('matches.lobby_list.ranked_match', user_id),
        3: translate('matches.lobby_list.ranked_match', user_id),
        4: translate('matches.lobby_list.ranked_match', user_id),
    }
    
    lobby_text = f"{translate('matches.lobby_list.title', user_id)}\n\n"
    
    for lobby_num in range(1, 5):
        count = get_lobby_player_count(str(lobby_num))
        status = translate('matches.lobby_list.full', user_id) if count >= 10 else translate('matches.lobby_list.open', user_id)
        lobby_text += f"🎯 <b>Lobby {lobby_num}</b> • {lobby_descriptions[lobby_num]} • {status}\n"
        lobby_text += f"👥 {count}/10 {translate('matches.lobby_list.players', user_id)}\n\n"
    
    lobby_text += translate('matches.lobby_list.description', user_id)
    
    await message.answer(
        lobby_text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("lobby_full_"))
async def handle_lobby_full(callback: CallbackQuery):
    """
        Обработчик заблокированных лобби
        Blocked lobby handler
    """
    await callback.answer(translate('matches.lobby_is_full', callback.from_user.id), show_alert=True)

@router.callback_query(F.data.startswith("join_lobby_"))
async def handle_lobby_join(callback: CallbackQuery, state: FSMContext):
    # получаем номер лобби из callback_data 
    # get lobby number from callback_data
    lobby_number = callback.data.split("_")[2] 
    user_id = callback.from_user.id
    
    # Проверяем бан
    if is_user_banned(user_id):
        await callback.answer(translate('matches.banned_alert', user_id), show_alert=True)
        return
    
    await callback.message.delete()
    
    with Session(engine) as session:
        # Получаем текущего пользователя
        user_stmt = select(UsersSchema).where(UsersSchema.telegram_id == user_id)
        user = session.exec(user_stmt).first()
        
        if user:
            profile_stmt = select(GameProfilesSchema).where(GameProfilesSchema.user_id == user.user_id)
            user_profile = session.exec(profile_stmt).first()
            current_user_nickname = user_profile.nickname if user_profile else user.first_name
        else:
            current_user_nickname = callback.from_user.first_name or translate('generic.player', user_id)

    # Инициализируем лобби если его нет
    # Initialize lobby if it doesn't exist
    if lobby_number not in active_lobbies:
        active_lobbies[lobby_number] = {
            'players': [],          # Пустой список ников | Empty nickname list
            'player_ids': [],       # Пустой список ID | Empty ID list  
            'player_profiles': {},  # Пустой словарь профилей | Empty profiles dict
            'status': 'waiting',    # Статус "ожидание" | "Waiting" status
            'captains': [],         # Пустой список капитанов | Empty captains list
            'messages': []          # Пустой список сообщений | Empty messages list
        }
    
    lobby_data = active_lobbies[lobby_number]
    
    # Проверяем, не заполнено ли лобби
    # Check if the lobby is full
    if len(lobby_data['players']) >= 10:
        await callback.message.answer(translate('matches.lobby_join_error', user_id))
        return
    
    # Проверяем, не в лобби ли уже пользователь
    # Check if the user is already in the lobby
    if user_id in lobby_data['player_ids']:
        await callback.message.answer(translate('matches.lobby_already_joined', user_id))
        return
    
    # Добавляем пользователя в лобби
    # Add a user to the lobby
    lobby_data['players'].append(current_user_nickname) # Добавляем ник | Add nickname
    lobby_data['player_ids'].append(user_id)            # Добавляем ID | Add ID
    
    # Сохраняем профиль пользователя
    # Save the user profile
    if user and user_profile:
        lobby_data['player_profiles'][user_id] = user_profile
    
    current_players = len(lobby_data['players'])
    
    cancel_builder = InlineKeyboardBuilder()
    cancel_builder.button(
        text=translate('buttons.leave_lobby', user_id),
        callback_data=f"leave_lobby_{lobby_number}"
    )
    
    lobby_message = await callback.message.answer(
        f"{translate('matches.lobby_waiting.selected', user_id, lobby_number=lobby_number)}\n\n"
        f"{translate('matches.lobby_waiting.players_count', user_id, current_players=current_players)}\n"
        + "\n".join([f"• {player}" for player in lobby_data['players']]) +
        f"\n\n{translate('matches.lobby_waiting.joined_as', user_id, nickname=current_user_nickname)}\n"
        f"{translate('matches.lobby_waiting.waiting', user_id)}",
        reply_markup=cancel_builder.as_markup(),
        parse_mode="HTML"
    )
    
    # Сохраняем сообщение для этого пользователя
    # Save message for this user
    lobby_data['messages'].append({
        'user_id': user_id,                     # ID пользователя | User ID
        'message_id': lobby_message.message_id, # ID сообщения | Message ID
        'chat_id': lobby_message.chat.id        # ID чата | Chat ID
    })
    
    # ОБНОВЛЯЕМ СООБЩЕНИЯ У ВСЕХ ИГРОКОВ В ЛОББИ
    await update_lobby_messages(callback.bot, lobby_number)
    
    # ОБНОВЛЯЕМ СПИСОК ЛОББИ ДЛЯ ВСЕХ
    await update_lobby_list(callback.bot)
    
    # Если лобби заполнено, начинаем выбор карт
    if current_players >= 10:
        # Выбираем случайных капитанов из всех игроков
        captains = random.sample(lobby_data['player_ids'], 2)
        lobby_data['captains'] = captains
        lobby_data['status'] = 'full'
        
        # Получаем ники капитанов
        captain_nicknames = []
        for captain_id in captains:
            if captain_id in lobby_data['player_profiles']:
                captain_nicknames.append(lobby_data['player_profiles'][captain_id].nickname)
            else:
                captain_nicknames.append(f"{translate('generic.player', user_id)} {captain_id}")
        
        # Уведомляем о выборе капитанов ВСЕХ игроков
        await update_lobby_messages(callback.bot, lobby_number, is_full=True, captain_nicknames=captain_nicknames)
        
        # Запускаем выбор карт (используем первое сообщение для этого)
        if lobby_data['messages']:
            first_message = lobby_data['messages'][0]
            try:
                message_obj = await callback.bot.edit_message_text(
                    chat_id=first_message['chat_id'],
                    message_id=first_message['message_id'],
                    text=f"{translate('matches.lobby_full.title', user_id, lobby_number=lobby_number)}\n\n"
                         f"{translate('matches.lobby_full.players_full', user_id)}\n"
                         + "\n".join([f"• {player}" for player in lobby_data['players']]) +
                         f"\n\n{translate('matches.lobby_full.captains_selected', user_id)}\n"
                         f"• {captain_nicknames[0]} (Команда А)\n"
                         f"• {captain_nicknames[1]} (Команда Б)\n\n"
                         f"{translate('matches.lobby_full.map_selection', user_id)}",
                    parse_mode="HTML"
                )
                await start_map_selection(message_obj, lobby_number)
            except Exception as e:
                print(f"Ошибка запуска выбора карт: {e}")

async def start_map_selection(message: Message, lobby_number: str):
    """
        Запуск процесса выбора карт
        Starting the card selection process
    """
    
    # Получаем данные лобби по его номеру
    # Get lobby data by its number
    lobby_data = active_lobbies[lobby_number]
    
    # Инициализируем процесс выбора карт для определенного лобби
    # Initialize map selection process for this lobby
    map_selections[lobby_number] = {
        'captains': lobby_data['captains'], # Список ID капитанов | List of captain IDs
        # Индекс текущего капитана (0 или 1)
        # Current captain index (0 or 1)
        'current_turn': 0, 
        # Доступные карты 
        # Available maps
        'available_maps': ["Sandstone", "Breeze", "Dune", "Hanami", "Province", "Rust", "Zone 7"],
        'banned_maps': [],   # Список исключенных карт | List of banned maps
        'message': message,  # Сообщение для редактирования | Message for editing
    }
    # Показываем интерфейс выбора карт - клавиатуру
    # Show map selection interface - keyboard
    await show_map_selection_interface(message, lobby_number)

async def show_map_selection_interface(message: Message, lobby_number: str):
    """
        Показ интерфейса выбора карт
        Showing the card selection interface
    """
    
    # Получаем данные выбора карт для лобби
    # Get map selection data for the lobby
    selection_data = map_selections.get(lobby_number)
    # Получаем данные лобби
    # Get lobby data
    lobby_data = active_lobbies.get(lobby_number, {})
    
    
    # Если данных нет, выходим
    # If no data, exit
    if not selection_data:
        return
    
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки для каждой доступной карты
    # Add buttons for each available map
    for map_name in selection_data['available_maps']:
        builder.button(
            text=translate('buttons.ban_map', 0, map_name=map_name),
            callback_data=f"ban_map_{lobby_number}_{map_name}"
        )
    
    
    builder.button(
        text=translate('buttons.leave_lobby', 0),
        callback_data=f"leave_lobby_{lobby_number}"
    )
    builder.adjust(2)
    
    # Создаем словарь с именами капитанов
    # Create dictionary with captain names
    captain_names = {}
    for captain_id in selection_data['captains']:
        # Если профиль капитана есть в данных лобби, используем его ник
        # If captain profile exists in lobby data, use their nickname
        if captain_id in lobby_data.get('player_profiles', {}):
            captain_names[captain_id] = lobby_data['player_profiles'][captain_id].nickname
        # Иначе создаем generic имя #! сделать проверку на регистрацию перед тем как зайти в лобби
        # Otherwise create generic name
        else:
            captain_names[captain_id] = f"{translate('generic.player', 0)} {captain_id}"
    
    # Определяем ID и имя текущего капитана
    # Determine current captain ID and name
    current_captain_id = selection_data['captains'][selection_data['current_turn']]
    current_captain_name = captain_names.get(current_captain_id, translate('generic.captain', 0))
    
    status_text = (
        f"{translate('matches.map_selection.title', 0, lobby_number=lobby_number)}\n\n"
        f"{translate('matches.map_selection.captains', 0)}\n"
        f"• Команда А: {captain_names[selection_data['captains'][0]]}\n"
        f"• Команда Б: {captain_names[selection_data['captains'][1]]}\n\n"
        f"{translate('matches.map_selection.current_turn', 0, captain_name=current_captain_name)}\n"
        f"{translate('matches.map_selection.available_maps', 0, maps=', '.join(selection_data['available_maps']))}\n"
        f"{translate('matches.map_selection.banned_maps', 0, maps=', '.join(selection_data['banned_maps']) or translate('matches.map_selection.no_banned', 0))}\n\n"
        f"{translate('matches.map_selection.instruction', 0)}"
    )
    # Пытаемся отредактировать сообщение с новым интерфейсом
    # Try to edit message with new interface
    try:
        await message.edit_text(status_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка редактирования сообщения: {e}")

@router.callback_query(F.data.startswith("ban_map_"))
async def handle_map_ban(callback: CallbackQuery):
    """
        Обработчик исключения карты
        Map exception handler
    """
    
    # Разбираем callback_data на части
    # Parse callback_data into parts
    data_parts = callback.data.split("_")
    lobby_number = data_parts[2]     # Номер лобби | Lobby number
    map_name = data_parts[3]         # Название карты | Map name
    user_id = callback.from_user.id  # ID пользователя | User ID
    
    # Получаем данные выбора карт
    # Get map selection data
    selection_data = map_selections.get(lobby_number)
    
    # Проверяем существование данных о лобби
    # Check if data exists about lobby
    if not selection_data:
        await callback.answer(translate('matches.lobby_data_not_found', user_id))
        return
    
    # Получаем ID текущего капитана
    # Get current captain ID
    current_captain_id = selection_data['captains'][selection_data['current_turn']]
    
    # Проверяем, что действие совершает текущий капитан
    # Verify that action is performed by current captain
    if user_id != current_captain_id:
        await callback.answer(translate('matches.not_your_turn', user_id))
        return
    
    # Если карта доступна для исключения
    # If map is available for banning
    if map_name in selection_data['available_maps']:
        # Удаляем карту из доступных и добавляем в исключенные
        # Remove map from available and add to banned
        selection_data['available_maps'].remove(map_name)
        selection_data['banned_maps'].append(map_name)
        
        await callback.answer(translate('matches.map_banned', user_id, map_name=map_name))
        
        # Переключаем очередь на другого капитана (0->1 или 1->0)
        # Switch turn to other captain (0->1 or 1->0)
        selection_data['current_turn'] = 1 - selection_data['current_turn']
        
        # Если осталась только одна карта - завершаем выбор
        # If only one map remains - finish selection
        if len(selection_data['available_maps']) == 1:
            final_map = selection_data['available_maps'][0]
            await finish_map_selection(callback.message, lobby_number, final_map)
        
        # Иначе показываем обновленный интерфейс
        # Otherwise show updated interface
        else:
            await show_map_selection_interface(callback.message, lobby_number)

@router.callback_query(F.data.startswith("leave_lobby_"))
async def handle_leave_lobby(callback: CallbackQuery):
    """
        Выход из лобби с системой банов
        Exiting the lobby with the ban system    
    """
    
    # Извлекаем номер лобби из callback_data
    # Extract lobby number from callback_data
    lobby_number = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    # Получаем данные лобби
    # Get lobby data
    lobby_data = active_lobbies.get(lobby_number, {})
    
    # Если лобби заполнено (10 игроков) - бан за выход
    # If lobby is full (10 players) - ban for leaving
    if len(lobby_data.get('players', [])) >= 10:
        ban_user(user_id, "lobby_leave", "Выход из заполненного лобби")
        
        await callback.message.edit_text(
            translate('matches.leave_banned', user_id),
            parse_mode="HTML"
        )
    else:
        # Иначе просто уведомляем о выходе
        # Otherwise just notify about leaving
        await callback.message.edit_text(
            translate('matches.leave_normal', user_id),
            parse_mode="HTML"
        )
        
    # Если пользователь был в лобби, удаляем его
    # If user was in lobby, remove them
    if user_id in lobby_data.get('player_ids', []):
        index = lobby_data['player_ids'].index(user_id)
        lobby_data['players'].pop(index)
        lobby_data['player_ids'].pop(index)
        
        # Удаляем сообщение пользователя из списка
        # Remove user's message from the list
        lobby_data['messages'] = [msg for msg in lobby_data.get('messages', []) if msg['user_id'] != user_id]
        
        # Если пользователь был капитаном, выбираем нового
        # If user was captain, select new one
        if user_id in lobby_data.get('captains', []):
            available_players = [pid for pid in lobby_data['player_ids'] if pid != user_id]
            if available_players:
                lobby_data['captains'] = random.sample(available_players, min(2, len(available_players)))
    
    # Обновляем сообщения у оставшихся игроков
    # Update messages for remaining players
    await update_lobby_messages(callback.bot, lobby_number)
    
    # Обновляем список лобби для всех пользователей
    # Update lobby list for all users
    await update_lobby_list(callback.bot)
    
    # Если в лобби не осталось игроков, очищаем данные
    # If no players left in lobby, clean up data
    if len(lobby_data.get('players', [])) == 0:
        if lobby_number in active_lobbies:
            del active_lobbies[lobby_number]
        if lobby_number in map_selections:
            del map_selections[lobby_number]

async def finish_map_selection(message: Message, lobby_number: str, final_map: str):
    """
        Завершение выбора карты с сохранением в БД
        Completing the card selection with saving to the database
    """
    
    # Получаем данные лобби
    # Get lobby data
    lobby_data = active_lobbies.get(lobby_number, {})
    real_players = lobby_data.get('players', [])  # Ники игроков | Player nicknames
    player_ids = lobby_data.get('player_ids', []) # ID игроков | Player IDs
    
    # Разделяем игроков на две команды
    # Split players into two teams
    team_a_players = real_players[:5]   # Первые 5 игроков | First 5 players
    team_b_players = real_players[5:10] # Следующие 5 игроков | Next 5 players
    
    captain_names = {}
    host_game_id = translate('generic.host_not_found', 0)  # ID игры хоста | Host game ID

    with Session(engine) as session:
        # Собираем информацию о капитанах
        # Collect information about captains
        for i, captain_id in enumerate(lobby_data.get('captains', [])):
            if captain_id in lobby_data.get('player_profiles', {}):
                profile = lobby_data['player_profiles'][captain_id]
                captain_names[captain_id] = profile.nickname
                # Первый капитан становится хостом | First captain becomes host
                if i == 0:
                    host_game_id = profile.game_id
            else:
                # Если профиля нет в кэше, запрашиваем из БД
                # If profile not in cache, query from DB
                user_stmt = select(UsersSchema).where(UsersSchema.telegram_id == captain_id)
                user = session.exec(user_stmt).first()
                
                if user:
                    profile_stmt = select(GameProfilesSchema).where(GameProfilesSchema.user_id == user.user_id)
                    profile = session.exec(profile_stmt).first()
                    
                    if profile:
                        captain_names[captain_id] = profile.nickname
                        if i == 0:
                            host_game_id = profile.game_id
                    else:
                        captain_names[captain_id] = user.first_name
                else:
                    captain_names[captain_id] = f"{translate('generic.player', 0)} {captain_id}"
        
        # Генерируем уникальный ID лобби из текущего времени
        # Generate unique lobby ID from current time
        lobby_id = int(datetime.now().strftime("%m%d%H%M%S"))
        
        
        # Создаем запись о матче в БД когда игра началась
        # Create match record in DB when game start
        new_match = MatchesSchema(
            map_name=final_map, # Выбранная карта | Selected map
            status="created",   # Статус матча | Match status
            lobby_id=lobby_id   # ID лобби | Lobby ID
        )
        session.add(new_match)
        session.commit()
        session.refresh(new_match)
        
        # Получаем ID созданного матча | Get created match ID
        match_id = new_match.match_id
        
        found_match = FoundMatchSchema(
            lobby_id=lobby_id,
            players=json.dumps(player_ids), # Сохраняем ID игроков как JSON | Save player IDs as JSON
            max_players=10,
            current_players=len(player_ids),
            status="finished",
            match_id=match_id,
            game_started_at=datetime.now(moscow_tz)
        )
        session.add(found_match)
        session.commit()
    
    final_text = (
        f"{translate('matches.game_created.title', 0)}\n\n"
        f"{translate('matches.game_created.game_number', 0, match_id=match_id)}\n"
        f"{translate('matches.game_created.map', 0, map_name=final_map)}\n"
        f"{translate('matches.game_created.host', 0, host_id=host_game_id)}\n"
        f"{translate('matches.game_created.captains', 0, captain_a=captain_names[lobby_data['captains'][0]], captain_b=captain_names[lobby_data['captains'][1]])}\n"
        f"{translate('matches.game_created.lobby_id', 0, lobby_id=lobby_id)}\n\n"
        f"{translate('matches.game_created.team_ct', 0)}\n" + "\n".join([f"  • {player}" for player in team_a_players]) + f"\n\n"
        f"{translate('matches.game_created.team_t', 0)}\n" + "\n".join([f"  • {player}" for player in team_b_players]) + f"\n\n"
        f"{translate('matches.game_created.good_luck', 0)}"
    )
    
    # Отправляем финальное сообщение всем игрокам в лобби
    for message_info in lobby_data.get('messages', []):
        try:
            await message.bot.edit_message_text(
                chat_id=message_info['chat_id'],
                message_id=message_info['message_id'],
                text=final_text,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка отправки финального сообщения для user_id {message_info['user_id']}: {e}")
    
    
    # Очищаем данные лобби после завершения
    # Clean up lobby data after completion
    if lobby_number in active_lobbies:
        del active_lobbies[lobby_number]
    if lobby_number in map_selections:
        del map_selections[lobby_number]