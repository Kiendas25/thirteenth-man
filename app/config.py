from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    require_human_approval: bool = True
    log_level: str = "INFO"
    db_path: str = "thirteenth_man.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
