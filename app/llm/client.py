from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from app.config import settings


def safe_error_body(response: httpx.Response) -> str:
    text = response.text.strip()
    if not text:
        return ""
    return text[:500]


class LLMClient:
    def __init__(self) -> None:
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/")
        self.model = settings.openai_model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def chat(self, prompt: str, temperature: float = 0.7) -> str:
        if not self.enabled:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=90, headers=headers) as client:
            try:
                response = await client.post(f"{self.base_url}/chat/completions", json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                detail = safe_error_body(exc.response)
                raise RuntimeError(
                    f"LLM request failed with HTTP {status_code}. "
                    f"Check OPENAI_API_KEY, OPENAI_BASE_URL, and OPENAI_MODEL. {detail}"
                ) from exc
            except httpx.RequestError as exc:
                raise RuntimeError(
                    f"LLM request network error: {exc}. Check OPENAI_BASE_URL and Streamlit network access."
                ) from exc
        data = response.json()
        return data["choices"][0]["message"]["content"]


def parse_json_object(text: str) -> Optional[dict[str, Any]]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None
