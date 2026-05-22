import re
from typing import Any, Optional
from playwright.async_api import Page


class AssertResult:
    """Результат выполнения assert-шага."""

    def __init__(self, passed: bool, message: str, actual: Any = None):
        self.passed = passed
        self.message = message
        self.actual = actual

    def to_dict(self) -> dict:
        return {"passed": self.passed, "message": self.message, "actual": self.actual}


async def evaluate_assert(page: Page, condition: str, expected: Optional[str] = None) -> AssertResult:
    """Выполняет assert-условие против текущей страницы браузера.

    Поддерживаемые условия:
    - url_contains('/path')      — проверка подстроки в URL
    - element_exists('#id')      — проверка наличия элемента в DOM
    - text_contains('строка')    — проверка текста внутри <body>
    - title_is('Title')          — точное сравнение заголовка страницы

    Args:
        page: страница Playwright
        condition: строка условия
        expected: ожидаемое значение (опционально, зарезервировано для будущих условий)

    Returns:
        AssertResult с полями passed, message, actual
    """
    condition = condition.strip()

    # url_contains('/path')
    m = re.match(r"url_contains\(['\"]?(.+?)['\"]?\)", condition)
    if m:
        url = page.url
        target = m.group(1)
        passed = target in url
        return AssertResult(
            passed,
            f"URL contains '{target}'" if passed else f"URL '{url}' does not contain '{target}'",
            url,
        )

    # element_exists('#selector')
    m = re.match(r"element_exists\(['\"]?(.+?)['\"]?\)", condition)
    if m:
        selector = m.group(1)
        try:
            el = await page.query_selector(selector)
            passed = el is not None
            return AssertResult(
                passed,
                f"Element '{selector}' exists" if passed else f"Element '{selector}' not found",
            )
        except Exception as e:
            return AssertResult(False, f"Error checking element '{selector}': {e}")

    # text_contains('str')
    m = re.match(r"text_contains\(['\"]?(.+?)['\"]?\)", condition)
    if m:
        text = m.group(1)
        body = await page.inner_text("body")
        passed = text in body
        return AssertResult(
            passed,
            f"Body contains '{text}'" if passed else f"Body does not contain '{text}'",
            body[:200],
        )

    # title_is('Title')
    m = re.match(r"title_is\(['\"]?(.+?)['\"]?\)", condition)
    if m:
        expected_title = m.group(1)
        title = await page.title()
        passed = title == expected_title
        return AssertResult(
            passed,
            f"Title is '{expected_title}'" if passed else f"Title is '{title}', expected '{expected_title}'",
            title,
        )

    return AssertResult(False, f"Unknown assert condition: {condition}")
