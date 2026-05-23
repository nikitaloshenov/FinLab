from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FinLab"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str

    moex_base_url: str = "https://iss.moex.com/iss"
    moex_default_engine: str = "stock"
    moex_default_market: str = "shares"
    moex_default_board: str = "TQBR"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()