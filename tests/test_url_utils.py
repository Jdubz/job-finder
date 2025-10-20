"""Tests for URL normalization utility."""

from job_finder.utils.url_utils import (
    normalize_url,
    normalize_job_url,
    get_url_hash,
    urls_are_equivalent,
)


class TestNormalizeUrl:
    """Test URL normalization."""

    def test_normalize_removes_trailing_slash(self):
        """Test that trailing slashes are removed."""
        url1 = "https://example.com/job/123"
        url2 = "https://example.com/job/123/"
        assert normalize_url(url1) == normalize_url(url2)

    def test_normalize_lowercase_domain(self):
        """Test that domain is converted to lowercase."""
        url1 = "https://example.com/job/123"
        url2 = "https://EXAMPLE.COM/job/123"
        assert normalize_url(url1) == normalize_url(url2)

    def test_normalize_removes_tracking_params(self):
        """Test that tracking parameters are removed."""
        url1 = "https://example.com/job/123"
        url2 = "https://example.com/job/123?utm_source=google&utm_campaign=search"
        assert normalize_url(url1) == normalize_url(url2)

    def test_normalize_removes_fbclid(self):
        """Test that fbclid is removed."""
        url1 = "https://example.com/job/123"
        url2 = "https://example.com/job/123?fbclid=abc123"
        assert normalize_url(url1) == normalize_url(url2)

    def test_normalize_sorts_params(self):
        """Test that query parameters are sorted."""
        url1 = "https://example.com/job?foo=1&bar=2"
        url2 = "https://example.com/job?bar=2&foo=1"
        assert normalize_url(url1) == normalize_url(url2)

    def test_normalize_removes_fragment(self):
        """Test that fragments are removed."""
        url1 = "https://example.com/job/123"
        url2 = "https://example.com/job/123#section"
        assert normalize_url(url1) == normalize_url(url2)

    def test_normalize_keeps_important_params(self):
        """Test that important params are kept."""
        url = "https://example.com/job?id=123&foo=1"
        normalized = normalize_url(url)
        assert "id=123" in normalized
        assert "foo=1" in normalized

    def test_normalize_empty_string(self):
        """Test that empty strings are handled."""
        assert normalize_url("") == ""

    def test_normalize_invalid_url(self):
        """Test that invalid URLs are handled gracefully."""
        # Should return original URL if parsing fails
        result = normalize_url("not a url")
        assert result is not None


class TestGetUrlHash:
    """Test URL hash generation."""

    def test_equivalent_urls_have_same_hash(self):
        """Test that equivalent URLs produce the same hash."""
        url1 = "https://example.com/job/123"
        url2 = "https://example.com/job/123/"
        assert get_url_hash(url1) == get_url_hash(url2)

    def test_different_urls_have_different_hashes(self):
        """Test that different URLs produce different hashes."""
        url1 = "https://example.com/job/123"
        url2 = "https://example.com/job/456"
        assert get_url_hash(url1) != get_url_hash(url2)

    def test_hash_is_deterministic(self):
        """Test that hashing is deterministic."""
        url = "https://example.com/job/123"
        hash1 = get_url_hash(url)
        hash2 = get_url_hash(url)
        assert hash1 == hash2


class TestUrlsAreEquivalent:
    """Test URL equivalence checking."""

    def test_equivalent_with_trailing_slash(self):
        """Test equivalence with trailing slash."""
        assert urls_are_equivalent("https://example.com/job/123", "https://example.com/job/123/")

    def test_equivalent_with_tracking_params(self):
        """Test equivalence with tracking parameters."""
        assert urls_are_equivalent(
            "https://example.com/job/123",
            "https://example.com/job/123?utm_source=google",
        )

    def test_equivalent_case_insensitive(self):
        """Test equivalence is case insensitive."""
        assert urls_are_equivalent("https://example.com/job/123", "https://EXAMPLE.COM/job/123")

    def test_not_equivalent_different_urls(self):
        """Test non-equivalent URLs."""
        assert not urls_are_equivalent("https://example.com/job/123", "https://example.com/job/456")

    def test_complex_equivalence(self):
        """Test complex equivalence with multiple differences."""
        url1 = "https://example.com/job/123?id=456&search=dev"
        url2 = "https://EXAMPLE.COM/job/123/?search=dev&id=456&utm_source=test&utm_campaign=camp"
        assert urls_are_equivalent(url1, url2)


class TestNormalizeJobUrl:
    """Test job-specific URL normalization."""

    def test_normalize_job_url_is_alias(self):
        """Test that normalize_job_url is an alias for normalize_url."""
        url = "https://example.com/jobs/123?utm_source=linkedin"
        assert normalize_job_url(url) == normalize_url(url)

    def test_normalize_greenhouse_url(self):
        """Test normalization of Greenhouse job URLs."""
        url1 = "https://boards.greenhouse.io/company/jobs/123?t=abc123"
        url2 = "https://boards.greenhouse.io/company/jobs/123"
        assert normalize_job_url(url1) == normalize_job_url(url2)

    def test_normalize_workday_url(self):
        """Test normalization of Workday job URLs."""
        url1 = "https://example.myworkdayjobs.com/en-US/Careers/job/Software-Engineer_123/"
        url2 = "https://example.myworkdayjobs.com/en-US/Careers/job/Software-Engineer_123"
        assert normalize_job_url(url1) == normalize_job_url(url2)

    def test_normalize_with_ref_param(self):
        """Test removal of ref tracking parameter."""
        url1 = "https://example.com/jobs/123?ref=social"
        url2 = "https://example.com/jobs/123"
        assert normalize_job_url(url1) == normalize_job_url(url2)

    def test_normalize_preserves_job_params(self):
        """Test that job-specific params are preserved."""
        url = "https://example.com/jobs?category=engineering&location=remote"
        normalized = normalize_job_url(url)
        assert "category=engineering" in normalized
        assert "location=remote" in normalized
        # Should be sorted alphabetically
        assert normalized.index("category") < normalized.index("location")
