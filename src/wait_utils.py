import asyncio
import logging
from typing import Optional

from playwright.async_api import Page, TimeoutError

logger = logging.getLogger(__name__)


async def smart_wait(
    page: Page,
    action_type: str,
    selector: Optional[str] = None,
    timeout: int = 5000,
):
    """
    Умное ожидание в зависимости от типа действия.
    """
    if action_type == "navigate":
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except TimeoutError:
            logger.debug("Timeout waiting for networkidle, falling back to domcontentloaded")
            await page.wait_for_load_state("domcontentloaded", timeout=timeout)
        return

    if action_type == "click":
        if selector:
            try:
                await page.wait_for_selector(selector, state="visible", timeout=2000)
            except TimeoutError:
                logger.debug("Timeout waiting for selector %s", selector)
                pass
        # Даем небольшое время SPA на реакцию
        await page.wait_for_timeout(300)
        return

    if action_type == "type":
        await page.wait_for_timeout(100)
        return

    if action_type == "scroll":
        await page.wait_for_timeout(300)
        return

    if action_type in ("hover", "right_click"):
        await page.wait_for_timeout(200)
        return

    if action_type == "screenshot":
        await page.wait_for_timeout(200)
        return

    # fallback
    await page.wait_for_timeout(300)
