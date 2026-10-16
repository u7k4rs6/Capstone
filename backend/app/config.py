from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "StockRoom API"
    app_version: str = "1.0.0"
    database_url: str = "postgresql+psycopg://stockroom:stockroom@localhost:5432/stockroom"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
