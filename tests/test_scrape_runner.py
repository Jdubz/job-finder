"""Tests for ScrapeRunner."""

from unittest.mock import MagicMock, patch

import pytest

from job_finder.scrape_runner import ScrapeRunner


@pytest.fixture
def mock_components():
    """Create mock components for ScrapeRunner."""
    return {
        "ai_matcher": MagicMock(),
        "job_storage": MagicMock(),
        "companies_manager": MagicMock(),
        "sources_manager": MagicMock(),
        "company_info_fetcher": MagicMock(),
        "profile": MagicMock(),
    }


@pytest.fixture
def scrape_runner(mock_components):
    """Create ScrapeRunner with mocked dependencies."""
    return ScrapeRunner(**mock_components)


@pytest.fixture
def mock_sources():
    """Create mock source documents."""
    return [
        {
            "id": "source-1",
            "name": "Netflix Greenhouse",
            "sourceType": "greenhouse",
            "config": {"board_token": "netflix"},
            "enabled": True,
        },
        {
            "id": "source-2",
            "name": "Stripe Greenhouse",
            "sourceType": "greenhouse",
            "config": {"board_token": "stripe"},
            "enabled": True,
        },
        {
            "id": "source-3",
            "name": "Google RSS",
            "sourceType": "rss",
            "config": {"url": "https://google.com/jobs/rss"},
            "enabled": True,
        },
    ]


class TestScrapeRunnerInit:
    """Test ScrapeRunner initialization."""

    def test_initializes_with_all_components(self, mock_components):
        """Test that ScrapeRunner stores all components."""
        runner = ScrapeRunner(**mock_components)

        assert runner.ai_matcher == mock_components["ai_matcher"]
        assert runner.job_storage == mock_components["job_storage"]
        assert runner.companies_manager == mock_components["companies_manager"]
        assert runner.sources_manager == mock_components["sources_manager"]
        assert runner.company_info_fetcher == mock_components["company_info_fetcher"]
        assert runner.profile == mock_components["profile"]


class TestRunScrapeDefaults:
    """Test run_scrape with default parameters."""

    def test_runs_with_defaults(self, scrape_runner, mock_sources):
        """Test scrape runs with default target_matches and max_sources."""
        scrape_runner.sources_manager.get_active_sources.return_value = mock_sources

        # Mock scraping to return no jobs
        with patch.object(
            scrape_runner,
            "_scrape_source",
            return_value={
                "jobs_found": 0,
                "remote_jobs": 0,
                "jobs_filtered_by_role": 0,
                "duplicates_skipped": 0,
                "jobs_analyzed": 0,
                "jobs_matched": 0,
                "jobs_saved": 0,
            },
        ):
            stats = scrape_runner.run_scrape()

        assert stats["sources_scraped"] == 3
        assert "errors" in stats


class TestRunScrapeWithNoneValues:
    """Test run_scrape with None for unlimited scraping."""

    def test_no_target_limit(self, scrape_runner, mock_sources):
        """Test that target_matches=None scrapes all sources."""
        scrape_runner.sources_manager.get_active_sources.return_value = mock_sources

        # Mock scraping to return many analyzed jobs (would normally stop at 5)
        with patch.object(
            scrape_runner,
            "_scrape_source",
            return_value={
                "jobs_found": 10,
                "remote_jobs": 10,
                "jobs_filtered_by_role": 0,
                "duplicates_skipped": 0,
                "jobs_analyzed": 10,  # More than default limit of 5
                "jobs_matched": 2,
                "jobs_saved": 2,
            },
        ):
            stats = scrape_runner.run_scrape(target_matches=None, max_sources=10)

        # Should scrape all 3 sources despite having 30 analyzed jobs
        assert stats["sources_scraped"] == 3
        assert stats["jobs_analyzed"] == 30

    def test_no_source_limit(self, scrape_runner):
        """Test that max_sources=None gets all sources."""
        # Create many sources
        many_sources = [
            {
                "id": f"source-{i}",
                "name": f"Company {i}",
                "sourceType": "greenhouse",
                "config": {"board_token": f"token-{i}"},
                "enabled": True,
            }
            for i in range(50)
        ]
        scrape_runner.sources_manager.get_active_sources.return_value = many_sources

        with patch.object(
            scrape_runner,
            "_scrape_source",
            return_value={
                "jobs_found": 0,
                "remote_jobs": 0,
                "jobs_filtered_by_role": 0,
                "duplicates_skipped": 0,
                "jobs_analyzed": 1,  # Hit target quickly
                "jobs_matched": 0,
                "jobs_saved": 0,
            },
        ):
            stats = scrape_runner.run_scrape(target_matches=5, max_sources=None)

        # Should get all 50 sources, but stop early at target_matches
        # So sources_scraped will be 5 (5 analyzed jobs / 1 per source)
        assert stats["sources_scraped"] == 5
        assert stats["jobs_analyzed"] == 5

    def test_both_limits_none(self, scrape_runner, mock_sources):
        """Test with both target_matches=None and max_sources=None."""
        scrape_runner.sources_manager.get_active_sources.return_value = mock_sources

        with patch.object(
            scrape_runner,
            "_scrape_source",
            return_value={
                "jobs_found": 10,
                "remote_jobs": 10,
                "jobs_filtered_by_role": 0,
                "duplicates_skipped": 0,
                "jobs_analyzed": 10,
                "jobs_matched": 2,
                "jobs_saved": 2,
            },
        ):
            stats = scrape_runner.run_scrape(target_matches=None, max_sources=None)

        # Should scrape all sources with no early exit
        assert stats["sources_scraped"] == 3
        assert stats["jobs_analyzed"] == 30


