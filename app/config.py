import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')
    BOT_NAME = "Proxima"
    GAME_NAME = "Standoff 2"
    
    # Настройки лобби
    MAX_PLAYERS = 10
    AVAILABLE_MAPS = ["Sandstone", "Breeze", "Dune", "Hanami", "Province","Rust","Zone 7"]

config = Config()