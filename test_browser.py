import asyncio
import os
from src.browser import BrowserController
from src.overlay import draw_overlay


async def main():
    os.makedirs("output", exist_ok=True)
    browser = BrowserController()
    await browser.launch(headless=True)
    try:
        await browser.navigate("https://example.com")
        raw_path = "output/test_raw.jpg"
        await browser.screenshot(raw_path)
        print(f"Screenshot saved: {raw_path}")

        elements = await browser.get_interactive_elements()
        print(f"Found {len(elements)} interactive elements")
        for el in elements[:10]:
            print(f"  {el.element_id}. [{el.tag}] '{el.text}' at ({el.x:.0f}, {el.y:.0f})")

        annotated_path = "output/test_annotated.jpg"
        draw_overlay(raw_path, elements, annotated_path)
        print(f"Annotated screenshot saved: {annotated_path}")
    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
