from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./smartfood.db"
    secret_key: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Seed admin (used only by `python -m app.seed`)
    admin_email: str = ""
    admin_password: str = ""

    # LLM settings (used in step 7)
    llm_api_key: str = ""
    llm_api_url: str = ""
    llm_model: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()