import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent import BrowserAgent
from src.actions import AgentAction


@pytest.fixture
def output_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.predict = MagicMock(return_value=AgentAction(action_type="finish", summary="Done"))
    llm.predict_text = MagicMock(return_value=AgentAction(action_type="finish", summary="Done"))
    return llm


@pytest.fixture
def mock_browser():
    browser = AsyncMock()
    page = MagicMock()
    page.url = "about:blank"
    page.wait_for_timeout = AsyncMock()
    context = MagicMock()
    context.pages = [page]
    browser._page = page
    browser._context = context
    browser.launch = AsyncMock()
    browser.navigate = AsyncMock()
    browser.screenshot = AsyncMock()
    browser.get_interactive_elements = AsyncMock(return_value=([], {}))
    browser.get_text_snapshot = AsyncMock(return_value=("URL: about:blank\nElements:\n  [1] button: OK", {1: {"cx": 10, "cy": 10, "tag": "button", "text": "OK"}}))
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def agent_patches(mock_browser, mock_llm):
    return (
        patch("src.agent.BrowserController", return_value=mock_browser),
        patch("src.agent.create_llm", return_value=mock_llm),
        patch("src.agent.draw_overlay", return_value=("annotated.jpg", {})),
        patch("src.agent.extract_page_context", new_callable=AsyncMock, return_value={}),
        patch("src.agent.format_page_context", return_value=""),
    )


@pytest.mark.asyncio
async def test_agent_run_finish(output_dir, mock_llm, mock_browser, agent_patches):
    with agent_patches[0], agent_patches[1], agent_patches[2], agent_patches[3], agent_patches[4]:
        agent = BrowserAgent(task="test", start_url="about:blank", output_dir=output_dir, max_steps=3)
        result = await agent.run()
        assert result["success"] is True
        assert result["steps_taken"] == 1


@pytest.mark.asyncio
async def test_agent_text_mode_finish(output_dir, mock_llm, mock_browser, agent_patches):
    with agent_patches[0], agent_patches[1], agent_patches[2], agent_patches[3], agent_patches[4]:
        agent = BrowserAgent(task="test", start_url="about:blank", output_dir=output_dir, max_steps=3, text_mode=True)
        result = await agent.run()
        assert result["success"] is True
        assert result["steps_taken"] == 1
        mock_llm.predict_text.assert_called_once()


@pytest.mark.asyncio
async def test_agent_retry_then_finish(output_dir, mock_browser, agent_patches):
    llm = MagicMock()
    llm.predict = MagicMock(side_effect=[
        AgentAction(action_type="click", element_display_id=1, reasoning="click it"),
        AgentAction(action_type="finish", summary="Done"),
    ])
    agent_patches = (
        patch("src.agent.BrowserController", return_value=mock_browser),
        patch("src.agent.create_llm", return_value=llm),
        patch("src.agent.draw_overlay", return_value=("annotated.jpg", {1: {"tag": "button"}})),
        patch("src.agent.extract_page_context", new_callable=AsyncMock, return_value={}),
        patch("src.agent.format_page_context", return_value=""),
    )
    el_mock = MagicMock()
    el_mock.cx = 10
    el_mock.cy = 10
    el_mock.tag = "button"
    el_mock.text = "OK"
    el_mock.selector = "button.ok"
    mock_browser.get_interactive_elements = AsyncMock(return_value=([el_mock], {1: el_mock}))
    mock_browser.click_by_coords = AsyncMock(side_effect=[Exception("boom"), None])

    with agent_patches[0], agent_patches[1], agent_patches[2], agent_patches[3], agent_patches[4]:
        agent = BrowserAgent(task="test", start_url="about:blank", output_dir=output_dir, max_steps=3)
        result = await agent.run()
        assert result["success"] is True


@pytest.mark.asyncio
async def test_agent_circuit_breaker(output_dir, mock_browser, agent_patches):
    llm = MagicMock()
    llm.predict = MagicMock(return_value=AgentAction(action_type="click", element_display_id=99, reasoning="click"))
    agent_patches = (
        patch("src.agent.BrowserController", return_value=mock_browser),
        patch("src.agent.create_llm", return_value=llm),
        patch("src.agent.draw_overlay", return_value=("annotated.jpg", {})),
        patch("src.agent.extract_page_context", new_callable=AsyncMock, return_value={}),
        patch("src.agent.format_page_context", return_value=""),
    )
    el_mock = MagicMock()
    el_mock.cx = 10
    el_mock.cy = 10
    el_mock.tag = "button"
    el_mock.text = "OK"
    el_mock.selector = "button.ok"
    mock_browser.get_interactive_elements = AsyncMock(return_value=([el_mock], {1: el_mock}))

    with agent_patches[0], agent_patches[1], agent_patches[2], agent_patches[3], agent_patches[4]:
        agent = BrowserAgent(task="test", start_url="about:blank", output_dir=output_dir, max_steps=5)
        result = await agent.run()
        assert result["success"] is False
        assert result["steps_taken"] == 3


@pytest.mark.asyncio
async def test_agent_resume(output_dir, mock_browser, agent_patches):
    state_path = Path(output_dir) / "agent_state.json"
    state_path.write_text(
        '{"history": [{"step": 1, "observation": "ok", "action": {"action_type": "navigate"}}], '
        '"current_url": "about:blank", "task": "test"}',
        encoding="utf-8",
    )

    llm = MagicMock()
    llm.predict = MagicMock(return_value=AgentAction(action_type="finish", summary="Done"))
    agent_patches = (
        patch("src.agent.BrowserController", return_value=mock_browser),
        patch("src.agent.create_llm", return_value=llm),
        patch("src.agent.draw_overlay", return_value=("annotated.jpg", {})),
        patch("src.agent.extract_page_context", new_callable=AsyncMock, return_value={}),
        patch("src.agent.format_page_context", return_value=""),
    )

    with agent_patches[0], agent_patches[1], agent_patches[2], agent_patches[3], agent_patches[4]:
        agent = BrowserAgent(task="test", output_dir=output_dir, resume=True, max_steps=3)
        assert len(agent.history) == 1
        result = await agent.run()
        assert result["success"] is True
