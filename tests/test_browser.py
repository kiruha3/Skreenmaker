import asyncio
import os
from pathlib import Path

import pytest
import pytest_asyncio

from src.browser import BrowserController


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest_asyncio.fixture
async def browser():
    b = BrowserController(viewport_width=1280, viewport_height=720)
    await b.launch(headless=True)
    yield b
    await b.close()


@pytest.mark.asyncio
async def test_navigate_to_fixture(browser):
    url = f"file:///{FIXTURES_DIR / 'login_form.html'}"
    await browser.navigate(url)
    title = await browser._page.title()
    assert title == "Login"


@pytest.mark.asyncio
async def test_get_interactive_elements_login(browser):
    url = f"file:///{FIXTURES_DIR / 'login_form.html'}"
    await browser.navigate(url)
    elements, elements_map = await browser.get_interactive_elements()
    tags = [e.tag for e in elements]
    assert "input" in tags
    assert "button" in tags
    assert "a" in tags
    # Должно быть 4 интерактивных элемента
    assert len(elements) == 4


@pytest.mark.asyncio
async def test_click_and_type(browser):
    url = f"file:///{FIXTURES_DIR / 'login_form.html'}"
    await browser.navigate(url)
    elements, elements_map = await browser.get_interactive_elements()
    # Находим поле email (обычно первый input)
    email_el = next(e for e in elements if e.tag == "input" and "email" in e.selector)
    await browser.click_by_coords(email_el.cx, email_el.cy)
    await browser._page.keyboard.type("test@example.com")
    value = await browser._page.input_value("#email")
    assert value == "test@example.com"


@pytest.mark.asyncio
async def test_screenshot(browser, tmp_path):
    url = f"file:///{FIXTURES_DIR / 'login_form.html'}"
    await browser.navigate(url)
    path = tmp_path / "shot.jpg"
    await browser.screenshot(str(path))
    assert path.exists()
    assert path.stat().st_size > 0
