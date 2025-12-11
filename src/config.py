import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ========== BOT CONFIGURATION ==========
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    OWNER_ID = int(os.getenv("OWNER_ID", 0))
    
    # ========== TELEGRAM API ==========
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    
    # ========== TELETHON SESSION STRING ==========
    # ✅ Yeh Telethon ka session string hai
    # Generate using: python scripts/generate_session.py
    SESSION_STRING = os.getenv("SESSION_STRING", "")
    
    # ========== DATABASE ==========
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "instavoice_bot")
    
    # ========== VOICE SETTINGS ==========
    # Instagram/TikTok style deep voice
    PITCH_SHIFT = -4  # -6 to -3 for deep voice
    BASS_BOOST = 10   # dB boost for bass
    REVERB_AMOUNT = 0.2
    COMPRESSION_RATIO = 3
    SPEED_FACTOR = 0.92
    
    # ========== PATHS ==========
    TEMP_DIR = "temp"
    SESSIONS_DIR = "sessions"
    LOGS_DIR = "logs"
    
    # ========== BOT SETTINGS ==========
    MAX_VOICE_SIZE = 20 * 1024 * 1024  # 20MB
    SUPPORTED_FORMATS = ['.ogg', '.mp3', '.m4a', '.wav']
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required = ['BOT_TOKEN', 'API_ID', 'API_HASH', 'SESSION_STRING']
        missing = [var for var in required if not getattr(cls, var)]
        
        if missing:
            raise ValueError(f"Missing environment variables: {missing}")
        
        print("✅ Configuration validated successfully")
        return True

# Create directories
os.makedirs(Config.TEMP_DIR, exist_ok=True)
os.makedirs(Config.SESSIONS_DIR, exist_ok=True)
os.makedirs(Config.LOGS_DIR, exist_ok=True)
