from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("./data")
    api_key: str = ""
    app_password: str = ""
    host: str = "0.0.0.0"
    port: int = 8080
    public_url: str = ""
    seed_demo: bool = False
    session_secret: str = ""


settings = Settings()
