from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    openweather_api_key: str = ""
    database_url: str = ""
    postgres_user: str = "aqi_user"
    postgres_password: str = ""
    postgres_db: str = "aqi_db"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    alert_email_from: str = ""
    alert_email_to: str = ""
    cors_origins: list[str] = ["http://localhost:5173"]
    log_format: str = "console"  # set to "json" in production


settings = Settings()
