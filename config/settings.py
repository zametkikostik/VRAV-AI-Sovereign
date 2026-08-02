from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "VRAV AI — Sovereign Agentic Orchestrator"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    data_dir: str = "data"

    # Auth: off | optional | required
    auth_mode: str = "optional"

    # Ollama (local sovereign) — default path when no commercial keys
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.1"
    prefer_ollama: bool = True

    # OpenRouter (optional commercial open-weight)
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "meta-llama/llama-3.1-70b-instruct"

    # BgGPT / national models (via Ollama or custom endpoint)
    bggpt_model: str = "bggpt"
    bggpt_endpoint: Optional[str] = None

    # Security
    log_encryption_key: Optional[str] = None
    max_prompt_length: int = 32000
    enable_prompt_injection_shield: bool = True
    enable_code_safety_filter: bool = True
    max_tool_rounds: int = 6

    # Search / Fact-check
    serper_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None

    # Logging
    log_level: str = "INFO"
    encrypted_log_path: str = "logs/secure_events.log"

    def ensure_dirs(self) -> None:
        root = Path(self.data_dir)
        for sub in ("", "workspace", "skills", "memory", "auth", "corpus", "rag"):
            (root / sub if sub else root).mkdir(parents=True, exist_ok=True)
        Path("logs").mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
