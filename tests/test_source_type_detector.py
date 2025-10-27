"""Tests for source type detector utility."""

from job_finder.job_queue.models import SourceTypeHint
from job_finder.utils.source_type_detector import SourceTypeDetector


class TestDetectFromPattern:
    """Test pattern-based source type detection."""

    def test_detects_greenhouse_from_url(self):
        """Should detect Greenhouse from boards.greenhouse.io URL."""
        url = "https://boards.greenhouse.io/stripe"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "greenhouse"
        assert config["board_token"] == "stripe"

    def test_detects_greenhouse_with_subdomain(self):
        """Should detect Greenhouse with different subdomain patterns."""
        url = "https://boards.greenhouse.io/netflix/jobs/123"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "greenhouse"
        assert config["board_token"] == "netflix"

    def test_detects_greenhouse_with_dashes(self):
        """Should handle Greenhouse board tokens with dashes."""
        url = "https://boards.greenhouse.io/data-dog"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "greenhouse"
        assert config["board_token"] == "data-dog"

    def test_detects_workday_from_url(self):
        """Should detect Workday from myworkdayjobs.com URL."""
        url = "https://netflix.wd1.myworkdayjobs.com/External"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "workday"
        assert config["company_id"] == "netflix"
        assert "https://netflix.wd1.myworkdayjobs.com" in config["base_url"]

    def test_detects_workday_different_wd_number(self):
        """Should detect Workday with different wd numbers."""
        url = "https://stripe.wd5.myworkdayjobs.com/Stripe_Careers"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "workday"
        assert config["company_id"] == "stripe"

    def test_detects_rss_from_xml_extension(self):
        """Should detect RSS from .xml extension."""
        url = "https://example.com/jobs.xml"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "rss"
        assert config["url"] == url

    def test_detects_rss_from_feed_path(self):
        """Should detect RSS from /feed path."""
        url = "https://example.com/jobs/feed"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "rss"
        assert config["url"] == url

    def test_detects_rss_from_rss_path(self):
        """Should detect RSS from /rss path."""
        url = "https://example.com/rss"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "rss"
        assert config["url"] == url

    def test_detects_rss_from_rss_extension(self):
        """Should detect RSS from .rss extension."""
        url = "https://example.com/jobs.rss"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "rss"
        assert config["url"] == url

    def test_detects_generic_for_unknown_url(self):
        """Should default to generic for unrecognized URLs."""
        url = "https://example.com/careers"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "generic"
        assert config["base_url"] == url

    def test_detects_generic_for_career_pages(self):
        """Should detect generic for common career page URLs."""
        urls = [
            "https://example.com/careers",
            "https://example.com/jobs",
            "https://example.com/work-with-us",
        ]

        for url in urls:
            source_type, config = SourceTypeDetector.detect(url)
            assert source_type == "generic"
            assert config["base_url"] == url


class TestTypeHintOverride:
    """Test type hint override behavior."""

    def test_respects_greenhouse_hint(self):
        """Should use Greenhouse type when hint provided."""
        url = "https://custom-domain.com/jobs"
        source_type, config = SourceTypeDetector.detect(url, SourceTypeHint.GREENHOUSE)

        assert source_type == "greenhouse"
        assert "board_token" in config

    def test_respects_workday_hint(self):
        """Should use Workday type when hint provided."""
        url = "https://custom-domain.com/careers"
        source_type, config = SourceTypeDetector.detect(url, SourceTypeHint.WORKDAY)

        assert source_type == "workday"
        assert "company_id" in config
        assert "base_url" in config

    def test_respects_rss_hint(self):
        """Should use RSS type when hint provided."""
        url = "https://example.com/jobs-list"
        source_type, config = SourceTypeDetector.detect(url, SourceTypeHint.RSS)

        assert source_type == "rss"
        assert config["url"] == url

    def test_respects_generic_hint(self):
        """Should use generic type when hint provided."""
        url = "https://boards.greenhouse.io/stripe"  # Would normally be greenhouse
        source_type, config = SourceTypeDetector.detect(url, SourceTypeHint.GENERIC)

        assert source_type == "generic"
        assert config["base_url"] == url

    def test_auto_hint_uses_pattern_detection(self):
        """Should use pattern detection when hint is AUTO."""
        url = "https://boards.greenhouse.io/stripe"
        source_type, config = SourceTypeDetector.detect(url, SourceTypeHint.AUTO)

        assert source_type == "greenhouse"
        assert config["board_token"] == "stripe"


