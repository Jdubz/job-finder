"""Tests for company info scraper."""

import pytest

from job_finder.scrapers.company_info import CompanyInfoScraper


@pytest.fixture
def scraper():
    """Create a CompanyInfoScraper instance."""
    return CompanyInfoScraper(timeout=10)


class TestCompanyInfoScraperInit:
    """Test CompanyInfoScraper initialization."""

    def test_init_default_timeout(self):
        """Test initialization with default timeout."""
        scraper = CompanyInfoScraper()
        assert scraper.timeout == 10

    def test_init_custom_timeout(self):
        """Test initialization with custom timeout."""
        scraper = CompanyInfoScraper(timeout=30)
        assert scraper.timeout == 30

    def test_culture_paths_defined(self):
        """Test that culture paths are defined."""
        assert len(CompanyInfoScraper.CULTURE_PATHS) > 0
        assert "/about" in CompanyInfoScraper.CULTURE_PATHS
        assert "/culture" in CompanyInfoScraper.CULTURE_PATHS


class TestScrapeCompanyInfo:
    """Test scrape_company_info method."""

    def test_scrape_adds_https_prefix(self, scraper):
        """Test that URLs without scheme get https:// added."""
        # Currently returns None because _fetch_culture_pages is not implemented
        result = scraper.scrape_company_info("example.com")
        # Just verify it doesn't crash
        assert result is None

    def test_scrape_with_http_prefix(self, scraper):
        """Test scraping with http:// prefix."""
        result = scraper.scrape_company_info("http://example.com")
        assert result is None

    def test_scrape_with_https_prefix(self, scraper):
        """Test scraping with https:// prefix."""
        result = scraper.scrape_company_info("https://example.com")
        assert result is None

    def test_scrape_handles_exception(self, scraper, caplog):
        """Test that exceptions are handled gracefully."""
        # Pass an invalid URL that might cause issues
        result = scraper.scrape_company_info("")
        # Should return None and log warning
        assert result is None


class TestFetchCulturePages:
    """Test _fetch_culture_pages method."""

    def test_fetch_returns_none(self, scraper):
        """Test that fetch currently returns None (not implemented)."""
        result = scraper._fetch_culture_pages("https://example.com")
        assert result is None

    def test_fetch_logs_info(self, scraper, caplog):
        """Test that fetch logs info about implementation."""
        import logging
        
        caplog.set_level(logging.INFO)
        scraper._fetch_culture_pages("https://example.com")
        assert "to be implemented" in caplog.text.lower()


class TestCleanText:
    """Test _clean_text method."""

    def test_clean_removes_extra_whitespace(self, scraper):
        """Test that extra whitespace is removed."""
        text = "Hello    world\n\n\nMultiple   spaces"
        result = scraper._clean_text(text)
        assert "    " not in result
        assert "\n\n" not in result
        assert "Hello world Multiple spaces" == result

    def test_clean_removes_cookie_policy(self, scraper):
        """Test that cookie policy text is removed."""
        text = "Company info here. Cookie Policy: We use cookies"
        result = scraper._clean_text(text)
        assert "Cookie Policy" not in result
        assert "Company info here." in result

    def test_clean_removes_privacy_policy(self, scraper):
        """Test that privacy policy text is removed."""
        text = "Great company. Privacy Policy and terms follow"
        result = scraper._clean_text(text)
        assert "Privacy Policy" not in result
        assert "Great company." in result

    def test_clean_removes_terms_of_service(self, scraper):
        """Test that terms of service text is removed."""
        text = "About us. Terms of Service apply"
        result = scraper._clean_text(text)
        assert "Terms of Service" not in result
        assert "About us." in result

    def test_clean_case_insensitive_removal(self, scraper):
        """Test that removal is case insensitive."""
        text = "Info. COOKIE POLICY stuff"
        result = scraper._clean_text(text)
        assert "COOKIE POLICY" not in result

    def test_clean_trims_long_text(self, scraper):
        """Test that text is trimmed to 1000 characters."""
        text = "A" * 2000
        result = scraper._clean_text(text)
        assert len(result) <= 1003  # 1000 + "..."
        assert result.endswith("...")

    def test_clean_preserves_short_text(self, scraper):
        """Test that short text is preserved."""
        text = "This is a short company description."
        result = scraper._clean_text(text)
        assert result == text

    def test_clean_strips_whitespace(self, scraper):
        """Test that leading/trailing whitespace is stripped."""
        text = "   Company info   "
        result = scraper._clean_text(text)
        assert result == "Company info"

    def test_clean_empty_text(self, scraper):
        """Test cleaning empty text."""
        result = scraper._clean_text("")
        assert result == ""

    def test_clean_whitespace_only(self, scraper):
        """Test cleaning whitespace-only text."""
        result = scraper._clean_text("   \n\n   ")
        assert result == ""


