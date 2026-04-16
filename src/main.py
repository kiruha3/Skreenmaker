import argparse
import asyncio
import os
import sys

from src.agent import BrowserAgent


def main():
    parser = argparse.ArgumentParser(description="Автономный агент для браузера")
    parser.add_argument("--url", type=str, required=True, help="Стартовый URL")
    parser.add_argument("--task", type=str, required=True, help="Задача для агента")
    parser.add_argument("--headless", action="store_true", default=True, help="Запускать браузер без GUI")
    parser.add_argument("--no-headless", action="store_true", dest="headless_false", help="Показывать окно браузера")
    parser.add_argument("--max-steps", type=int, default=15, help="Максимальное число шагов")
    parser.add_argument("--output-dir", type=str, default="output", help="Папка для скриншотов")
    parser.add_argument("--model", type=str, default="gpt-4o", help="Модель OpenAI Vision")
    parser.add_argument("--api-key", type=str, default=os.environ.get("OPENAI_API_KEY"), help="OpenAI API ключ")

    args = parser.parse_args()

    if not args.api_key:
        print("Ошибка: нужен OpenAI API ключ. Установите OPENAI_API_KEY или передайте --api-key")
        sys.exit(1)

    headless = False if args.headless_false else args.headless

    agent = BrowserAgent(
        task=args.task,
        start_url=args.url,
        headless=headless,
        max_steps=args.max_steps,
        output_dir=args.output_dir,
        api_key=args.api_key,
        model=args.model,
    )

    result = asyncio.run(agent.run())
    print(result)


if __name__ == "__main__":
    main()