class TestRunScrapeWithSpecificSources:
    """Test run_scrape with specific source IDs."""

    def test_scrapes_specific_sources_only(self, scrape_runner, mock_sources):
        """Test that source_ids limits scraping to specific sources."""
        scrape_runner.sources_manager.get_source_by_id.side_effect = lambda id: next(
            (s for s in mock_sources if s["id"] == id), None
        )

        with patch.object(
            scrape_runner,
            "_scrape_source",
            return_value={
                "jobs_found": 5,
                "remote_jobs": 5,
                "jobs_filtered_by_role": 0,
                "duplicates_skipped": 0,
                "jobs_analyzed": 2,
                "jobs_matched": 1,
                "jobs_saved": 1,
            },
        ):
            stats = scrape_runner.run_scrape(
                source_ids=["source-1", "source-2"], target_matches=None
            )

        # Should only scrape 2 sources
        assert stats["sources_scraped"] == 2

    def test_handles_nonexistent_source_id(self, scrape_runner):
        """Test that nonexistent source IDs are skipped with warning."""
        scrape_runner.sources_manager.get_source_by_id.return_value = None

        with patch.object(scrape_runner, "_scrape_source") as mock_scrape:
            stats = scrape_runner.run_scrape(source_ids=["nonexistent"])

        # Should not attempt to scrape
        mock_scrape.assert_not_called()
        assert stats["sources_scraped"] == 0


class TestGetNextSourcesByRotation:
    """Test source rotation logic."""

    def test_sorts_by_last_scraped_oldest_first(self, scrape_runner):
        """Test that sources are sorted by lastScrapedAt."""
        from datetime import datetime, timezone

        sources = [
            {"id": "1", "lastScrapedAt": datetime(2025, 1, 3, tzinfo=timezone.utc)},
            {"id": "2", "lastScrapedAt": datetime(2025, 1, 1, tzinfo=timezone.utc)},
            {"id": "3", "lastScrapedAt": datetime(2025, 1, 2, tzinfo=timezone.utc)},
        ]
        scrape_runner.sources_manager.get_active_sources.return_value = sources

        result = scrape_runner._get_next_sources_by_rotation(limit=10)

        # Should be sorted oldest to newest
        assert result[0]["id"] == "2"  # 2025-01-01
        assert result[1]["id"] == "3"  # 2025-01-02
        assert result[2]["id"] == "1"  # 2025-01-03

    def test_never_scraped_sources_first(self, scrape_runner):
        """Test that sources with no lastScrapedAt come first."""
        from datetime import datetime, timezone

        sources = [
            {"id": "1", "lastScrapedAt": datetime(2025, 1, 1, tzinfo=timezone.utc)},
            {"id": "2", "lastScrapedAt": None},
            {"id": "3", "lastScrapedAt": None},
        ]
        scrape_runner.sources_manager.get_active_sources.return_value = sources

        result = scrape_runner._get_next_sources_by_rotation(limit=10)

        # Never-scraped sources should come first
        assert result[0]["lastScrapedAt"] is None
        assert result[1]["lastScrapedAt"] is None
        assert result[2]["id"] == "1"

    def test_respects_limit(self, scrape_runner, mock_sources):
        """Test that limit parameter restricts number of sources."""
        scrape_runner.sources_manager.get_active_sources.return_value = mock_sources

        result = scrape_runner._get_next_sources_by_rotation(limit=2)

        assert len(result) == 2

    def test_none_limit_returns_all_sources(self, scrape_runner, mock_sources):
        """Test that limit=None returns all sources."""
        scrape_runner.sources_manager.get_active_sources.return_value = mock_sources

        result = scrape_runner._get_next_sources_by_rotation(limit=None)

        assert len(result) == 3


