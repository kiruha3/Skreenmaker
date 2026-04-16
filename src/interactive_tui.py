import argparse
import webbrowser

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Запуск Web TUI для SkreenMaker")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Хост")
    parser.add_argument("--port", type=int, default=8080, help="Порт")
    parser.add_argument("--no-open", action="store_true", help="Не открывать браузер автоматически")
    args = parser.parse_args()

    from src.tui_web import app

    url = f"http://{args.host}:{args.port}"
    print(f"Starting SkreenMaker TUI at {url}")
    if not args.no_open:
        webbrowser.open(url)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
