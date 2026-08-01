from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "VRAV AI — Sovereign Agentic Orchestrator"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.1"

    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "meta-llama/llama-3.1-70b-instruct"

    bggpt_model: str = "bggpt"
    bggpt_endpoint: Optional[str] = None

    log_encryption_key: Optional[str] = None
    max_prompt_length: int = 32000
    enable_prompt_injection_shield: bool = True
    enable_code_safety_filter: bool = True

    serper_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None

    log_level: str = "INFO"
    encrypted_log_path: str = "logs/secure_events.log"


settings = Settings()
