import json
import os
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel

from src.browser import BrowserController
from src.overlay import draw_overlay
from src.llm_client import VisionLLM
from src.prompts import SYSTEM_PROMPT, build_elements_list
from src.actions import AgentAction


console = Console()


class BrowserAgent:
    def __init__(
        self,
        task: str,
        start_url: Optional[str] = None,
        headless: bool = True,
        max_steps: int = 15,
        output_dir: str = "output",
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
    ):
        self.task = task
        self.start_url = start_url
        self.headless = headless
        self.max_steps = max_steps
        self.output_dir = output_dir
        self.browser = BrowserController()
        self.llm = VisionLLM(api_key=api_key, model=model)
        self.history: List[Dict[str, Any]] = []

        os.makedirs(self.output_dir, exist_ok=True)

    async def run(self) -> Dict[str, Any]:
        await self.browser.launch(headless=self.headless)
        try:
            if self.start_url:
                await self.browser.navigate(self.start_url)

            for step in range(1, self.max_steps + 1):
                console.rule(f"[bold cyan]Step {step}/{self.max_steps}")

                # 1. Скриншот
                raw_screenshot = os.path.join(self.output_dir, f"step_{step}_raw.jpg")
                await self.browser.screenshot(raw_screenshot)

                # 2. Интерактивные элементы
                elements, elements_map = await self.browser.get_interactive_elements()

                # 3. Overlay
                annotated = os.path.join(self.output_dir, f"step_{step}_annotated.jpg")
                _, overlay_map = draw_overlay(raw_screenshot, elements, annotated)

                # 4. Формируем промпт
                elements_list = build_elements_list(overlay_map)
                system_prompt = SYSTEM_PROMPT.format(elements_list=elements_list)

                # 5. Запрос к LLM
                try:
                    action = self.llm.predict(
                        system_prompt=system_prompt,
                        user_task=self.task,
                        screenshot_path=annotated,
                        history=self.history,
                    )
                except Exception as e:
                    console.print(f"[red]LLM error: {e}[/red]")
                    action = AgentAction(action_type="fail", reason=f"LLM error: {e}")

                console.print(Panel(
                    f"[bold]{action.action_type.upper()}[/bold]\n{action.reasoning}",
                    title="Agent Decision",
                    border_style="green",
                ))

                # 6. Выполняем действие
                observation = await self._execute_action(action, elements_map)

                # 7. Сохраняем в историю
                self.history.append({
                    "step": step,
                    "observation": observation,
                    "action": action.model_dump(exclude_none=True),
                })

                if action.action_type in ("finish", "fail"):
                    break

            # Финальный скриншот
            final_shot = os.path.join(self.output_dir, "final.jpg")
            await self.browser.screenshot(final_shot)

            last_action = self.history[-1]["action"] if self.history else {}
            result = {
                "success": last_action.get("action_type") == "finish",
                "summary": last_action.get("summary") or last_action.get("reason"),
                "steps_taken": len(self.history),
                "output_dir": self.output_dir,
            }
            console.print(Panel(json.dumps(result, ensure_ascii=False, indent=2), title="Result", border_style="blue"))
            return result

        finally:
            await self.browser.close()

    async def _execute_action(self, action: AgentAction, elements_map: Dict[int, Any]) -> str:
        if action.action_type == "navigate":
            if action.url:
                await self.browser.navigate(action.url)
                return f"Navigated to {action.url}"
            return "No URL provided for navigate"

        if action.action_type == "click":
            if action.element_display_id and action.element_display_id in elements_map:
                info = elements_map[action.element_display_id]
                await self.browser.click_by_coords(info["cx"], info["cy"])
                return f"Clicked element {action.element_display_id} ({info['tag']}: {info['text']})"
            return f"Element {action.element_display_id} not found on current screen"

        if action.action_type == "right_click":
            if action.element_display_id and action.element_display_id in elements_map:
                info = elements_map[action.element_display_id]
                await self.browser._page.mouse.click(info["cx"], info["cy"], button="right")
                return f"Right-clicked element {action.element_display_id}"
            return f"Element {action.element_display_id} not found"

        if action.action_type == "hover":
            if action.element_display_id and action.element_display_id in elements_map:
                info = elements_map[action.element_display_id]
                await self.browser.hover(info["cx"], info["cy"])
                return f"Hovered element {action.element_display_id}"
            return f"Element {action.element_display_id} not found"

        if action.action_type == "type":
            if action.element_display_id and action.element_display_id in elements_map:
                info = elements_map[action.element_display_id]
                await self.browser.click_by_coords(info["cx"], info["cy"])
                if action.text:
                    await self.browser._page.keyboard.type(action.text)
                    return f"Typed '{action.text}' into element {action.element_display_id}"
                return "No text provided for type"
            return f"Element {action.element_display_id} not found for typing"

        if action.action_type == "press_key":
            key = action.key or "Enter"
            await self.browser.press_key(key)
            return f"Pressed key {key}"

        if action.action_type == "scroll":
            direction = action.direction or "down"
            amount = action.amount or 300
            await self.browser.scroll(direction, amount)
            return f"Scrolled {direction} by {amount}px"

        if action.action_type == "screenshot":
            fname = action.filename or "manual.jpg"
            path = os.path.join(self.output_dir, fname)
            await self.browser.screenshot(path)
            return f"Screenshot saved to {path}"

        if action.action_type == "wait":
            import asyncio
            seconds = action.seconds or 1
            await asyncio.sleep(seconds)
            return f"Waited {seconds}s"

        if action.action_type == "finish":
            return f"Task finished: {action.summary}"

        if action.action_type == "fail":
            return f"Task failed: {action.reason}"

        return f"Unknown action: {action.action_type}"
