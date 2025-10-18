"""Greenhouse ATS scraper for job postings.

Greenhouse is a popular ATS (Applicant Tracking System) used by many companies.
This scraper uses their public API to fetch job postings.

API Documentation: https://developers.greenhouse.io/job-board.html
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from job_finder.utils.date_utils import parse_job_date

from .base import BaseScraper
from .text_sanitizer import sanitize_company_name, sanitize_html_description, sanitize_title

logger = logging.getLogger(__name__)


class GreenhouseScraper(BaseScraper):
    """Scraper for Greenhouse-powered career pages.

    Usage:
        config = {
            'board_token': 'deepgram',  # Company's Greenhouse board token
            'name': 'Deepgram Careers',
            'company_website': 'https://deepgram.com'
        }
        scraper = GreenhouseScraper(config)
        jobs = scraper.scrape()
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize Greenhouse scraper.

        Args:
            config: Configuration dict with:
                - board_token (str): Company's Greenhouse board token
                - name (str): Company name
                - company_website (str, optional): Company website URL
        """
        super().__init__(config)
        self.board_token = config.get("board_token")
        self.company_name = config.get("name", "Unknown")
        self.company_website = config.get("company_website", "")
        self.base_url = "https://boards-api.greenhouse.io/v1/boards"

        if not self.board_token:
            raise ValueError("board_token is required for Greenhouse scraper")

    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape jobs from Greenhouse API.

        Returns:
            List of standardized job dictionaries.
        """
        jobs = []

        try:
            # Fetch all jobs from the board
            url = f"{self.base_url}/{self.board_token}/jobs"
            params = {"content": "true"}  # Include job content

            logger.info(f"Fetching jobs from Greenhouse: {self.company_name}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            job_list = data.get("jobs", [])

            logger.info(f"Found {len(job_list)} jobs from {self.company_name}")

            for job_data in job_list:
                try:
                    job = self.parse_job(job_data)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Failed to parse job: {e}")
                    continue

        except requests.RequestException as e:
            logger.error(f"Failed to fetch jobs from Greenhouse ({self.company_name}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error scraping Greenhouse ({self.company_name}): {e}")

        return jobs

    def parse_job(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a Greenhouse job posting.

        Args:
            job_data: Raw job data from Greenhouse API.

        Returns:
            Standardized job dictionary or None if parsing fails.
        """
        try:
            # Extract location
            location = self._extract_location(job_data)

            # Extract departments/tags
            departments = [dept.get("name", "") for dept in job_data.get("departments", [])]

            # Build job URL
            absolute_url = job_data.get("absolute_url", "")

            # Extract description - combine content fields
            description = self._extract_description(job_data)

            # Parse posted date
            posted_date_str = ""
            posted_date_raw = job_data.get("updated_at") or job_data.get("created_at")
            if posted_date_raw:
                parsed_date = parse_job_date(posted_date_raw)
                if parsed_date:
                    posted_date_str = parsed_date.isoformat()
                else:
                    posted_date_str = posted_date_raw

            # Sanitize all text fields
            title_clean = sanitize_title(job_data.get("title", "Unknown"))
            company_clean = sanitize_company_name(self.company_name)
            description_clean = sanitize_html_description(description)

            job = {
                "title": title_clean,
                "company": company_clean,
                "company_website": self.company_website,
                "location": location,
                "description": description_clean,
                "url": absolute_url,
            }

            # Add optional fields only if present
            if posted_date_str:
                job["posted_date"] = posted_date_str  # ISO format datetime string
            # Note: Greenhouse API typically doesn't provide salary or company info
            # Note: Department metadata previously stored in keywords is now removed.
            #       ATS keywords are generated by AI analysis only.

            return job

        except Exception as e:
            logger.warning(f"Failed to parse Greenhouse job: {e}")
            return None

    def _extract_location(self, job_data: Dict[str, Any]) -> str:
        """Extract location from job data.

        Args:
            job_data: Raw job data.

        Returns:
            Location string.
        """
        location_obj = job_data.get("location", {})

        if isinstance(location_obj, dict):
            # Get location name
            location_name = location_obj.get("name", "")
            return location_name or "Unknown"

        return "Unknown"

    def _extract_description(self, job_data: Dict[str, Any]) -> str:
        """Extract and combine description content.

        Args:
            job_data: Raw job data.

        Returns:
            Combined description text.
        """
        content = job_data.get("content", "")

        # If content is empty, try to combine other fields
        if not content:
            parts = []

            # Add title and location
            title = job_data.get("title", "")
            location = self._extract_location(job_data)
            if title:
                parts.append(f"Position: {title}")
            if location:
                parts.append(f"Location: {location}")

            # Add departments
            departments = [dept.get("name", "") for dept in job_data.get("departments", [])]
            if departments:
                parts.append(f"Departments: {', '.join(departments)}")

            content = "\n\n".join(parts)

        return content or "No description available"


def create_scraper_for_company(
    company_name: str, board_token: str, company_website: str = ""
) -> GreenhouseScraper:
    """Helper function to create a Greenhouse scraper for a specific company.

    Args:
        company_name: Name of the company (e.g., "Deepgram")
        board_token: Company's Greenhouse board token
        company_website: Company website URL

    Returns:
        Configured GreenhouseScraper instance

    Example:
        >>> scraper = create_scraper_for_company("Deepgram", "deepgram", "https://deepgram.com")
        >>> jobs = scraper.scrape()
    """
    config = {"board_token": board_token, "name": company_name, "company_website": company_website}
    return GreenhouseScraper(config)
