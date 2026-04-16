import argparse
import asyncio
import os
import sys

from src.agent import BrowserAgent
from src.config import load_config


def main():
    parser = argparse.ArgumentParser(description="Автономный агент для браузера")
    parser.add_argument("--url", type=str, required=True, help="Стартовый URL")
    parser.add_argument("--task", type=str, required=True, help="Задача для агента")
    parser.add_argument("--headless", action="store_true", default=True, help="Запускать браузер без GUI")
    parser.add_argument("--no-headless", action="store_true", dest="headless_false", help="Показывать окно браузера")
    parser.add_argument("--max-steps", type=int, default=None, help="Максимальное число шагов")
    parser.add_argument("--output-dir", type=str, default=None, help="Папка для скриншотов")
    parser.add_argument("--provider", type=str, default=None, help="LLM провайдер: openai | ollama | anthropic")
    parser.add_argument("--model", type=str, default=None, help="Модель Vision")
    parser.add_argument("--api-key", type=str, default=None, help="API ключ")
    parser.add_argument("--base-url", type=str, default=None, help="Base URL для API")
    parser.add_argument("--config", type=str, default=None, help="Путь к config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)

    provider = (args.provider or cfg.llm_provider).lower()
    api_key = args.api_key or cfg.api_key
    model = args.model or cfg.model
    base_url = args.base_url or cfg.base_url
    output_dir = args.output_dir or cfg.output_dir
    max_steps = args.max_steps if args.max_steps is not None else cfg.max_steps

    if provider == "openai" and not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    if provider == "anthropic" and not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")

    if provider in ("openai", "anthropic") and not api_key:
        print(f"Ошибка: нужен API ключ для {provider}. Установите env var или передайте --api-key")
        sys.exit(1)

    headless = False if args.headless_false else args.headless

    agent = BrowserAgent(
        task=args.task,
        start_url=args.url,
        headless=headless,
        max_steps=max_steps,
        output_dir=output_dir,
        llm_provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
    )

    result = asyncio.run(agent.run())
    print(result)


if __name__ == "__main__":
    main()
