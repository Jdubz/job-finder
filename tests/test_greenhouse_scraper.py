"""Tests for Greenhouse scraper."""

from unittest.mock import Mock, patch

import pytest

from job_finder.exceptions import ScraperError
from job_finder.scrapers.greenhouse_scraper import GreenhouseScraper, create_scraper_for_company


class TestGreenhouseScraperInit:
    """Test Greenhouse scraper initialization."""

    def test_init_with_valid_config(self):
        """Test scraper initialization with valid configuration."""
        config = {
            "board_token": "test-company",
            "name": "Test Company",
            "company_website": "https://test.com",
        }
        scraper = GreenhouseScraper(config)

        assert scraper.board_token == "test-company"
        assert scraper.company_name == "Test Company"
        assert scraper.company_website == "https://test.com"
        assert scraper.base_url == "https://boards-api.greenhouse.io/v1/boards"

    def test_init_without_board_token(self):
        """Test scraper initialization fails without board_token."""
        config = {"name": "Test Company"}

        with pytest.raises(ScraperError, match="board_token is required"):
            GreenhouseScraper(config)

    def test_init_with_minimal_config(self):
        """Test scraper initialization with minimal configuration."""
        config = {"board_token": "test-company"}
        scraper = GreenhouseScraper(config)

        assert scraper.board_token == "test-company"
        assert scraper.company_name == "Unknown"
        assert scraper.company_website == ""


