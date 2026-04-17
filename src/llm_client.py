import base64
import json
import os
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


def _call_with_retry(func, *args, **kwargs):
    delays = [1.0, 3.0, 9.0]
    last_exc = None
    for attempt, delay in enumerate(delays):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < len(delays) - 1:
                time.sleep(delay)
    raise last_exc

from openai import OpenAI

from src.actions import AgentAction


class BaseVisionLLM(ABC):
    @abstractmethod
    def predict(
        self,
        system_prompt: str,
        user_task: str,
        screenshot_path: str,
        history: List[Dict[str, Any]],
        page_context: Optional[str] = None,
    ) -> AgentAction:
        raise NotImplementedError

    @abstractmethod
    def predict_text(
        self,
        system_prompt: str,
        user_task: str,
        history: List[Dict[str, Any]],
        page_context: Optional[str] = None,
    ) -> AgentAction:
        raise NotImplementedError

    @staticmethod
    def _clean_json(raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[-1]
            raw = raw.replace("json", "", 1).strip()
        return raw

    @staticmethod
    def _extract_response_text(response) -> str:
        msg = response.choices[0].message
        text = msg.content or ""
        if not text and hasattr(msg, "reasoning_content"):
            text = msg.reasoning_content or ""
        return text

    @staticmethod
    def _build_messages(
        system_prompt: str,
        user_task: str,
        history: List[Dict[str, Any]],
        page_context: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]

        for entry in history:
            messages.append({"role": "user", "content": entry["observation"]})
            if entry.get("action"):
                messages.append({"role": "assistant", "content": json.dumps(entry["action"], ensure_ascii=False)})

        task_text = f"Задача: {user_task}\n\nЧто делать дальше? Ответь строго JSON с полями action_type, reasoning и нужными параметрами."
        if page_context:
            task_text = f"Контекст страницы:\n{page_context}\n\n{task_text}"

        messages.append({"role": "user", "content": task_text})
        return messages


class OpenAILLM(BaseVisionLLM):
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o", base_url: Optional[str] = None, max_tokens: int = 800):
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("OpenAI API key is required.")
        self.client = OpenAI(api_key=key, base_url=base_url, timeout=60.0)
        self.model = model
        self.max_tokens = max_tokens

    def predict(
        self,
        system_prompt: str,
        user_task: str,
        screenshot_path: str,
        history: List[Dict[str, Any]],
        page_context: Optional[str] = None,
    ) -> AgentAction:
        with open(screenshot_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        messages = self._build_messages(system_prompt, user_task, history, page_context)
        # Добавляем изображение к последнему user-сообщению
        last_msg = messages[-1]
        if isinstance(last_msg["content"], str):
            last_msg["content"] = [
                {"type": "text", "text": last_msg["content"]},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}", "detail": "low"},
                },
            ]
        else:
            last_msg["content"].append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}", "detail": "low"},
                }
            )

        response = _call_with_retry(
            self.client.chat.completions.create,
            model=self.model,
            messages=messages,
            temperature=0.2,
            max_tokens=self.max_tokens,
        )
        raw = self._clean_json(self._extract_response_text(response) or "{}")
        data = json.loads(raw)
        return AgentAction(**data)

    def predict_text(
        self,
        system_prompt: str,
        user_task: str,
        history: List[Dict[str, Any]],
        page_context: Optional[str] = None,
    ) -> AgentAction:
        messages = self._build_messages(system_prompt, user_task, history, page_context)
        response = _call_with_retry(
            self.client.chat.completions.create,
            model=self.model,
            messages=messages,
            temperature=0.2,
            max_tokens=self.max_tokens,
        )
        raw = self._clean_json(self._extract_response_text(response) or "{}")
        data = json.loads(raw)
        return AgentAction(**data)


class OllamaLLM(BaseVisionLLM):
    def __init__(self, base_url: str = "http://localhost:11434/v1", model: str = "llava"):
        self.client = OpenAI(base_url=base_url, api_key="ollama", timeout=60.0)
        self.model = model

    def predict(
        self,
        system_prompt: str,
        user_task: str,
        screenshot_path: str,
        history: List[Dict[str, Any]],
        page_context: Optional[str] = None,
    ) -> AgentAction:
        with open(screenshot_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        messages = self._build_messages(system_prompt, user_task, history, page_context)
        last_msg = messages[-1]
        if isinstance(last_msg["content"], str):
            last_msg["content"] = [
                {"type": "text", "text": last_msg["content"]},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                },
            ]
        else:
            last_msg["content"].append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                }
            )

        response = _call_with_retry(
            self.client.chat.completions.create,
            model=self.model,
            messages=messages,
            temperature=0.2,
            max_tokens=self.max_tokens,
        )
        raw = self._clean_json(self._extract_response_text(response) or "{}")
        data = json.loads(raw)
        return AgentAction(**data)

    def predict_text(
        self,
        system_prompt: str,
        user_task: str,
        history: List[Dict[str, Any]],
        page_context: Optional[str] = None,
    ) -> AgentAction:
        messages = self._build_messages(system_prompt, user_task, history, page_context)
        response = _call_with_retry(
            self.client.chat.completions.create,
            model=self.model,
            messages=messages,
            temperature=0.2,
            max_tokens=self.max_tokens,
        )
        raw = self._clean_json(self._extract_response_text(response) or "{}")
        data = json.loads(raw)
        return AgentAction(**data)


