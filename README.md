# SkreenMaker

Автономный агент для управления браузером: скриншоты, клики, навигация.

## Архитектура

- **Playwright** — управление браузером Chromium.
- **Overlay-маркировка** — на скриншоты накладываются номера интерактивных элементов для точных кликов.
- **Два режима работы:**
  1. **Автономный** (OpenAI Vision API) — агент сам принимает решения на основе скриншотов.
  2. **Интерактивный** (Kimi-режим) — вы смотрите скриншоты и отдаете команды агенту пошагово.

## Установка

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Режим 1. Автономный агент (OpenAI)

Требуется `OPENAI_API_KEY`.

```bash
python -m src.main \
  --url "https://example.com" \
  --task "Найди ссылку 'Learn more' и перейди по ней" \
  --output-dir output
```

Параметры:
- `--url` — стартовый URL
- `--task` — задача в свободной форме
- `--model` — модель OpenAI (по умолчанию `gpt-4o`)
- `--max-steps` — лимит шагов (по умолчанию 15)
- `--headless` / `--no-headless` — показывать окно браузера

## Режим 2. Интерактивный (Kimi-режим)

На каждом шаге агент делает скриншот с номерами элементов, сохраняет его и ждет вашей команды.

### Шаг 1. Первый запуск

```bash
python -m src.interactive_step --url "https://example.com" --history "[]"
```

Агент сохранит:
- `output/step_1_annotated.jpg` — скриншот с номерами элементов
- `output/state/current_state.json` — список элементов и состояние

### Шаг 2. Анализ и следующее действие

Откройте `output/step_1_annotated.jpg`, выберите элемент и подготовьте JSON действия.

### Шаг 3. Следующий шаг

Сохраните историю действий в файл и запустите:

```bash
# Windows PowerShell
echo '[{"action_type":"click","element_id":1}]' > output/history.json
python -m src.interactive_step --url "https://example.com" --history-file output/history.json
```

Агент восстановит сессию (cookies, localStorage), выполнит все действия из истории и сделает новый скриншот.

### Доступные действия

```json
{"action_type": "navigate", "url": "https://iana.org"}
{"action_type": "click", "element_id": 5}
{"action_type": "type", "element_id": 3, "text": "hello"}
{"action_type": "scroll", "direction": "down", "amount": 300}
{"action_type": "screenshot", "filename": "result.jpg"}
{"action_type": "wait", "seconds": 2}
```

## Структура проекта

```
src/
  browser.py          — управление Playwright
  overlay.py          — рисование номеров на скриншотах
  actions.py          — Pydantic-модели действий
  llm_client.py       — клиент OpenAI Vision
  prompts.py          — системные промпты
  agent.py            — автономный цикл агента
  main.py             — CLI для автономного режима
  interactive_step.py — CLI для интерактивного режима
```

## Тестирование

```bash
# Быстрый тест браузера + overlay
python test_browser.py
```
