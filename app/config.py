from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM provider: "openai" or "ollama"
    llm_provider: str = "ollama"
    openai_api_key: str = ""
    llm_model: str = "llama3.1:8b"
    ollama_base_url: str = "http://localhost:11434/v1"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    require_human_approval: bool = True
    log_level: str = "INFO"
    db_path: str = "thirteenth_man.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
