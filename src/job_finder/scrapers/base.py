"""Base scraper class for all job site scrapers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseScraper(ABC):
    """Abstract base class for job scrapers.

    Standard job dictionary structure:
    {
        "title": str,              # Job title/role
        "company": str,            # Company name
        "company_website": str,    # Company website URL
        "company_info": str,       # Company culture/mission statements (optional)
        "location": str,           # Job location
        "description": str,        # Full job description
        "url": str,                # Job posting URL
        "posted_date": str,        # When the job was posted (optional)
        "salary": str,             # Salary range (optional)
        "keywords": List[str],     # Keywords for emphasis (populated by AI)
    }
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
    def parse_job(self, element: Any) -> Dict[str, Any]:
        """
        Parse a single job posting element.

        Args:
            element: Raw job posting element from the page.

        Returns:
            Standardized job posting dictionary with required fields:
            - title, company, company_website, location, description, url
            Optional fields:
            - company_info, posted_date, salary, keywords
        """
        pass
