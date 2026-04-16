import asyncio
import os
from pathlib import Path

import pytest
import pytest_asyncio

from src.browser import BrowserController
from src.overlay import draw_overlay
from src.report_generator import generate_report


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest_asyncio.fixture
async def browser():
    b = BrowserController(viewport_width=1280, viewport_height=720)
    await b.launch(headless=True)
    yield b
    await b.close()


@pytest.mark.asyncio
async def test_walkthrough_dashboard(browser, tmp_path):
    url = f"file:///{FIXTURES_DIR / 'dashboard.html'}"
    await browser.navigate(url)

    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    before_dir.mkdir()
    after_dir.mkdir()

    elements, elements_map = await browser.get_interactive_elements()
    assert len(elements) >= 5

    steps = []
    # Кликаем по первому элементу
    first = elements[0]
    before = before_dir / f"step_01.jpg"
    after = after_dir / f"step_01.jpg"
    await browser.screenshot(str(before))
    await browser.click_by_coords(first.cx, first.cy)
    await browser.screenshot(str(after))

    steps.append({
        "step": 1,
        "action": "click",
        "element": f"{first.display_id} {first.tag}",
        "result": "Clicked",
        "before_image": before.name,
        "after_image": after.name,
        "has_change": True,
    })

    report_path = tmp_path / "report.html"
    generate_report(steps, str(report_path), str(before_dir), str(after_dir))
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "SkreenMaker Walkthrough Report" in content
    assert "Steps: 1" in content
