'''
ACCESS CHECKER FOR ADMIN/MODERATOR COMMANDS
ПРОВЕРКА ДОСТУПА ДЛЯ АДМИН/МОДЕРАТОР КОМАНД
'''

from sqlmodel import Session, select
from database.models import engine, UsersSchema

def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором
    Checks if user is administrator
    """
    with Session(engine) as session:
        user_stmt = select(UsersSchema).where(UsersSchema.telegram_id == user_id)
        user = session.exec(user_stmt).first()
        return user and user.role == "admin"

def is_moderator(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь модератором или выше
    Checks if user is moderator or higher
    """
    with Session(engine) as session:
        user_stmt = select(UsersSchema).where(UsersSchema.telegram_id == user_id)
        user = session.exec(user_stmt).first()
        return user and user.role in ["moderator", "admin"]

def can_ban_user(executor_id: int, target_user) -> bool:
    """
        Проверяет, может ли исполнитель забанить игрока
        Checks if executor can ban target
    """
    # Исполнитель не может банить сам себя
    if executor_id == target_user.telegram_id:
        return False
    
    # Получаем роль исполнителя
    with Session(engine) as session:
        executor_stmt = select(UsersSchema).where(UsersSchema.telegram_id == executor_id)
        executor = session.exec(executor_stmt).first()
        
        if not executor:
            return False
        
        # Админ может банить модераторов и игроков
        if executor.role == "admin":
            return target_user.role in ["moderator", "player"]
        
        # Модератор может банить только игроков
        if executor.role == "moderator":
            return target_user.role == "player"
        
        return False

def find_user_by_identifier(identifier: str):
    """
    Находит пользователя по username или Telegram ID
    Finds user by username or Telegram ID
    
    Возвращает: (user, error_message)
    Returns: (user, error_message)
    """
    with Session(engine) as session:
        # Если это числовой ID (Telegram ID)
        if identifier.isdigit():
            telegram_id = int(identifier)
            user_stmt = select(UsersSchema).where(UsersSchema.telegram_id == telegram_id)
            user = session.exec(user_stmt).first()
            if not user:
                return None, f"❌ Пользователь с ID {identifier} не найден"
            return user, ""
        
        # Если это username (начинается с @ или без)
        username = identifier.replace('@', '').strip()
        
        # Ищем по username БЕЗ @ в начале
        user_stmt = select(UsersSchema).where(UsersSchema.username == username)
        user = session.exec(user_stmt).first()
        
        if not user:
            return None, f"❌ Пользователь @{username} не найден"
        
        return user, ""