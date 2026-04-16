import asyncio
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
        self._pending_dialog_action: str = "dismiss"

    def _on_dialog(self, dialog):
        action = getattr(self, "_pending_dialog_action", "dismiss")
        if action == "accept":
            asyncio.get_event_loop().create_task(dialog.accept())
        else:
            asyncio.get_event_loop().create_task(dialog.dismiss())

    async def launch(self, headless: bool = True):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless)
        self._context = await self._browser.new_context(
            viewport={"width": self.viewport_width, "height": self.viewport_height},
        )
        self._page = await self._context.new_page()
        self._page.on("dialog", self._on_dialog)

    async def set_dialog_action(self, action: str):
        self._pending_dialog_action = action

    async def keyboard_type(self, text: str):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.keyboard.type(text)
        await smart_wait(self._page, "type")

    async def mouse_click(self, x: float, y: float, button: str = "left"):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.mouse.click(x, y, button=button)
        await smart_wait(self._page, "click")

    async def wait_for_timeout(self, ms: int):
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.wait_for_timeout(ms)

    async def bring_to_front_tab(self, idx: int):
        if not self._context or not self._page:
            raise RuntimeError("Browser not launched")
        pages = self._context.pages
        if 0 <= idx < len(pages):
            self._page = pages[idx]
            await self._page.bring_to_front()

    async def save_storage_state(self, path: str):
        if self._context:
            await self._context.storage_state(path=path)

    async def load_storage_state(self, path: str):
        if not self._browser:
            raise RuntimeError("Browser not launched")
        if self._context:
            await self._context.close()
        self._context = await self._browser.new_context(
            viewport={"width": self.viewport_width, "height": self.viewport_height},
            storage_state=path,
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

        js_code = """
        (viewportWidth, viewportHeight) => {
            const selectors = [
                "a", "button", "input", "textarea", "select",
                "label[for]", "[contenteditable='true']",
                "[role='button']", "[role='link']", "[role='checkbox']",
                "[role='radio']", "[role='tab']", "[role='menuitem']",
                "[role='switch']", "[role='searchbox']", "[role='textbox']",
            ];
            const nodes = Array.from(document.querySelectorAll(selectors.join(", ")));
            const results = [];
            for (const el of nodes) {
                const rect = el.getBoundingClientRect();
                if (rect.width < 5 || rect.height < 5) continue;
                if (rect.right < 0 || rect.bottom < 0) continue;
                if (rect.left > viewportWidth || rect.top > viewportHeight) continue;
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
                let tag = el.tagName.toLowerCase();
                if (el.hasAttribute('role')) {
                    tag = el.getAttribute('role');
                }
                const txt = (el.innerText || el.textContent || el.value || el.placeholder || '').trim().slice(0, 50);
                let sel = el.tagName.toLowerCase();
                if (el.id) sel = '#' + el.id;
                else {
                    const cls = Array.from(el.classList).slice(0,2).join('.');
                    if (cls) sel = el.tagName.toLowerCase() + '.' + cls;
                }
                results.push({
                    tag: tag,
                    text: txt,
                    selector: sel,
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                    is_visible: true,
                });
            }
            return results;
        }
        """
        raw_elements = await self._page.evaluate(js_code, [self.viewport_width, self.viewport_height])
        return track_elements(raw_elements)

    async def close(self):
        try:
            if self._browser and self._browser.is_connected():
                await self._browser.close()
        except Exception:
            pass
        finally:
            try:
                if self._playwright:
                    await self._playwright.stop()
            except Exception:
                pass
