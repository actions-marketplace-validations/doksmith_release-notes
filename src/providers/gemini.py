import os
import time
from typing import List, Optional
from .base import BaseAIProvider

GEMINI_CANDIDATE_MODELS = (
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
)
GEMINI_MAX_ATTEMPTS_PER_MODEL = 2


def redact_api_key(message: str, api_key: str) -> str:
    return message.replace(api_key, "[REDACTED]") if api_key else message


class GeminiProvider(BaseAIProvider):
    name = "gemini"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        try:
            from google import genai
        except ImportError as e:
            raise RuntimeError(
                "google-genai SDK is not installed. Please install requirements.txt"
            ) from e

        return genai.Client(
            api_key=self.api_key,
            http_options={
                "timeout": 30000,
                "retry_options": {"attempts": 1},
            },
        )

    def list_available_models(self) -> List[str]:
        if not self.is_configured():
            return []

        client = self._get_client()
        try:
            models = []
            for item in client.models.list():
                methods = getattr(item, "supported_generation_methods", []) or []
                if "generateContent" in methods or not methods:
                    name = getattr(item, "name", "")
                    if name.startswith("models/"):
                        name = name[len("models/"):]
                    models.append(name)
            return models
        except Exception as e:
            print(f"[release-notes] Warning: Could not list Gemini models: {redact_api_key(str(e), self.api_key)}")
            return list(GEMINI_CANDIDATE_MODELS)
        finally:
            client.close()

    def resolve_model(self, requested_model: Optional[str] = None) -> str:
        available = self.list_available_models()
        if requested_model:
            clean = requested_model.removeprefix("models/")
            for m in available:
                if m == clean or clean in m:
                    return m
            print(f"[release-notes] Requested model '{requested_model}' not found in active list.")

        # Candidate order: latest -> 3.5 -> 3.6 -> 3.7 -> 3.8
        for candidate in GEMINI_CANDIDATE_MODELS:
            for m in available:
                if candidate in m or m == candidate:
                    return m

        return available[0] if available else GEMINI_CANDIDATE_MODELS[0]

    def generate_release_notes(self, prompt: str, system_prompt: str, model: str) -> str:
        client = self._get_client()
        models_to_try = [model] if model else list(GEMINI_CANDIDATE_MODELS)

        last_error = None
        try:
            for target_model in models_to_try:
                for attempt in range(1, GEMINI_MAX_ATTEMPTS_PER_MODEL + 1):
                    try:
                        print(
                            f"[release-notes] Querying Gemini model {target_model} "
                            f"(attempt {attempt}/{GEMINI_MAX_ATTEMPTS_PER_MODEL})..."
                        )
                        combined_contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

                        response = client.models.generate_content(
                            model=target_model,
                            contents=combined_contents,
                            config={
                                "temperature": 0.2,
                                "max_output_tokens": 2048,
                            },
                        )
                        content = getattr(response, "text", "")
                        if content and content.strip():
                            print(f"[release-notes] Successfully generated release notes with {target_model}.")
                            return content.strip()
                        raise RuntimeError(f"{target_model} returned empty content")

                    except Exception as error:
                        print(
                            f"[release-notes] Gemini {target_model} attempt {attempt} error: "
                            f"{redact_api_key(str(error), self.api_key)}"
                        )
                        last_error = error
                        status_code = getattr(error, "code", None)
                        message = str(error).lower()

                        if status_code == 429 or "resource_exhausted" in message:
                            print("[release-notes] Gemini quota/rate limit reached; skipping Gemini.")
                            raise

                        model_unavailable = status_code == 404 or any(
                            marker in message
                            for marker in (
                                "model not found",
                                "model is not found",
                                "model is no longer available",
                                "model is not supported",
                            )
                        )
                        if model_unavailable:
                            print(f"[release-notes] Skipping unavailable Gemini model {target_model}.")
                            break

                        if status_code in (408, 500, 502, 503, 504) or any(
                            marker in type(error).__name__.lower()
                            for marker in ("timeout", "connection")
                        ):
                            if attempt < GEMINI_MAX_ATTEMPTS_PER_MODEL:
                                print(f"[release-notes] Retrying transient error for {target_model}...")
                                time.sleep(attempt)
                                continue
                            print(f"[release-notes] Skipping {target_model} after transient error.")
                            break

                        if status_code in (401, 403):
                            print("[release-notes] Gemini auth error; skipping provider.")
                            raise

                        break
        finally:
            client.close()

        raise last_error or RuntimeError("Failed to generate release notes from all candidate Gemini models.")
