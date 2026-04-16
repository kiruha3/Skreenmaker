import asyncio
import os
from src.browser import BrowserController
from src.overlay import draw_overlay
from src.config import load_config


async def main():
    os.makedirs("output/phase1", exist_ok=True)

    # Тест конфигурации
    cfg = load_config()
    print(f"Config loaded: viewport={cfg.viewport_width}x{cfg.viewport_height}, model={cfg.model}")

    browser = BrowserController(viewport_width=cfg.viewport_width, viewport_height=cfg.viewport_height)
    await browser.launch(headless=True)
    try:
        await browser.navigate("https://example.com")
        raw_path = "output/phase1/test_raw.jpg"
        await browser.screenshot(raw_path)
        print(f"Screenshot saved: {raw_path}")

        elements, elements_map = await browser.get_interactive_elements()
        print(f"Found {len(elements)} interactive elements (stable IDs)")
        for el in elements:
            print(f"  display_id={el.display_id}, hash={el.stable_hash}, [{el.tag}] '{el.text}'")

        annotated_path = "output/phase1/test_annotated.jpg"
        _, overlay_map = draw_overlay(raw_path, elements, annotated_path)
        print(f"Annotated screenshot saved: {annotated_path}")

        # Проверяем стабильность хешей
        elements2, elements_map2 = await browser.get_interactive_elements()
        for e1, e2 in zip(elements, elements2):
            assert e1.stable_hash == e2.stable_hash, f"Hash mismatch for {e1.display_id}"
        print("Hash stability: OK")

    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
