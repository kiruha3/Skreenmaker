import asyncio
import os
from typing import Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import tempfile
import base64

from src.server import app as server_app, get_session
from src.agent import BrowserAgent


# Монтируем server routes под тем же приложением
app = server_app

# Шаблоны
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

_active_agent: Optional[BrowserAgent] = None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/agent_screenshot")
async def agent_screenshot():
    global _active_agent
    if not _active_agent:
        return {"status": "error", "message": "Agent not running"}
    from src.overlay import draw_overlay
    with tempfile.NamedTemporaryFile(suffix="_raw.jpg", delete=False) as tmp:
        raw_path = tmp.name
    with tempfile.NamedTemporaryFile(suffix="_ann.jpg", delete=False) as tmp:
        ann_path = tmp.name
    try:
        await _active_agent.browser.screenshot(raw_path)
        elements, elements_map = await _active_agent.browser.get_interactive_elements()
        draw_overlay(raw_path, elements, ann_path)
        with open(ann_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")
        return {"image": b64_img, "elements": {str(k): v for k, v in elements_map.items()}}
    finally:
        for p in (raw_path, ann_path):
            try:
                os.unlink(p)
            except Exception:
                pass


@app.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    global _active_agent
    await websocket.accept()
    try:
        msg = await websocket.receive_json()

        def on_event(event_type: str, payload: dict):
            asyncio.create_task(websocket.send_json({"type": event_type, **payload}))

        from src.config import load_config

        cfg = load_config(None)
        provider = (msg.get("provider") or cfg.llm_provider).lower()
        api_key = msg.get("api_key") or cfg.api_key
        model = msg.get("model") or cfg.model
        base_url = msg.get("base_url") or cfg.base_url
        output_dir = msg.get("output_dir") or cfg.output_dir
        max_steps = msg.get("max_steps") if msg.get("max_steps") is not None else cfg.max_steps

        if provider == "openai" and not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
        if provider == "kimi" and not api_key:
            api_key = os.environ.get("MOONSHOT_API_KEY")
        if provider == "anthropic" and not api_key:
            api_key = os.environ.get("ANTHROPIC_API_KEY")

        _active_agent = BrowserAgent(
            task=msg.get("task", ""),
            start_url=msg.get("url"),
            headless=msg.get("headless", True),
            max_steps=max_steps,
            output_dir=output_dir,
            llm_provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            text_mode=msg.get("text_mode", False),
            on_event=on_event,
            screenshot_on_demand=msg.get("screenshot_on_demand", False),
        )
        result = await _active_agent.run()
        await websocket.send_json({"type": "finish", **result})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        _active_agent = None
        try:
            await websocket.close()
        except Exception:
            pass
