<!-- From: e:\Agent_test\skreenmaker\AGENTS.md -->
# SkreenMaker — Agent Instructions

## Project Overview

SkreenMaker — это автономный агент для управления браузером через скриншоты и Vision-LLM. Проект предоставляет четыре режима работы и два вспомогательных скрипта для ручного управления:

1. **Автономный агент** (`src/main.py` → `BrowserAgent`) — LLM самостоятельно принимает решения на основе скриншотов страницы и выполняет задачи в браузере. Цикл observe → think → act.
2. **Пошаговый интерактивный режим** (`src/interactive_step.py`) — пользователь или внешний AI анализирует скриншот и задаёт следующее действие вручную через CLI.
3. **Web TUI** (`src/interactive_tui.py` + `src/tui_web.py` + Vue-фронтенд) — веб-интерфейс для ручного управления браузером с аннотированными скриншотами, конструктором сценариев (scenarios) и последовательностей (sequences).
4. **FastAPI-сервер** (`src/server.py`) — программное управление браузером через HTTP API (REST + WebSocket).

Дополнительно в корне проекта лежат вспомогательные скрипты:
- `manual_agent.py` — упрощённый CLI-скрипт для ручного пошагового управления браузером с сохранением состояния в `manual_state.json`.
- `manual_step.py` — пример скрипта, который обращается к запущенному FastAPI-серверу для выполнения действий и получения скриншотов.

## Technology Stack

- **Python** 3.9+
- **Playwright** — асинхронная автоматизация Chromium (скриншоты, клики, ввод, навигация, инъекция JS для поиска элементов)
- **FastAPI + Uvicorn** — HTTP API и Web TUI backend
- **WebSocket** — потоковая передача скриншотов и статуса шагов при replay и работе агента
- **Pydantic v2 / pydantic-settings** — валидация моделей (`AgentAction`, `AppConfig`) и конфигурации
- **Pillow (PIL)** — наложение overlay с номерами интерактивных элементов
- **Rich** — цветной вывод в консоль
- **OpenAI / Anthropic / Ollama / Kimi SDK** — Vision LLM для принятия решений
- **pytest + pytest-asyncio** — тестирование
- **Vue 3 (Composition API) + Vite** — фронтенд Web TUI
- **@vue-flow/core** — визуальный конструктор последовательностей сценариев на фронтенде

## Project Structure

```
src/
  main.py              — CLI entry point для автономного агента
  agent.py             — ядро BrowserAgent: observe → think → act loop, circuit breaker, history compaction
  browser.py           — обёртка над Playwright (BrowserController): скриншоты, навигация, поиск элементов, fallback-цепочка
  actions.py           — Pydantic-модель AgentAction (все возможные действия агента) + валидаторы безопасности
  overlay.py           — рисование номеров элементов на скриншоте через PIL
  element_tracker.py   — трекинг интерактивных элементов: deduplication, stable hash, display_id
  page_parser.py       — извлечение текстового контекста страницы (title, headings, links, body)
  prompts.py           — системный промпт для LLM (на русском языке), build_elements_list
  llm_client.py        — клиенты OpenAI, Anthropic, Ollama, Kimi, KimiCli с единым интерфейсом BaseVisionLLM + retry-логика
  config.py            — загрузка конфигурации из .env и YAML через pydantic-settings
  server.py            — FastAPI приложение с эндпоинтами /launch, /navigate, /act, /screenshot, /elements, /close
  interactive_step.py  — CLI для пошагового ручного режима
  interactive_tui.py   — launcher для Web TUI (открывает uvicorn + браузер)
  tui_web.py           — FastAPI роуты для Web TUI: сценарии, последовательности, WebSocket (/ws/replay, /ws/replay_sequence, /ws/agent)
  report_generator.py  — генератор HTML-отчётов по walkthrough
  wait_utils.py        — smart_wait с различной логикой ожидания в зависимости от действия

tests/
  test_agent.py        — unit-тесты BrowserAgent (моки)
  test_browser.py      — интеграционные тесты BrowserController против локальных HTML-фикстур
  test_config.py       — тесты загрузки конфигурации
  test_element_tracker.py — тесты deduplication и stable hash
  test_overlay.py      — тесты overlay
  test_server.py       — unit-тесты FastAPI endpoints (моки + TestClient)
  test_walkthrough.py  — интеграционный тест walkthrough + report generation
  fixtures/            — login_form.html, dashboard.html

.templates/
  index.html           — Jinja2-шаблон фронтенда Web TUI (подключает static/dist/app.mjs)

static/
  app.js               — исходный Vue 3 фронтенд (Composition API + VueFlow) — НЕ используется напрямую, собирается через Vite
  app.css              — стили Web TUI
  dist/                — собранные ассеты (app.mjs, app.css), генерируются Vite

.tmp-build/
  main.js              — резервная копия entry point (синхронизируется со static/app.js)
  package.json         — legacy зависимости (не используется, см. корневой package.json)
  vite.config.js       — legacy конфигурация (не используется, см. корневой vite.config.js)

manual_agent.py        — упрощённый ручной агент (сохраняет manual_state.json + скриншоты)
manual_step.py         — пример клиента к FastAPI серверу
scenarios.json         — runtime-хранилище сценариев и последовательностей (gitignored, содержит credentials)
test_login.json        — тестовые credentials (gitignored)
```

