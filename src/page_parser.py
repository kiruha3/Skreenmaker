import logging
from typing import Dict, List, Any, TYPE_CHECKING

from playwright.async_api import Page

if TYPE_CHECKING:
    from src.element_tracker import TrackedElement

logger = logging.getLogger(__name__)


async def extract_page_context(page: Page, max_body_chars: int = 2000) -> Dict[str, Any]:
    """
    Извлекает текстовый контекст страницы для подачи в LLM вместе со скриншотом.
    """
    title = await page.title()
    body_text = ""
    try:
        body_text = await page.inner_text("body")
    except Exception as e:
        logger.debug("Failed to extract body text: %s", e)
        pass
    body_text = body_text[:max_body_chars].strip()

    headings: List[str] = []
    try:
        for level in ["h1", "h2", "h3"]:
            els = await page.query_selector_all(level)
            for el in els:
                text = await el.inner_text()
                if text and text.strip():
                    headings.append(f"{level}: {text.strip()}")
    except Exception as e:
        logger.debug("Failed to extract headings: %s", e)
        pass

    links: List[str] = []
    try:
        anchor_els = await page.query_selector_all("a")
        for el in anchor_els:
            text = await el.inner_text()
            href = await el.get_attribute("href") or ""
            if text and text.strip():
                links.append(f"{text.strip()} -> {href}")
    except Exception as e:
        logger.debug("Failed to extract links: %s", e)
        pass
    # Ограничиваем список ссылок
    links = links[:30]

    return {
        "title": title,
        "body_preview": body_text,
        "headings": headings,
        "links": links,
    }


def format_page_context(ctx: Dict[str, Any]) -> str:
    """Форматирует контекст страницы в строку для промпта."""
    lines = [f"Page title: {ctx.get('title', '')}"]
    headings = ctx.get("headings", [])
    if headings:
        lines.append("Headings:")
        for h in headings[:15]:
            lines.append(f"  - {h}")
    links = ctx.get("links", [])
    if links:
        lines.append("Links:")
        for l in links[:20]:
            lines.append(f"  - {l}")
    body = ctx.get("body_preview", "")
    if body:
        lines.append(f"Body preview:\n{body}")
    return "\n".join(lines)


def format_text_snapshot(
    url: str,
    title: str,
    elements: List["TrackedElement"],
    max_elements: int = 100,
    max_body_chars: int = 800,
) -> str:
    """
    Форматирует страницу в компактное текстовое представление для text-mode агента.
    Нумерация элементов совпадает с их display_id.
    """
    lines: List[str] = []
    lines.append(f"URL: {url}")
    lines.append(f"Title: {title}")
    lines.append("")

    if elements:
        lines.append("Elements:")
        for el in elements[:max_elements]:
            tag = el.tag or "element"
            text = (el.text or "").strip()
            desc = f"[{el.display_id}] {tag}"
            if text:
                desc += f": {text}"
            lines.append(f"  {desc}")
        if len(elements) > max_elements:
            lines.append(f"  ... and {len(elements) - max_elements} more elements")
    else:
        lines.append("Elements: (none)")

    lines.append("")
    return "\n".join(lines)
