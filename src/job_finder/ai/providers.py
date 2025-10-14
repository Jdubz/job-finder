"""AI provider abstractions for different LLM services."""
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from anthropic import Anthropic
from openai import OpenAI


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate a response from the AI model.

        Args:
            prompt: The prompt to send to the model.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0.0 to 1.0).

        Returns:
            The generated text response.
        """
        pass


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Claude provider.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var).
            model: Model identifier.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key must be provided or set in ANTHROPIC_API_KEY environment variable"
            )

        self.model = model
        self.client = Anthropic(api_key=self.api_key)

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Generate a response using Claude."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Claude API error: {str(e)}") from e


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var).
            model: Model identifier.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key must be provided or set in OPENAI_API_KEY environment variable"
            )

        self.model = model
        self.client = OpenAI(api_key=self.api_key)

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Generate a response using GPT."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}") from e


def create_provider(provider_type: str, api_key: Optional[str] = None, model: Optional[str] = None) -> AIProvider:
    """
    Factory function to create AI provider instances.

    Args:
        provider_type: Type of provider ('claude', 'openai').
        api_key: Optional API key (otherwise uses environment variable).
        model: Optional model name (uses default if not specified).

    Returns:
        AIProvider instance.

    Raises:
        ValueError: If provider_type is not supported.
    """
    provider_type = provider_type.lower()

    if provider_type == "claude":
        kwargs = {"api_key": api_key} if api_key else {}
        if model:
            kwargs["model"] = model
        return ClaudeProvider(**kwargs)

    elif provider_type == "openai":
        kwargs = {"api_key": api_key} if api_key else {}
        if model:
            kwargs["model"] = model
        return OpenAIProvider(**kwargs)

    else:
        raise ValueError(
            f"Unsupported AI provider: {provider_type}. Supported providers: claude, openai"
        )
