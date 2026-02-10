"""
Конфигурация приложения
Загружает переменные окружения из .env файла
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Telegram Bot
    telegram_bot_token: str
    
    # OpenRouter AI
    openrouter_api_key: str
    openrouter_model: str = "anthropic/claude-3.5-sonnet"
    
    # Supabase Database
    supabase_url: str
    supabase_service_role_key: str
    
    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # Webhook (для деплоя)
    webhook_url: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Глобальный экземпляр настроек
settings = Settings()