class TestURLValidation:
    """Test URL validation."""

    def test_validates_http_url(self):
        """Should accept valid HTTP URLs."""
        assert SourceTypeDetector.is_valid_url("http://example.com")

    def test_validates_https_url(self):
        """Should accept valid HTTPS URLs."""
        assert SourceTypeDetector.is_valid_url("https://example.com")

    def test_validates_url_with_path(self):
        """Should accept URLs with paths."""
        assert SourceTypeDetector.is_valid_url("https://example.com/careers/jobs")

    def test_validates_url_with_query(self):
        """Should accept URLs with query parameters."""
        assert SourceTypeDetector.is_valid_url("https://example.com?foo=bar")

    def test_rejects_url_without_scheme(self):
        """Should reject URLs without http/https scheme."""
        assert not SourceTypeDetector.is_valid_url("example.com")

    def test_rejects_url_without_domain(self):
        """Should reject URLs without domain."""
        assert not SourceTypeDetector.is_valid_url("https://")

    def test_rejects_invalid_scheme(self):
        """Should reject non-HTTP(S) schemes."""
        assert not SourceTypeDetector.is_valid_url("ftp://example.com")

    def test_rejects_empty_url(self):
        """Should reject empty URLs."""
        assert not SourceTypeDetector.is_valid_url("")

    def test_rejects_malformed_url(self):
        """Should reject malformed URLs."""
        assert not SourceTypeDetector.is_valid_url("not a url at all")


class TestCompanyNameExtraction:
    """Test company name extraction from URLs."""

    def test_extracts_from_greenhouse_board_token(self):
        """Should extract company name from Greenhouse board token."""
        url = "https://boards.greenhouse.io/stripe"
        name = SourceTypeDetector.get_company_name_from_url(url)

        assert name == "Stripe"

    def test_extracts_from_greenhouse_with_dashes(self):
        """Should convert dashed tokens to CamelCase."""
        url = "https://boards.greenhouse.io/data-dog"
        name = SourceTypeDetector.get_company_name_from_url(url)

        assert name == "DataDog"

    def test_extracts_from_greenhouse_with_multiple_dashes(self):
        """Should handle multiple dashes in token."""
        url = "https://boards.greenhouse.io/open-ai-research"
        name = SourceTypeDetector.get_company_name_from_url(url)

        assert name == "Open Ai Research"

    def test_extracts_from_workday_subdomain(self):
        """Should extract company name from Workday subdomain."""
        url = "https://netflix.wd1.myworkdayjobs.com/External"
        name = SourceTypeDetector.get_company_name_from_url(url)

        assert name == "Netflix"

    def test_extracts_from_workday_with_dashes(self):
        """Should handle dashes in Workday subdomain."""
        url = "https://meta-platforms.wd1.myworkdayjobs.com/Careers"
        name = SourceTypeDetector.get_company_name_from_url(url)

        assert name == "MetaPlatforms"

    def test_extracts_from_generic_domain(self):
        """Should extract company name from generic domain."""
        url = "https://stripe.com/careers"
        name = SourceTypeDetector.get_company_name_from_url(url)

        assert name == "Stripe"

    def test_extracts_from_domain_with_www(self):
        """Should handle www prefix."""
        url = "https://www.netflix.com/jobs"
        name = SourceTypeDetector.get_company_name_from_url(url)

        assert name == "Netflix"

    def test_returns_none_for_invalid_url(self):
        """Should return None or empty string for invalid URLs."""
        name = SourceTypeDetector.get_company_name_from_url("not a url")

        # Implementation returns empty string for invalid URLs
        assert name in (None, "")


class TestTokenToCompanyName:
    """Test token to company name conversion."""

    def test_converts_simple_token(self):
        """Should capitalize simple tokens."""
        assert SourceTypeDetector._token_to_company_name("stripe") == "Stripe"

    def test_converts_token_with_dash(self):
        """Should convert dashed tokens to CamelCase."""
        assert SourceTypeDetector._token_to_company_name("data-dog") == "DataDog"

    def test_converts_token_with_underscore(self):
        """Should convert underscored tokens to CamelCase."""
        assert SourceTypeDetector._token_to_company_name("open_ai") == "OpenAi"

    def test_converts_token_with_multiple_words(self):
        """Should handle multiple words with spaces."""
        result = SourceTypeDetector._token_to_company_name("open-ai-research")
        assert result == "Open Ai Research"

    def test_handles_empty_token(self):
        """Should handle empty token."""
        assert SourceTypeDetector._token_to_company_name("") == ""

    def test_handles_single_character(self):
        """Should handle single character tokens."""
        assert SourceTypeDetector._token_to_company_name("a") == "A"


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    def test_handles_url_with_trailing_slash(self):
        """Should handle URLs with trailing slashes."""
        url = "https://boards.greenhouse.io/stripe/"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "greenhouse"
        assert config["board_token"] == "stripe"

    def test_handles_url_with_port(self):
        """Should handle URLs with port numbers."""
        url = "https://example.com:8080/careers"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "generic"

    def test_handles_url_with_fragment(self):
        """Should handle URLs with fragments."""
        url = "https://boards.greenhouse.io/stripe#jobs"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "greenhouse"

    def test_handles_case_insensitive_detection(self):
        """Should detect patterns case-insensitively."""
        url = "https://BOARDS.GREENHOUSE.IO/STRIPE"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "greenhouse"
        assert config["board_token"] == "STRIPE"

    def test_handles_workday_with_mixed_case(self):
        """Should handle Workday URLs with mixed case."""
        url = "https://Netflix.WD1.MyWorkdayJobs.com/External"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "workday"

    def test_handles_rss_feed_with_trailing_slash(self):
        """Should detect RSS feed with trailing slash."""
        url = "https://example.com/feed/"
        source_type, config = SourceTypeDetector.detect(url)

        assert source_type == "rss"
