import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from playwright.async_api import async_playwright, Page, Browser, BrowserContext


@dataclass
class InteractiveElement:
    element_id: int
    tag: str
    text: str
    selector: str
    x: float
    y: float
    width: float
    height: float
    is_visible: bool


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
        await asyncio.sleep(0.5)

    async def screenshot(self, path: str):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.screenshot(path=path, type="jpeg", quality=80)

    async def click_by_coords(self, x: float, y: float):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.mouse.click(x, y)
        await asyncio.sleep(0.5)

    async def click_by_selector(self, selector: str):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.click(selector)
        await asyncio.sleep(0.5)

    async def type_text(self, selector: str, text: str):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.fill(selector, text)
        await asyncio.sleep(0.3)

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
        await asyncio.sleep(0.5)

    async def get_interactive_elements(self) -> List[InteractiveElement]:
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

        result: List[InteractiveElement] = []
        element_id = 1
        for el in elements:
            box = await el.bounding_box()
            if not box:
                continue
            # Skip tiny or off-screen elements
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
            # Build a stable-ish selector
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

            result.append(
                InteractiveElement(
                    element_id=element_id,
                    tag=tag,
                    text=text,
                    selector=selector,
                    x=box["x"],
                    y=box["y"],
                    width=box["width"],
                    height=box["height"],
                    is_visible=visible,
                )
            )
            element_id += 1

        return result

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