## Entry Points

### Автономный агент
```bash
python -m src.main \
  --url "https://example.com" \
  --task "Нажми кнопку Login" \
  --output-dir output \
  --max-steps 15
```

### Пошаговый режим
```bash
python -m src.interactive_step --url "https://example.com" --history "[]"
```

### Web TUI
```bash
python -m src.interactive_tui --port 8080
```

### FastAPI сервер
```bash
python -m src.server
# или через uvicorn напрямую:
uvicorn src.server:app --host 0.0.0.0 --port 8000
```

### Ручной скрипт (manual_agent.py)
```bash
python manual_agent.py
```
Скрипт открывает браузер (headless=False), делает скриншот, накладывает overlay и сохраняет состояние в `manual_state.json`, не закрывая браузер.

## Configuration

Конфигурация загружается в следующем приоритете (от низкого к высокому):
1. Значения по умолчанию в `AppConfig` (`src/config.py`)
2. `.env` файл (через `pydantic-settings`)
3. YAML-файл, переданный через `--config`
4. CLI-аргументы

Основные параметры:
- `llm_provider`: `openai` | `kimi` | `ollama` | `anthropic`
- `api_key`: API-ключ (или `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` в env)
- `model`: например `gpt-4o`, `claude-3-5-sonnet-20241022`, `llava`
- `base_url`: кастомный base URL для API (для Ollama по умолчанию `http://localhost:11434/v1`)
- `viewport_width` / `viewport_height`: размеры viewport (default 1280×720)
- `headless`: запускать ли браузер без GUI (default `true`)
- `output_dir`: папка для скриншотов и state (default `output`)
- `max_steps`: максимальное число шагов автономного агента (default `15`)

## Build and Test Commands

### Установка зависимостей
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### Сборка фронтенда Web TUI
Требуется Node.js 18+.
```bash
npm install
npm run build
```
После сборки в `static/dist/` появятся `app.mjs` и `app.css`. `templates/index.html` подключает именно эти собранные файлы.

### Запуск тестов
```bash
pytest tests/
```

### Запуск конкретного теста
```bash
pytest tests/test_agent.py -v
pytest tests/test_browser.py -v
pytest tests/test_server.py -v
```

## Code Style Guidelines

- **Язык комментариев и docstrings**: русский (доминирующий в проекте), кодовые сущности на английском.
- **Типизация**: активно используются type hints (`typing.List`, `Dict`, `Optional`, `Tuple`, `Any`, `Literal`, `Callable`).
- **Асинхронность**: весь Playwright-взаимодействие асинхронное (`async def` + `await`).
- **Pydantic v2**: все действия агента валидируются через `AgentAction` (`src/actions.py`), конфигурация через `AppConfig` (`src/config.py`).
- **Именование**:
  - приватные поля/методы: префикс `_` (`_page`, `_context`, `_on_dialog`)
  - константы: `UPPER_SNAKE_CASE` (`SYSTEM_PROMPT`, `ELEMENT_COLORS`)
  - функции/переменные: `snake_case`
  - классы: `PascalCase`
- **Обработка ошибок**: в `browser.py` и `server.py` ошибки при закрытии браузера подавляются через `try/except/pass` чтобы избежать исключений на cleanup.
- **Пути**: используется `pathlib.Path` и `os.path`; в валидаторах `AgentAction` запрещены абсолютные пути и `..` в `file_path` / `filename`.

## Testing Instructions

