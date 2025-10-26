"""Detect job source type from URL patterns."""

import logging
import re
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

from job_finder.job_queue.models import SourceTypeHint

logger = logging.getLogger(__name__)


class SourceTypeDetector:
    """
    Detect source type from URL patterns.

    Recognizes:
    - Greenhouse boards (boards.greenhouse.io/{token})
    - Workday boards (*.wd*.myworkdayjobs.com/{company})
    - RSS feeds (*.xml, */feed, */rss)
    - Generic HTML (everything else)
    """

    # URL patterns for known source types
    GREENHOUSE_PATTERN = re.compile(r"boards\.greenhouse\.io/([a-zA-Z0-9\-_]+)", re.IGNORECASE)
    WORKDAY_PATTERN = re.compile(
        r"([a-zA-Z0-9\-_]+)\.wd\d+\.myworkdayjobs\.com/([a-zA-Z0-9\-_]+)",
        re.IGNORECASE,
    )
    RSS_PATTERNS = [
        re.compile(r"\.xml$", re.IGNORECASE),
        re.compile(r"/feed/?$", re.IGNORECASE),
        re.compile(r"/rss/?$", re.IGNORECASE),
        re.compile(r"\.rss$", re.IGNORECASE),
    ]

    @classmethod
    def detect(
        cls, url: str, type_hint: Optional[SourceTypeHint] = None
    ) -> Tuple[str, Dict[str, str]]:
        """
        Detect source type and extract configuration from URL.

        Args:
            url: URL to analyze
            type_hint: Optional hint about expected type (user override)

        Returns:
            Tuple of (source_type, config_dict)
            - source_type: "greenhouse" | "workday" | "rss" | "generic"
            - config_dict: Extracted configuration specific to source type

        Examples:
            >>> detect("https://boards.greenhouse.io/stripe")
            ("greenhouse", {"board_token": "stripe"})

            >>> detect("https://company.wd1.myworkdayjobs.com/External")
            ("workday", {"company_id": "company", "base_url": "https://..."})

            >>> detect("https://example.com/feed")
            ("rss", {"url": "https://example.com/feed"})

            >>> detect("https://example.com/careers")
            ("generic", {"base_url": "https://example.com/careers"})
        """
        # Respect explicit type hint
        if type_hint and type_hint != SourceTypeHint.AUTO:
            logger.info(f"Using type hint: {type_hint} for {url}")
            return cls._detect_with_hint(url, type_hint)

        # Try pattern matching
        source_type, config = cls._detect_from_pattern(url)

        logger.info(f"Detected source type '{source_type}' for URL: {url}")
        return source_type, config

    @classmethod
    def _detect_from_pattern(cls, url: str) -> Tuple[str, Dict[str, str]]:
        """Detect source type from URL pattern matching."""

        # Check for Greenhouse
        greenhouse_match = cls.GREENHOUSE_PATTERN.search(url)
        if greenhouse_match:
            board_token = greenhouse_match.group(1)
            return "greenhouse", {"board_token": board_token}

        # Check for Workday
        workday_match = cls.WORKDAY_PATTERN.search(url)
        if workday_match:
            company_id = workday_match.group(1)
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            return "workday", {
                "company_id": company_id,
                "base_url": base_url,
            }

        # Check for RSS
        for rss_pattern in cls.RSS_PATTERNS:
            if rss_pattern.search(url):
                return "rss", {"url": url}

        # Default to generic HTML scraping
        return "generic", {"base_url": url}

    @classmethod
    def _detect_with_hint(cls, url: str, type_hint: SourceTypeHint) -> Tuple[str, Dict[str, str]]:
        """Use type hint to guide detection."""

        if type_hint == SourceTypeHint.GREENHOUSE:
            # Try to extract board token from URL
            match = cls.GREENHOUSE_PATTERN.search(url)
            if match:
                return "greenhouse", {"board_token": match.group(1)}
            # Fallback: assume last path segment is token
            parsed = urlparse(url)
            token = parsed.path.strip("/").split("/")[-1]
            return "greenhouse", {"board_token": token}

        elif type_hint == SourceTypeHint.WORKDAY:
            match = cls.WORKDAY_PATTERN.search(url)
            if match:
                company_id = match.group(1)
                parsed = urlparse(url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                return "workday", {"company_id": company_id, "base_url": base_url}
            # Fallback: use domain as company_id
            parsed = urlparse(url)
            company_id = parsed.netloc.split(".")[0]
            return "workday", {
                "company_id": company_id,
                "base_url": f"{parsed.scheme}://{parsed.netloc}",
            }

        elif type_hint == SourceTypeHint.RSS:
            return "rss", {"url": url}

        else:  # GENERIC
            return "generic", {"base_url": url}

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        """
        Check if URL is valid and accessible.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid, False otherwise
        """
        try:
            parsed = urlparse(url)
            return all([parsed.scheme in ("http", "https"), parsed.netloc])
        except Exception as e:
            logger.error(f"Invalid URL: {url} - {e}")
            return False

    @classmethod
    def get_company_name_from_url(cls, url: str) -> Optional[str]:
        """
        Extract company name from URL if possible.

        Args:
            url: URL to analyze

        Returns:
            Company name or None

        Examples:
            >>> get_company_name_from_url("https://boards.greenhouse.io/stripe")
            "Stripe"

            >>> get_company_name_from_url("https://netflix.wd1.myworkdayjobs.com/External")
            "Netflix"

            >>> get_company_name_from_url("https://example.com/careers")
            "Example"
        """
        # Greenhouse: Use board token
        greenhouse_match = cls.GREENHOUSE_PATTERN.search(url)
        if greenhouse_match:
            token = greenhouse_match.group(1)
            # Convert "stripe" → "Stripe", "data-dog" → "DataDog"
            return cls._token_to_company_name(token)

        # Workday: Use company ID from subdomain
        workday_match = cls.WORKDAY_PATTERN.search(url)
        if workday_match:
            company_id = workday_match.group(1)
            return cls._token_to_company_name(company_id)

        # Generic: Use domain name
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www. and TLD
            name = domain.replace("www.", "").split(".")[0]
            return cls._token_to_company_name(name)
        except Exception:
            return None

    @staticmethod
    def _token_to_company_name(token: str) -> str:
        """
        Convert URL token to company name.

        Examples:
            >>> _token_to_company_name("stripe")
            "Stripe"
            >>> _token_to_company_name("data-dog")
            "DataDog"
            >>> _token_to_company_name("openai-api")
            "OpenAI API"
        """
        # Split on dashes/underscores
        parts = re.split(r"[-_]", token)
        # Capitalize each part
        capitalized = [part.capitalize() for part in parts if part]
        # Join with spaces (or no space for camelCase effect)
        # Using no space for DataDog style
        return "".join(capitalized) if len(capitalized) <= 2 else " ".join(capitalized)