class TestEarlyExitLogic:
    """Test early exit when target_matches is reached."""

    def test_stops_at_target_matches(self, scrape_runner, mock_sources):
        """Test that scraping stops when target_matches is reached."""
        scrape_runner.sources_manager.get_active_sources.return_value = mock_sources

        # First source returns 3 analyzed, second returns 2, third shouldn't be called
        side_effects = [
            {
                "jobs_found": 10,
                "remote_jobs": 5,
                "jobs_filtered_by_role": 0,
                "duplicates_skipped": 0,
                "jobs_analyzed": 3,
                "jobs_matched": 1,
                "jobs_saved": 1,
            },
            {
                "jobs_found": 10,
                "remote_jobs": 5,
                "jobs_filtered_by_role": 0,
                "duplicates_skipped": 0,
                "jobs_analyzed": 2,
                "jobs_matched": 1,
                "jobs_saved": 1,
            },
        ]

        with patch.object(scrape_runner, "_scrape_source", side_effect=side_effects):
            stats = scrape_runner.run_scrape(target_matches=5, max_sources=10)

        # Should stop after 2 sources (3 + 2 = 5 analyzed jobs)
        assert stats["sources_scraped"] == 2
        assert stats["jobs_analyzed"] == 5

    def test_continues_if_under_target(self, scrape_runner, mock_sources):
        """Test that scraping continues if under target_matches."""
        scrape_runner.sources_manager.get_active_sources.return_value = mock_sources

        with patch.object(
            scrape_runner,
            "_scrape_source",
            return_value={
                "jobs_found": 10,
                "remote_jobs": 5,
                "jobs_filtered_by_role": 0,
                "duplicates_skipped": 0,
                "jobs_analyzed": 1,
                "jobs_matched": 0,
                "jobs_saved": 0,
            },
        ):
            stats = scrape_runner.run_scrape(target_matches=5, max_sources=10)

        # Should scrape all 3 sources (only 3 analyzed jobs total)
        assert stats["sources_scraped"] == 3
        assert stats["jobs_analyzed"] == 3


class TestErrorHandling:
    """Test error handling during scraping."""

    def test_continues_after_source_error(self, scrape_runner, mock_sources):
        """Test that errors on one source don't stop other sources."""
        # Use only 2 sources for this test
        scrape_runner.sources_manager.get_active_sources.return_value = mock_sources[:2]

        # First source errors, second succeeds
        side_effects = [
            Exception("Scraping failed"),
            {
                "jobs_found": 10,
                "remote_jobs": 5,
                "jobs_filtered_by_role": 0,
                "duplicates_skipped": 0,
                "jobs_analyzed": 2,
                "jobs_matched": 1,
                "jobs_saved": 1,
            },
        ]

        with patch.object(scrape_runner, "_scrape_source", side_effect=side_effects):
            stats = scrape_runner.run_scrape(target_matches=10, max_sources=10)

        # Should process both sources despite first error
        assert stats["sources_scraped"] == 1  # Only successful one counts
        assert len(stats["errors"]) == 1
        assert "Scraping failed" in stats["errors"][0]

    def test_updates_source_status_on_error(self, scrape_runner, mock_sources):
        """Test that source status is updated when scraping fails."""
        scrape_runner.sources_manager.get_active_sources.return_value = [mock_sources[0]]

        with patch.object(scrape_runner, "_scrape_source", side_effect=Exception("Network error")):
            scrape_runner.run_scrape()

        # Should call update_scrape_status with error
        scrape_runner.sources_manager.update_scrape_status.assert_called_with(
            "source-1", status="error", error="Network error"
        )


class TestScrapeSourceMethod:
    """Test _scrape_source method."""

    def test_scrapes_greenhouse_source(self, scrape_runner):
        """Test scraping a Greenhouse source."""
        source = {
            "id": "test",
            "name": "Test Company",
            "sourceType": "greenhouse",
            "config": {"board_token": "test-token"},
        }

        # Mock the scraper
        with patch("job_finder.scrape_runner.GreenhouseScraper") as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.scrape.return_value = [
                {
                    "title": "Engineer",
                    "company": "Test",
                    "company_website": "https://test.com",
                    "url": "https://job.com/1",
                }
            ]
            mock_scraper_class.return_value = mock_scraper

            # Mock profile preferences
            scrape_runner.profile.preferences = MagicMock()

            # Mock filter to pass
            with patch("job_finder.scrape_runner.filter_job") as mock_filter:
                from job_finder.utils.job_type_filter import FilterDecision

                mock_filter.return_value = (FilterDecision.ACCEPT, "Passed")

                # Mock job doesn't exist
                scrape_runner.job_storage.job_exists.return_value = False

                # Mock AI matcher
                scrape_runner.ai_matcher.analyze_job.return_value = MagicMock(match_score=85)

                # Mock company manager
                scrape_runner.companies_manager.get_or_create_company.return_value = {
                    "id": "company-1"
                }

                # Mock job storage
                scrape_runner.job_storage.save_job_match.return_value = "job-1"

                stats = scrape_runner._scrape_source(source)

        assert stats["jobs_found"] == 1
        assert stats["jobs_analyzed"] == 1
        assert stats["jobs_matched"] == 1
        assert stats["jobs_saved"] == 1

    def test_handles_unsupported_source_type(self, scrape_runner):
        """Test that unsupported source types are handled gracefully."""
        source = {
            "id": "test",
            "name": "Test",
            "sourceType": "unsupported",
            "config": {},
        }

        stats = scrape_runner._scrape_source(source)

        # Should return empty stats
        assert stats["jobs_found"] == 0
        assert stats["jobs_analyzed"] == 0
