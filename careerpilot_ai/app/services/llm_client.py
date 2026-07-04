import json
from typing import TypeVar

import httpx
from pydantic import BaseModel

from careerpilot_ai.app.config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Optional OpenAI-compatible client for later agent upgrades."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.llm_api_key)

    def structured_completion(self, system: str, prompt: str, output_model: type[T]) -> T:
        if not self.configured:
            raise RuntimeError("LLM_API_KEY is not configured; deterministic MVP agents remain available.")
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        payload = {
            "model": self.settings.llm_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        last_error: Exception | None = None
        with httpx.Client(timeout=45) as client:
            for attempt in range(2):
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                try:
                    return output_model.model_validate(json.loads(content))
                except (json.JSONDecodeError, ValueError) as exc:
                    last_error = exc
                    if attempt == 0:
                        messages.extend([
                            {"role": "assistant", "content": content},
                            {
                                "role": "user",
                                "content": (
                                    "Return corrected JSON only. It must validate against this schema: "
                                    + json.dumps(output_model.model_json_schema())
                                ),
                            },
                        ])
        raise RuntimeError(f"LLM returned invalid structured output after one retry: {last_error}")
