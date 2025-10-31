import json
import os

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

# Простая функция перевода | func to translate
def t(key: str, lang: str = 'ru', **kwargs):
    """Получить перевод по ключу"""
    keys = key.split('.')
    text = TRANSLATIONS.get(lang, TRANSLATIONS['ru'])
    
    for k in keys:
        text = text.get(k, key)
    
    if isinstance(text, str) and kwargs:
        return text.format(**kwargs)
    return text