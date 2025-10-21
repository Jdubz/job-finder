"""Tests for deduplication cache."""

import time

import pytest

from job_finder.utils.dedup_cache import DuplicationCache


class TestDuplicationCache:
    """Test deduplication cache functionality."""

    def test_init_default_ttl(self):
        """Test cache initialization with default TTL."""
        cache = DuplicationCache()
        assert cache.ttl == 300
        assert cache.hits == 0
        assert cache.misses == 0
        assert len(cache.cache) == 0

    def test_init_custom_ttl(self):
        """Test cache initialization with custom TTL."""
        cache = DuplicationCache(ttl_seconds=600)
        assert cache.ttl == 600

    def test_check_miss_not_in_cache(self):
        """Test cache miss when URL not in cache."""
        cache = DuplicationCache()
        result = cache.check("https://example.com/job/123")
        assert result is None
        assert cache.misses == 1
        assert cache.hits == 0

    def test_set_and_check_hit(self):
        """Test setting and checking cache entry."""
        cache = DuplicationCache()
        url = "https://example.com/job/123"

        # Set cache entry
        cache.set(url, True)
        assert len(cache.cache) == 1

        # Check cache hit
        result = cache.check(url)
        assert result is True
        assert cache.hits == 1
        assert cache.misses == 0

    def test_set_false_value(self):
        """Test setting and checking False value."""
        cache = DuplicationCache()
        url = "https://example.com/job/123"

        cache.set(url, False)
        result = cache.check(url)
        assert result is False
        assert cache.hits == 1

    def test_url_normalization(self):
        """Test that URLs are normalized for cache lookup."""
        cache = DuplicationCache()

        # Set with one version of URL
        cache.set("https://example.com/job/123?utm_source=linkedin", True)

        # Check with normalized version
        result = cache.check("https://example.com/job/123")
        assert result is True
        assert cache.hits == 1

    def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        cache = DuplicationCache(ttl_seconds=1)  # 1 second TTL
        url = "https://example.com/job/123"

        # Set cache entry
        cache.set(url, True)
        assert len(cache.cache) == 1

        # Immediate check should hit
        result = cache.check(url)
        assert result is True
        assert cache.hits == 1

        # Wait for expiration
        time.sleep(1.1)

        # Check should miss and remove expired entry
        result = cache.check(url)
        assert result is None
        assert cache.misses == 1
        assert len(cache.cache) == 0

    def test_set_many(self):
        """Test setting multiple URLs at once."""
        cache = DuplicationCache()
        results = {
            "https://example.com/job/1": True,
            "https://example.com/job/2": False,
            "https://example.com/job/3": True,
        }

        cache.set_many(results)
        assert len(cache.cache) == 3

        # Verify all entries
        assert cache.check("https://example.com/job/1") is True
        assert cache.check("https://example.com/job/2") is False
        assert cache.check("https://example.com/job/3") is True
        assert cache.hits == 3

    def test_clear(self):
        """Test clearing all cache entries."""
        cache = DuplicationCache()

        # Add some entries
        cache.set("https://example.com/job/1", True)
        cache.set("https://example.com/job/2", False)
        assert len(cache.cache) == 2

        # Clear cache
        cache.clear()
        assert len(cache.cache) == 0

        # Verify entries are gone
        assert cache.check("https://example.com/job/1") is None
        assert cache.check("https://example.com/job/2") is None

    def test_get_stats(self):
        """Test getting cache statistics."""
        cache = DuplicationCache(ttl_seconds=300)

        # Add some entries and do some checks
        cache.set("https://example.com/job/1", True)
        cache.set("https://example.com/job/2", False)

        cache.check("https://example.com/job/1")  # hit
        cache.check("https://example.com/job/2")  # hit
        cache.check("https://example.com/job/3")  # miss

        stats = cache.get_stats()

        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total_checks"] == 3
        assert stats["hit_rate_percent"] == pytest.approx(66.67, rel=0.01)
        assert stats["entries_in_cache"] == 2
        assert stats["ttl_seconds"] == 300

    def test_get_stats_no_checks(self):
        """Test stats with no checks performed."""
        cache = DuplicationCache()
        stats = cache.get_stats()

        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_checks"] == 0
        assert stats["hit_rate_percent"] == 0
        assert stats["entries_in_cache"] == 0

    def test_repr(self):
        """Test string representation."""
        cache = DuplicationCache()
        cache.set("https://example.com/job/1", True)
        cache.check("https://example.com/job/1")  # hit
        cache.check("https://example.com/job/2")  # miss

        repr_str = repr(cache)

        assert "DuplicationCache" in repr_str
        assert "entries=1" in repr_str
        assert "hits=1" in repr_str
        assert "misses=1" in repr_str
        assert "50.0%" in repr_str

    def test_multiple_sets_same_url(self):
        """Test setting same URL multiple times updates the entry."""
        cache = DuplicationCache()
        url = "https://example.com/job/123"

        # Set to True
        cache.set(url, True)
        assert cache.check(url) is True

        # Set to False (update)
        cache.set(url, False)
        assert cache.check(url) is False

        # Should still be only 1 entry
        assert len(cache.cache) == 1

    def test_case_sensitive_domains(self):
        """Test that domain casing is handled correctly."""
        cache = DuplicationCache()

        # URLs with different domain casing should normalize to same entry
        cache.set("https://EXAMPLE.com/job/123", True)
        result = cache.check("https://example.com/job/123")
        assert result is True

    def test_trailing_slash_normalization(self):
        """Test that trailing slashes are normalized."""
        cache = DuplicationCache()

        cache.set("https://example.com/job/123/", True)
        result = cache.check("https://example.com/job/123")
        assert result is True

    def test_high_hit_rate_scenario(self):
        """Test scenario with high hit rate (repeated checks)."""
        cache = DuplicationCache()

        # Set some URLs
        urls = [f"https://example.com/job/{i}" for i in range(10)]
        for url in urls:
            cache.set(url, True)

        # Check each URL multiple times (should hit)
        for _ in range(5):
            for url in urls:
                result = cache.check(url)
                assert result is True

        stats = cache.get_stats()
        assert stats["hits"] == 50
        assert stats["misses"] == 0
        assert stats["hit_rate_percent"] == 100.0

    def test_cache_with_special_characters(self):
        """Test cache with URLs containing special characters."""
        cache = DuplicationCache()
        url = "https://example.com/job/test-job?param=value&other=123"

        cache.set(url, True)
        result = cache.check(url)
        assert result is True

    def test_empty_url_handling(self):
        """Test cache behavior with empty URLs."""
        cache = DuplicationCache()

        # normalize_url should handle empty string
        cache.set("", False)
        result = cache.check("")
        assert result is False
