import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "ВАШ_ЛОКАЛЬНЫЙ_ТОКЕН_ДЛЯ_ТЕСТОВ")
    SCHEDULE_FILE: str = "schedule.xlsx"

settings = Settings()
