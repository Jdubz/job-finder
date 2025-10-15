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


@pytest.fixture
def mock_profile():
    """Create a mock profile object."""
    profile = Mock()
    profile.name = "Test User"
    profile.email = "test@example.com"
    profile.experience = [Mock()]
    profile.skills = [Mock(), Mock()]
    return profile


@pytest.fixture
def sample_job():
    """Create a sample job dictionary."""
    return {
        "title": "Senior Software Engineer",
        "company": "Test Company",
        "company_website": "https://test.com",
        "company_info": "",
        "location": "Remote",
        "description": "Job description here",
        "url": "https://test.com/job/123",
        "posted_date": datetime.now(timezone.utc).isoformat(),
        "salary": "$150k-$200k",
        "keywords": ["Python", "AWS"],
    }


class TestJobSearchOrchestratorInit:
    """Test orchestrator initialization."""

    def test_init_stores_config(self, mock_config):
        """Test orchestrator stores configuration."""
        orchestrator = JobSearchOrchestrator(mock_config)

        assert orchestrator.config == mock_config
        assert orchestrator.profile is None
        assert orchestrator.ai_matcher is None
        assert orchestrator.job_storage is None
        assert orchestrator.listings_manager is None
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
        mock_matcher_class.assert_called_once_with(
            provider=mock_provider,
            profile=mock_profile,
            min_match_score=80,
            generate_intake=True,
            portland_office_bonus=15,
        )


class TestInitializeStorage:
    """Test storage initialization."""

    @patch("job_finder.search_orchestrator.CompanyInfoFetcher")
    @patch("job_finder.search_orchestrator.CompaniesManager")
    @patch("job_finder.search_orchestrator.JobListingsManager")
    @patch("job_finder.search_orchestrator.FirestoreJobStorage")
    def test_initialize_storage(
        self,
        mock_storage_class,
        mock_listings_class,
        mock_companies_class,
        mock_fetcher_class,
        mock_config,
    ):
        """Test storage initialization."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_listings = Mock()
        mock_listings_class.return_value = mock_listings
        mock_companies = Mock()
        mock_companies_class.return_value = mock_companies
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.ai_matcher = Mock()
        orchestrator.ai_matcher.provider = Mock()
        orchestrator._initialize_storage()

        assert orchestrator.job_storage == mock_storage
        assert orchestrator.listings_manager == mock_listings
        assert orchestrator.companies_manager == mock_companies
        assert orchestrator.company_info_fetcher == mock_fetcher

        mock_storage_class.assert_called_once_with(database_name="test-storage")
        mock_listings_class.assert_called_once_with(database_name="test-storage")
        mock_companies_class.assert_called_once_with(database_name="test-storage")

    @patch.dict("os.environ", {"STORAGE_DATABASE_NAME": "env-storage-db"})
    @patch("job_finder.search_orchestrator.CompanyInfoFetcher")
    @patch("job_finder.search_orchestrator.CompaniesManager")
    @patch("job_finder.search_orchestrator.JobListingsManager")
    @patch("job_finder.search_orchestrator.FirestoreJobStorage")
    def test_initialize_storage_respects_env_var(
        self,
        mock_storage_class,
        mock_listings_class,
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
        mock_listings_class.assert_called_once_with(database_name="env-storage-db")
        mock_companies_class.assert_called_once_with(database_name="env-storage-db")


class TestGetActiveListings:
    """Test listing retrieval and sorting."""

    def test_get_active_listings_sorted_by_priority(self, mock_config):
        """Test listings are sorted by priority score."""
        mock_listings = [
            {"id": "1", "name": "Company A", "priorityScore": 50, "tier": "B"},
            {"id": "2", "name": "Company B", "priorityScore": 100, "tier": "A"},
            {"id": "3", "name": "Company C", "priorityScore": 150, "tier": "S"},
            {"id": "4", "name": "Company D", "priorityScore": 50, "tier": "B"},
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.listings_manager = Mock()
        orchestrator.listings_manager.get_active_listings.return_value = mock_listings

        sorted_listings = orchestrator._get_active_listings()

        # Should be sorted by score (descending), then name
        assert sorted_listings[0]["priorityScore"] == 150  # Highest first
        assert sorted_listings[1]["priorityScore"] == 100
        assert sorted_listings[2]["name"] == "Company A"  # Alphabetical for same score
        assert sorted_listings[3]["name"] == "Company D"

    def test_get_active_listings_handles_missing_score(self, mock_config):
        """Test listings with missing priority scores."""
        mock_listings = [
            {"id": "1", "name": "Company A"},  # Missing priorityScore
            {"id": "2", "name": "Company B", "priorityScore": 100},
        ]

        orchestrator = JobSearchOrchestrator(mock_config)
        orchestrator.listings_manager = Mock()
        orchestrator.listings_manager.get_active_listings.return_value = mock_listings

        sorted_listings = orchestrator._get_active_listings()

        # Company B should come first (has score 100 vs 0)
        assert sorted_listings[0]["name"] == "Company B"
        assert sorted_listings[1]["name"] == "Company A"


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
            "board_token": "test-company",
            "name": "Test Company",
            "company_website": "https://test.com",
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

    @patch("job_finder.search_orchestrator.filter_job")
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

    @patch("job_finder.search_orchestrator.filter_job")
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
