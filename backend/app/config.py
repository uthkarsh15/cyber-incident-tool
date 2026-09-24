from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/cyber_incidents"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/cyber_incidents"
    redis_url: str = "redis://localhost:6379/0"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    scraper_interval_minutes: int = 30
    scraper_rate_limit_seconds: int = 2

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