class TestGreenhouseScraperScrape:
    """Test Greenhouse scraper scraping functionality."""

    @patch("job_finder.scrapers.greenhouse_scraper.requests.get")
    def test_scrape_success(self, mock_get):
        """Test successful job scraping."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "jobs": [
                {
                    "id": 1,
                    "title": "Senior Software Engineer",
                    "location": {"name": "Remote"},
                    "absolute_url": "https://boards.greenhouse.io/test/jobs/1",
                    "content": "Job description here",
                    "updated_at": "2025-10-15T10:00:00Z",
                    "departments": [{"name": "Engineering"}],
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        config = {"board_token": "test-company", "name": "Test Company"}
        scraper = GreenhouseScraper(config)
        jobs = scraper.scrape()

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Senior Software Engineer"
        assert jobs[0]["company"] == "Test Company"
        assert jobs[0]["location"] == "Remote"

    @patch("job_finder.scrapers.greenhouse_scraper.requests.get")
    def test_scrape_empty_response(self, mock_get):
        """Test scraping with empty job list."""
        mock_response = Mock()
        mock_response.json.return_value = {"jobs": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        config = {"board_token": "test-company", "name": "Test Company"}
        scraper = GreenhouseScraper(config)
        jobs = scraper.scrape()

        assert len(jobs) == 0

    @patch("job_finder.scrapers.greenhouse_scraper.requests.get")
    def test_scrape_request_exception(self, mock_get):
        """Test scraping handles request exceptions."""
        import requests

        mock_get.side_effect = requests.RequestException("API Error")

        config = {"board_token": "test-company", "name": "Test Company"}
        scraper = GreenhouseScraper(config)
        jobs = scraper.scrape()

        assert len(jobs) == 0  # Should return empty list on error

    @patch("job_finder.scrapers.greenhouse_scraper.requests.get")
    def test_scrape_invalid_json(self, mock_get):
        """Test scraping handles invalid JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        config = {"board_token": "test-company", "name": "Test Company"}
        scraper = GreenhouseScraper(config)
        jobs = scraper.scrape()

        assert len(jobs) == 0

    @patch("job_finder.scrapers.greenhouse_scraper.requests.get")
    def test_scrape_with_parsing_errors(self, mock_get):
        """Test scraping continues when some jobs fail to parse."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jobs": [
                {
                    "id": 1,
                    "title": "Valid Job",
                    "location": {"name": "Remote"},
                    "absolute_url": "https://test.com/1",
                    "content": "Description",
                },
                {
                    "id": 2,
                    # Parser handles missing fields gracefully with defaults
                },
                {
                    "id": 3,
                    "title": "Another Valid Job",
                    "location": {"name": "NYC"},
                    "absolute_url": "https://test.com/3",
                    "content": "Description",
                },
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        config = {"board_token": "test-company", "name": "Test Company"}
        scraper = GreenhouseScraper(config)
        jobs = scraper.scrape()

        # Parser handles missing fields gracefully, so all 3 jobs parse successfully
        assert len(jobs) == 3
        assert jobs[0]["title"] == "Valid Job"
        assert jobs[1]["title"] == "Unknown"  # Default when title missing
        assert jobs[2]["title"] == "Another Valid Job"


class TestGreenhouseScraperParseJob:
    """Test Greenhouse job parsing."""

    def test_parse_job_complete_data(self):
        """Test parsing job with all fields."""
        config = {
            "board_token": "test",
            "name": "Test Company",
            "company_website": "https://test.com",
        }
        scraper = GreenhouseScraper(config)

        job_data = {
            "id": 123,
            "title": "Senior Backend Engineer",
            "location": {"name": "Remote - US"},
            "absolute_url": "https://boards.greenhouse.io/test/jobs/123",
            "content": "<p>We are looking for a Senior Backend Engineer...</p>",
            "updated_at": "2025-10-15T10:00:00Z",
            "departments": [{"name": "Engineering"}, {"name": "Backend"}],
        }

        job = scraper.parse_job(job_data)

        assert job is not None
        assert job["title"] == "Senior Backend Engineer"
        assert job["company"] == "Test Company"
        assert job["company_website"] == "https://test.com"
        assert job["location"] == "Remote - US"
        assert "Senior Backend Engineer" in job["description"]
        assert job["url"] == "https://boards.greenhouse.io/test/jobs/123"
        assert job["posted_date"].startswith("2025-10-15")
        # Note: keywords field removed - ATS keywords now only in resumeIntakeData (AI-generated)
        assert "keywords" not in job  # Verify field is not populated by scraper

    def test_parse_job_minimal_data(self):
        """Test parsing job with minimal required fields."""
        config = {"board_token": "test", "name": "Test Company"}
        scraper = GreenhouseScraper(config)

        job_data = {
            "title": "Engineer",
            "location": {"name": "Unknown"},
            "absolute_url": "https://test.com/job",
        }

        job = scraper.parse_job(job_data)

        assert job is not None
        assert job["title"] == "Engineer"
        assert job["company"] == "Test Company"
        assert job["location"] == "Unknown"
        assert job["url"] == "https://test.com/job"

    def test_parse_job_with_created_at(self):
        """Test parsing job uses created_at when updated_at is missing."""
        config = {"board_token": "test", "name": "Test Company"}
        scraper = GreenhouseScraper(config)

        job_data = {
            "title": "Engineer",
            "location": {"name": "Remote"},
            "absolute_url": "https://test.com/job",
            "created_at": "2025-10-14T12:00:00Z",
        }

        job = scraper.parse_job(job_data)

        assert job is not None
        assert job["posted_date"].startswith("2025-10-14")

    def test_parse_job_handles_exception(self):
        """Test parsing returns None on exception."""
        config = {"board_token": "test", "name": "Test Company"}
        scraper = GreenhouseScraper(config)

        # Invalid job data that will cause exception
        job_data = None

        job = scraper.parse_job(job_data)

        assert job is None


class TestGreenhouseExtractLocation:
    """Test location extraction."""

    def test_extract_location_with_dict(self):
        """Test location extraction from dict object."""
        config = {"board_token": "test", "name": "Test"}
        scraper = GreenhouseScraper(config)

        job_data = {"location": {"name": "San Francisco, CA"}}
        location = scraper._extract_location(job_data)

        assert location == "San Francisco, CA"

    def test_extract_location_empty_name(self):
        """Test location extraction with empty name."""
        config = {"board_token": "test", "name": "Test"}
        scraper = GreenhouseScraper(config)

        job_data = {"location": {"name": ""}}
        location = scraper._extract_location(job_data)

        assert location == "Unknown"

    def test_extract_location_no_location(self):
        """Test location extraction with missing location."""
        config = {"board_token": "test", "name": "Test"}
        scraper = GreenhouseScraper(config)

        job_data = {}
        location = scraper._extract_location(job_data)

        assert location == "Unknown"

    def test_extract_location_non_dict(self):
        """Test location extraction with non-dict location."""
        config = {"board_token": "test", "name": "Test"}
        scraper = GreenhouseScraper(config)

        job_data = {"location": "Not a dict"}
        location = scraper._extract_location(job_data)

        assert location == "Unknown"


class TestGreenhouseExtractDescription:
    """Test description extraction."""

    def test_extract_description_with_content(self):
        """Test description extraction when content exists."""
        config = {"board_token": "test", "name": "Test"}
        scraper = GreenhouseScraper(config)

        job_data = {"content": "<p>Full job description here</p>"}
        description = scraper._extract_description(job_data)

        assert description == "<p>Full job description here</p>"

    def test_extract_description_without_content(self):
        """Test description extraction builds from other fields."""
        config = {"board_token": "test", "name": "Test"}
        scraper = GreenhouseScraper(config)

        job_data = {
            "title": "Software Engineer",
            "location": {"name": "Remote"},
            "departments": [{"name": "Engineering"}, {"name": "Backend"}],
        }
        description = scraper._extract_description(job_data)

        assert "Position: Software Engineer" in description
        assert "Location: Remote" in description
        assert "Departments: Engineering, Backend" in description

    def test_extract_description_empty_data(self):
        """Test description extraction with empty data."""
        config = {"board_token": "test", "name": "Test"}
        scraper = GreenhouseScraper(config)

        job_data = {}
        description = scraper._extract_description(job_data)

        # When content is missing, builds description from location
        assert "Location: Unknown" in description


class TestCreateScraperForCompany:
    """Test helper function to create scraper."""

    def test_create_scraper_for_company(self):
        """Test creating scraper with helper function."""
        scraper = create_scraper_for_company(
            company_name="Deepgram",
            board_token="deepgram",
            company_website="https://deepgram.com",
        )

        assert isinstance(scraper, GreenhouseScraper)
        assert scraper.company_name == "Deepgram"
        assert scraper.board_token == "deepgram"
        assert scraper.company_website == "https://deepgram.com"

    def test_create_scraper_without_website(self):
        """Test creating scraper without website."""
        scraper = create_scraper_for_company(company_name="Test Company", board_token="test")

        assert isinstance(scraper, GreenhouseScraper)
        assert scraper.company_name == "Test Company"
        assert scraper.board_token == "test"
        assert scraper.company_website == ""