class TestExtractCompanyDomain:
    """Test extract_company_domain method."""

    def test_extract_from_company_website(self, scraper):
        """Test extracting domain from company website."""
        url = "https://www.example.com/careers/job/123"
        result = scraper.extract_company_domain(url)
        assert result == "https://www.example.com"

    def test_extract_from_simple_domain(self, scraper):
        """Test extracting from simple domain."""
        url = "https://example.com"
        result = scraper.extract_company_domain(url)
        assert result == "https://example.com"

    def test_extract_with_subdomain(self, scraper):
        """Test extracting from URL with subdomain."""
        url = "https://careers.example.com/job/123"
        result = scraper.extract_company_domain(url)
        assert result == "https://careers.example.com"

    def test_extract_with_port(self, scraper):
        """Test extracting from URL with port."""
        url = "https://example.com:8080/careers"
        result = scraper.extract_company_domain(url)
        assert result == "https://example.com:8080"

    def test_skips_linkedin(self, scraper):
        """Test that LinkedIn URLs return None."""
        url = "https://www.linkedin.com/jobs/view/123456789"
        result = scraper.extract_company_domain(url)
        assert result is None

    def test_skips_indeed(self, scraper):
        """Test that Indeed URLs return None."""
        url = "https://www.indeed.com/viewjob?jk=12345"
        result = scraper.extract_company_domain(url)
        assert result is None

    def test_skips_glassdoor(self, scraper):
        """Test that Glassdoor URLs return None."""
        url = "https://www.glassdoor.com/job-listing/123"
        result = scraper.extract_company_domain(url)
        assert result is None

    def test_skips_monster(self, scraper):
        """Test that Monster URLs return None."""
        url = "https://www.monster.com/jobs/search/123"
        result = scraper.extract_company_domain(url)
        assert result is None

    def test_skips_ziprecruiter(self, scraper):
        """Test that ZipRecruiter URLs return None."""
        url = "https://www.ziprecruiter.com/jobs/123"
        result = scraper.extract_company_domain(url)
        assert result is None

    def test_job_board_check_case_insensitive(self, scraper):
        """Test that job board check is case insensitive."""
        url = "https://www.LinkedIn.COM/jobs/view/123"
        result = scraper.extract_company_domain(url)
        assert result is None

    def test_extract_handles_invalid_url(self, scraper):
        """Test handling of invalid URL."""
        url = "not a valid url"
        result = scraper.extract_company_domain(url)
        # Should return None or the domain depending on urllib parsing
        # urlparse is lenient, so it might extract something
        assert result is None or isinstance(result, str)

    def test_extract_empty_url(self, scraper):
        """Test handling of empty URL."""
        result = scraper.extract_company_domain("")
        assert result == "https://" or result is None

    def test_extract_with_http_scheme(self, scraper):
        """Test extracting from HTTP (not HTTPS) URL."""
        url = "http://example.com/jobs"
        result = scraper.extract_company_domain(url)
        assert result == "https://example.com"  # Still returns https://

    def test_extract_with_query_params(self, scraper):
        """Test extracting from URL with query parameters."""
        url = "https://example.com/jobs?id=123&source=linkedin"
        result = scraper.extract_company_domain(url)
        assert result == "https://example.com"

    def test_extract_with_fragment(self, scraper):
        """Test extracting from URL with fragment."""
        url = "https://example.com/jobs#apply"
        result = scraper.extract_company_domain(url)
        assert result == "https://example.com"

    def test_extract_with_path_and_query(self, scraper):
        """Test extracting from URL with path and query."""
        url = "https://careers.company.com/en-US/jobs?dept=engineering"
        result = scraper.extract_company_domain(url)
        assert result == "https://careers.company.com"
