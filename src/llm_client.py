import base64
import json
import os
from typing import List, Dict, Any, Optional

from openai import OpenAI

from src.actions import AgentAction


class VisionLLM:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY env var or pass api_key."
            )
        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def predict(
        self,
        system_prompt: str,
        user_task: str,
        screenshot_path: str,
        history: List[Dict[str, Any]],
    ) -> AgentAction:
        """
        Отправляет скриншот + историю + задачу в LLM и возвращает структурированное действие.
        """
        with open(screenshot_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]

        for entry in history:
            messages.append({"role": "user", "content": entry["observation"]})
            if entry.get("action"):
                messages.append({"role": "assistant", "content": json.dumps(entry["action"], ensure_ascii=False)})

        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Задача: {user_task}\n\nЧто делать дальше? Ответь строго JSON с полями action_type, reasoning и нужными параметрами.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}",
                            "detail": "low",
                        },
                    },
                ],
            }
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
            max_tokens=800,
        )

        raw = response.choices[0].message.content or "{}"
        # Иногда модель оборачивает JSON в ```json ... ```
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[-1]
            raw = raw.replace("json", "", 1).strip()

        data = json.loads(raw)
        return AgentAction(**data)
