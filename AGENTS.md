# SkreenMaker — Agent Instructions

## Project Overview

SkreenMaker — это автономный агент для управления браузером через скриншоты и Vision-LLM. Проект предоставляет три режима работы:

1. **Автономный агент** (`src/main.py`) — LLM самостоятельно принимает решения на основе скриншотов страницы и выполняет задачи в браузере.
2. **Пошаговый интерактивный режим** (`src/interactive_step.py`) — пользователь или внешний AI анализирует скриншот и задаёт следующее действие вручную.
3. **Web TUI** (`src/interactive_tui.py` + `src/tui_web.py`) — веб-интерфейс для ручного управления браузером с аннотированными скриншотами.

Кроме того, проект содержит FastAPI-сервер (`src/server.py`) для программного управления браузером через HTTP API.

## Technology Stack

- **Python** 3.9+
- **Playwright** — автоматизация Chromium (скриншоты, клики, ввод, навигация)
- **FastAPI + Uvicorn** — HTTP API и Web TUI
- **Pydantic / pydantic-settings** — валидация моделей и конфигурация
- **Pillow (PIL)** — наложение overlay с номерами интерактивных элементов
- **Rich** — цветной вывод в консоль
- **OpenAI / Anthropic / Ollama SDK** — Vision LLM для принятия решений
- **pytest + pytest-asyncio** — тестирование

## Project Structure

```
src/
  main.py              — CLI entry point для автономного агента
  agent.py             — ядро BrowserAgent: observe → think → act loop
  browser.py           — обёртка над Playwright (BrowserController)
  actions.py           — Pydantic-модель AgentAction (все возможные действия агента)
  overlay.py           — рисование номеров элементов на скриншоте
  element_tracker.py   — трекинг интерактивных элементов: deduplication, stable hash, display_id
  page_parser.py       — извлечение текстового контекста страницы (title, headings, links, body)
  prompts.py           — системный промпт для LLM (на русском языке)
  llm_client.py        — клиенты для OpenAI, Anthropic, Ollama с единым интерфейсом BaseVisionLLM
  config.py            — загрузка конфигурации из .env и YAML
  server.py            — FastAPI приложение с эндпоинтами /launch, /navigate, /act, /screenshot, /elements, /close
  interactive_step.py  — CLI для пошагового ручного режима
  interactive_tui.py   — launcher для Web TUI (открывает uvicorn + браузер)
  tui_web.py           — FastAPI роуты для Web TUI (рендерит templates/index.html)
  report_generator.py  — генератор HTML-отчётов по walkthrough
  wait_utils.py        — smart_wait с различной логикой ожидания в зависимости от действия

tests/
  test_agent.py        — unit-тесты BrowserAgent (с моками)
  test_browser.py      — интеграционные тесты BrowserController против локальных HTML-фикстур
  test_config.py       — тесты загрузки конфигурации
  test_element_tracker.py — тесты deduplication и stable hash
  test_overlay.py      — тесты overlay
  test_server.py       — unit-тесты FastAPI endpoints (с моками)
  test_walkthrough.py  — интеграционный тест walkthrough + report generation
  fixtures/            — login_form.html, dashboard.html

templates/
  index.html           — фронтенд Web TUI

config.yaml.example    — пример YAML-конфигурации
.env.example           — пример переменных окружения
pytest.ini            — asyncio_mode = auto
requirements.txt       — зависимости проекта
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

## Configuration

Конфигурация загружается в следующем приоритете (от низкого к высокому):
1. Значения по умолчанию в `AppConfig` (`src/config.py`)
2. `.env` файл (через `pydantic-settings`)
3. YAML-файл, переданный через `--config`
4. CLI-аргументы

Основные параметры:
- `llm_provider`: `openai` | `ollama` | `anthropic`
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

### Запуск тестов
```bash
pytest tests/
```

### Запуск конкретного теста
```bash
pytest tests/test_agent.py -v
pytest tests/test_browser.py -v
```

## Code Style Guidelines

- **Язык комментариев и docstrings**: русский (доминирующий в проекте), кодовые сущности на английском.
- **Типизация**: активно используются type hints (`typing.List`, `Dict`, `Optional`, `Tuple`, `Any`).
- **Асинхронность**: весь Playwright-взаимодействие асинхронное (`async def` + `await`).
- **Pydantic**: все действия агента валидируются через `AgentAction` (`src/actions.py`).
- **Именование**:
  - приватные поля/методы: префикс `_` (`_page`, `_context`, `_on_dialog`)
  - константы: UPPER_SNAKE_CASE (`SYSTEM_PROMPT`, `ELEMENT_COLORS`)
  - функции/переменные: snake_case
  - классы: PascalCase
- **Обработка ошибок**: в `browser.py` и `server.py` ошибки при закрытии браузера подавляются через `try/except/pass` чтобы избежать исключений на cleanup.
- **Пути**: используется `pathlib.Path` и `os.path`; в валидаторах `AgentAction` запрещены абсолютные пути и `..` в `file_path` / `filename`.

## Testing Instructions

- **pytest.ini** задаёт `asyncio_mode = auto` и `asyncio_default_fixture_loop_scope = function`.
- Unit-тесты (`test_agent.py`, `test_server.py`) используют `unittest.mock.AsyncMock` / `MagicMock` и `patch`, не требуют реального браузера.
- Интеграционные тесты (`test_browser.py`, `test_walkthrough.py`) запускают реальный Chromium в `headless=True` против локальных HTML-файлов из `tests/fixtures/`.
- Тесты конфигурации (`test_config.py`) создают временные YAML-файлы и проверяют приоритеты загрузки.

## Security Considerations

- **API ключи**: хранятся в `.env` или передаются через `--api-key`. Файл `.env` добавлен в `.gitignore`.
- **Path traversal**: в `AgentAction` есть валидатор, который блокирует `..`, абсолютные пути (`/`, `\`, `C:`) в полях `file_path` и `filename`.
- **Диалоги браузера**: автоматически закрываются через `dismiss` по умолчанию; можно переключить на `accept` через действия агента.
- **LLM-инструкции**: в промпте явно указано `Не вводи личные данные, пароли, платежную информацию`.
- **Выходные данные**: скриншоты и state сохраняются в `output/` (в `.gitignore`).

## Available Skills

- **graphify** (`.kimi/skills/graphify/SKILL.md`) — Turn any folder into a navigable knowledge graph (code, docs, images, papers). Trigger: `/graphify`.

When the user types `/graphify`, invoke the skill by reading `.kimi/skills/graphify/SKILL.md` and following its instructions before doing anything else.

## Docs

- `docs/skreenmaker_architecture.png` — архитектурная схема
- `docs/skreenmaker_architecture.excalidraw` — редактируемый исходник схемы
