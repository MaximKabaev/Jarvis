from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "Friday AI Assistant"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://friday:friday@localhost:5432/friday"

    # JWT Authentication
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_days: int = 7

    # CORS
    allowed_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
