import os
import tempfile
from pathlib import Path

from src.config import load_config, AppConfig


def test_load_config_defaults():
    cfg = load_config()
    assert cfg.llm_provider == "openai"
    assert cfg.model == "gpt-4o"
    assert cfg.viewport_width == 1280
    assert cfg.viewport_height == 720
    assert cfg.headless is True
    assert cfg.max_steps == 15


def test_load_config_yaml_override():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write("model: gpt-4o-mini\nmax_steps: 25\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.model == "gpt-4o-mini"
        assert cfg.max_steps == 25
        assert cfg.llm_provider == "openai"  # unchanged default
    finally:
        os.unlink(path)


def test_load_config_ollama_fallback_base_url():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write("llm_provider: ollama\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.llm_provider == "ollama"
        assert cfg.base_url == "http://localhost:11434/v1"
    finally:
        os.unlink(path)


def test_resolved_output_dir():
    cfg = AppConfig(output_dir="output")
    assert cfg.resolved_output_dir.is_absolute()
