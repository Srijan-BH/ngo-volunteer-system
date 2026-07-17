"""
Application Configuration Settings
Loads all environment variables and defines config classes for different environments.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class."""

    # ─── Application ────────────────────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    TESTING = False
    PORT = int(os.getenv("PORT", 5000))

    # ─── MongoDB ─────────────────────────────────────────────────────────────────
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/ngo_volunteer_db")
    MONGO_DBNAME = os.getenv("MONGO_DBNAME", "ngo_volunteer_db")

    # ─── JWT ─────────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", 24))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", 30))
    )
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_BLACKLIST_ENABLED = True

    # ─── CORS ────────────────────────────────────────────────────────────────────
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # ─── File Uploads ────────────────────────────────────────────────────────────
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    PROFILE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "profiles")
    EVENT_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "events")
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    ALLOWED_DOC_EXTENSIONS = {"pdf", "doc", "docx"}
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # 16 MB

    # ─── Logging ─────────────────────────────────────────────────────────────────
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

    # ─── Email (Optional / Future) ───────────────────────────────────────────────
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@ngo.com")

    # ─── Security & Headers ──────────────────────────────────────────────────────
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "True").lower() in ("true", "1")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # ─── Rate Limiting ───────────────────────────────────────────────────────────
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per day, 50 per hour")

    # ─── Pagination ──────────────────────────────────────────────────────────────
    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", 10))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", 100))


class DevelopmentConfig(Config):
    """Development-specific configuration."""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Testing-specific configuration."""
    TESTING = True
    DEBUG = True
    MONGO_URI = os.getenv("TEST_MONGO_URI", "mongodb://localhost:27017/ngo_volunteer_test_db")
    MONGO_DBNAME = "ngo_volunteer_test_db"


class ProductionConfig(Config):
    """Production-specific configuration."""
    DEBUG = False
    LOG_LEVEL = "WARNING"


# ─── Config Map ──────────────────────────────────────────────────────────────
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(env: str = None) -> Config:
    """Return the appropriate config class based on the environment."""
    env = env or os.getenv("FLASK_ENV", "default")
    return config_map.get(env, DevelopmentConfig)
