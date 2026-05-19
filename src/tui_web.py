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

# In-memory хранилище сценариев и последовательностей
_scenarios: Dict[str, Dict[str, Any]] = {}
_current_scenario_id: Optional[str] = None
_sequences: Dict[str, Dict[str, Any]] = {}
_current_sequence_id: Optional[str] = None

SCENARIOS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenarios.json")


def _load_scenarios():
    global _scenarios, _current_scenario_id, _sequences, _current_sequence_id
    if os.path.exists(SCENARIOS_FILE):
        try:
            with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            _scenarios = data.get("scenarios", {})
            _current_scenario_id = data.get("current_scenario_id")
            _sequences = data.get("sequences", {})
            _current_sequence_id = data.get("current_sequence_id")
        except Exception:
            _scenarios = {}
            _current_scenario_id = None
            _sequences = {}
            _current_sequence_id = None
    else:
        _scenarios = {}
        _current_scenario_id = None
        _sequences = {}
        _current_sequence_id = None


def _save_scenarios():
    try:
        with open(SCENARIOS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "scenarios": _scenarios,
                "current_scenario_id": _current_scenario_id,
                "sequences": _sequences,
                "current_sequence_id": _current_sequence_id,
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _new_scenario_id() -> str:
    return str(uuid.uuid4())[:8]


def _new_sequence_id() -> str:
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


class SequenceCreate(BaseModel):
    name: str
    scenario_ids: Optional[List[str]] = None


class SequenceRename(BaseModel):
    sequence_id: str
    name: str


class SequenceSelect(BaseModel):
    sequence_id: str


class SequenceReorder(BaseModel):
    sequence_id: str
    scenario_ids: List[str]


class TagAdd(BaseModel):
    scenario_id: str
    tag: str


class TagRemove(BaseModel):
    scenario_id: str
    tag: str


class GroupSet(BaseModel):
    scenario_id: str
    group: Optional[str] = None


# ---------- Routes ----------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


# ---- Scenario CRUD ----

@app.post("/scenario/create")
async def scenario_create(req: ScenarioCreate):
    global _current_scenario_id
    sid = _new_scenario_id()
    _scenarios[sid] = {"id": sid, "name": req.name, "steps": [], "tags": [], "group": None}
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
    # Удаляем сценарий из всех последовательностей
    for seq in _sequences.values():
        if req.scenario_id in seq.get("scenario_ids", []):
            seq["scenario_ids"] = [sid for sid in seq["scenario_ids"] if sid != req.scenario_id]
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


# ---- Tags / Groups ----

@app.post("/scenario/tag/add")
async def scenario_tag_add(req: TagAdd):
    s = _scenarios.get(req.scenario_id)
    if not s:
        return {"status": "error", "message": "Scenario not found"}
    tag = req.tag.strip().lower()
    if tag and tag not in s.get("tags", []):
        s.setdefault("tags", []).append(tag)
        _save_scenarios()
    return {"status": "ok", "scenario": s}


@app.post("/scenario/tag/remove")
async def scenario_tag_remove(req: TagRemove):
    s = _scenarios.get(req.scenario_id)
    if not s:
        return {"status": "error", "message": "Scenario not found"}
    tag = req.tag.strip().lower()
    if tag in s.get("tags", []):
        s["tags"] = [t for t in s["tags"] if t != tag]
        _save_scenarios()
    return {"status": "ok", "scenario": s}


@app.post("/scenario/group/set")
async def scenario_group_set(req: GroupSet):
    s = _scenarios.get(req.scenario_id)
    if not s:
        return {"status": "error", "message": "Scenario not found"}
    s["group"] = req.group.strip() if req.group else None
    _save_scenarios()
    return {"status": "ok", "scenario": s}


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
    return {"status": "ok", "json": json.dumps({"name": s["name"], "steps": s["steps"], "tags": s.get("tags", []), "group": s.get("group")}, ensure_ascii=False, indent=2)}


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
    _scenarios[sid] = {"id": sid, "name": name, "steps": validated_steps, "tags": [], "group": None}
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


# ---- Sequences CRUD ----

@app.post("/sequence/create")
async def sequence_create(req: SequenceCreate):
    global _current_sequence_id
    sid = _new_sequence_id()
    _sequences[sid] = {"id": sid, "name": req.name, "scenario_ids": req.scenario_ids or []}
    _current_sequence_id = sid
    _save_scenarios()
    return {"status": "ok", "sequence": _sequences[sid]}


@app.post("/sequence/rename")
async def sequence_rename(req: SequenceRename):
    seq = _sequences.get(req.sequence_id)
    if not seq:
        return {"status": "error", "message": "Sequence not found"}
    seq["name"] = req.name
    _save_scenarios()
    return {"status": "ok", "sequence": seq}


@app.post("/sequence/delete")
async def sequence_delete(req: SequenceSelect):
    global _current_sequence_id
    _sequences.pop(req.sequence_id, None)
    if _current_sequence_id == req.sequence_id:
        _current_sequence_id = next(iter(_sequences.keys()), None)
    _save_scenarios()
    return {"status": "ok", "current_sequence_id": _current_sequence_id}


@app.get("/sequence/list")
async def sequence_list():
    return {
        "status": "ok",
        "sequences": list(_sequences.values()),
        "current_sequence_id": _current_sequence_id,
    }


@app.get("/sequence/{sequence_id}")
async def sequence_get(sequence_id: str):
    seq = _sequences.get(sequence_id)
    if not seq:
        return {"status": "error", "message": "Sequence not found"}
    return {"status": "ok", "sequence": seq}


@app.post("/sequence/select")
async def sequence_select(req: SequenceSelect):
    global _current_sequence_id
    if req.sequence_id not in _sequences:
        return {"status": "error", "message": "Sequence not found"}
    _current_sequence_id = req.sequence_id
    _save_scenarios()
    return {"status": "ok", "sequence": _sequences[req.sequence_id]}


@app.post("/sequence/reorder")
async def sequence_reorder(req: SequenceReorder):
    seq = _sequences.get(req.sequence_id)
    if not seq:
        return {"status": "error", "message": "Sequence not found"}
    # Фильтруем только существующие сценарии
    valid_ids = [sid for sid in req.scenario_ids if sid in _scenarios]
    seq["scenario_ids"] = valid_ids
    _save_scenarios()
    return {"status": "ok", "sequence": seq}


@app.post("/sequence/add_scenario")
async def sequence_add_scenario(req: SequenceReorder):
    seq = _sequences.get(req.sequence_id)
    if not seq:
        return {"status": "error", "message": "Sequence not found"}
    for sid in req.scenario_ids:
        if sid in _scenarios and sid not in seq["scenario_ids"]:
            seq["scenario_ids"].append(sid)
    _save_scenarios()
    return {"status": "ok", "sequence": seq}


@app.post("/sequence/remove_scenario")
async def sequence_remove_scenario(req: SequenceReorder):
    seq = _sequences.get(req.sequence_id)
    if not seq:
        return {"status": "error", "message": "Sequence not found"}
    seq["scenario_ids"] = [sid for sid in seq["scenario_ids"] if sid not in req.scenario_ids]
    _save_scenarios()
    return {"status": "ok", "sequence": seq}


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


# ---- Sequence Replay WebSocket ----

@app.websocket("/ws/replay_sequence")
async def replay_sequence_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        msg = await websocket.receive_json()
        sequence_id = msg.get("sequence_id")
        seq = _sequences.get(sequence_id)
        if not seq:
            await websocket.send_json({"type": "error", "message": "Sequence not found"})
            return
        sess = get_session()
        scenario_ids = seq.get("scenario_ids", [])
        delay = float(msg.get("delay", 0.5))
        inter_scenario_delay = float(msg.get("inter_scenario_delay", 1.0))
        await websocket.send_json({"type": "sequence_start", "sequence_id": sequence_id, "total_scenarios": len(scenario_ids)})
        overall_success = True
        for sc_idx, sid in enumerate(scenario_ids):
            s = _scenarios.get(sid)
            if not s:
                await websocket.send_json({"type": "scenario_start", "scenario_index": sc_idx, "scenario_id": sid, "name": "(deleted)", "total_steps": 0})
                await websocket.send_json({"type": "scenario_result", "scenario_index": sc_idx, "scenario_id": sid, "skipped": True, "error": "Scenario not found"})
                continue
            steps = s["steps"]
            await websocket.send_json({"type": "scenario_start", "scenario_index": sc_idx, "scenario_id": sid, "name": s["name"], "total_steps": len(steps)})
            scenario_success = True
            for i, step in enumerate(steps):
                await websocket.send_json({"type": "step_start", "scenario_index": sc_idx, "step_index": i, "total_steps": len(steps), "action": step})
                if delay > 0 and (i > 0 or sc_idx > 0):
                    await asyncio.sleep(delay)
                try:
                    result = await sess.act(step)
                except Exception as e:
                    await websocket.send_json({"type": "step_result", "scenario_index": sc_idx, "step_index": i, "result": None, "error": str(e)})
                    scenario_success = False
                    overall_success = False
                    await websocket.send_json({"type": "scenario_result", "scenario_index": sc_idx, "scenario_id": sid, "success": False, "stopped_at": i})
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
                        "scenario_index": sc_idx,
                        "step_index": i,
                        "image": shot["image"],
                        "elements": elements_serializable,
                    })
                await websocket.send_json({"type": "step_result", "scenario_index": sc_idx, "step_index": i, "result": result, "error": None})
            if scenario_success:
                await websocket.send_json({"type": "scenario_result", "scenario_index": sc_idx, "scenario_id": sid, "success": True})
            if sc_idx < len(scenario_ids) - 1 and inter_scenario_delay > 0:
                await asyncio.sleep(inter_scenario_delay)
        await websocket.send_json({"type": "finish", "success": overall_success})
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
