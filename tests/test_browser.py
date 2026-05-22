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


@pytest.mark.asyncio
async def test_get_text_snapshot(browser):
    url = f"file:///{FIXTURES_DIR / 'login_form.html'}"
    await browser.navigate(url)
    snapshot, elements_map = await browser.get_text_snapshot()
    assert isinstance(snapshot, str)
    assert "URL:" in snapshot
    assert "Elements:" in snapshot
    assert len(elements_map) > 0


@pytest.mark.asyncio
async def test_click_by_index(browser):
    url = f"file:///{FIXTURES_DIR / 'login_form.html'}"
    await browser.navigate(url)
    # На login_form.html порядок элементов: input#email, input#password, button, a
    await browser.click_by_index(1)
    # После клика на поле email фокус должен быть на нем (проверим через активный элемент)
    active = await browser._page.evaluate("() => document.activeElement.id")
    assert active == "email"


@pytest.mark.asyncio
async def test_type_by_index(browser):
    url = f"file:///{FIXTURES_DIR / 'login_form.html'}"
    await browser.navigate(url)
    await browser.type_by_index(1, "hello@example.com")
    value = await browser._page.input_value("#email")
    assert value == "hello@example.com"


@pytest.mark.asyncio
async def test_click_with_fallback_by_stable_hash(browser):
    url = f"file:///{FIXTURES_DIR / 'login_form.html'}"
    await browser.navigate(url)
    elements, elements_map = await browser.get_interactive_elements()
    email_el = next(e for e in elements if e.tag == "input" and "email" in e.selector)
    # Передаём неверный индекс, но правильный stable_hash — должен сработать fallback
    await browser.click_with_fallback(999, stable_hash=email_el.stable_hash)
    active = await browser._page.evaluate("() => document.activeElement.id")
    assert active == "email"


@pytest.mark.asyncio
async def test_click_with_fallback_by_selector(browser):
    url = f"file:///{FIXTURES_DIR / 'login_form.html'}"
    await browser.navigate(url)
    elements, elements_map = await browser.get_interactive_elements()
    email_el = next(e for e in elements if e.tag == "input" and "email" in e.selector)
    await browser.click_with_fallback(999, selector=email_el.selector)
    active = await browser._page.evaluate("() => document.activeElement.id")
    assert active == "email"


@pytest.mark.asyncio
async def test_type_with_fallback_by_stable_hash(browser):
    url = f"file:///{FIXTURES_DIR / 'login_form.html'}"
    await browser.navigate(url)
    elements, elements_map = await browser.get_interactive_elements()
    email_el = next(e for e in elements if e.tag == "input" and "email" in e.selector)
    await browser.type_with_fallback(999, "fallback@example.com", stable_hash=email_el.stable_hash)
    value = await browser._page.input_value("#email")
    assert value == "fallback@example.com"


@pytest.mark.asyncio
async def test_get_interactive_elements_detects_pointer_cursor_divs(browser):
    """Div elements with cursor:pointer (tree nodes, cards, custom buttons) must be detected."""
    url = f"file:///{FIXTURES_DIR / 'tree_view.html'}"
    await browser.navigate(url)
    elements, elements_map = await browser.get_interactive_elements()
    texts = [e.text for e in elements]
    # tree-node divs with cursor:pointer
    assert "Project Alpha" in texts
    assert "Project Beta" in texts
    # action-btn div with cursor:pointer
    assert "Create New" in texts
    # card div with cursor:pointer
    assert "Card One" in texts
    # Real button should also be detected
    assert "Real Button" in texts
    # plain-div (no cursor:pointer) should NOT be detected
    assert "Not clickable" not in texts
    # Should find 5 elements total: 2 tree-node + action-btn + card + button
    # plain-div (no cursor:pointer) is correctly excluded
    assert len(elements) == 5