- **pytest.ini** задаёт `asyncio_mode = auto` и `asyncio_default_fixture_loop_scope = function`.
- **Unit-тесты** (`test_agent.py`, `test_server.py`) используют `unittest.mock.AsyncMock` / `MagicMock` и `patch`, не требуют реального браузера.
- **Интеграционные тесты** (`test_browser.py`, `test_walkthrough.py`) запускают реальный Chromium в `headless=True` против локальных HTML-файлов из `tests/fixtures/`.
- **Тесты конфигурации** (`test_config.py`) создают временные YAML-файлы и проверяют приоритеты загрузки.
- `test_agent.py` использует кастомную фикстуру `agent_patches`, которая одновременно патчит 5 зависимостей.
- `test_browser.py` и `test_walkthrough.py` используют `pytest_asyncio.fixture` для асинхронного управления жизненным циклом браузера (launch → yield → close).

## Architecture & Key Design Patterns

### Ядро автономного агента (agent.py)
```
BrowserAgent.run()
  ├── BrowserController.launch()
  ├── BrowserController.screenshot()
  ├── BrowserController.get_interactive_elements()
  │     └── element_tracker.track_elements()   # deduplicate + display_id + stable_hash
  ├── overlay.draw_overlay()                    # аннотирует скриншот номерами
  ├── page_parser.extract_page_context()        # извлекает текст страницы
  ├── prompts.build_elements_list()             # форматирует список элементов для LLM
  └── llm_client.BaseVisionLLM.predict()        # отправляет скриншот + промпт → AgentAction
        └── agent._execute_action()             # маршрутизирует действие в BrowserController
              └── wait_utils.smart_wait()       # контекстное ожидание
```

- **Circuit Breaker** (`_is_stuck`): обнаруживает 3 подряд одинаковых неудачных действия и прерывает цикл, чтобы избежать бесконечного зацикливания.
- **History Compaction** (`_compact_history`): когда история превышает 8 шагов, старые шаги суммаризируются через LLM для экономии токенов.
- **Два режима работы агента**: Vision mode (скриншот + overlay) и Text mode (DOM snapshot как текст). Text mode используется как fallback при ошибках vision-режима.
- **Цепочка fallback для элементов**: `display_id` → `stable_hash` → `selector` → координатный клик. Это делает автоматизацию устойчивой к изменениям DOM.

### Web TUI (tui_web.py)
- **Scenario** (сценарий) = упорядоченный список шагов `AgentAction` + метаданные (tags, group).
- **Sequence** (последовательность) = упорядоченный список ID сценариев, визуально представлен как граф в VueFlow.
- Персистентность: `scenarios.json` на диске.
- WebSocket endpoints:
  - `/ws/replay` — потоковое выполнение сценария с отправкой скриншотов и статуса
  - `/ws/replay_sequence` — цепочка выполнения нескольких сценариев
  - `/ws/agent` — запуск `BrowserAgent` с пересылкой событий на фронтенд

### Унифицированный LLM-интерфейс (llm_client.py)
- `BaseVisionLLM` — абстрактный базовый класс.
- `predict()` — vision-режим (скриншот + текст).
- `predict_text()` — текстовый режим.
- `_call_with_retry()` — экспоненциальная задержка (1с, 3с, 9с) для API-вызовов.

## Security Considerations

- **API ключи**: хранятся в `.env` или передаются через `--api-key`. Файл `.env` добавлен в `.gitignore`.
- **Path traversal**: в `AgentAction` есть Pydantic `@field_validator`, который блокирует `..`, абсолютные пути (`/`, `\`, `C:`) в полях `file_path` и `filename`.
- **Диалоги браузера**: автоматически закрываются через `dismiss` по умолчанию; можно переключить на `accept` через действия агента.
- **LLM-инструкции**: в промпте явно указано `Не вводи личные данные, пароли, платежную информацию`.
- **Чувствительные данные**: файлы `scenarios.json` и `test_login.json` содержат credentials и добавлены в `.gitignore`. Не коммитьте их в репозиторий.
- **Выходные данные**: скриншоты и state сохраняются в `output/` (в `.gitignore`).

## Available Skills

- **graphify** (`.kimi/skills/graphify/SKILL.md`) — Turn any folder into a navigable knowledge graph (code, docs, images, papers). Trigger: `/graphify`.

## Docs

- `docs/skreenmaker_architecture.png` — архитектурная схема
- `docs/skreenmaker_architecture.excalidraw` — редактируемый исходник схемы
