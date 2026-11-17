from abc import ABC, abstractmethod
from typing import List, Optional


class BaseAIProvider(ABC):
    """Abstract Base Class for all AI model providers."""

    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Verify whether required API keys or credentials are set."""
        pass

    @abstractmethod
    def list_available_models(self) -> List[str]:
        """Fetch list of actively available models from the official provider endpoint."""
        pass

    @abstractmethod
    def resolve_model(self, requested_model: Optional[str] = None) -> str:
        """
        Validate requested model against available live models.
        If requested_model is empty or unavailable, select the best active default.
        """
        pass

    @abstractmethod
    def generate_release_notes(self, prompt: str, system_prompt: str, model: str) -> str:
        """Execute text generation and return release notes in markdown format."""
        pass
