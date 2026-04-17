import asyncio
import base64
import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from src.browser import BrowserController
from src.overlay import draw_overlay


app = FastAPI(title="SkreenMaker Browser Server")

# Глобальная сессия браузера
_session: Optional["BrowserSession"] = None
_session_lock = asyncio.Lock()


class BrowserSession:
    def __init__(self, viewport_width: int = 1280, viewport_height: int = 720):
        self.controller = BrowserController(viewport_width, viewport_height)
        self._launched = False

    async def launch(self, headless: bool = True):
        if not self._launched:
            await self.controller.launch(headless=headless)
            self._launched = True

    async def navigate(self, url: str):
        await self.launch()
        await self.controller.navigate(url)

    async def act(self, action: Dict[str, Any]):
        await self.launch()
        from src.actions import AgentAction

        act = AgentAction(**action)

        if act.action_type == "navigate" and act.url:
            await self.controller.navigate(act.url)
            return {"status": "ok", "observation": f"Navigated to {act.url}"}

        if act.action_type in ("click", "type", "hover", "right_click", "select_option", "upload_file"):
            use_fallback = bool(act.selector or act.stable_hash)

            if act.action_type == "click":
                if use_fallback:
                    await self.controller.click_with_fallback(act.element_display_id or 0, act.selector, act.stable_hash)
                else:
                    elements, elements_map = await self.controller.get_interactive_elements()
                    target = elements_map.get(act.element_display_id)
                    if not target:
                        return {"status": "error", "observation": f"Element {act.element_display_id} not found"}
                    await self.controller.click_by_coords(target.cx, target.cy)
                return {"status": "ok", "observation": f"Clicked element {act.element_display_id}"}

            if act.action_type == "right_click":
                elements, elements_map = await self.controller.get_interactive_elements()
                target = elements_map.get(act.element_display_id)
                if not target:
                    return {"status": "error", "observation": f"Element {act.element_display_id} not found"}
                await self.controller.mouse_click(target.cx, target.cy, button="right")
                return {"status": "ok", "observation": f"Right-clicked element {act.element_display_id}"}

            if act.action_type == "hover":
                elements, elements_map = await self.controller.get_interactive_elements()
                target = elements_map.get(act.element_display_id)
                if not target:
                    return {"status": "error", "observation": f"Element {act.element_display_id} not found"}
                await self.controller.hover(target.cx, target.cy)
                return {"status": "ok", "observation": f"Hovered element {act.element_display_id}"}

            if act.action_type == "type" and act.text:
                if use_fallback:
                    await self.controller.type_with_fallback(act.element_display_id or 0, act.text, act.selector, act.stable_hash)
                else:
                    elements, elements_map = await self.controller.get_interactive_elements()
                    target = elements_map.get(act.element_display_id)
                    if not target:
                        return {"status": "error", "observation": f"Element {act.element_display_id} not found"}
                    await self.controller.click_by_coords(target.cx, target.cy)
                    await self.controller.keyboard_type(act.text)
                return {"status": "ok", "observation": f"Typed into element {act.element_display_id}"}

            if act.action_type == "select_option":
                val = act.option_value or act.text or ""
                elements, elements_map = await self.controller.get_interactive_elements()
                target = elements_map.get(act.element_display_id)
                if not target:
                    return {"status": "error", "observation": f"Element {act.element_display_id} not found"}
                if target.selector:
                    await self.controller.select_option(target.selector, val)
                    return {"status": "ok", "observation": f"Selected {val}"}
                return {"status": "error", "observation": "No selector for select_option"}

            if act.action_type == "upload_file":
                elements, elements_map = await self.controller.get_interactive_elements()
                target = elements_map.get(act.element_display_id)
                if not target:
                    return {"status": "error", "observation": f"Element {act.element_display_id} not found"}
                if target.selector and act.file_path:
                    if not os.path.exists(act.file_path):
                        return {"status": "error", "observation": f"File not found: {act.file_path}"}
                    await self.controller.upload_file(target.selector, act.file_path)
                    return {"status": "ok", "observation": f"Uploaded {act.file_path}"}
                return {"status": "error", "observation": "Missing selector or file_path"}

        if act.action_type == "scroll":
            await self.controller.scroll(act.direction or "down", act.amount or 300)
            return {"status": "ok", "observation": f"Scrolled {act.direction}"}

        if act.action_type == "press_key":
            await self.controller.press_key(act.key or "Enter")
            return {"status": "ok", "observation": f"Pressed {act.key}"}

        if act.action_type == "screenshot":
            return {"status": "ok", "observation": "Screenshot captured"}

        if act.action_type == "wait":
            await asyncio.sleep(act.seconds or 1)
            return {"status": "ok", "observation": f"Waited {act.seconds}s"}

        if act.action_type == "switch_tab":
            idx = act.tab_index or 0
            try:
                await self.controller.bring_to_front_tab(idx)
                return {"status": "ok", "observation": f"Switched to tab {idx}"}
            except (IndexError, RuntimeError):
                return {"status": "error", "observation": "Tab index out of range"}

        if act.action_type == "dismiss_alert":
            await self.controller.set_dialog_action("dismiss")
            return {"status": "ok", "observation": "Alert will be dismissed"}

        if act.action_type == "accept_alert":
            await self.controller.set_dialog_action("accept")
            return {"status": "ok", "observation": "Alert will be accepted"}

        return {"status": "error", "observation": f"Unsupported action {act.action_type}"}

    async def screenshot_base64(self) -> str:
        await self.launch()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            await self.controller.screenshot(path=tmp_path)
            with open(tmp_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode("utf-8")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    async def screenshot_annotated_base64(self) -> Dict[str, Any]:
        await self.launch()
        with tempfile.NamedTemporaryFile(suffix="_raw.jpg", delete=False) as tmp_raw:
            raw_path = tmp_raw.name
        with tempfile.NamedTemporaryFile(suffix="_annotated.jpg", delete=False) as tmp_ann:
            ann_path = tmp_ann.name
        try:
            await self.controller.screenshot(path=raw_path)
            elements, elements_map = await self.controller.get_interactive_elements()
            draw_overlay(raw_path, elements, ann_path)
            with open(ann_path, "rb") as f:
                data = f.read()
            b64 = base64.b64encode(data).decode("utf-8")
            serializable_map = {str(k): v for k, v in elements_map.items()}
            return {"image": b64, "elements": serializable_map}
        finally:
            for p in (raw_path, ann_path):
                try:
                    os.unlink(p)
                except Exception:
                    pass

    async def get_elements(self) -> Dict[str, Any]:
        await self.launch()
        elements, elements_map = await self.controller.get_interactive_elements()
        return {
            "elements": [{"display_id": e.display_id, "tag": e.tag, "text": e.text, "hash": e.stable_hash} for e in elements],
            "map": {str(k): v for k, v in elements_map.items()},
        }

    async def get_text_snapshot(self) -> Dict[str, Any]:
        await self.launch()
        snapshot, elements_map = await self.controller.get_text_snapshot()
        return {
            "snapshot": snapshot,
            "map": {str(k): v for k, v in elements_map.items()},
        }

    async def close(self):
        if self._launched:
            await self.controller.close()
            self._launched = False


def get_session() -> BrowserSession:
    global _session
    if _session is None:
        _session = BrowserSession()
    return _session


class LaunchRequest(BaseModel):
    headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 720


class NavigateRequest(BaseModel):
    url: str


class ActRequest(BaseModel):
    action: Dict[str, Any]


@app.post("/launch")
async def launch(req: LaunchRequest):
    global _session
    async with _session_lock:
        _session = BrowserSession(req.viewport_width, req.viewport_height)
        await _session.launch(headless=req.headless)
    return {"status": "ok"}


@app.post("/navigate")
async def navigate(req: NavigateRequest):
    sess = get_session()
    async with _session_lock:
        await sess.navigate(req.url)
    return {"status": "ok", "url": req.url}


@app.post("/act")
async def act(req: ActRequest):
    sess = get_session()
    async with _session_lock:
        result = await sess.act(req.action)
    return result


@app.get("/screenshot")
async def screenshot():
    sess = get_session()
    b64 = await sess.screenshot_base64()
    return {"image": b64}


@app.post("/screenshot_annotated")
async def screenshot_annotated():
    sess = get_session()
    result = await sess.screenshot_annotated_base64()
    return result


@app.post("/screenshot_step")
async def screenshot_step():
    sess = get_session()
    result = await sess.screenshot_annotated_base64()
    return result


@app.get("/elements")
async def elements():
    sess = get_session()
    return await sess.get_elements()


@app.get("/text_snapshot")
async def text_snapshot():
    sess = get_session()
    return await sess.get_text_snapshot()


@app.post("/close")
async def close():
    sess = get_session()
    async with _session_lock:
        await sess.close()
    return {"status": "ok"}


@app.on_event("shutdown")
async def shutdown_event():
    sess = get_session()
    await sess.close()
