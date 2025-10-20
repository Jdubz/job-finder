"""Utilities for URL normalization and deduplication."""

import hashlib
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """
    Normalize URL for consistent comparison and deduplication.

    Performs the following normalizations:
    - Lower case domain and scheme
    - Remove trailing slashes (preserving single slash for domain)
    - Sort query parameters alphabetically
    - Remove tracking parameters (utm_*, fbclid, msclkid, etc)
    - Remove URL fragments
    - Decode percent-encoded characters

    Args:
        url: URL to normalize

    Returns:
        Normalized URL string

    Examples:
        >>> normalize_url("https://example.com/job/123/")
        "https://example.com/job/123"

        >>> normalize_url("https://EXAMPLE.COM/job/123?foo=1&bar=2")
        "https://example.com/job/123?bar=2&foo=1"

        >>> normalize_url("https://example.com/job/123?utm_source=google")
        "https://example.com/job/123"
    """
    if not url:
        return ""

    try:
        # Parse URL components
        parsed = urlparse(url)

        # Normalize scheme and netloc (domain) to lowercase
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path

        # Remove trailing slash from path unless it's the root
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        # Parse query parameters
        query_params = parse_qs(parsed.query, keep_blank_values=True)

        # Filter out tracking parameters
        tracking_params = {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_content",
            "utm_term",
            "fbclid",
            "msclkid",
            "gclid",
            "gclsrc",
            "dclid",
            "_ga",
            "_gid",
            "_gat",
            "ref",  # Generic referrer tracking
            "source",  # Generic source tracking
            "t",  # Greenhouse and other job board tracking tokens
        }

        filtered_params = {
            k: v for k, v in query_params.items() if k.lower() not in tracking_params
        }

        # Sort parameters alphabetically and reconstruct query string
        sorted_params = sorted(filtered_params.items())
        # Flatten the list of lists (parse_qs returns lists for each value)
        flat_params = [(k, v[0] if isinstance(v, list) and v else v) for k, v in sorted_params]
        query = urlencode(flat_params) if flat_params else ""

        # Reconstruct URL without fragment
        # Note: fragment is not included (intentionally removed for dedup purposes)
        normalized = urlunparse((scheme, netloc, path, "", query, ""))

        return normalized

    except Exception as e:
        logger.warning(f"Error normalizing URL '{url}': {e}")
        # Return original URL if normalization fails
        return url


def get_url_hash(url: str) -> str:
    """
    Get SHA256 hash of normalized URL for fast comparison.

    Args:
        url: URL to hash

    Returns:
        Hex-encoded SHA256 hash

    Examples:
        >>> hash1 = get_url_hash("https://example.com/job/123")
        >>> hash2 = get_url_hash("https://example.com/job/123/")
        >>> hash1 == hash2
        True
    """
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode()).hexdigest()


def urls_are_equivalent(url1: str, url2: str) -> bool:
    """
    Check if two URLs are equivalent after normalization.

    Args:
        url1: First URL
        url2: Second URL

    Returns:
        True if URLs normalize to the same value

    Examples:
        >>> urls_are_equivalent("https://example.com/job/123", "https://example.com/job/123/")
        True

        >>> urls_are_equivalent(
        ...     "https://example.com/job/123?utm_source=google",
        ...     "https://example.com/job/123"
        ... )
        True
    """
    return normalize_url(url1) == normalize_url(url2)


def normalize_job_url(url: str) -> str:
    """
    Normalize a job URL for duplicate detection and storage.

    This is an alias for normalize_url() with job-specific documentation.
    Used throughout the codebase to ensure consistent URL handling for job postings.

    Args:
        url: Job posting URL to normalize

    Returns:
        Normalized URL string

    Examples:
        >>> normalize_job_url("https://boards.greenhouse.io/company/jobs/123?t=abc")
        "https://boards.greenhouse.io/company/jobs/123"

        >>> normalize_job_url(
        ...     "https://example.myworkdayjobs.com/en-US/Careers/job/Software-Engineer_123/"
        ... )
        "https://example.myworkdayjobs.com/en-US/Careers/job/Software-Engineer_123"
    """
    return normalize_url(url)
