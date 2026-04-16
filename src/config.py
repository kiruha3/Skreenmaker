import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: Literal["openai", "ollama", "anthropic"] = Field(default="openai")
    api_key: Optional[str] = Field(default=None)
    model: str = Field(default="gpt-4o")
    base_url: Optional[str] = Field(default=None)

    viewport_width: int = Field(default=1280)
    viewport_height: int = Field(default=720)
    headless: bool = Field(default=True)
    output_dir: str = Field(default="output")
    max_steps: int = Field(default=15)

    @property
    def resolved_output_dir(self) -> Path:
        return Path(self.output_dir).resolve()


def load_config(yaml_path: Optional[str] = None) -> AppConfig:
    """
    Загружает конфигурацию: сначала .env, затем опциональный YAML.
    YAML имеет приоритет над .env для явно заданных полей.
    """
    cfg = AppConfig()

    if yaml_path and os.path.exists(yaml_path):
        import yaml
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # Переопределяем только те поля, что есть в YAML
        updates = {k: v for k, v in data.items() if v is not None}
        if updates:
            cfg = cfg.model_copy(update=updates)

    # Fallback для Ollama base_url
    if cfg.llm_provider == "ollama" and not cfg.base_url:
        cfg.base_url = "http://localhost:11434/v1"

    return cfg
