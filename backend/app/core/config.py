from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NOVA AI"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api"

    model_base_url: str = "https://api.openai.com/v1"
    model_api_key: str = ""
    model_name: str = ""
    model_provider_name: str = "openai-compatible"
    database_url: str = "sqlite+aiosqlite:///./nova.db"
    auth_secret: str = ""
    search_base_url: str = ""
    search_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
