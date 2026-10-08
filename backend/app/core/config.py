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
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""
    oauth_public_base_url: str = ""
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    x_oauth_client_id: str = ""
    x_oauth_client_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
