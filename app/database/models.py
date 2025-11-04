import random
from sqlmodel import Field, Session, SQLModel, create_engine, select, delete, Relationship
from typing import Optional, List, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json

moscow_tz = ZoneInfo("Europe/Moscow")


class UsersSchema(SQLModel, table=True):
    __tablename__ = "users"
    
    user_id: Optional[int] = Field(
        default=None, primary_key=True
    )
    telegram_id: int = Field(
        unique=True, index=True, nullable=False
    )
    username: Optional[str] = Field(default=None)
    first_name: str = Field(nullable=False)
    last_name: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(moscow_tz)
    )
    is_banned: bool = Field(default=False)
    ban_reason: Optional[str] = Field(default=None)
    #todo Create DB with roles for users
    role: str = Field(default="player")
    
class GameProfilesSchema(SQLModel, table=True):
    __tablename__ = "game_profiles"
    
    game_profile_id: Optional[int] = Field(
        default=None, primary_key=True
    )
    user_id: int = Field(foreign_key="users.user_id", nullable=False)
    nickname: str = Field(
        nullable=False, max_length=16
    )
    game_id: str = Field(
        nullable=False,
        unique=True,
        min_length=8,  #* Только цифры, минимум 8| Only int. Min 8
    )
    level: int = Field(default=1)
    experience: int = Field(default=0)
    #todo Create DB with leagues: Stater|Pro|Elite
    league: str = Field(default="starter")
    join_date: datetime = Field(
        default_factory=lambda: datetime.now(moscow_tz)
    )
    total_games: int = Field(default=0)
    
class UserStatsSchema(SQLModel, table=True):
    __tablename__ = "user_statistics"
    
    stats_id: Optional[int] = Field(
        default=None, primary_key=True,
    )
    user_id: int = Field(foreign_key="users.user_id", nullable=False)
    profile_id: int = Field(foreign_key="game_profiles.game_profile_id", nullable=False)
    kills: int = Field(default=0)
    deaths: int = Field(default=0)
    kd_ratio: float = Field(default=0.0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    win_rate: float = Field(default=0.0)
    avg_score: float = Field(default=0.0)
    fpr: float = Field(default=0.0)
    assists: int = Field(default=0)
    rating: int = Field(default=0)

class MatchPlayersSchema(SQLModel, table=True):
    __tablename__ = "match_players"
    
    match_player_id: Optional[int] = Field(
        default=None, primary_key=True,
    )
    match_id: int = Field(foreign_key="matches.match_id", nullable=False)
    user_id: int = Field(foreign_key="users.user_id", nullable=False)
    kills: int = Field(default=0)
    deaths: int = Field(default=0)
    assists: int = Field(default=0)

class MatchesSchema(SQLModel, table=True):
    __tablename__ = "matches"
    
    match_id: Optional[int] = Field(
        default=None, primary_key=True
    )
    map_name: str = Field(nullable=False)
    status: str = Field(default="created")
    game_created_at: datetime = Field(
        default_factory=lambda: datetime.now(moscow_tz)
    )
    finished_at: Optional[datetime] = Field(default=None)
    lobby_id: Optional[int] = Field(foreign_key="found_match.lobby_id", default=None)

class FoundMatchSchema(SQLModel, table=True):
    __tablename__ = "found_match"
    
    lobby_id: Optional[int] = Field(default=None, primary_key=True)
    # lobby_name: str = Field(default="Быстрый матч")
    #* JSON строка с списком telegram_id игроков
    #* JSON dict with telegram_id players for simple work
    players: str = Field(default="[]")
    max_players: int = Field(default=10)
    current_players: int = Field(default=0)
    status: str = Field(default="waiting")  #? waiting|full|started|finished
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(moscow_tz)
    )
    game_started_at: Optional[datetime] = Field(default=None)
    match_id: Optional[int] = Field(foreign_key="matches.match_id", default=None)
    

    # def get_players_list(self) -> List[int]:
    #     """Get Python list of players"""
    #     return json.loads(self.players)
    
    # def add_player(self, telegram_id: int) -> bool:
    #     """Добавить игрока в лобби"""
    #     '''Adding player in lobby'''
    #     players = self.get_players_list()
    #     if len(players) < self.max_players and telegram_id not in players:
    #         players.append(telegram_id)
    #         self.players = json.dumps(players)
    #         self.current_players = len(players)
            
    #         #* Проверка на заполнение лобби (10 человек)
    #         #* Cheking are lobby is full (10 players)
    #         if self.current_players >= self.max_players:
    #             self.status = "full"
    #             self.game_started_at = datetime.now(moscow_tz)
    #             return True  #* Лобби заполнено| Lobby not full
    #         return True  #* Игрок добавлен| User added
    #     return False  #* Не удалось добавить| Error to adding user
    
    # def remove_player(self, telegram_id: int) -> bool:
    #     """Удалить игрока из лобби"""
    #     '''Remode player from lobby'''
    #     players = self.get_players_list()
    #     if telegram_id in players:
    #         players.remove(telegram_id)
    #         self.players = json.dumps(players)
    #         self.current_players = len(players)
    #         #* Сбрасываем статус, т.к. лобби не полное| Reset status because lobby are empty
    #         self.status = "waiting"  
    #         return True
    #     return False
    
    #* данная функция запускается после каждого входа любого игрока
    #* This func activating after player connecting in lobby
    def is_full(self) -> bool:
        """Проверить, заполнено ли лобби"""
        '''Cheking are lobby is full (10 players)'''
        return self.current_players >= self.max_players

class UserBansSchema(SQLModel, table=True):
    __tablename__ = "user_bans"
    
    ban_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.user_id", nullable=False)
    banned_by: int = Field(foreign_key="users.user_id", nullable=False)  # Кто забанил | Who ban
    ban_type: str = Field(default="admin_mute")  # admin_mute, lobby_leave, etc
    reason: str = Field(default="Не указана")
    duration_minutes: int = Field(default=60)  # Длительность в минутах | Time in minutes
    banned_at: datetime = Field(default_factory=lambda: datetime.now(moscow_tz))
    unbanned_at: datetime = Field(default_factory=lambda: datetime.now(moscow_tz) + timedelta(minutes=60))
    is_active: bool = Field(default=True)
    unbanned_by: Optional[int] = Field(foreign_key="users.user_id", default=None)  # Кто разбанил | Who unban
    unbanned_at_time: Optional[datetime] = Field(default=None)  # Когда разбанен | When take unban

class MatchPhotosSchema(SQLModel, table=True):
    __tablename__ = "match_photos"
    
    photo_id: Optional[int] = Field(default=None, primary_key=True)
    match_id: int = Field(foreign_key="matches.match_id", nullable=False)
    user_id: int = Field(foreign_key="users.user_id", nullable=False)
    photo_path: str = Field(nullable=False)  # Путь к файлу фото | path to photo
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(moscow_tz))
    status: str = Field(default="pending")  # pending, approved, rejected
    
# Create DB
#todo Remake to PostgreSQL (or use Supabase.com)
#? for test I will use SQLite3
engine = create_engine("sqlite:///database.db")
SQLModel.metadata.create_all(engine)