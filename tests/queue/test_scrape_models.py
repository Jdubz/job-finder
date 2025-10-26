"""Tests for SCRAPE queue models and configuration."""

from job_finder.job_queue.models import JobQueueItem, QueueItemType, ScrapeConfig


class TestScrapeConfig:
    """Test ScrapeConfig model."""

    def test_creates_with_defaults(self):
        """Test that ScrapeConfig has sensible defaults."""
        config = ScrapeConfig()

        assert config.target_matches == 5
        assert config.max_sources == 20
        assert config.source_ids is None
        assert config.min_match_score is None

    def test_creates_with_custom_values(self):
        """Test creating ScrapeConfig with custom values."""
        config = ScrapeConfig(
            target_matches=10,
            max_sources=50,
            source_ids=["source-1", "source-2"],
            min_match_score=75,
        )

        assert config.target_matches == 10
        assert config.max_sources == 50
        assert config.source_ids == ["source-1", "source-2"]
        assert config.min_match_score == 75

    def test_allows_none_for_target_matches(self):
        """Test that target_matches can be None (unlimited)."""
        config = ScrapeConfig(target_matches=None)

        assert config.target_matches is None

    def test_allows_none_for_max_sources(self):
        """Test that max_sources can be None (unlimited)."""
        config = ScrapeConfig(max_sources=None)

        assert config.max_sources is None

    def test_allows_empty_source_ids_list(self):
        """Test that source_ids can be an empty list."""
        config = ScrapeConfig(source_ids=[])

        assert config.source_ids == []

    def test_serializes_to_dict(self):
        """Test that ScrapeConfig serializes correctly."""
        config = ScrapeConfig(target_matches=10, max_sources=30, source_ids=["s1", "s2"])

        data = config.model_dump()

        assert data["target_matches"] == 10
        assert data["max_sources"] == 30
        assert data["source_ids"] == ["s1", "s2"]
        assert data["min_match_score"] is None


class TestJobQueueItemWithScrape:
    """Test JobQueueItem with SCRAPE type."""

    def test_creates_scrape_queue_item(self):
        """Test creating a SCRAPE queue item."""
        scrape_config = ScrapeConfig(target_matches=10)

        item = JobQueueItem(
            type=QueueItemType.SCRAPE,
            source="user_submission",
            scrape_config=scrape_config,
        )

        assert item.type == QueueItemType.SCRAPE
        assert item.source == "user_submission"
        assert item.scrape_config.target_matches == 10
        assert item.url == ""  # Empty for SCRAPE type
        assert item.company_name == ""  # Empty for SCRAPE type

    def test_scrape_item_without_scrape_config(self):
        """Test that SCRAPE item can be created without scrape_config."""
        item = JobQueueItem(type=QueueItemType.SCRAPE, source="automated_scan")

        assert item.type == QueueItemType.SCRAPE
        assert item.scrape_config is None

    def test_scrape_item_serializes_correctly(self):
        """Test that SCRAPE item serializes to Firestore format."""
        scrape_config = ScrapeConfig(target_matches=5, max_sources=20)

        item = JobQueueItem(
            type=QueueItemType.SCRAPE,
            source="user_submission",
            scrape_config=scrape_config,
        )

        data = item.to_firestore()

        assert data["type"] == "scrape"
        assert data["source"] == "user_submission"
        assert "scrape_config" in data
        assert data["scrape_config"]["target_matches"] == 5

    def test_scrape_item_from_firestore(self):
        """Test creating SCRAPE item from Firestore data."""
        data = {
            "type": "scrape",
            "source": "automated_scan",
            "status": "pending",
            "scrape_config": {
                "target_matches": 10,
                "max_sources": 30,
                "source_ids": ["s1"],
                "min_match_score": 80,
            },
        }

        item = JobQueueItem.from_firestore("test-id", data)

        assert item.id == "test-id"
        assert item.type == QueueItemType.SCRAPE
        assert item.scrape_config.target_matches == 10
        assert item.scrape_config.max_sources == 30
        assert item.scrape_config.source_ids == ["s1"]
        assert item.scrape_config.min_match_score == 80


class TestScrapeConfigEdgeCases:
    """Test edge cases for ScrapeConfig."""

    def test_zero_target_matches(self):
        """Test that target_matches can be 0 (though unusual)."""
        config = ScrapeConfig(target_matches=0)

        assert config.target_matches == 0

    def test_zero_max_sources(self):
        """Test that max_sources can be 0 (though unusual)."""
        config = ScrapeConfig(max_sources=0)

        assert config.max_sources == 0

    def test_large_values(self):
        """Test that large values are accepted."""
        config = ScrapeConfig(target_matches=999, max_sources=999)

        assert config.target_matches == 999
        assert config.max_sources == 999

    def test_min_match_score_range(self):
        """Test various min_match_score values."""
        # Valid values
        config_low = ScrapeConfig(min_match_score=0)
        config_high = ScrapeConfig(min_match_score=100)

        assert config_low.min_match_score == 0
        assert config_high.min_match_score == 100

    def test_single_source_id(self):
        """Test with a single source ID."""
        config = ScrapeConfig(source_ids=["single-source"])

        assert len(config.source_ids) == 1
        assert config.source_ids[0] == "single-source"

    def test_many_source_ids(self):
        """Test with many source IDs."""
        many_ids = [f"source-{i}" for i in range(100)]
        config = ScrapeConfig(source_ids=many_ids)

        assert len(config.source_ids) == 100


class TestScrapeConfigBehaviorDocumentation:
    """Test that config behavior matches documentation."""

    def test_none_target_means_unlimited(self):
        """Verify that None target_matches means no early exit."""
        config = ScrapeConfig(target_matches=None, max_sources=10)

        # This is a documentation test - the actual behavior is in ScrapeRunner
        # but we verify the config allows this combination
        assert config.target_matches is None
        assert config.max_sources == 10

    def test_none_max_sources_means_unlimited(self):
        """Verify that None max_sources means all sources."""
        config = ScrapeConfig(target_matches=5, max_sources=None)

        assert config.target_matches == 5
        assert config.max_sources is None

    def test_both_none_means_complete_scrape(self):
        """Verify that both None means scrape everything."""
        config = ScrapeConfig(target_matches=None, max_sources=None)

        assert config.target_matches is None
        assert config.max_sources is None

    def test_source_ids_overrides_rotation(self):
        """Verify that providing source_ids means specific sources only."""
        config = ScrapeConfig(source_ids=["s1", "s2"], max_sources=100)

        # max_sources should be ignored when source_ids is provided
        # (actual behavior in ScrapeRunner, but config allows this)
        assert config.source_ids == ["s1", "s2"]
        assert config.max_sources == 100


class TestQueueItemTypeEnum:
    """Test QueueItemType enum with SCRAPE."""

    def test_scrape_type_exists(self):
        """Test that SCRAPE is a valid queue item type."""
        assert QueueItemType.SCRAPE == "scrape"

    def test_all_types_are_strings(self):
        """Test that all queue item types are strings."""
        assert isinstance(QueueItemType.JOB, str)
        assert isinstance(QueueItemType.COMPANY, str)
        assert isinstance(QueueItemType.SCRAPE, str)

    def test_scrape_type_in_enum(self):
        """Test that SCRAPE is in the enum values."""
        values = [item.value for item in QueueItemType]
        assert "scrape" in values
