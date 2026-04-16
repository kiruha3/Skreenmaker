import json
import os
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel

from src.browser import BrowserController
from src.overlay import draw_overlay
from src.llm_client import create_llm, BaseVisionLLM
from src.page_parser import extract_page_context, format_page_context
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
        llm_provider: str = "openai",
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        base_url: Optional[str] = None,
        resume: bool = False,
    ):
        self.task = task
        self.start_url = start_url
        self.headless = headless
        self.max_steps = max_steps
        self.output_dir = output_dir
        self.browser = BrowserController()
        self.llm: BaseVisionLLM = create_llm(
            provider=llm_provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
        self.history: List[Dict[str, Any]] = []
        self.resume = resume
        self._state_path = os.path.join(self.output_dir, "agent_state.json")

        os.makedirs(self.output_dir, exist_ok=True)

        if self.resume:
            self._load_state()

    def _load_state(self):
        if os.path.exists(self._state_path):
            try:
                with open(self._state_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.history = state.get("history", [])
                self.start_url = state.get("current_url", self.start_url)
                console.print(f"[yellow]Resumed session from step {len(self.history)}[/yellow]")
            except Exception as e:
                console.print(f"[red]Failed to load state: {e}[/red]")

    def _save_state(self, current_url: str):
        state = {
            "history": self.history,
            "current_url": current_url,
            "task": self.task,
        }
        try:
            with open(self._state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            console.print(f"[red]Failed to save state: {e}[/red]")

    async def run(self) -> Dict[str, Any]:
        await self.browser.launch(headless=self.headless)
        try:
            starting_step = len(self.history) + 1
            if self.start_url and starting_step == 1:
                await self.browser.navigate(self.start_url)

            for step in range(starting_step, self.max_steps + 1):
                console.rule(f"[bold cyan]Step {step}/{self.max_steps}")

                action, observation = await self._step(step)

                self.history.append({
                    "step": step,
                    "observation": observation,
                    "action": action.model_dump(exclude_none=True),
                })

                current_url = self.browser._page.url
                self._save_state(current_url)

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

    async def _step(self, step: int, max_retries: int = 2) -> tuple[AgentAction, str]:
        """Один полный цикл observe → think → act с возможностью retry."""
        for attempt in range(max_retries + 1):
            # 1. Скриншот
            raw_screenshot = os.path.join(self.output_dir, f"step_{step}_raw.jpg")
            await self.browser.screenshot(raw_screenshot)

            # 2. Интерактивные элементы
            elements, elements_map = await self.browser.get_interactive_elements()

            # 3. Overlay
            annotated = os.path.join(self.output_dir, f"step_{step}_annotated.jpg")
            _, overlay_map = draw_overlay(raw_screenshot, elements, annotated)

            # 4. Текстовый контекст страницы
            page_ctx = await extract_page_context(self.browser._page)
            page_ctx_str = format_page_context(page_ctx)

            # 5. Формируем промпт
            elements_list = build_elements_list(overlay_map)
            system_prompt = SYSTEM_PROMPT.format(elements_list=elements_list)

            # 6. Запрос к LLM
            try:
                action = self.llm.predict(
                    system_prompt=system_prompt,
                    user_task=self.task,
                    screenshot_path=annotated,
                    history=await self._compact_history(),
                    page_context=page_ctx_str,
                )
            except Exception as e:
                console.print(f"[red]LLM error: {e}[/red]")
                action = AgentAction(action_type="fail", reason=f"LLM error: {e}")

            console.print(Panel(
                f"[bold]{action.action_type.upper()}[/bold]\n{action.reasoning}",
                title="Agent Decision",
                border_style="green",
            ))

            # 7. Circuit breaker — проверяем, не застрял ли агент
            if self._is_stuck(action):
                return AgentAction(action_type="fail", reason="Agent stuck in a loop for 3 consecutive steps"), "Circuit breaker triggered"

            # 8. Выполняем действие
            try:
                observation = await self._execute_action(action, elements_map)
                return action, observation
            except Exception as e:
                console.print(f"[yellow]Action error (attempt {attempt + 1}/{max_retries + 1}): {e}[/yellow]")
                if attempt < max_retries:
                    await self.browser.wait_for_timeout(500)
                else:
                    return AgentAction(action_type="fail", reason=f"Action failed after {max_retries + 1} attempts: {e}"), f"Action failed: {e}"

        return AgentAction(action_type="fail", reason="Unknown failure"), "Unknown failure"

    def _is_stuck(self, current_action: AgentAction) -> bool:
        """Circuit breaker: если последние 3 шага — одно и то же действие с ошибкой / без изменений."""
        if len(self.history) < 2:
            return False
        recent = self.history[-2:]
        current_type = current_action.action_type
        # Проверяем, что последние 2 + текущее = одинаковый тип и последние 2 имели проблемы
        types = [h["action"].get("action_type") for h in recent] + [current_type]
        if len(set(types)) != 1:
            return False
        # Проверяем, что последние 2 observation содержали признаки неудачи
        failure_signals = ("not found", "failed", "error", "no change", "out of range")
        stuck_count = sum(1 for h in recent if any(sig in h.get("observation", "").lower() for sig in failure_signals))
        return stuck_count >= 2

    async def _compact_history(self) -> List[Dict[str, Any]]:
        """Если история > 8 шагов, суммируем первые шаги для экономии токенов."""
        if len(self.history) <= 8:
            return self.history

        # Пробуем сделать LLM-summary первых шагов
        steps_to_summarize = self.history[:-5]
        try:
            summary_text = await self._summarize_history(steps_to_summarize)
        except Exception:
            summary_text = f"Previous {len(steps_to_summarize)} steps summarized."

        summary = {
            "step": 0,
            "observation": summary_text,
            "action": {"action_type": "summary"},
        }
        return [summary] + self.history[-5:]

    async def _summarize_history(self, steps: List[Dict[str, Any]]) -> str:
        """Отправляет старую историю к LLM для краткого summary."""
        lines = []
        for h in steps:
            action = h.get("action", {})
            lines.append(
                f"Step {h.get('step')}: {action.get('action_type')} -> {h.get('observation')}"
            )
        prompt = (
            "Summarize the following browser automation steps in 3-5 sentences. "
            "Focus on what was accomplished and any important state changes:\n\n"
            + "\n".join(lines)
        )
        # Создаём минимальный dummy-скриншот, т.к. predict требует путь к изображению
        import tempfile
        from PIL import Image
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            dummy_path = tmp.name
        try:
            Image.new("RGB", (1, 1), color="white").save(dummy_path, "JPEG")
            summary_action = self.llm.predict(
                system_prompt="You are a helpful assistant. Respond with a concise plain-text summary only.",
                user_task=prompt,
                screenshot_path=dummy_path,
                history=[],
                page_context="",
            )
            return summary_action.reasoning or str(summary_action.model_dump())
        except Exception:
            raise
        finally:
            try:
                os.unlink(dummy_path)
            except Exception:
                pass

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
                await self.browser.mouse_click(info["cx"], info["cy"], button="right")
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
                    await self.browser.keyboard_type(action.text)
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

        if action.action_type == "select_option":
            if action.element_display_id and action.element_display_id in elements_map:
                info = elements_map[action.element_display_id]
                selector = info.get("selector", "")
                if selector:
                    val = action.option_value or action.text or ""
                    await self.browser.select_option(selector, val)
                    return f"Selected '{val}' in element {action.element_display_id}"
                return "No selector available for select_option"
            return f"Element {action.element_display_id} not found"

        if action.action_type == "upload_file":
            if action.element_display_id and action.element_display_id in elements_map:
                info = elements_map[action.element_display_id]
                selector = info.get("selector", "")
                if selector and action.file_path:
                    await self.browser.upload_file(selector, action.file_path)
                    return f"Uploaded {action.file_path} to element {action.element_display_id}"
                return "Missing selector or file_path for upload"
            return f"Element {action.element_display_id} not found"

        if action.action_type == "switch_tab":
            idx = action.tab_index or 0
            try:
                await self.browser.bring_to_front_tab(idx)
                return f"Switched to tab {idx}"
            except (IndexError, RuntimeError):
                return f"Tab index {idx} out of range"

        if action.action_type == "dismiss_alert":
            await self.browser.set_dialog_action("dismiss")
            return "Alert will be dismissed"

        if action.action_type == "accept_alert":
            await self.browser.set_dialog_action("accept")
            return "Alert will be accepted"

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
