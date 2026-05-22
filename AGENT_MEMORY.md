# SkreenMaker — Agent Memory

## Project Status

### Completed Phases

#### Phase 1: Variables MVP ✅
- Pydantic models for scenario variables
- CRUD endpoints (`/scenario/variables/set`, `/scenario/variables/get`)
- `${var}` interpolation via `variable_resolver.py`
- UI panel for variable editing
- WebSocket integration during replay
- Tests: 7 tests in `test_variable_resolver.py`

#### Phase 2: Screenshot Click ✅
- `/elements_with_bboxes` endpoint returning `x,y,width,height`
- Frontend overlay divs rendered via `v-for` over `computedBboxes`
- Hover sync between element list and overlay
- Zoom/pan support with `screenshotTransformStyle`
- Click on overlay → `sendAction({action_type:'click', element_display_id})` → **real browser click** + updates `lastElementDisplayId` for `typeText`
- Step is added to scenario **only when `autoRecordEnabled === true`** (`maybeAutoRecord`)
- **Div/span/li/etc with `cursor:pointer`** now detected via second pass in `get_interactive_elements` (tree nodes, cards, custom buttons)
- Clean screenshot (no Python-drawn overlay accumulation)
- Tests: `test_ui_enhancements.py` (6 tests), `test_browser.py` (11 tests)

#### Phase 3: Assertions MVP ✅
- `assert` action type in `AgentAction`
- `assert_engine.py` with 4 condition types (`url_contains`, `element_exists`, `text_contains`, `title_is`)
- WebSocket assert reporting (stops replay on fail)
- UI StepModal support for assert steps
- CSS color coding for assert results
- Tests: 8 tests in `test_assert_engine.py`

### Architecture Decisions
- **Overlay**: Switched from Python-drawn overlay to pure frontend overlay divs for clean, scalable, interactive rendering
- **Screenshot source**: Use `/screenshot` (clean) + `/elements` (data) instead of `/screenshot_annotated`
- **Variable interpolation**: Resolves all string fields in scenario steps via `resolve_step()`
- **Assert in replay**: Fails immediately, reports error via WebSocket, UI shows `step-assert-fail` highlight

### Known Issues
- Port 8080 conflicts: old python.exe processes may hold port — use `taskkill /F /IM python.exe` before restart

### Test Count
- Total: 90+ tests passing (21 new: 7 variable + 8 assert + 6 UI integration)
