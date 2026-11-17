import os
from typing import List, Optional
from .base import BaseAIProvider

# Verified Groq models prioritizing low token overhead and high speed
GROQ_CANDIDATE_MODELS = (
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-20b",
)


class GroqProvider(BaseAIProvider):
    name = "groq"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "").strip()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        try:
            from groq import Groq
        except ImportError as e:
            raise RuntimeError(
                "groq SDK is not installed. Please install requirements.txt"
            ) from e

        return Groq(api_key=self.api_key, timeout=30.0, max_retries=2)

    def list_available_models(self) -> List[str]:
        if not self.is_configured():
            return []

        client = self._get_client()
        try:
            resp = client.models.list()
            models = []
            for item in getattr(resp, "data", []):
                if getattr(item, "active", True):
                    models.append(item.id)
            return models
        except Exception as e:
            print(f"[release-notes] Warning: Could not query Groq models endpoint: {e}")
            return list(GROQ_CANDIDATE_MODELS)

    def resolve_model(self, requested_model: Optional[str] = None) -> str:
        available = self.list_available_models()
        if requested_model:
            for m in available:
                if m == requested_model:
                    return m
            print(f"[release-notes] Requested Groq model '{requested_model}' not found in active list.")

        for candidate in GROQ_CANDIDATE_MODELS:
            for m in available:
                if candidate in m or m == candidate:
                    return m

        return available[0] if available else GROQ_CANDIDATE_MODELS[0]

    def generate_release_notes(self, prompt: str, system_prompt: str, model: str) -> str:
        print(f"[release-notes] Querying Groq with official SDK ({model})...")
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
            raise RuntimeError(f"Groq ({model}) returned empty text response.")

        print(f"[release-notes] Successfully generated release notes with Groq ({model}).")
        return content.strip()
