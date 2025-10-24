"""Tests for job search orchestrator."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from job_finder.search_orchestrator import JobSearchOrchestrator
from job_finder.utils.job_type_filter import FilterDecision


@pytest.fixture
def mock_config():
    """Create a mock configuration dictionary."""
    return {
        "profile": {
            "source": "firestore",
            "firestore": {
                "database_name": "test-db",
                "user_id": None,
                "name": "Test User",
                "email": "test@example.com",
            },
        },
        "ai": {
            "enabled": True,
            "provider": "claude",
            "model": "claude-3-haiku-20240307",
            "min_match_score": 80,
            "generate_intake_data": True,
            "portland_office_bonus": 15,
        },
        "storage": {"database_name": "test-storage"},
        "search": {"max_jobs": 10},
        "scraping": {"delay_between_requests": 0},  # No delay in tests
        "filters": {
            "strict_role_filtering": True,
            "min_seniority_level": "senior",
        },
    }


# mock_profile and sample_job fixtures now provided by tests/conftest.py


class TestJobSearchOrchestratorInit:
    """Test orchestrator initialization."""

    def test_init_stores_config(self, mock_config):
        """Test orchestrator stores configuration."""
        orchestrator = JobSearchOrchestrator(mock_config)

        assert orchestrator.config == mock_config
        assert orchestrator.profile is None
        assert orchestrator.ai_matcher is None
        assert orchestrator.job_storage is None
        assert orchestrator.sources_manager is None
        assert orchestrator.companies_manager is None
        assert orchestrator.company_info_fetcher is None


class TestLoadProfile:
    """Test profile loading."""

    @patch("job_finder.search_orchestrator.FirestoreProfileLoader")
    def test_load_profile_from_firestore(self, mock_loader_class, mock_config, mock_profile):
        """Test loading profile from Firestore."""
        mock_loader = Mock()
        mock_loader.load_profile.return_value = mock_profile
        mock_loader_class.return_value = mock_loader

        orchestrator = JobSearchOrchestrator(mock_config)
        profile = orchestrator._load_profile()

        assert profile == mock_profile
        mock_loader_class.assert_called_once_with(database_name="test-db")
        mock_loader.load_profile.assert_called_once_with(
            user_id=None, name="Test User", email="test@example.com"
        )

    @patch.dict("os.environ", {"PROFILE_DATABASE_NAME": "env-override-db"})
    @patch("job_finder.search_orchestrator.FirestoreProfileLoader")
    def test_load_profile_respects_env_var(self, mock_loader_class, mock_config, mock_profile):
        """Test profile loading respects environment variable override."""
        mock_loader = Mock()
        mock_loader.load_profile.return_value = mock_profile
        mock_loader_class.return_value = mock_loader

        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator._load_profile()

        # Should use env var instead of config
        mock_loader_class.assert_called_once_with(database_name="env-override-db")

    def test_load_profile_json_not_implemented(self, mock_config):
        """Test JSON profile loading raises NotImplementedError."""
        mock_config["profile"]["source"] = "json"

        orchestrator = JobSearchOrchestrator(mock_config)

        with pytest.raises(NotImplementedError, match="JSON profile loading not yet implemented"):
            orchestrator._load_profile()


class TestInitializeAI:
    """Test AI matcher initialization."""

    @patch("job_finder.search_orchestrator.create_provider")
    @patch("job_finder.search_orchestrator.AIJobMatcher")
    def test_initialize_ai(
        self, mock_matcher_class, mock_create_provider, mock_config, mock_profile
    ):
        """Test AI matcher initialization with config."""
        mock_provider = Mock()
        mock_create_provider.return_value = mock_provider
        mock_matcher = Mock()
        mock_matcher_class.return_value = mock_matcher

        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.profile = mock_profile
        matcher = orchestrator._initialize_ai()

        assert matcher == mock_matcher
        mock_create_provider.assert_called_once_with(
            provider_type="claude", model="claude-3-haiku-20240307"
        )
        # Check that AIJobMatcher was called with correct arguments
        call_kwargs = mock_matcher_class.call_args.kwargs
        assert call_kwargs["provider"] == mock_provider
        assert call_kwargs["profile"] == mock_profile
        assert call_kwargs["min_match_score"] == 80
        assert call_kwargs["generate_intake"] is True
        assert call_kwargs["portland_office_bonus"] == 15
        assert "config" in call_kwargs  # Config should be passed


class TestInitializeStorage:
    """Test storage initialization."""

    @patch("job_finder.search_orchestrator.CompanyInfoFetcher")
    @patch("job_finder.search_orchestrator.CompaniesManager")
    @patch("job_finder.search_orchestrator.JobSourcesManager")
    @patch("job_finder.search_orchestrator.FirestoreJobStorage")
    def test_initialize_storage(
        self,
        mock_storage_class,
        mock_sources_class,
        mock_companies_class,
        mock_fetcher_class,
        mock_config,
    ):
        """Test storage initialization."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_sources = Mock()
        mock_sources_class.return_value = mock_sources
        mock_companies = Mock()
        mock_companies_class.return_value = mock_companies
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.ai_matcher = Mock()
        orchestrator.ai_matcher.provider = Mock()
        orchestrator._initialize_storage()

        assert orchestrator.job_storage == mock_storage
        assert orchestrator.sources_manager == mock_sources
        assert orchestrator.companies_manager == mock_companies
        assert orchestrator.company_info_fetcher == mock_fetcher

        mock_storage_class.assert_called_once_with(database_name="test-storage")
        mock_sources_class.assert_called_once_with(database_name="test-storage")
        mock_companies_class.assert_called_once_with(database_name="test-storage")

    @patch.dict("os.environ", {"STORAGE_DATABASE_NAME": "env-storage-db"})
    @patch("job_finder.search_orchestrator.CompanyInfoFetcher")
    @patch("job_finder.search_orchestrator.CompaniesManager")
    @patch("job_finder.search_orchestrator.JobSourcesManager")
    @patch("job_finder.search_orchestrator.FirestoreJobStorage")
    def test_initialize_storage_respects_env_var(
        self,
        mock_storage_class,
        mock_sources_class,
        mock_companies_class,
        mock_fetcher_class,
        mock_config,
    ):
        """Test storage initialization respects environment variable."""
        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.ai_matcher = Mock()
        orchestrator._initialize_storage()

        # All should use env var
        mock_storage_class.assert_called_once_with(database_name="env-storage-db")
        mock_sources_class.assert_called_once_with(database_name="env-storage-db")
        mock_companies_class.assert_called_once_with(database_name="env-storage-db")


