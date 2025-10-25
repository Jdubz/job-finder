"""Tests for AI model selection and cost optimization."""

import pytest
from unittest.mock import patch, MagicMock

from job_finder.ai.providers import AITask, ModelTier, create_provider, get_model_for_task
from job_finder.exceptions import AIProviderError


class TestModelSelection:
    """Test automatic model selection based on task."""

    def test_scrape_uses_fast_claude(self):
        """SCRAPE task should use cheap/fast Claude model."""
        model = get_model_for_task("claude", AITask.SCRAPE)
        assert model == "claude-3-5-haiku-20241022"

    def test_analyze_uses_fast_claude(self):
        """ANALYZE task should use cheap/fast Claude model (cost optimization)."""
        model = get_model_for_task("claude", AITask.ANALYZE)
        assert model == "claude-3-5-haiku-20241022"

    def test_discovery_uses_fast_claude(self):
        """SELECTOR_DISCOVERY task should use cheap/fast model."""
        model = get_model_for_task("claude", AITask.SELECTOR_DISCOVERY)
        assert model == "claude-3-5-haiku-20241022"

    def test_scrape_uses_fast_openai(self):
        """SCRAPE task should use cheap/fast OpenAI model."""
        model = get_model_for_task("openai", AITask.SCRAPE)
        assert model == "gpt-4o-mini"

    def test_analyze_uses_fast_openai(self):
        """ANALYZE task should use cheap/fast OpenAI model (cost optimization)."""
        model = get_model_for_task("openai", AITask.ANALYZE)
        assert model == "gpt-4o-mini"

    def test_raises_for_unsupported_provider(self):
        """Should raise AIProviderError for unsupported provider."""
        with pytest.raises(AIProviderError, match="Unsupported AI provider"):
            get_model_for_task("invalid", AITask.SCRAPE)


class TestProviderCreation:
    """Test provider creation with task-based selection."""

    @patch("job_finder.ai.providers.ClaudeProvider")
    def test_creates_with_scrape_task(self, mock_claude):
        """Should create provider with SCRAPE task model."""
        mock_instance = MagicMock()
        mock_instance.model = "claude-3-5-haiku-20241022"
        mock_claude.return_value = mock_instance

        provider = create_provider("claude", task=AITask.SCRAPE)

        # Verify ClaudeProvider was called with correct model
        mock_claude.assert_called_once()
        call_kwargs = mock_claude.call_args[1]
        assert call_kwargs["model"] == "claude-3-5-haiku-20241022"

    @patch("job_finder.ai.providers.ClaudeProvider")
    def test_creates_with_analyze_task(self, mock_claude):
        """Should create provider with ANALYZE task model (cost optimized to Haiku)."""
        mock_instance = MagicMock()
        mock_instance.model = "claude-3-5-haiku-20241022"
        mock_claude.return_value = mock_instance

        provider = create_provider("claude", task=AITask.ANALYZE)

        # Verify ClaudeProvider was called with correct model
        mock_claude.assert_called_once()
        call_kwargs = mock_claude.call_args[1]
        assert call_kwargs["model"] == "claude-3-5-haiku-20241022"

    @patch("job_finder.ai.providers.ClaudeProvider")
    def test_explicit_model_overrides_task(self, mock_claude):
        """Explicit model should override task-based selection."""
        mock_instance = MagicMock()
        mock_instance.model = "claude-opus-4-20250514"
        mock_claude.return_value = mock_instance

        provider = create_provider("claude", model="claude-opus-4-20250514", task=AITask.SCRAPE)

        # Verify ClaudeProvider was called with explicit model (not task model)
        mock_claude.assert_called_once()
        call_kwargs = mock_claude.call_args[1]
        assert call_kwargs["model"] == "claude-opus-4-20250514"

    @patch("job_finder.ai.providers.ClaudeProvider")
    def test_no_task_uses_default(self, mock_claude):
        """Should use provider default when no task specified."""
        mock_instance = MagicMock()
        mock_instance.model = "claude-opus-4-20250514"
        mock_claude.return_value = mock_instance

        provider = create_provider("claude")

        # Verify ClaudeProvider was called without explicit model (uses provider default)
        mock_claude.assert_called_once()
        call_kwargs = mock_claude.call_args[1]
        # When no task is specified, no model kwarg is passed (provider uses its default)
        assert "model" not in call_kwargs


class TestCostOptimization:
    """Test cost optimization strategy."""

    def test_all_tasks_use_fast_models(self):
        """All tasks should use cheap/fast models for maximum cost savings."""
        scrape = get_model_for_task("claude", AITask.SCRAPE)
        analyze = get_model_for_task("claude", AITask.ANALYZE)
        discovery = get_model_for_task("claude", AITask.SELECTOR_DISCOVERY)

        # All use Haiku for 95% cost savings
        assert "haiku" in scrape.lower()
        assert "haiku" in analyze.lower()
        assert "haiku" in discovery.lower()

    def test_task_to_tier_mapping(self):
        """All tasks should map to FAST tier for cost optimization."""
        from job_finder.ai.providers import TASK_MODEL_TIERS

        assert TASK_MODEL_TIERS[AITask.SCRAPE] == ModelTier.FAST
        assert TASK_MODEL_TIERS[AITask.ANALYZE] == ModelTier.FAST
        assert TASK_MODEL_TIERS[AITask.SELECTOR_DISCOVERY] == ModelTier.FAST
