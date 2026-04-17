# Graph Report - src  (2026-04-17)

## Corpus Check
- 17 files · ~7,751 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 157 nodes · 386 edges · 9 communities detected
- Extraction: 61% EXTRACTED · 39% INFERRED · 0% AMBIGUOUS · INFERRED: 151 edges (avg confidence: 0.72)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]

## God Nodes (most connected - your core abstractions)
1. `BrowserController` - 41 edges
2. `AgentAction` - 30 edges
3. `BrowserAgent` - 17 edges
4. `smart_wait()` - 16 edges
5. `_execute_action()` - 15 edges
6. `BrowserSession` - 14 edges
7. `run_step()` - 13 edges
8. `BaseVisionLLM` - 12 edges
9. `get_session()` - 11 edges
10. `launch()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Рисует на скриншоте номера интерактивных элементов.     Возвращает путь к анноти` --uses--> `TrackedElement`  [INFERRED]
  src\overlay.py → src\element_tracker.py
- `Извлекает текстовый контекст страницы для подачи в LLM вместе со скриншотом.` --uses--> `TrackedElement`  [INFERRED]
  src\page_parser.py → src\element_tracker.py
- `Форматирует контекст страницы в строку для промпта.` --uses--> `TrackedElement`  [INFERRED]
  src\page_parser.py → src\element_tracker.py
- `BrowserAgent` --uses--> `AgentAction`  [INFERRED]
  src\agent.py → src\actions.py
- `Выполняет одно действие. Для replay используем упрощенную логику.` --uses--> `AgentAction`  [INFERRED]
  src\interactive_step.py → src\actions.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.14
Nodes (20): ABC, AgentAction, Один полный цикл observe → think → act с возможностью retry., Fallback vision-шаг для text-mode при ошибке действия., Circuit breaker: если последние 3 шага — одно и то же действие с ошибкой / без и, Если история > 8 шагов, суммируем первые шаги для экономии токенов., Отправляет старую историю к LLM для краткого summary., AnthropicLLM (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.12
Nodes (19): BaseModel, main(), act(), ActRequest, BrowserSession, close(), elements(), get_session() (+11 more)

### Community 2 - "Community 2"
Cohesion: 0.15
Nodes (5): BrowserController, _execute_action(), Выполняет одно действие. Для replay используем упрощенную логику., Умное ожидание в зависимости от типа действия., smart_wait()

### Community 3 - "Community 3"
Cohesion: 0.21
Nodes (6): BrowserAgent, extract_page_context(), format_page_context(), Извлекает текстовый контекст страницы для подачи в LLM вместе со скриншотом., Форматирует контекст страницы в строку для промпта., build_elements_list()

### Community 4 - "Community 4"
Cohesion: 0.16
Nodes (13): Возвращает текстовый snapshot страницы и маппинг display_id -> element., compute_element_hash(), deduplicate_elements(), _iou(), _quantize(), Генерирует стабильный хеш на основе грубых координат и текста., Intersection over Union для двух прямоугольников., Удаляет вложенные/дублирующиеся элементы. Если IoU > threshold, оставляет больши (+5 more)

### Community 5 - "Community 5"
Cohesion: 0.31
Nodes (6): load_history(), main(), run_step(), draw_overlay(), _get_color(), Рисует на скриншоте номера интерактивных элементов.     Возвращает путь к анноти

### Community 6 - "Community 6"
Cohesion: 0.29
Nodes (5): BaseSettings, AppConfig, load_config(), Загружает конфигурацию: сначала .env, затем опциональный YAML.     YAML имеет пр, main()

### Community 7 - "Community 7"
Cohesion: 0.67
Nodes (3): generate_report(), _image_to_base64(), Генерирует HTML-отчет по walkthrough.      steps: список словарей с ключами:

### Community 8 - "Community 8"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **7 isolated node(s):** `Загружает конфигурацию: сначала .env, затем опциональный YAML.     YAML имеет пр`, `Генерирует стабильный хеш на основе грубых координат и текста.`, `Intersection over Union для двух прямоугольников.`, `Удаляет вложенные/дублирующиеся элементы. Если IoU > threshold, оставляет больши`, `Принимает сырые элементы, дедуплицирует, назначает display_id и stable_hash.` (+2 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 8`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BrowserController` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`?**
  _High betweenness centrality (0.305) - this node is a cross-community bridge._
- **Why does `AgentAction` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 5`?**
  _High betweenness centrality (0.243) - this node is a cross-community bridge._
- **Why does `BrowserAgent` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 6`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `BrowserController` (e.g. with `BrowserAgent` and `Один полный цикл observe → think → act с возможностью retry.`) actually correct?**
  _`BrowserController` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `AgentAction` (e.g. with `BrowserAgent` and `Один полный цикл observe → think → act с возможностью retry.`) actually correct?**
  _`AgentAction` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `BrowserAgent` (e.g. with `BrowserController` and `BaseVisionLLM`) actually correct?**
  _`BrowserAgent` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `smart_wait()` (e.g. with `.keyboard_type()` and `.mouse_click()`) actually correct?**
  _`smart_wait()` has 14 INFERRED edges - model-reasoned connections that need verification._