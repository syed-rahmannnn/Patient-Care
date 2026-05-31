from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/patient_care"
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_TTL_MIN: int = 60
    REFRESH_TOKEN_TTL_DAYS: int = 14
    WS_TICKET_TTL_SEC: int = 60
    DEVICE_TOKEN_TTL_DAYS: int = 365

    FIREBASE_CREDS_JSON: str = ""

    BOOTSTRAP_ADMIN_EMAIL: str = "admin@patient.care"
    BOOTSTRAP_ADMIN_PASSWORD: str = "Test1234!"


@lru_cache
def get_settings() -> Settings:
    return Settings()
