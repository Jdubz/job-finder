"""Tests for RSS Job Scraper."""

from unittest.mock import Mock, patch
import pytest
from job_finder.scrapers.rss_scraper import RSSJobScraper


@pytest.fixture
def base_config():
    return {"delay_between_requests": 0}


@pytest.fixture
def listing_config():
    return {
        "url": "https://example.com/jobs.rss",
        "title_field": "title",
        "description_field": "description",
        "link_field": "link",
    }


@pytest.fixture
def mock_rss_entry():
    entry = Mock()
    entry.title = "Senior Software Engineer at TechCorp"
    entry.description = "Looking for a senior engineer."
    entry.link = "https://example.com/jobs/123"
    entry.published = "Mon, 25 Oct 2025 10:00:00 GMT"
    return entry


class TestRSSJobScraperInit:
    def test_init_stores_config(self, base_config, listing_config):
        scraper = RSSJobScraper(base_config, listing_config)
        assert scraper.feed_url == "https://example.com/jobs.rss"

    def test_init_without_url(self, base_config):
        scraper = RSSJobScraper(base_config, {})
        assert scraper.feed_url is None


class TestRSSJobScraperScrape:
    @patch("job_finder.scrapers.rss_scraper.feedparser.parse")
    def test_scrape_valid_feed(self, mock_parse, base_config, listing_config, mock_rss_entry):
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [mock_rss_entry]
        mock_parse.return_value = mock_feed

        scraper = RSSJobScraper(base_config, listing_config)
        jobs = scraper.scrape()

        assert len(jobs) == 1
        assert "Senior" in jobs[0]["title"]

    @patch("job_finder.scrapers.rss_scraper.feedparser.parse")
    def test_scrape_empty_feed(self, mock_parse, base_config, listing_config):
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = []
        mock_parse.return_value = mock_feed

        scraper = RSSJobScraper(base_config, listing_config)
        assert len(scraper.scrape()) == 0

    def test_scrape_without_url(self, base_config):
        scraper = RSSJobScraper(base_config, {})
        assert scraper.scrape() == []

    @patch("job_finder.scrapers.rss_scraper.feedparser.parse")
    def test_scrape_handles_errors(self, mock_parse, base_config, listing_config):
        mock_parse.side_effect = Exception("Network error")
        scraper = RSSJobScraper(base_config, listing_config)
        assert scraper.scrape() == []


class TestCompanyExtraction:
    def test_extract_company_at_pattern(self, base_config, listing_config):
        scraper = RSSJobScraper(base_config, listing_config)
        assert scraper._extract_company_from_title("Engineer at TechCorp") == "TechCorp"

    def test_extract_company_colon_pattern(self, base_config, listing_config):
        scraper = RSSJobScraper(base_config, listing_config)
        assert scraper._extract_company_from_title("TechCorp: Engineer") == "TechCorp"

    def test_extract_company_dash_pattern(self, base_config, listing_config):
        scraper = RSSJobScraper(base_config, listing_config)
        assert scraper._extract_company_from_title("Engineer - TechCorp") == "TechCorp"

    def test_extract_company_no_match(self, base_config, listing_config):
        scraper = RSSJobScraper(base_config, listing_config)
        assert scraper._extract_company_from_title("Software Engineer") == ""


class TestLocationExtraction:
    def test_extract_remote(self, base_config, listing_config):
        scraper = RSSJobScraper(base_config, listing_config)
        assert scraper._extract_location("Engineer (Remote)", "") == "Remote"

    def test_extract_unknown(self, base_config, listing_config):
        scraper = RSSJobScraper(base_config, listing_config)
        assert scraper._extract_location("Engineer", "") == "Unknown"


class TestSalaryExtraction:
    def test_extract_salary_range(self, base_config, listing_config):
        scraper = RSSJobScraper(base_config, listing_config)
        salary = scraper._extract_salary("", "$100,000 - $150,000")
        assert "$100,000" in salary

    def test_extract_salary_none(self, base_config, listing_config):
        scraper = RSSJobScraper(base_config, listing_config)
        assert scraper._extract_salary("Engineer", "Great job") == ""


class TestTitleCleaning:
    def test_clean_title_removes_company(self, base_config, listing_config):
        scraper = RSSJobScraper(base_config, listing_config)
        cleaned = scraper._clean_title("Engineer at TechCorp", "TechCorp")
        assert cleaned == "Engineer"
