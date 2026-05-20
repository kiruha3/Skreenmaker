# SkreenMaker

Автономный агент для управления браузером через скриншоты и Vision-LLM. Проект предоставляет три режима работы и HTTP API для программного управления.

## Возможности

- **Скриншоты + overlay** — на скриншоты накладываются номера интерактивных элементов для точных кликов.
- **Автономный агент** — LLM самостоятельно принимает решения на основе скриншотов страницы.
- **Пошаговый интерактивный режим** — вы анализируете скриншот и отдаёте команды вручную.
- **Web TUI** — веб-интерфейс для ручного управления браузером с аннотированными скриншотами.
- **FastAPI-сервер** — программное управление браузером через HTTP API.

## Технологии

- **Python** 3.9+
- **Playwright** — автоматизация Chromium
- **FastAPI + Uvicorn** — HTTP API и Web TUI
- **Pydantic / pydantic-settings** — валидация и конфигурация
- **Pillow (PIL)** — overlay с номерами элементов
- **Rich** — цветной вывод в консоль
- **OpenAI / Anthropic / Ollama SDK** — Vision LLM

---

## Установка с нуля

### 1. Клонирование и переход в папку

```bash
cd skreenmaker
```

### 2. Виртуальное окружение (рекомендуется)

```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python -m venv .venv
source .venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Установка браузера Chromium для Playwright

```bash
python -m playwright install chromium
```

### 5. Сборка фронтенда (для Web TUI)

Требуется Node.js 18+.

```bash
npm install
npm run build
```

После сборки в `static/dist/` появятся `app.mjs`, `app.css` и `vue-flow.css`.

### 6. Конфигурация (опционально)

Для автономного режима требуется API-ключ. Создайте файл `.env` в корне проекта:

```bash
cp .env.example .env
# Отредактируй .env, добавив API-ключи и настройки провайдера
```

Также можно использовать `config.yaml` (см. `config.yaml.example`) или установить пакет через `pip install -e .`.

---

## Режимы запуска

### Режим 1. Автономный агент (CLI)

LLM самостоятельно управляет браузером на основе скриншотов.

```bash
python -m src.main \
  --url "https://example.com" \
  --task "Найди ссылку 'Learn more' и перейди по ней" \
  --output-dir output \
  --max-steps 15
```

Параметры:
- `--url` — стартовый URL
- `--task` — задача в свободной форме
- `--model` — модель LLM (по умолчанию `gpt-4o`)
- `--max-steps` — лимит шагов (по умолчанию 15)
- `--headless` / `--no-headless` — показывать окно браузера
- `--config` — путь к YAML-конфигу

### Режим 2. Пошаговый интерактивный режим (CLI)

На каждом шаге агент делает скриншот с номерами элементов, сохраняет его и ждёт вашей команды.

**Первый запуск:**

```bash
python -m src.interactive_step --url "https://example.com" --history "[]"
```

Агент сохранит:
- `output/step_1_annotated.jpg` — скриншот с номерами элементов
- `output/state/current_state.json` — список элементов и состояние

Откройте скриншот, выберите элемент и подготовьте JSON действия.

**Следующий шаг (с историей):**

```bash
# Windows PowerShell
$history = '[{"action_type":"click","element_id":1}]'
python -m src.interactive_step --url "https://example.com" --history $history
```

Доступные действия:
```json
{"action_type": "navigate", "url": "https://iana.org"}
{"action_type": "click", "element_id": 5}
{"action_type": "type", "element_id": 3, "text": "hello"}
{"action_type": "scroll", "direction": "down", "amount": 300}
{"action_type": "screenshot", "filename": "result.jpg"}
{"action_type": "wait", "seconds": 2}
```

### Режим 3. Web TUI (веб-интерфейс)

Запуск веб-сервера с интерфейсом для ручного управления браузером.

```bash
python -m src.interactive_tui --port 8080
```

Откройте в браузере: **http://127.0.0.1:8080**

Дополнительные опции:
```bash
# Не открывать браузер автоматически
python -m src.interactive_tui --no-open --port 8080

# Доступ из локальной сети
python -m src.interactive_tui --host 0.0.0.0 --port 8080
```

Остановка сервера — `Ctrl + C` в терминале.

### Режим 4. FastAPI-сервер (HTTP API)

Программное управление браузером через REST API.

```bash
python -m src.server
# или
uvicorn src.server:app --host 0.0.0.0 --port 8000
```

Основные эндпоинты:
- `POST /launch` — запуск браузера
- `POST /navigate` — навигация по URL
- `POST /act` — выполнить действие
- `GET /screenshot` — получить скриншот
- `GET /elements` — получить список интерактивных элементов
- `POST /close` — закрыть браузер

---

## Конфигурация

Конфигурация загружается в следующем приоритете (от низкого к высокому):
1. Значения по умолчанию в `AppConfig`
2. `.env` файл
3. YAML-файл (`--config`)
4. CLI-аргументы

Основные параметры:
- `llm_provider`: `openai` | `ollama` | `anthropic`
- `api_key` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
- `model`: `gpt-4o`, `claude-3-5-sonnet-20241022`, `llava`
- `base_url`: кастомный base URL для API
- `viewport_width` / `viewport_height`: размеры viewport (default 1280×720)
- `headless`: запускать ли браузер без GUI (default `true`)
- `output_dir`: папка для скриншотов и state (default `output`)
- `max_steps`: максимальное число шагов (default 15)

---

## Docker

```bash
# Сборка образа
docker build -t skreenmaker .

# Запуск API-сервера
docker run -p 8000:8000 --env-file .env skreenmaker

# Запуск Web TUI
docker run -p 8080:8080 --env-file .env skreenmaker python -m src.interactive_tui --host 0.0.0.0 --port 8080
```

## Тестирование

```bash
# Все тесты
pytest tests/

# Конкретный файл
pytest tests/test_agent.py -v
pytest tests/test_browser.py -v
pytest tests/test_server.py -v
```

---

## Структура проекта

```
src/
  main.py              — CLI entry point для автономного агента
  agent.py             — ядро BrowserAgent: observe → think → act loop
  browser.py           — обёртка над Playwright (BrowserController)
  actions.py           — Pydantic-модель AgentAction
  overlay.py           — рисование номеров элементов на скриншоте
  element_tracker.py   — трекинг интерактивных элементов
  page_parser.py       — извлечение текстового контекста страницы
  prompts.py           — системный промпт для LLM
  llm_client.py        — клиенты OpenAI, Anthropic, Ollama
  config.py            — загрузка конфигурации
  server.py            — FastAPI приложение
  interactive_step.py  — CLI для пошагового ручного режима
  interactive_tui.py   — launcher для Web TUI
  tui_web.py           — FastAPI роуты для Web TUI
  report_generator.py  — генератор HTML-отчётов
  wait_utils.py        — умное ожидание элементов

tests/
  test_agent.py
  test_browser.py
  test_config.py
  test_element_tracker.py
  test_overlay.py
  test_server.py
  test_walkthrough.py
  fixtures/

templates/
  index.html           — фронтенд Web TUI

static/
  app.js               — JS фронтенда
  app.css              — стили фронтенда
  dist/                — собранные ассеты
```

---

## Примечания

- Первый запуск Playwright может занять некоторое время из-за инициализации браузера.
- Статические файлы (`static/app.js`, `static/app.css`) подхватываются автоматически — перезагружать сервер после их изменений не нужно, достаточно обновить страницу (F5).
- Скриншоты и state сохраняются в `output/`.
