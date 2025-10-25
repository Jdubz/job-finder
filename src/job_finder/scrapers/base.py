"""Base scraper class for all job site scrapers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseScraper(ABC):
    """Abstract base class for job scrapers.

    Standard job dictionary structure returned by scrapers:
    {
        # REQUIRED FIELDS (must be present for all jobs)
        "title": str,              # Job title/role
        "company": str,            # Company name
        "company_website": str,    # Company website URL
        "location": str,           # Job location
        "description": str,        # Full job description
        "url": str,                # Job posting URL (unique identifier)

        # OPTIONAL FIELDS (may be absent if not available on job page)
        "posted_date": str,        # Job posting date (None if not found)
        "salary": str,             # Salary range (None if not listed)
        "company_info": str,       # Company about/culture (fetched later, not from scraper)
    }

    REMOVED FIELDS:
    - "keywords": Previously used for scraper metadata. Now removed.
      ATS keywords are stored in resumeIntakeData.atsKeywords (AI-generated only).
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the scraper with configuration."""
        self.config = config

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape job postings from the site.

        Returns:
            List of job posting dictionaries with standardized fields.
        """
        pass

    @abstractmethod
    def parse_job(self, element: Any) -> Optional[Dict[str, Any]]:
        """
        Parse a single job posting element.

        Args:
            element: Raw job posting element from the page.

        Returns:
            Standardized job posting dictionary with REQUIRED fields:
            - title, company, company_website, location, description, url

            OPTIONAL fields (only include if available):
            - posted_date, salary

            Returns None if parsing fails or required fields are missing.
        """
        pass
