from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    BOT_TOKEN: str = "8695951010:AAGg-CfES8y0wb8uYko1umc7v6G_PAL7Yfs"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ebl"
    WEBHOOK_SECRET: str = "ebl-secret-2024"
    WEBHOOK_HOST: str = "https://your-app.railway.app"
    WEBAPP_URL: str = "https://your-app.railway.app/app"
    ADMIN_IDS: List[int] = []
    TIMEZONE: str = "Europe/Moscow"
    SEASON_START_YEAR: int = 2026
    ULTRAUNIQUE_START_DATE: str = "2023-01-01"
    EDIT_WINDOW_HOURS: int = 2

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
