# SkreenMaker — Agent Instructions

## Available Skills

- **graphify** (`.kimi/skills/graphify/SKILL.md`) — Turn any folder into a navigable knowledge graph (code, docs, images, papers). Trigger: `/graphify`.

When the user types `/graphify`, invoke the skill by reading `.kimi/skills/graphify/SKILL.md` and following its instructions before doing anything else.

## Project Context

- **Stack**: Python 3.9, Playwright, FastAPI, pytest
- **Entry points**: `src/main.py` (CLI agent), `src/server.py` (FastAPI server), `src/interactive_tui.py` (Web TUI launcher)
- **Tests**: `pytest tests/`
- **Docs**: `docs/skreenmaker_architecture.png` + `.excalidraw`
