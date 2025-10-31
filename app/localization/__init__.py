import json
import os
from typing import Dict, Any

# Глобальный словарь для хранения языковых настроек пользователей
# Для проекта под одну страну устанавливаем русский для всех
USER_LANGUAGES: Dict[int, str] = {}

# Загружаем переводы | load localizations
def load_translations():
    translations = {}
    loc_dir = os.path.join(os.path.dirname(__file__))
    
    for file in os.listdir(loc_dir):
        if file.endswith('.json'):
            lang = file.replace('.json', '')
            with open(os.path.join(loc_dir, file), 'r', encoding='utf-8') as f:
                translations[lang] = json.load(f)
    
    return translations

# Глобальная переменная с переводами
TRANSLATIONS = load_translations()

def set_user_language(user_id: int, language: str):
    """Установить язык для пользователя"""
    # Для проекта под одну страну всегда русский
    USER_LANGUAGES[user_id] = 'ru'

def get_user_language(user_id: int) -> str:
    """Получить язык пользователя"""
    # Для проекта под одну страну всегда русский
    return 'ru'

def t(key: str, user_id: int = None, lang: str = None, **kwargs) -> str:
    """Получить перевод по ключу для пользователя"""
    # Для проекта под одну страну всегда русский
    language = 'ru'
    
    keys = key.split('.')
    text_dict = TRANSLATIONS[language]
    
    # Рекурсивно ищем вложенные ключи
    for k in keys:
        if isinstance(text_dict, dict) and k in text_dict:
            text_dict = text_dict[k]
        else:
            return key  # ключ не найден
    
    # Если нашли строку, форматируем её
    if isinstance(text_dict, str) and kwargs:
        try:
            return text_dict.format(**kwargs)
        except KeyError:
            return text_dict
    
    return text_dict if isinstance(text_dict, str) else key

# Удобные алиасы для импорта
translate = t
set_language = set_user_language
get_language = get_user_language