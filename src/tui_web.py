import asyncio
import os
import uuid
import json
import tempfile
import base64
from typing import Optional, Dict, Any, List

from fastapi import Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from src.server import app as server_app, get_session
from src.agent import BrowserAgent


# Монтируем server routes под тем же приложением
app = server_app

# Static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Шаблоны
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

_active_agent: Optional[BrowserAgent] = None

# In-memory хранилище сценариев
_scenarios: Dict[str, Dict[str, Any]] = {}
_current_scenario_id: Optional[str] = None

SCENARIOS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenarios.json")


def _load_scenarios():
    global _scenarios, _current_scenario_id
    if os.path.exists(SCENARIOS_FILE):
        try:
            with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            _scenarios = data.get("scenarios", {})
            _current_scenario_id = data.get("current_scenario_id")
        except Exception:
            _scenarios = {}
            _current_scenario_id = None
    else:
        _scenarios = {}
        _current_scenario_id = None


def _save_scenarios():
    try:
        with open(SCENARIOS_FILE, "w", encoding="utf-8") as f:
            json.dump({"scenarios": _scenarios, "current_scenario_id": _current_scenario_id}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _new_scenario_id() -> str:
    return str(uuid.uuid4())[:8]


_load_scenarios()


# ---------- Pydantic models ----------

class ScenarioCreate(BaseModel):
    name: str


class ScenarioRename(BaseModel):
    scenario_id: str
    name: str


class ScenarioSelect(BaseModel):
    scenario_id: str


class StepAdd(BaseModel):
    scenario_id: str
    action: Dict[str, Any]


class StepUpdate(BaseModel):
    scenario_id: str
    step_index: int
    action: Dict[str, Any]


class StepMove(BaseModel):
    scenario_id: str
    step_index: int
    direction: int


class StepIndex(BaseModel):
    scenario_id: str
    step_index: int


class ReplayRequest(BaseModel):
    scenario_id: str


class ImportRequest(BaseModel):
    name: Optional[str] = None
    steps: List[Dict[str, Any]]


# ---------- Routes ----------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---- Scenario CRUD ----

@app.post("/scenario/create")
async def scenario_create(req: ScenarioCreate):
    global _current_scenario_id
    sid = _new_scenario_id()
    _scenarios[sid] = {"id": sid, "name": req.name, "steps": []}
    _current_scenario_id = sid
    _save_scenarios()
    return {"status": "ok", "scenario": _scenarios[sid]}


@app.post("/scenario/rename")
async def scenario_rename(req: ScenarioRename):
    s = _scenarios.get(req.scenario_id)
    if not s:
        return {"status": "error", "message": "Scenario not found"}
    s["name"] = req.name
    _save_scenarios()
    return {"status": "ok", "scenario": s}


@app.post("/scenario/delete")
async def scenario_delete(req: ScenarioSelect):
    global _current_scenario_id
    _scenarios.pop(req.scenario_id, None)
    if _current_scenario_id == req.scenario_id:
        _current_scenario_id = next(iter(_scenarios.keys()), None)
    _save_scenarios()
    return {"status": "ok", "current_scenario_id": _current_scenario_id}


@app.get("/scenario/list")
async def scenario_list():
    return {
        "status": "ok",
        "scenarios": list(_scenarios.values()),
        "current_scenario_id": _current_scenario_id,
    }


@app.get("/scenario/{scenario_id}")
async def scenario_get(scenario_id: str):
    s = _scenarios.get(scenario_id)
    if not s:
        return {"status": "error", "message": "Scenario not found"}
    return {"status": "ok", "scenario": s}


@app.post("/scenario/select")
async def scenario_select(req: ScenarioSelect):
    global _current_scenario_id
    if req.scenario_id not in _scenarios:
        return {"status": "error", "message": "Scenario not found"}
    _current_scenario_id = req.scenario_id
    _save_scenarios()
    return {"status": "ok", "scenario": _scenarios[req.scenario_id]}


# ---- Steps ----

@app.post("/scenario/step/add")
async def scenario_step_add(req: StepAdd):
    s = _scenarios.get(req.scenario_id)
    if not s:
        return {"status": "error", "message": "Scenario not found"}
    from src.actions import AgentAction
    try:
        validated = AgentAction(**req.action).model_dump()
    except Exception as e:
        return {"status": "error", "message": str(e)}
    s["steps"].append(validated)
    _save_scenarios()
    return {"status": "ok", "scenario": s}


@app.post("/scenario/step/update")
async def scenario_step_update(req: StepUpdate):
    s = _scenarios.get(req.scenario_id)
    if not s:
        return {"status": "error", "message": "Scenario not found"}
    if not (0 <= req.step_index < len(s["steps"])):
        return {"status": "error", "message": "Invalid step index"}
    from src.actions import AgentAction
    try:
        validated = AgentAction(**req.action).model_dump()
    except Exception as e:
        return {"status": "error", "message": str(e)}
    s["steps"][req.step_index] = validated
    _save_scenarios()
    return {"status": "ok", "scenario": s}


@app.post("/scenario/step/delete")
async def scenario_step_delete(req: StepIndex):
    s = _scenarios.get(req.scenario_id)
    if not s:
        return {"status": "error", "message": "Scenario not found"}
    if not (0 <= req.step_index < len(s["steps"])):
        return {"status": "error", "message": "Invalid step index"}
    s["steps"].pop(req.step_index)
    _save_scenarios()
    return {"status": "ok", "scenario": s}


@app.post("/scenario/step/move")
async def scenario_step_move(req: StepMove):
    s = _scenarios.get(req.scenario_id)
    if not s:
        return {"status": "error", "message": "Scenario not found"}
    idx = req.step_index
    new_idx = idx + req.direction
    if not (0 <= idx < len(s["steps"]) and 0 <= new_idx < len(s["steps"])):
        return {"status": "error", "message": "Cannot move step"}
    s["steps"][idx], s["steps"][new_idx] = s["steps"][new_idx], s["steps"][idx]
    _save_scenarios()
    return {"status": "ok", "scenario": s}


@app.post("/scenario/step/duplicate")
async def scenario_step_duplicate(req: StepIndex):
    s = _scenarios.get(req.scenario_id)
    if not s:
        return {"status": "error", "message": "Scenario not found"}
    if not (0 <= req.step_index < len(s["steps"])):
        return {"status": "error", "message": "Invalid step index"}
    s["steps"].insert(req.step_index + 1, dict(s["steps"][req.step_index]))
    _save_scenarios()
    return {"status": "ok", "scenario": s}


# ---- Import / Export / Replay ----

@app.post("/scenario/export")
async def scenario_export(req: ScenarioSelect):
    s = _scenarios.get(req.scenario_id)
    if not s:
        return {"status": "error", "message": "Scenario not found"}
    return {"status": "ok", "json": json.dumps({"name": s["name"], "steps": s["steps"]}, ensure_ascii=False, indent=2)}


@app.post("/scenario/import")
async def scenario_import(req: ImportRequest):
    global _current_scenario_id
    sid = _new_scenario_id()
    name = req.name or f"Imported {sid}"
    from src.actions import AgentAction
    validated_steps = []
    for step in (req.steps or []):
        try:
            validated_steps.append(AgentAction(**step).model_dump())
        except Exception as e:
            return {"status": "error", "message": f"Invalid step: {e}"}
    _scenarios[sid] = {"id": sid, "name": name, "steps": validated_steps}
    _current_scenario_id = sid
    _save_scenarios()
    return {"status": "ok", "scenario": _scenarios[sid]}


@app.post("/scenario/replay")
async def scenario_replay(req: ReplayRequest):
    s = _scenarios.get(req.scenario_id)
    if not s:
        return {"status": "error", "message": "Scenario not found"}
    sess = get_session()
    results = []
    for step in s["steps"]:
        try:
            result = await sess.act(step)
            results.append({"action": step, "result": result, "error": None})
        except Exception as e:
            results.append({"action": step, "result": None, "error": str(e)})
            break
    try:
        final_shot = await sess.screenshot_annotated_base64()
    except Exception:
        final_shot = None
    return {"status": "ok", "results": results, "final_image": final_shot}


# ---- Agent screenshot ----

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


# ---- Replay WebSocket ----

@app.websocket("/ws/replay")
async def replay_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        msg = await websocket.receive_json()
        scenario_id = msg.get("scenario_id")
        s = _scenarios.get(scenario_id)
        if not s:
            await websocket.send_json({"type": "error", "message": "Scenario not found"})
            return
        sess = get_session()
        steps = s["steps"]
        success = True
        delay = float(msg.get("delay", 0.5))
        for i, step in enumerate(steps):
            await websocket.send_json({"type": "step_start", "index": i, "total": len(steps), "action": step})
            if delay > 0 and i > 0:
                await asyncio.sleep(delay)
            try:
                result = await sess.act(step)
            except Exception as e:
                await websocket.send_json({"type": "step_result", "index": i, "result": None, "error": str(e)})
                success = False
                await websocket.send_json({"type": "finish", "success": False, "stopped_at": i})
                break
            try:
                shot = await sess.screenshot_annotated_base64()
            except Exception:
                shot = None
            if shot:
                elements_raw = shot.get("elements")
                if elements_raw:
                    from dataclasses import asdict
                    elements_serializable = {str(k): asdict(v) for k, v in elements_raw.items()}
                else:
                    elements_serializable = None
                await websocket.send_json({
                    "type": "screenshot",
                    "index": i,
                    "image": shot["image"],
                    "elements": elements_serializable,
                })
            await websocket.send_json({"type": "step_result", "index": i, "result": result, "error": None})
        if success:
            await websocket.send_json({"type": "finish", "success": True})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ---- Agent WebSocket ----

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
        if _active_agent and _active_agent.browser:
            try:
                await _active_agent.browser.close()
            except Exception:
                pass
        _active_agent = None
        try:
            await websocket.close()
        except Exception:
            pass
