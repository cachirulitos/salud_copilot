from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_ENV = str(Path(__file__).parent.parent.parent / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ROOT_ENV,
        case_sensitive=False,
        extra="ignore",
    )

    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_verify_token: str = "saludcopilot_verify"
    llm_api_key: str = ""
    api_base_url: str = "http://localhost:8000"
    internal_api_token: str = "saludcopilot-internal-token-change-in-prod"
    internal_bot_token: str = "saludcopilot-internal-token-change-in-prod"
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()
