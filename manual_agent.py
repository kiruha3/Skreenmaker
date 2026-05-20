import asyncio
import json
import os
import sys
from pathlib import Path

from src.browser import BrowserController
from src.overlay import draw_overlay


STATE_FILE = Path("manual_state.json")
SCREENSHOT_PATH = Path("manual_current.jpg")
ANNOTATED_PATH = Path("manual_current_annotated.jpg")


async def main():
    browser = BrowserController()
    await browser.launch(headless=False)

    try:
        # Восстанавливаем состояние если есть
        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            current_url = state.get("url", "https://example.test/")
            await browser.navigate(current_url)
            print(f"Resumed at {current_url}")
        else:
            await browser.navigate("https://example.test/")
            print("Navigated to https://example.test/")

        # Делаем скриншот и overlay
        await browser.screenshot(str(SCREENSHOT_PATH))
        elements, elements_map = await browser.get_interactive_elements()
        _, overlay_map = draw_overlay(str(SCREENSHOT_PATH), elements, str(ANNOTATED_PATH))

        # Сохраняем состояние
        state = {
            "url": browser._page.url,
            "elements": {str(k): v for k, v in overlay_map.items()},
        }
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\nScreenshot: {SCREENSHOT_PATH.absolute()}")
        print(f"Annotated:  {ANNOTATED_PATH.absolute()}")
        print(f"Elements ({len(overlay_map)}):")
        for display_id, info in overlay_map.items():
            print(f"  {display_id:2d}. [{info['tag']:10s}] '{info['text'][:40]}'")

        print("\nWaiting for action... (I will read the screenshot and tell you the next step)")

    finally:
        # Не закрываем браузер — пусть висит для следующего шага
        pass


if __name__ == "__main__":
    asyncio.run(main())
