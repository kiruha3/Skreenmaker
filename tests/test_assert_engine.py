import pytest
from unittest.mock import AsyncMock
from src.assert_engine import evaluate_assert, AssertResult


@pytest.fixture
def mock_page():
    p = AsyncMock()
    p.url = "https://example.com/dashboard"
    p.title.return_value = "Dashboard"
    p.inner_text.return_value = "Welcome admin"
    p.query_selector.return_value = AsyncMock()
    return p


@pytest.mark.asyncio
async def test_url_contains_pass(mock_page):
    r = await evaluate_assert(mock_page, "url_contains('/dashboard')")
    assert r.passed is True
    assert "contains" in r.message


@pytest.mark.asyncio
async def test_url_contains_fail(mock_page):
    r = await evaluate_assert(mock_page, "url_contains('/login')")
    assert r.passed is False


@pytest.mark.asyncio
async def test_element_exists_pass(mock_page):
    r = await evaluate_assert(mock_page, "element_exists('#menu')")
    assert r.passed is True


@pytest.mark.asyncio
async def test_element_exists_not_found(mock_page):
    mock_page.query_selector.return_value = None
    r = await evaluate_assert(mock_page, "element_exists('#missing')")
    assert r.passed is False


@pytest.mark.asyncio
async def test_text_contains_pass(mock_page):
    r = await evaluate_assert(mock_page, "text_contains('Welcome')")
    assert r.passed is True


@pytest.mark.asyncio
async def test_title_is_pass(mock_page):
    r = await evaluate_assert(mock_page, "title_is('Dashboard')")
    assert r.passed is True


@pytest.mark.asyncio
async def test_title_is_fail(mock_page):
    r = await evaluate_assert(mock_page, "title_is('Login')")
    assert r.passed is False


@pytest.mark.asyncio
async def test_unknown_condition(mock_page):
    r = await evaluate_assert(mock_page, "invalid_condition")
    assert r.passed is False
    assert "Unknown" in r.message
