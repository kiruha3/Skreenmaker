import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.server import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_browser():
    browser = AsyncMock()
    page = MagicMock()
    page.url = "about:blank"
    context = MagicMock()
    context.pages = [page]
    browser._page = page
    browser._context = context
    browser.launch = AsyncMock()
    browser.navigate = AsyncMock()
    browser.screenshot = AsyncMock()
    browser.get_interactive_elements = AsyncMock(return_value=([], {}))
    browser.close = AsyncMock()
    return browser


def test_launch(client, mock_browser):
    with patch("src.server.BrowserController", return_value=mock_browser):
        response = client.post("/launch", json={"headless": True, "viewport_width": 1280, "viewport_height": 720})
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_navigate(client, mock_browser):
    with patch("src.server.BrowserController", return_value=mock_browser):
        client.post("/launch", json={"headless": True, "viewport_width": 1280, "viewport_height": 720})
        response = client.post("/navigate", json={"url": "about:blank"})
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_elements(client, mock_browser):
    with patch("src.server.BrowserController", return_value=mock_browser):
        client.post("/launch", json={"headless": True, "viewport_width": 1280, "viewport_height": 720})
        response = client.get("/elements")
        assert response.status_code == 200
        data = response.json()
        assert "elements" in data
        assert "map" in data


def test_screenshot(client, mock_browser):
    with patch("src.server.BrowserController", return_value=mock_browser):
        client.post("/launch", json={"headless": True, "viewport_width": 1280, "viewport_height": 720})
        response = client.get("/screenshot")
        assert response.status_code == 200
        assert "image" in response.json()


def test_act_screenshot(client, mock_browser):
    with patch("src.server.BrowserController", return_value=mock_browser):
        client.post("/launch", json={"headless": True, "viewport_width": 1280, "viewport_height": 720})
        response = client.post("/act", json={"action": {"action_type": "screenshot"}})
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_close(client, mock_browser):
    with patch("src.server.BrowserController", return_value=mock_browser):
        client.post("/launch", json={"headless": True, "viewport_width": 1280, "viewport_height": 720})
        response = client.post("/close")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
