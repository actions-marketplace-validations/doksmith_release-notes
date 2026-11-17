import os
from typing import List, Optional
from .base import BaseAIProvider

# Verified OpenAI models prioritizing cost-effective and capable models
OPENAI_CANDIDATE_MODELS = (
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-3.5-turbo",
)


class OpenAIProvider(BaseAIProvider):
    name = "openai"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "")).strip() or None

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "openai SDK is not installed. Please install requirements.txt"
            ) from e

        kwargs = {"api_key": self.api_key, "timeout": 30.0, "max_retries": 2}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return OpenAI(**kwargs)

    def list_available_models(self) -> List[str]:
        if not self.is_configured():
            return []

        client = self._get_client()
        try:
            resp = client.models.list()
            models = [getattr(item, "id", "") for item in getattr(resp, "data", [])]
            return [m for m in models if m]
        except Exception as e:
            print(f"[release-notes] Warning: Could not query OpenAI models endpoint: {e}")
            return list(OPENAI_CANDIDATE_MODELS)

    def resolve_model(self, requested_model: Optional[str] = None) -> str:
        available = self.list_available_models()
        if requested_model:
            for m in available:
                if m == requested_model:
                    return m
            print(f"[release-notes] Requested OpenAI model '{requested_model}' not found in available list.")

        for candidate in OPENAI_CANDIDATE_MODELS:
            for m in available:
                if candidate in m or m == candidate:
                    return m

        return available[0] if available else OPENAI_CANDIDATE_MODELS[0]

    def generate_release_notes(self, prompt: str, system_prompt: str, model: str) -> str:
        print(f"[release-notes] Querying OpenAI with official SDK ({model})...")
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_completion_tokens=2048,
        )

        content = completion.choices[0].message.content if completion.choices else None
        if not content or not content.strip():
            raise RuntimeError(f"OpenAI ({model}) returned empty text response.")

        print(f"[release-notes] Successfully generated release notes with OpenAI ({model}).")
        return content.strip()