class AnthropicLLM(BaseVisionLLM):
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("Anthropic API key is required.")
        # Anthropic SDK можно использовать напрямую, но OpenAI-compatible wrapper
        # иногда проще; здесь используем нативный SDK если доступен
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=key, timeout=60.0)
            self.native = True
        except ImportError:
            self.client = OpenAI(api_key=key, base_url="https://api.anthropic.com/v1/", timeout=60.0)
            self.native = False
        self.model = model

    def predict(
        self,
        system_prompt: str,
        user_task: str,
        screenshot_path: str,
        history: List[Dict[str, Any]],
        page_context: Optional[str] = None,
    ) -> AgentAction:
        with open(screenshot_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        messages = self._build_messages(system_prompt, user_task, history, page_context)
        last_msg = messages[-1]
        text_content = last_msg["content"] if isinstance(last_msg["content"], str) else last_msg["content"][0]["text"]

        if self.native:
            content_blocks = [
                {"type": "text", "text": text_content},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_b64,
                    },
                },
            ]
            # Преобразуем history в формат Anthropic
            anthropic_messages: List[Dict[str, Any]] = []
            for m in messages[:-1]:
                role = "user" if m["role"] == "user" else "assistant"
                anthropic_messages.append({"role": role, "content": m["content"]})
            anthropic_messages.append({"role": "user", "content": content_blocks})

            response = _call_with_retry(
                self.client.messages.create,
                model=self.model,
                max_tokens=800,
                temperature=0.2,
                system=system_prompt,
                messages=anthropic_messages,
            )
            raw = self._clean_json(response.content[0].text if response.content else "{}")
        else:
            # OpenAI-compatible fallback
            last_msg["content"] = [
                {"type": "text", "text": text_content},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                },
            ]
            response = _call_with_retry(
                self.client.chat.completions.create,
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=self.max_tokens,
            )
            raw = self._clean_json(self._extract_response_text(response) or "{}")

        data = json.loads(raw)
        return AgentAction(**data)

    def predict_text(
        self,
        system_prompt: str,
        user_task: str,
        history: List[Dict[str, Any]],
        page_context: Optional[str] = None,
    ) -> AgentAction:
        messages = self._build_messages(system_prompt, user_task, history, page_context)
        if self.native:
            anthropic_messages: List[Dict[str, Any]] = []
            for m in messages:
                role = "user" if m["role"] == "user" else "assistant"
                anthropic_messages.append({"role": role, "content": m["content"]})
            response = _call_with_retry(
                self.client.messages.create,
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.2,
                system=system_prompt,
                messages=anthropic_messages,
            )
            raw = self._clean_json(response.content[0].text if response.content else "{}")
        else:
            response = _call_with_retry(
                self.client.chat.completions.create,
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=self.max_tokens,
            )
            raw = self._clean_json(self._extract_response_text(response) or "{}")
        data = json.loads(raw)
        return AgentAction(**data)


class KimiLLM(OpenAILLM):
    def __init__(self, api_key: Optional[str] = None, model: str = "moonshot-v1-8k-vision-preview"):
        key = api_key or os.environ.get("MOONSHOT_API_KEY")
        if not key:
            raise ValueError("Moonshot (Kimi) API key is required.")
        super().__init__(api_key=key, model=model, base_url="https://api.moonshot.cn/v1")


class KimiCliLLM(OpenAILLM):
    """Использует установленный Kimi CLI без ручного ввода API-ключа."""

    def __init__(self, model: str = "kimi-for-coding"):
        token, headers = self._resolve_auth()
        self.client = OpenAI(
            api_key=token,
            base_url="https://api.kimi.com/coding/v1",
            timeout=60.0,
            default_headers=headers,
        )
        self.model = model
        self.max_tokens = 4000

    @staticmethod
    def _resolve_auth() -> tuple[str, dict[str, str]]:
        creds_path = os.path.expanduser("~/.kimi/credentials/kimi-code.json")
        if not os.path.exists(creds_path):
            raise ValueError(
                "Kimi CLI credentials not found. Please run 'kimi login' first."
            )
        with open(creds_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        token = data.get("access_token")
        if not token:
            raise ValueError("Kimi CLI access_token is missing or expired. Please run 'kimi login'.")

        version = "1.34.0"
        user_agent = "KimiCLI/1.34.0"
        try:
            import sys
            candidate = None
            for sp in sys.path:
                if "kimi-cli" in sp and "site-packages" in sp:
                    candidate = sp
                    break
            if candidate is None:
                candidate = os.path.expanduser(
                    "~\\AppData\\Roaming\\uv\\tools\\kimi-cli\\Lib\\site-packages"
                )
            inserted = False
            if candidate not in sys.path:
                sys.path.insert(0, candidate)
                inserted = True
            try:
                from kimi_cli.constant import VERSION, USER_AGENT
                version = VERSION
                user_agent = USER_AGENT
            finally:
                if inserted:
                    sys.path.remove(candidate)
        except Exception:
            pass

        headers = {
            "User-Agent": user_agent,
            "X-Msh-Platform": "kimi_cli",
            "X-Msh-Version": version,
        }
        return token, headers


def create_llm(provider: str, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None) -> BaseVisionLLM:
    provider = provider.lower()
    if provider == "openai":
        return OpenAILLM(api_key=api_key, model=model or "gpt-4o", base_url=base_url)
    if provider == "kimi":
        return KimiLLM(api_key=api_key, model=model or "moonshot-v1-8k-vision-preview")
    if provider == "kimi-cli":
        return KimiCliLLM(model=model or "kimi-for-coding")
    if provider == "ollama":
        return OllamaLLM(base_url=base_url or "http://localhost:11434/v1", model=model or "llava")
    if provider == "anthropic":
        return AnthropicLLM(api_key=api_key, model=model or "claude-3-5-sonnet-20241022")
    raise ValueError(f"Unknown LLM provider: {provider}")
