"""AI provider abstractions for different LLM services."""

import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from anthropic import Anthropic
from openai import OpenAI

from job_finder.exceptions import AIProviderError


class AITask(str, Enum):
    """
    Types of AI tasks with different model requirements.

    Different tasks have different cost/quality tradeoffs:
    - SCRAPE: Extract structured data from HTML (cheap, fast - Haiku)
    - FILTER: Not used (filtering is rule-based)
    - ANALYZE: Match job to profile (cheap, fast - Haiku, 95% cost savings vs Sonnet)
    - SELECTOR_DISCOVERY: Discover CSS selectors (cheap, one-time - Haiku)
    """

    SCRAPE = "scrape"
    ANALYZE = "analyze"
    SELECTOR_DISCOVERY = "selector_discovery"


class ModelTier(str, Enum):
    """
    Model performance tiers.

    - FAST: Cheap, fast models for simple extraction (Haiku, GPT-4o-mini)
    - SMART: Expensive, capable models for complex analysis (Sonnet, GPT-4)
    """

    FAST = "fast"
    SMART = "smart"


# Model mappings by provider and tier
MODEL_SELECTION = {
    "claude": {
        ModelTier.FAST: "claude-3-5-haiku-20241022",  # $0.001/1K tokens
        ModelTier.SMART: "claude-3-5-sonnet-20241022",  # $0.015-0.075/1K tokens
    },
    "openai": {
        ModelTier.FAST: "gpt-4o-mini",  # $0.00015-0.0006/1K tokens
        ModelTier.SMART: "gpt-4o",  # $0.0025-0.01/1K tokens
    },
}

# Task to tier mapping
TASK_MODEL_TIERS = {
    AITask.SCRAPE: ModelTier.FAST,
    AITask.ANALYZE: ModelTier.FAST,  # Changed to FAST - Haiku handles job analysis well at 95% cost savings
    AITask.SELECTOR_DISCOVERY: ModelTier.FAST,
}


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

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-20250514"):
        """
        Initialize Claude provider.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var).
            model: Model identifier (default: claude-opus-4-20250514, the most capable model).
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise AIProviderError(
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
            raise AIProviderError(f"Claude API error: {str(e)}") from e


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
            raise AIProviderError(
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
            raise AIProviderError(f"OpenAI API error: {str(e)}") from e


def get_model_for_task(provider_type: str, task: AITask) -> str:
    """
    Get the appropriate model for a specific task.

    Uses cost-optimized model selection:
    - Fast/cheap models (Haiku, GPT-4o-mini) for ALL tasks (95% cost savings)
    - Haiku handles job analysis well despite being cheaper than Sonnet

    Args:
        provider_type: Type of provider ('claude', 'openai')
        task: The AI task to perform

    Returns:
        Model identifier string

    Raises:
        ValueError: If provider_type is not supported

    Example:
        >>> get_model_for_task("claude", AITask.SCRAPE)
        'claude-3-5-haiku-20241022'
        >>> get_model_for_task("claude", AITask.ANALYZE)
        'claude-3-5-haiku-20241022'
    """
    provider_type = provider_type.lower()

    if provider_type not in MODEL_SELECTION:
        raise AIProviderError(
            f"Unsupported AI provider: {provider_type}. Supported providers: {list(MODEL_SELECTION.keys())}"
        )

    tier = TASK_MODEL_TIERS[task]
    return MODEL_SELECTION[provider_type][tier]


def create_provider(
    provider_type: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    task: Optional[AITask] = None,
) -> AIProvider:
    """
    Factory function to create AI provider instances.

    Args:
        provider_type: Type of provider ('claude', 'openai').
        api_key: Optional API key (otherwise uses environment variable).
        model: Optional explicit model name (overrides task-based selection).
        task: Optional task type for automatic model selection (ignored if model is provided).

    Returns:
        AIProvider instance.

    Raises:
        ValueError: If provider_type is not supported.

    Example:
        # Automatic model selection for scraping (uses Haiku)
        provider = create_provider("claude", task=AITask.SCRAPE)

        # Automatic model selection for analysis (uses Sonnet)
        provider = create_provider("claude", task=AITask.ANALYZE)

        # Explicit model override
        provider = create_provider("claude", model="claude-opus-4-20250514")
    """
    provider_type = provider_type.lower()

    # Determine model
    if model:
        # Explicit model provided, use it
        selected_model = model
    elif task:
        # Task provided, select appropriate model
        selected_model = get_model_for_task(provider_type, task)
    else:
        # No model or task provided, use None to trigger provider default
        selected_model = None

    if provider_type == "claude":
        kwargs = {"api_key": api_key} if api_key else {}
        if selected_model:
            kwargs["model"] = selected_model
        return ClaudeProvider(**kwargs)

    elif provider_type == "openai":
        kwargs = {"api_key": api_key} if api_key else {}
        if selected_model:
            kwargs["model"] = selected_model
        return OpenAIProvider(**kwargs)

    else:
        raise AIProviderError(
            f"Unsupported AI provider: {provider_type}. Supported providers: claude, openai"
        )
