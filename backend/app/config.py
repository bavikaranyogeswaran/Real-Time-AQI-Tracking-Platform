from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    openweather_api_key: str = ""
    database_url: str = "postgresql+asyncpg://aqi_user:aqi_pass@db:5432/aqi_db"
    postgres_user: str = "aqi_user"
    postgres_password: str = "aqi_pass"
    postgres_db: str = "aqi_db"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    alert_email_from: str = ""
    alert_email_to: str = ""


settings = Settings()
