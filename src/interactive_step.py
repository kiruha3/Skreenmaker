import argparse
import asyncio
import json
import os
import sys

from src.browser import BrowserController
from src.overlay import draw_overlay
from src.actions import AgentAction


def load_history(history_str: str):
    try:
        return json.loads(history_str)
    except Exception as e:
        print(f"Failed to parse history JSON: {e}")
        sys.exit(1)


async def run_step(url: str, history: list, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    state_dir = os.path.join(output_dir, "state")
    os.makedirs(state_dir, exist_ok=True)

    storage_path = os.path.join(state_dir, "storage_state.json")

    browser = BrowserController()
    await browser.launch(headless=True)
    try:
        # Восстанавливаем storage state если есть
        if os.path.exists(storage_path) and browser._context:
            # Пересоздаем context с storage state
            await browser._context.close()
            browser._context = await browser._browser.new_context(
                viewport={"width": browser.viewport_width, "height": browser.viewport_height},
                storage_state=storage_path,
            )
            browser._page = await browser._context.new_page()

        await browser.navigate(url)

        # Воспроизводим всю историю действий
        for i, action_data in enumerate(history):
            action = AgentAction(**action_data)
            try:
                await _execute_action(browser, action)
            except Exception as e:
                # Если страница перезагрузилась (например, после login), подождем немного
                print(f"  Replayed action {i+1}: {action.action_type} (navigation detected, waiting...)")
                import asyncio
                await asyncio.sleep(1.5)
            print(f"  Replayed action {i+1}: {action.action_type}")

        # Делаем скриншот текущего состояния
        step_num = len(history) + 1
        raw_path = os.path.join(output_dir, f"step_{step_num}_raw.jpg")
        await browser.screenshot(raw_path)

        elements, elements_map = await browser.get_interactive_elements()
        annotated_path = os.path.join(output_dir, f"step_{step_num}_annotated.jpg")
        _, overlay_map = draw_overlay(raw_path, elements, annotated_path)

        # Сохраняем текущее состояние
        current_state = {
            "step": step_num,
            "url": url,
            "history": history,
            "elements": overlay_map,
            "annotated_screenshot": annotated_path,
            "raw_screenshot": raw_path,
        }
        state_path = os.path.join(state_dir, "current_state.json")
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(current_state, f, ensure_ascii=False, indent=2)

        # Сохраняем storage state для следующего шага
        if browser._context:
            await browser._context.storage_state(path=storage_path)

        print(f"\n=== STEP {step_num} COMPLETE ===")
        print(f"Annotated screenshot: {annotated_path}")
        print(f"Raw screenshot: {raw_path}")
        print(f"State file: {state_path}")
        print(f"\nInteractive elements ({len(overlay_map)}):")
        for display_id, info in overlay_map.items():
            print(f"  {display_id}. [{info['tag']}] '{info['text']}'")

        print("\nNext: analyze the annotated screenshot and provide the next action.")
        print("Run:")
        next_history = history + [{"action_type": "YOUR_ACTION", "element_display_id": 1}]
        print(f'  python -m src.interactive_step --url "{url}" --history \'{json.dumps(next_history, ensure_ascii=False)}\'')

    finally:
        await browser.close()


async def _execute_action(browser: BrowserController, action: AgentAction):
    """Выполняет одно действие. Для replay используем упрощенную логику."""
    if action.action_type == "navigate" and action.url:
        await browser.navigate(action.url)
        return

    if action.action_type == "click" and action.element_display_id is not None:
        _, fresh_map = await browser.get_interactive_elements()
        target = fresh_map.get(action.element_display_id)
        if target:
            await browser.click_by_coords(target.cx, target.cy)
        return

    if action.action_type == "right_click" and action.element_display_id is not None:
        _, fresh_map = await browser.get_interactive_elements()
        target = fresh_map.get(action.element_display_id)
        if target:
            await browser._page.mouse.click(target.cx, target.cy, button="right")
        return

    if action.action_type == "hover" and action.element_display_id is not None:
        _, fresh_map = await browser.get_interactive_elements()
        target = fresh_map.get(action.element_display_id)
        if target:
            await browser.hover(target.cx, target.cy)
        return

    if action.action_type == "type" and action.element_display_id is not None and action.text:
        _, fresh_map = await browser.get_interactive_elements()
        target = fresh_map.get(action.element_display_id)
        if target:
            await browser.click_by_coords(target.cx, target.cy)
            await browser._page.keyboard.type(action.text)
        return

    if action.action_type == "press_key" and action.key:
        await browser.press_key(action.key)
        return

    if action.action_type == "scroll":
        await browser.scroll(action.direction or "down", action.amount or 300)
        return

    if action.action_type == "select_option" and action.element_display_id is not None:
        _, fresh_map = await browser.get_interactive_elements()
        target = fresh_map.get(action.element_display_id)
        if target and target.selector:
            val = action.option_value or action.text or ""
            await browser.select_option(target.selector, val)
        return

    if action.action_type == "upload_file" and action.element_display_id is not None:
        _, fresh_map = await browser.get_interactive_elements()
        target = fresh_map.get(action.element_display_id)
        if target and target.selector and action.file_path:
            await browser.upload_file(target.selector, action.file_path)
        return

    if action.action_type == "switch_tab" and action.tab_index is not None:
        pages = browser._context.pages
        if 0 <= action.tab_index < len(pages):
            browser._page = pages[action.tab_index]
            await browser._page.bring_to_front()
        return

    if action.action_type == "screenshot" and action.filename:
        path = os.path.join("output", action.filename)
        await browser.screenshot(path)
        return

    if action.action_type == "wait":
        import asyncio
        await asyncio.sleep(action.seconds or 1)
        return


def main():
    parser = argparse.ArgumentParser(description="Interactive browser step for Kimi")
    parser.add_argument("--url", type=str, required=True, help="URL")
    parser.add_argument("--history", type=str, default="[]", help="JSON array of previous AgentAction objects")
    parser.add_argument("--history-file", type=str, default=None, help="Path to JSON file with previous actions")
    parser.add_argument("--output-dir", type=str, default="output", help="Output directory")
    args = parser.parse_args()

    if args.history_file:
        with open(args.history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = load_history(args.history)
    asyncio.run(run_step(args.url, history, args.output_dir))


if __name__ == "__main__":
    main()
