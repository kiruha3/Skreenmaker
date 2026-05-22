"""Интеграционные тесты UI Enhancement: Variables + Assertions."""
import pytest
from unittest.mock import AsyncMock

from src.variable_resolver import resolve_steps
from src.assert_engine import evaluate_assert


def test_variable_integration():
    """Переменные подставляются во все строковые поля шагов."""
    steps = [
        {"action_type": "navigate", "url": "${host}/login"},
        {"action_type": "type", "text": "${user}"},
    ]
    variables = {"host": "https://app.com", "user": "admin"}
    result = resolve_steps(steps, variables)
    assert result[0]["url"] == "https://app.com/login"
    assert result[1]["text"] == "admin"


def test_variable_preserves_non_strings():
    """Немодифицируемые поля (числа, bool) не трогаются."""
    steps = [
        {"action_type": "click", "element_display_id": 5, "text": "${x}"},
    ]
    result = resolve_steps(steps, {"x": "hello"})
    assert result[0]["element_display_id"] == 5
    assert result[0]["text"] == "hello"


@pytest.mark.asyncio
async def test_assert_integration_pass():
    """Assert проходит при совпадении условия."""
    page = AsyncMock()
    page.url = "https://example.com/success"
    r = await evaluate_assert(page, "url_contains('/success')")
    assert r.passed is True
    assert "/success" in r.message


@pytest.mark.asyncio
async def test_assert_integration_fail():
    """Assert падает при несовпадении."""
    page = AsyncMock()
    page.url = "https://example.com/fail"
    r = await evaluate_assert(page, "url_contains('/success')")
    assert r.passed is False
    assert "does not contain" in r.message


@pytest.mark.asyncio
async def test_assert_element_exists():
    """Проверка наличия элемента в DOM."""
    page = AsyncMock()
    page.query_selector.return_value = AsyncMock()
    r = await evaluate_assert(page, "element_exists('#submit')")
    assert r.passed is True


@pytest.mark.asyncio
async def test_assert_text_contains():
    """Проверка текста на странице."""
    page = AsyncMock()
    page.inner_text.return_value = "Welcome to Dashboard"
    r = await evaluate_assert(page, "text_contains('Dashboard')")
    assert r.passed is True
