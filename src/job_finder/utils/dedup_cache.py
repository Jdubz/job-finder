"""Cache for deduplication checks to avoid repeated Firestore queries."""

import logging
import time
from typing import Any, Dict, Optional, Tuple

from job_finder.utils.url_utils import normalize_url

logger = logging.getLogger(__name__)


class DuplicationCache:
    """
    Cache for deduplication check results.

    Stores recent dedup lookups with TTL to avoid repeated Firestore queries
    for the same URLs within a short time window.

    This is particularly useful during batch job imports where many jobs from
    the same scrape operation might check the same set of URLs.

    Example:
        ```python
        cache = DuplicationCache(ttl_seconds=300)  # 5 minute TTL

        # First check hits Firestore
        exists = cache.check("https://example.com/job/123")  # None (not cached)

        # Store result
        cache.set("https://example.com/job/123", True)

        # Subsequent checks hit cache
        exists = cache.check("https://example.com/job/123")  # True (from cache)
        ```
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize deduplication cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default: 300/5 minutes)
        """
        self.cache: Dict[str, Tuple[bool, float]] = {}  # {normalized_url: (exists, timestamp)}
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0

    def check(self, url: str) -> Optional[bool]:
        """
        Check cache for URL existence result.

        Returns cached result if entry exists and is still within TTL.

        Args:
            url: URL to check

        Returns:
            True if URL exists in cache and is current
            False if URL exists in cache and is current but was not found
            None if URL not in cache or cache entry expired
        """
        normalized = normalize_url(url)

        if normalized not in self.cache:
            self.misses += 1
            return None

        exists, timestamp = self.cache[normalized]

        # Check if cache entry is still valid
        if time.time() - timestamp > self.ttl:
            # Expired
            del self.cache[normalized]
            self.misses += 1
            return None

        # Cache hit
        self.hits += 1
        logger.debug(f"Cache hit for URL: {normalized}")
        return exists

    def set(self, url: str, exists: bool) -> None:
        """
        Store URL existence result in cache.

        Args:
            url: URL to cache
            exists: Whether URL exists in storage
        """
        normalized = normalize_url(url)
        self.cache[normalized] = (exists, time.time())
        logger.debug(f"Cached URL: {normalized} (exists={exists})")

    def set_many(self, results: Dict[str, bool]) -> None:
        """
        Store multiple URL results at once.

        Args:
            results: Dictionary mapping URLs to existence booleans
        """
        for url, exists in results.items():
            self.set(url, exists)

    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cleared {count} cache entries")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit count, miss count, hit rate, and entry count
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_checks": total,
            "hit_rate_percent": hit_rate,
            "entries_in_cache": len(self.cache),
            "ttl_seconds": self.ttl,
        }

    def __repr__(self) -> str:
        """Return string representation with stats."""
        stats = self.get_stats()
        return (
            f"DuplicationCache(entries={stats['entries_in_cache']}, "
            f"hits={stats['hits']}, misses={stats['misses']}, "
            f"hit_rate={stats['hit_rate_percent']:.1f}%)"
        )
