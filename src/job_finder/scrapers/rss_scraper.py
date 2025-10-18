"""RSS feed scraper for job boards."""

import logging
import re
from typing import Any, Dict, List

import feedparser

from job_finder.scrapers.base import BaseScraper
from job_finder.scrapers.text_sanitizer import (
    sanitize_company_name,
    sanitize_html_description,
    sanitize_title,
)
from job_finder.utils.date_utils import parse_job_date

logger = logging.getLogger(__name__)


class RSSJobScraper(BaseScraper):
    """Scraper for RSS job feeds."""

    def __init__(self, config: Dict[str, Any], listing_config: Dict[str, Any]):
        """
        Initialize RSS scraper.

        Args:
            config: General scraping configuration
            listing_config: RSS feed configuration from job listing
        """
        super().__init__(config)
        self.listing_config = listing_config
        self.feed_url = listing_config.get("url")

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from RSS feed.

        Returns:
            List of job dictionaries
        """
        if not self.feed_url:
            logger.error("RSS feed URL not provided")
            return []

        try:
            logger.info(f"Fetching RSS feed: {self.feed_url}")
            feed = feedparser.parse(self.feed_url)

            if feed.bozo:
                logger.warning(f"RSS feed has issues: {feed.bozo_exception}")

            jobs = []
            for entry in feed.entries:
                try:
                    job = self.parse_job(entry)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Error parsing RSS entry: {str(e)}")
                    continue

            logger.info(f"Scraped {len(jobs)} jobs from RSS feed")
            return jobs

        except Exception as e:
            logger.error(f"Error scraping RSS feed {self.feed_url}: {str(e)}")
            return []

    def parse_job(self, entry: Any) -> Dict[str, Any]:
        """
        Parse a single RSS entry into job dictionary.

        Args:
            entry: RSS feed entry from feedparser

        Returns:
            Job dictionary with standardized fields
        """
        # Get field names from config
        title_field = self.listing_config.get("title_field", "title")
        description_field = self.listing_config.get("description_field", "description")
        link_field = self.listing_config.get("link_field", "link")
        company_field = self.listing_config.get("company_field")

        # Extract basic fields
        title = getattr(entry, title_field, "")
        description = getattr(entry, description_field, "")
        url = getattr(entry, link_field, "")

        # Handle description variants
        if not description and hasattr(entry, "summary"):
            description = entry.summary
        if not description and hasattr(entry, "content"):
            description = entry.content[0].value if entry.content else ""

        # Extract company name
        company = ""
        if company_field:
            company = getattr(entry, company_field, "")

        # If company extraction is "from_title", parse from title
        if self.listing_config.get("company_extraction") == "from_title":
            company = self._extract_company_from_title(title)

        # If no company found, try to extract from description
        if not company:
            company = self._extract_company_from_description(description)

        # Extract location
        location = self._extract_location(title, description)

        # Get and parse posted date
        posted_date_str = ""
        posted_date_raw = None
        if hasattr(entry, "published"):
            posted_date_raw = entry.published
        elif hasattr(entry, "updated"):
            posted_date_raw = entry.updated

        # Parse date to datetime and convert to ISO format
        if posted_date_raw:
            parsed_date = parse_job_date(posted_date_raw)
            if parsed_date:
                posted_date_str = parsed_date.isoformat()
            else:
                # Keep raw string if parsing fails
                posted_date_str = posted_date_raw

        # Extract salary if present
        salary = self._extract_salary(title, description)

        # Sanitize all text fields
        title_clean = self._clean_title(title, company)
        title_clean = sanitize_title(title_clean)
        company_clean = sanitize_company_name(company or "Unknown")
        description_clean = sanitize_html_description(description)

        job: Dict[str, Any] = {
            "title": title_clean,
            "company": company_clean,
            "company_website": "",  # Will be populated later if available
            "location": location,
            "description": description_clean,
            "url": url,
        }

        # Add optional fields only if present
        if posted_date_str:
            job["posted_date"] = posted_date_str  # ISO format datetime string
        if salary:
            job["salary"] = salary
        # Note: ATS keywords are generated by AI analysis, not from RSS feed

        return job

    def _extract_company_from_title(self, title: str) -> str:
        """
        Extract company name from title.

        Common formats:
        - "Job Title at Company Name"
        - "Company Name: Job Title"
        - "Job Title - Company Name"
        """
        # Try "at Company" pattern
        match = re.search(r"\sat\s+([^|:]+?)(?:\s*[|:]|$)", title)
        if match:
            return match.group(1).strip()

        # Try "Company: Job" pattern
        if ":" in title:
            parts = title.split(":", 1)
            if len(parts) == 2 and len(parts[0]) < 50:  # Likely company name
                return parts[0].strip()

        # Try "Job - Company" pattern
        if " - " in title:
            parts = title.split(" - ")
            if len(parts) >= 2:
                # Last part is often the company
                return parts[-1].strip()

        return ""

    def _extract_company_from_description(self, description: str) -> str:
        """Extract company name from job description."""
        # Look for common patterns like "We are X" or "X is hiring"
        patterns = [
            r"(?:We are|Join)\s+([A-Z][a-zA-Z0-9\s&]+?)(?:\s+is|,|\.|!)",
            r"([A-Z][a-zA-Z0-9\s&]+?)\s+is (?:hiring|looking|seeking)",
        ]

        for pattern in patterns:
            match = re.search(pattern, description[:500])  # Check first 500 chars
            if match:
                company = match.group(1).strip()
                if 3 < len(company) < 50:  # Reasonable company name length
                    return company

        return ""

    def _clean_title(self, title: str, company: str) -> str:
        """Clean job title by removing company name and location."""
        # Remove company name from title
        if company and company in title:
            title = title.replace(f" at {company}", "")
            title = title.replace(f"{company}:", "")
            title = title.replace(f" - {company}", "")
            title = title.replace(f"{company} -", "")

        # Remove common location indicators
        title = re.sub(
            r"\s*[|(]\s*(?:Remote|USA|US|United States).*$", "", title, flags=re.IGNORECASE
        )

        return title.strip()

    def _extract_location(self, title: str, description: str) -> str:
        """Extract location from title or description."""
        # Check for "Remote" in title
        if re.search(r"\b(?:Remote|Anywhere)\b", title, re.IGNORECASE):
            return "Remote"

        # Check for location patterns in title
        location_match = re.search(r"[|(]\s*([^|()]+(?:Remote|USA|US|United States)[^|()]*)", title)
        if location_match:
            return location_match.group(1).strip()

        # Check for location in first part of description
        remote_match = re.search(
            r"\b(?:Remote|Work from (?:home|anywhere))\b", description[:500], re.IGNORECASE
        )
        if remote_match:
            return "Remote"

        return "Unknown"

    def _extract_salary(self, title: str, description: str) -> str:
        """Extract salary information if present."""
        text = f"{title} {description[:1000]}"

        # Common salary patterns
        patterns = [
            r"\$[\d,]+k?\s*-\s*\$[\d,]+k?",
            r"\$[\d,]+k?(?:\s*-\s*\$?[\d,]+k?)?(?:\s*/\s*(?:year|yr|hour|hr))?",
            r"[\d,]+k\s*-\s*[\d,]+k",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)

        return ""
