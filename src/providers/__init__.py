from typing import Dict, Type, List, Optional
from .base import BaseAIProvider
from .gemini import GeminiProvider
from .groq import GroqProvider
from .openai_compat import OpenAIProvider

_REGISTRY: Dict[str, Type[BaseAIProvider]] = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "openai": OpenAIProvider,
}


def register_provider(name: str, provider_cls: Type[BaseAIProvider]):
    """Register a new AI provider class dynamically."""
    _REGISTRY[name.lower()] = provider_cls


def get_provider(name: str) -> Optional[BaseAIProvider]:
    """Retrieve an instantiated provider by name."""
    cls = _REGISTRY.get(name.lower())
    if cls:
        return cls()
    return None


def get_available_providers() -> List[str]:
    """List all registered provider names."""
    return list(_REGISTRY.keys())
