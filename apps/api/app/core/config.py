import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Ruta dinámica al .env de la raíz (Salud Copilot)
# config.py está en: apps/api/app/core/config.py (5 niveles)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
ENV_FILE_PATH = ROOT_DIR / ".env"

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str
    environment: str = "development"
    log_level: str = "debug"
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_verify_token: str = "saludcopilot_verify"
    llm_api_key: str = ""
    cors_allowed_origins: str = "http://localhost:3000"
    bot_base_url: str = "http://localhost:8001"
    internal_bot_token: str = "saludcopilot-internal-token-change-in-prod"

    class Config:
        env_file = str(ENV_FILE_PATH)
        case_sensitive = False
        extra = "ignore"


settings = Settings()
