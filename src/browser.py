from typing import List, Optional, Dict, Any, Tuple

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from src.element_tracker import TrackedElement, track_elements
from src.wait_utils import smart_wait


class BrowserController:
    def __init__(self, viewport_width: int = 1280, viewport_height: int = 720):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def launch(self, headless: bool = True):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless)
        self._context = await self._browser.new_context(
            viewport={"width": self.viewport_width, "height": self.viewport_height},
        )
        self._page = await self._context.new_page()

    async def navigate(self, url: str):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.goto(url, wait_until="domcontentloaded")
        await smart_wait(self._page, "navigate")

    async def screenshot(self, path: str):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.screenshot(path=path, type="jpeg", quality=80)

    async def click_by_coords(self, x: float, y: float):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.mouse.click(x, y)
        await smart_wait(self._page, "click")

    async def click_by_selector(self, selector: str):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.click(selector)
        await smart_wait(self._page, "click", selector=selector)

    async def type_text(self, selector: str, text: str):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.fill(selector, text)
        await smart_wait(self._page, "type")

    async def scroll(self, direction: str = "down", amount: int = 300):
        if not self._page:
            raise RuntimeError("Browser not launched")
        if direction == "down":
            await self._page.mouse.wheel(0, amount)
        elif direction == "up":
            await self._page.mouse.wheel(0, -amount)
        elif direction == "left":
            await self._page.mouse.wheel(-amount, 0)
        elif direction == "right":
            await self._page.mouse.wheel(amount, 0)
        await smart_wait(self._page, "scroll")

    async def hover(self, x: float, y: float):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.mouse.move(x, y)
        await smart_wait(self._page, "hover")

    async def press_key(self, key: str):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.keyboard.press(key)
        await smart_wait(self._page, "press_key")

    async def select_option(self, selector: str, value: str):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.select_option(selector, value)
        await smart_wait(self._page, "select_option")

    async def upload_file(self, selector: str, file_path: str):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.set_input_files(selector, file_path)
        await smart_wait(self._page, "upload_file")

    async def get_interactive_elements(self) -> Tuple[List[TrackedElement], Dict[int, TrackedElement]]:
        if not self._page:
            raise RuntimeError("Browser not launched")

        selectors = [
            "a",
            "button",
            "input",
            "textarea",
            "select",
            "[role='button']",
            "[role='link']",
        ]
        combined_selector = ", ".join(selectors)
        elements = await self._page.query_selector_all(combined_selector)

        raw_elements: List[Dict[str, Any]] = []
        for el in elements:
            box = await el.bounding_box()
            if not box:
                continue
            if box["width"] < 5 or box["height"] < 5:
                continue
            if box["x"] + box["width"] < 0 or box["y"] + box["height"] < 0:
                continue
            if box["x"] > self.viewport_width or box["y"] > self.viewport_height:
                continue

            visible = await el.is_visible()
            if not visible:
                continue

            tag = await el.evaluate("el => el.tagName.toLowerCase()")
            text = await el.evaluate(
                """
                el => {
                    const txt = el.innerText || el.textContent || el.value || el.placeholder || '';
                    return txt.trim().slice(0, 50);
                }
                """
            )
            selector = await el.evaluate(
                """
                el => {
                    if (el.id) return '#' + el.id;
                    const classes = Array.from(el.classList).slice(0,2).join('.');
                    if (classes) return el.tagName.toLowerCase() + '.' + classes;
                    return el.tagName.toLowerCase();
                }
                """
            )

            raw_elements.append(
                {
                    "tag": tag,
                    "text": text,
                    "selector": selector,
                    "x": box["x"],
                    "y": box["y"],
                    "width": box["width"],
                    "height": box["height"],
                    "is_visible": visible,
                }
            )

        return track_elements(raw_elements)

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
