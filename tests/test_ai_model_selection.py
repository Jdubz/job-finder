"""Tests for AI model selection and cost optimization."""

import pytest

from job_finder.ai.providers import AITask, ModelTier, create_provider, get_model_for_task


class TestModelSelection:
    """Test automatic model selection based on task."""

    def test_scrape_uses_fast_claude(self):
        """SCRAPE task should use cheap/fast Claude model."""
        model = get_model_for_task("claude", AITask.SCRAPE)
        assert model == "claude-3-5-haiku-20241022"

    def test_analyze_uses_smart_claude(self):
        """ANALYZE task should use expensive/smart Claude model."""
        model = get_model_for_task("claude", AITask.ANALYZE)
        assert model == "claude-3-5-sonnet-20241022"

    def test_discovery_uses_fast_claude(self):
        """SELECTOR_DISCOVERY task should use cheap/fast model."""
        model = get_model_for_task("claude", AITask.SELECTOR_DISCOVERY)
        assert model == "claude-3-5-haiku-20241022"

    def test_scrape_uses_fast_openai(self):
        """SCRAPE task should use cheap/fast OpenAI model."""
        model = get_model_for_task("openai", AITask.SCRAPE)
        assert model == "gpt-4o-mini"

    def test_analyze_uses_smart_openai(self):
        """ANALYZE task should use expensive/smart OpenAI model."""
        model = get_model_for_task("openai", AITask.ANALYZE)
        assert model == "gpt-4o"

    def test_raises_for_unsupported_provider(self):
        """Should raise ValueError for unsupported provider."""
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            get_model_for_task("invalid", AITask.SCRAPE)


class TestProviderCreation:
    """Test provider creation with task-based selection."""

    def test_creates_with_scrape_task(self):
        """Should create provider with SCRAPE task model."""
        provider = create_provider("claude", task=AITask.SCRAPE)
        assert provider.model == "claude-3-5-haiku-20241022"

    def test_creates_with_analyze_task(self):
        """Should create provider with ANALYZE task model."""
        provider = create_provider("claude", task=AITask.ANALYZE)
        assert provider.model == "claude-3-5-sonnet-20241022"

    def test_explicit_model_overrides_task(self):
        """Explicit model should override task-based selection."""
        provider = create_provider("claude", model="claude-opus-4-20250514", task=AITask.SCRAPE)
        assert provider.model == "claude-opus-4-20250514"

    def test_no_task_uses_default(self):
        """Should use provider default when no task specified."""
        provider = create_provider("claude")
        assert provider.model == "claude-opus-4-20250514"


class TestCostOptimization:
    """Test cost optimization strategy."""

    def test_scrape_cheaper_than_analyze(self):
        """SCRAPE should use cheaper model than ANALYZE."""
        scrape = get_model_for_task("claude", AITask.SCRAPE)
        analyze = get_model_for_task("claude", AITask.ANALYZE)

        # Haiku is cheaper than Sonnet
        assert "haiku" in scrape.lower()
        assert "sonnet" in analyze.lower()

    def test_task_to_tier_mapping(self):
        """Tasks should map to correct tiers."""
        from job_finder.ai.providers import TASK_MODEL_TIERS

        assert TASK_MODEL_TIERS[AITask.SCRAPE] == ModelTier.FAST
        assert TASK_MODEL_TIERS[AITask.ANALYZE] == ModelTier.SMART
        assert TASK_MODEL_TIERS[AITask.SELECTOR_DISCOVERY] == ModelTier.FAST
