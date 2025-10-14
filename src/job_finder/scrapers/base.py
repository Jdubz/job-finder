"""Base scraper class for all job site scrapers."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseScraper(ABC):
    """Abstract base class for job scrapers."""

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
            Standardized job posting dictionary.
        """
        pass
