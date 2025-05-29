import os
from dotenv import load_dotenv
import logging

load_dotenv()


class Config:
    """Application configuration settings"""

    PORT = int(os.getenv("PORT", 3000))
    TIKTOK_API_BASE = os.getenv("TIKTOK_API_BASE", "https://www.tikwm.com/api/")
    DOWNLOAD_FOLDER = os.getenv("DOWNLOAD_FOLDER", "./downloads")
    CONVERTED_FOLDER = os.getenv("CONVERTED_FOLDER", "./converted")
    ENV = os.getenv("ENV", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    # Google OAuth2 settings
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/callback")
    SESSION_SECRET = os.getenv("SESSION_SECRET", "modimodimodi")
    YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
    YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
    YOUTUBE_REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI", "https://api-demo.goodorbitt.com/auth/callback")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("tiktok_converter")


config = Config()

logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

os.makedirs(config.DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(config.CONVERTED_FOLDER, exist_ok=True)

logger.info(f"Loaded config: ENV={config.ENV}, PORT={config.PORT}")
