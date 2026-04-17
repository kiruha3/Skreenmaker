# Graph Report - src  (2026-04-17)

## Corpus Check
- Corpus is ~5,485 words - fits in a single context window. You may not need a graph.

## Summary
- 116 nodes · 247 edges · 11 communities detected
- Extraction: 62% EXTRACTED · 38% INFERRED · 0% AMBIGUOUS · INFERRED: 95 edges (avg confidence: 0.72)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Browser Controller & Session|Browser Controller & Session]]
- [[_COMMUNITY_LLM Providers & Actions|LLM Providers & Actions]]
- [[_COMMUNITY_Agent Orchestration|Agent Orchestration]]
- [[_COMMUNITY_FastAPI Server|FastAPI Server]]
- [[_COMMUNITY_Element Tracking|Element Tracking]]
- [[_COMMUNITY_Configuration|Configuration]]
- [[_COMMUNITY_Visual Overlay|Visual Overlay]]
- [[_COMMUNITY_HTML Reports|HTML Reports]]
- [[_COMMUNITY_Interactive CLI Step|Interactive CLI Step]]
- [[_COMMUNITY_Web TUI Frontend|Web TUI Frontend]]
- [[_COMMUNITY_Package Init|Package Init]]

## God Nodes (most connected - your core abstractions)
1. `BrowserController` - 26 edges
2. `AgentAction` - 19 edges
3. `BrowserSession` - 14 edges
4. `BrowserAgent` - 12 edges
5. `_execute_action()` - 12 edges
6. `run_step()` - 11 edges
7. `smart_wait()` - 11 edges
8. `launch()` - 10 edges
9. `TrackedElement` - 8 edges
10. `BaseVisionLLM` - 8 edges

## Surprising Connections (you probably didn't know these)
- `Рисует на скриншоте номера интерактивных элементов.     Возвращает путь к анноти` --uses--> `TrackedElement`  [INFERRED]
  src\overlay.py → src\element_tracker.py
- `BrowserAgent` --uses--> `AgentAction`  [INFERRED]
  src\agent.py → src\actions.py
- `Если история > 8 шагов, суммируем первые шаги для экономии токенов.` --uses--> `AgentAction`  [INFERRED]
  src\agent.py → src\actions.py
- `Выполняет одно действие. Для replay используем упрощенную логику.` --uses--> `AgentAction`  [INFERRED]
  src\interactive_step.py → src\actions.py
- `BrowserSession` --uses--> `AgentAction`  [INFERRED]
  src\server.py → src\actions.py

## Communities

### Community 0 - "Browser Controller & Session"
Cohesion: 0.18
Nodes (5): BrowserController, _execute_action(), Выполняет одно действие. Для replay используем упрощенную логику., Умное ожидание в зависимости от типа действия., smart_wait()

### Community 1 - "LLM Providers & Actions"
Cohesion: 0.18
Nodes (14): ABC, AgentAction, BaseModel, TrackedElement, AnthropicLLM, BaseVisionLLM, _build_messages(), _clean_json() (+6 more)

### Community 2 - "Agent Orchestration"
Cohesion: 0.13
Nodes (9): BrowserAgent, Если история > 8 шагов, суммируем первые шаги для экономии токенов., main(), main(), extract_page_context(), format_page_context(), Форматирует контекст страницы в строку для промпта., Извлекает текстовый контекст страницы для подачи в LLM вместе со скриншотом. (+1 more)

### Community 3 - "FastAPI Server"
Cohesion: 0.27
Nodes (10): run_step(), act(), BrowserSession, close(), elements(), get_session(), launch(), navigate() (+2 more)

### Community 4 - "Element Tracking"
Cohesion: 0.23
Nodes (9): compute_element_hash(), deduplicate_elements(), _iou(), _quantize(), Генерирует стабильный хеш на основе грубых координат и текста., Intersection over Union для двух прямоугольников., Удаляет вложенные/дублирующиеся элементы. Если IoU > threshold, оставляет больши, Принимает сырые элементы, дедуплицирует, назначает display_id и stable_hash. (+1 more)

### Community 5 - "Configuration"
Cohesion: 0.4
Nodes (4): BaseSettings, AppConfig, load_config(), Загружает конфигурацию: сначала .env, затем опциональный YAML.     YAML имеет пр

### Community 6 - "Visual Overlay"
Cohesion: 0.67
Nodes (3): draw_overlay(), _get_color(), Рисует на скриншоте номера интерактивных элементов.     Возвращает путь к анноти

### Community 7 - "HTML Reports"
Cohesion: 0.67
Nodes (3): generate_report(), _image_to_base64(), Генерирует HTML-отчет по walkthrough.      steps: список словарей с ключами:

### Community 8 - "Interactive CLI Step"
Cohesion: 1.0
Nodes (2): load_history(), main()

### Community 9 - "Web TUI Frontend"
Cohesion: 1.0
Nodes (0): 

### Community 10 - "Package Init"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **9 isolated node(s):** `Загружает конфигурацию: сначала .env, затем опциональный YAML.     YAML имеет пр`, `Генерирует стабильный хеш на основе грубых координат и текста.`, `Intersection over Union для двух прямоугольников.`, `Удаляет вложенные/дублирующиеся элементы. Если IoU > threshold, оставляет больши`, `Принимает сырые элементы, дедуплицирует, назначает display_id и stable_hash.` (+4 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Web TUI Frontend`** (2 nodes): `tui_web.py`, `index()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Package Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BrowserController` connect `Browser Controller & Session` to `LLM Providers & Actions`, `Agent Orchestration`, `FastAPI Server`?**
  _High betweenness centrality (0.227) - this node is a cross-community bridge._
- **Why does `AgentAction` connect `LLM Providers & Actions` to `Browser Controller & Session`, `Agent Orchestration`, `FastAPI Server`?**
  _High betweenness centrality (0.204) - this node is a cross-community bridge._
- **Why does `BrowserAgent` connect `Agent Orchestration` to `Browser Controller & Session`, `LLM Providers & Actions`?**
  _High betweenness centrality (0.121) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `BrowserController` (e.g. with `BrowserAgent` and `Если история > 8 шагов, суммируем первые шаги для экономии токенов.`) actually correct?**
  _`BrowserController` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `AgentAction` (e.g. with `BrowserAgent` and `Если история > 8 шагов, суммируем первые шаги для экономии токенов.`) actually correct?**
  _`AgentAction` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `BrowserSession` (e.g. with `BrowserController` and `AgentAction`) actually correct?**
  _`BrowserSession` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `BrowserAgent` (e.g. with `BrowserController` and `BaseVisionLLM`) actually correct?**
  _`BrowserAgent` has 4 INFERRED edges - model-reasoned connections that need verification._