class TestGetActiveListings:
    """Test source retrieval and sorting."""

    def test_get_active_sources_sorted_by_priority(self, mock_config):
        """Test sources are sorted by priority score."""
        # Mock sources with company links
        mock_sources = [
            {"id": "1", "name": "RSS Feed", "companyId": None},  # No company
            {"id": "2", "name": "Company B Source", "companyId": "comp-b"},
            {"id": "3", "name": "Company C Source", "companyId": "comp-c"},
        ]

        # Mock company data
        mock_companies = {
            "comp-b": {
                "id": "comp-b",
                "priorityScore": 100,
                "tier": "A",
                "hasPortlandOffice": False,
                "techStack": [],
            },
            "comp-c": {
                "id": "comp-c",
                "priorityScore": 150,
                "tier": "S",
                "hasPortlandOffice": True,
                "techStack": ["Python"],
            },
        }

        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.sources_manager = Mock()
        orchestrator.companies_manager = Mock()
        orchestrator.sources_manager.get_active_sources.return_value = mock_sources
        # Use batch_get_companies instead of individual get_company_by_id
        orchestrator.companies_manager.batch_get_companies.return_value = mock_companies

        sorted_sources = orchestrator._get_active_sources()

        # Should be sorted by score (descending), then name
        assert sorted_sources[0]["name"] == "Company C Source"  # Score 150
        assert sorted_sources[1]["name"] == "Company B Source"  # Score 100
        assert sorted_sources[2]["name"] == "RSS Feed"  # Score 0 (no company)

    def test_get_active_sources_handles_missing_company(self, mock_config):
        """Test sources with missing company data."""
        mock_sources = [
            {"id": "1", "name": "Orphaned Source", "companyId": "missing-id"},
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.sources_manager = Mock()
        orchestrator.companies_manager = Mock()
        orchestrator.sources_manager.get_active_sources.return_value = mock_sources
        # Return empty dict for batch_get_companies - company not found
        orchestrator.companies_manager.batch_get_companies.return_value = {}

        sorted_sources = orchestrator._get_active_sources()

        # Should set default priority for missing company
        assert sorted_sources[0]["priorityScore"] == 0
        assert sorted_sources[0]["tier"] == "D"


class TestScrapeJobsFromListing:
    """Test job scraping dispatch."""

    @patch("job_finder.search_orchestrator.RSSJobScraper")
    def test_scrape_rss_source(self, mock_scraper_class, mock_config, sample_job):
        """Test scraping from RSS source."""
        mock_scraper = Mock()
        mock_scraper.scrape.return_value = [sample_job]
        mock_scraper_class.return_value = mock_scraper

        listing = {
            "sourceType": "rss",
            "name": "RSS Feed",
            "config": {"feed_url": "https://example.com/feed"},
        }

        orchestrator = JobSearchOrchestrator(mock_config)
        jobs = orchestrator._scrape_jobs_from_listing(listing)

        assert len(jobs) == 1
        assert jobs[0] == sample_job
        mock_scraper.scrape.assert_called_once()

    @patch("job_finder.search_orchestrator.GreenhouseScraper")
    def test_scrape_greenhouse_source(self, mock_scraper_class, mock_config, sample_job):
        """Test scraping from Greenhouse source."""
        mock_scraper = Mock()
        mock_scraper.scrape.return_value = [sample_job]
        mock_scraper_class.return_value = mock_scraper

        listing = {
            "sourceType": "greenhouse",
            "name": "Test Company Source",
            "companyName": "Test Company",
            "company_website": "https://test.com",
            "config": {
                "board_token": "test-company",
            },
        }

        orchestrator = JobSearchOrchestrator(mock_config)
        jobs = orchestrator._scrape_jobs_from_listing(listing)

        assert len(jobs) == 1
        assert jobs[0] == sample_job
        mock_scraper_class.assert_called_once()

    def test_scrape_unknown_source_type(self, mock_config):
        """Test scraping unknown source type returns empty list."""
        listing = {"sourceType": "unknown", "name": "Unknown Source"}

        orchestrator = JobSearchOrchestrator(mock_config)
        jobs = orchestrator._scrape_jobs_from_listing(listing)

        assert jobs == []

    def test_scrape_api_not_implemented(self, mock_config):
        """Test API scraping returns empty list (not yet implemented)."""
        listing = {"sourceType": "api", "name": "API Source"}

        orchestrator = JobSearchOrchestrator(mock_config)
        jobs = orchestrator._scrape_jobs_from_listing(listing)

        assert jobs == []


class TestFilterRemoteOnly:
    """Test remote job filtering."""

    def test_filter_remote_keyword_in_location(self, mock_config):
        """Test filtering accepts remote keyword in location."""
        jobs = [
            {"title": "Engineer", "location": "Remote - US", "description": "Job desc"},
            {"title": "Engineer", "location": "San Francisco, CA", "description": "Job desc"},
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        filtered = orchestrator._filter_remote_only(jobs)

        assert len(filtered) == 1
        assert filtered[0]["location"] == "Remote - US"

    def test_filter_remote_keyword_in_title(self, mock_config):
        """Test filtering accepts remote keyword in title."""
        jobs = [
            {"title": "Remote Engineer", "location": "Unknown", "description": "Job desc"},
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        filtered = orchestrator._filter_remote_only(jobs)

        assert len(filtered) == 1

    def test_filter_remote_keyword_in_description(self, mock_config):
        """Test filtering accepts remote keyword in description."""
        jobs = [
            {
                "title": "Engineer",
                "location": "Unknown",
                "description": "This is a remote position working from anywhere",
            },
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        filtered = orchestrator._filter_remote_only(jobs)

        assert len(filtered) == 1

    def test_filter_portland_location(self, mock_config):
        """Test filtering accepts Portland, OR locations."""
        jobs = [
            {"title": "Engineer", "location": "Portland, OR", "description": "Job desc"},
            {"title": "Engineer", "location": "Portland, Oregon", "description": "Job desc"},
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        filtered = orchestrator._filter_remote_only(jobs)

        assert len(filtered) == 2

    def test_filter_rejects_non_remote_non_portland(self, mock_config):
        """Test filtering rejects non-remote, non-Portland jobs."""
        jobs = [
            {"title": "Engineer", "location": "New York, NY", "description": "On-site position"},
            {"title": "Engineer", "location": "Austin, TX", "description": "Hybrid"},
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        filtered = orchestrator._filter_remote_only(jobs)

        assert len(filtered) == 0


class TestFilterByAge:
    """Test age-based filtering."""

    def test_filter_by_age_accepts_recent_jobs(self, mock_config):
        """Test filtering accepts jobs within age limit."""
        recent_date = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        jobs = [
            {
                "title": "Recent Job",
                "company": "Test",
                "posted_date": recent_date,
            },
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        filtered = orchestrator._filter_by_age(jobs, max_days=7)

        assert len(filtered) == 1

    def test_filter_by_age_rejects_old_jobs(self, mock_config):
        """Test filtering rejects jobs older than age limit."""
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        jobs = [
            {
                "title": "Old Job",
                "company": "Test",
                "posted_date": old_date,
            },
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        filtered = orchestrator._filter_by_age(jobs, max_days=7)

        assert len(filtered) == 0

    def test_filter_by_age_skips_no_date(self, mock_config):
        """Test filtering skips jobs with no posted_date."""
        jobs = [
            {"title": "No Date Job", "company": "Test"},
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        filtered = orchestrator._filter_by_age(jobs, max_days=7)

        assert len(filtered) == 0


class TestFilterByJobType:
    """Test job type and seniority filtering."""

    @patch("job_finder.utils.common_filters.filter_job")
    def test_filter_by_job_type_accepts_valid_jobs(self, mock_filter, mock_config):
        """Test filtering accepts valid engineering jobs."""
        mock_filter.return_value = (FilterDecision.ACCEPT, "Passed all filters")

        jobs = [
            {"title": "Senior Software Engineer", "description": "Job desc"},
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        filtered, stats = orchestrator._filter_by_job_type(jobs)

        assert len(filtered) == 1
        assert stats == {}
        mock_filter.assert_called_once()

    @patch("job_finder.utils.common_filters.filter_job")
    def test_filter_by_job_type_rejects_invalid_jobs(self, mock_filter, mock_config):
        """Test filtering rejects non-engineering jobs."""
        mock_filter.return_value = (
            FilterDecision.REJECT,
            "Management/Executive role: 'manager'",
        )

        jobs = [
            {"title": "Engineering Manager", "description": "Job desc"},
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        filtered, stats = orchestrator._filter_by_job_type(jobs)

        assert len(filtered) == 0
        assert stats["Management/Executive role: 'manager'"] == 1


class TestCheckForDuplicates:
    """Test duplicate detection."""

    def test_check_for_duplicates_identifies_existing(self, mock_config):
        """Test duplicate checking identifies existing jobs."""
        jobs = [
            {"url": "https://test.com/job1", "title": "Job 1"},
            {"url": "https://test.com/job2", "title": "Job 2"},
            {"url": "https://test.com/job3", "title": "Job 3"},
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.job_storage = Mock()
        orchestrator.job_storage.batch_check_exists.return_value = {
            "https://test.com/job1": True,  # Exists
            "https://test.com/job2": False,  # New
            "https://test.com/job3": False,  # New
        }

        existing_jobs, duplicates_count, new_jobs_count = orchestrator._check_for_duplicates(jobs)

        assert duplicates_count == 1
        assert new_jobs_count == 2
        assert existing_jobs["https://test.com/job1"] is True
        assert existing_jobs["https://test.com/job2"] is False


class TestBuildCompanyInfoString:
    """Test company info string building."""

    def test_build_company_info_with_all_fields(self, mock_config):
        """Test building company info with all fields present."""
        company_info = {
            "about": "We are a great company",
            "culture": "We value innovation",
            "mission": "To change the world",
        }

        orchestrator = JobSearchOrchestrator(mock_config)
        info_str = orchestrator._build_company_info_string(company_info)

        assert "About: We are a great company" in info_str
        assert "Culture: We value innovation" in info_str
        assert "Mission: To change the world" in info_str

    def test_build_company_info_with_partial_fields(self, mock_config):
        """Test building company info with only some fields."""
        company_info = {
            "about": "We are a company",
            "culture": "",
            "mission": "",
        }

        orchestrator = JobSearchOrchestrator(mock_config)
        info_str = orchestrator._build_company_info_string(company_info)

        assert "About: We are a company" in info_str
        assert "Culture:" not in info_str
        assert "Mission:" not in info_str

    def test_build_company_info_empty(self, mock_config):
        """Test building company info with no fields."""
        company_info = {}

        orchestrator = JobSearchOrchestrator(mock_config)
        info_str = orchestrator._build_company_info_string(company_info)

        assert info_str == ""


class TestLogListingHeader:
    """Test listing header logging."""

    def test_log_listing_header_with_all_fields(self, mock_config):
        """Test logging header with all listing fields."""
        listing = {
            "name": "Test Company",
            "sourceType": "greenhouse",
            "priorityScore": 100,
            "tier": "A",
            "hasPortlandOffice": True,
        }

        orchestrator = JobSearchOrchestrator(mock_config)
        # Should not raise any errors
        orchestrator._log_listing_header(listing)

    def test_log_listing_header_with_minimal_fields(self, mock_config):
        """Test logging header with minimal fields."""
        listing = {"name": "Minimal Company"}

        orchestrator = JobSearchOrchestrator(mock_config)
        # Should not raise any errors, uses defaults
        orchestrator._log_listing_header(listing)

    def test_log_listing_header_tier_emojis(self, mock_config):
        """Test different tier emojis."""
        orchestrator = JobSearchOrchestrator(mock_config)

        for tier in ["S", "A", "B", "C", "D"]:
            listing = {"name": "Company", "tier": tier}
            # Should not raise any errors
            orchestrator._log_listing_header(listing)


class TestFetchAndAttachCompanyInfo:
    """Test company info fetching and attachment."""

    def test_fetch_and_attach_with_valid_website(self, mock_config, sample_job):
        """Test fetching and attaching company info with valid website."""
        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.companies_manager = Mock()
        orchestrator.company_info_fetcher = Mock()

        company_info = {
            "about": "Great company",
            "culture": "Innovation focused",
            "mission": "Change the world",
        }
        orchestrator.companies_manager.get_or_create_company.return_value = company_info

        listing = {
            "name": "Test Company",
            "company_website": "https://test.com",
        }
        jobs = [sample_job.copy(), sample_job.copy()]

        orchestrator._fetch_and_attach_company_info(listing, jobs)

        # All jobs should have company info attached (format is "About: ..." with capital A)
        assert "great company" in jobs[0]["company_info"].lower()
        assert "great company" in jobs[1]["company_info"].lower()

    def test_fetch_and_attach_without_website(self, mock_config, sample_job):
        """Test handling jobs when no company website is available."""
        orchestrator = JobSearchOrchestrator(mock_config)

        listing = {"name": "Test Company", "company_website": ""}
        jobs = [sample_job.copy()]

        orchestrator._fetch_and_attach_company_info(listing, jobs)

        # Should set empty company_info
        assert jobs[0]["company_info"] == ""

    def test_fetch_and_attach_handles_errors(self, mock_config, sample_job):
        """Test error handling when company info fetch fails."""
        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.companies_manager = Mock()
        orchestrator.company_info_fetcher = Mock()

        # Simulate fetch error
        orchestrator.companies_manager.get_or_create_company.side_effect = Exception(
            "Network error"
        )

        listing = {
            "name": "Test Company",
            "company_website": "https://test.com",
        }
        jobs = [sample_job.copy()]

        # Should not raise, but log warning and continue
        orchestrator._fetch_and_attach_company_info(listing, jobs)

        # Should set empty company_info on error
        assert jobs[0]["company_info"] == ""


class TestMatchAndSaveJobs:
    """Test AI matching and saving logic."""

    def test_match_and_save_with_matched_jobs(self, mock_config, sample_job):
        """Test matching and saving jobs that meet threshold."""
        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.ai_matcher = Mock()
        orchestrator.job_storage = Mock()

        # Mock successful match
        mock_result = Mock()
        mock_result.match_score = 85
        mock_result.application_priority = "High"
        orchestrator.ai_matcher.analyze_job.return_value = mock_result
        orchestrator.job_storage.save_job_match.return_value = "job-id-123"

        jobs = [sample_job.copy()]
        existing_jobs = {sample_job["url"]: False}  # Not a duplicate
        listing = {"hasPortlandOffice": True}

        stats = orchestrator._match_and_save_jobs(jobs, existing_jobs, 1, listing)

        assert stats["jobs_analyzed"] == 1
        assert stats["jobs_matched"] == 1
        assert stats["jobs_saved"] == 1

    def test_match_and_save_below_threshold(self, mock_config, sample_job):
        """Test handling jobs below match threshold."""
        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.ai_matcher = Mock()

        # Mock below threshold (returns None)
        orchestrator.ai_matcher.analyze_job.return_value = None

        jobs = [sample_job.copy()]
        existing_jobs = {sample_job["url"]: False}
        listing = {}

        stats = orchestrator._match_and_save_jobs(jobs, existing_jobs, 1, listing)

        assert stats["jobs_analyzed"] == 1
        assert stats["jobs_matched"] == 0
        assert stats["jobs_saved"] == 0

    def test_match_and_save_skips_duplicates(self, mock_config, sample_job):
        """Test skipping jobs that already exist."""
        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.ai_matcher = Mock()

        jobs = [sample_job.copy()]
        existing_jobs = {sample_job["url"]: True}  # Is a duplicate
        listing = {}

        stats = orchestrator._match_and_save_jobs(jobs, existing_jobs, 0, listing)

        # Should not analyze duplicates
        assert stats["jobs_analyzed"] == 0
        assert stats["jobs_matched"] == 0
        assert stats["jobs_saved"] == 0
        orchestrator.ai_matcher.analyze_job.assert_not_called()

    def test_match_and_save_handles_errors(self, mock_config, sample_job):
        """Test error handling during matching."""
        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.ai_matcher = Mock()

        # Simulate error during matching
        orchestrator.ai_matcher.analyze_job.side_effect = Exception("AI error")

        jobs = [sample_job.copy(), sample_job.copy()]
        existing_jobs = {
            jobs[0]["url"]: False,
            jobs[1]["url"]: False,
        }
        listing = {}

        # Should continue despite errors
        stats = orchestrator._match_and_save_jobs(jobs, existing_jobs, 2, listing)

        # Both jobs attempted (counter incremented before AI analysis)
        assert stats["jobs_analyzed"] == 2  # Both attempted (counter before AI call)
        assert stats["jobs_matched"] == 0  # None matched (errors occurred)
        assert stats["jobs_saved"] == 0  # None saved (errors occurred)
