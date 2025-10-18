'''
ACCESS CHECKER FOR ADMIN/MODERATOR COMMANDS
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
        return user and user.role in ["admin", "moderator"]

def is_moderator(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь модератором или выше
    Checks if user is moderator or higher
    """
    with Session(engine) as session:
        user_stmt = select(UsersSchema).where(UsersSchema.telegram_id == user_id)
        user = session.exec(user_stmt).first()
        return user and user.role in ["moderator", "admin"]

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