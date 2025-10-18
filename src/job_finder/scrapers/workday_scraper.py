"""Workday ATS scraper for job postings.

Workday is a popular enterprise ATS used by large companies like Atlassian.
This scraper uses their public JSON endpoints to fetch job postings.

Note: Workday URLs vary by company and region.
Common patterns:
- {company}.wd1.myworkdayjobs.com
- {company}.wd5.myworkdayjobs.com
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from .base import BaseScraper

logger = logging.getLogger(__name__)


class WorkdayScraper(BaseScraper):
    """Scraper for Workday-powered career pages.

    Usage:
        config = {
            'company_id': 'atlassian',
            'site_id': 'Atlassian',
            'name': 'Atlassian',
            'company_website': 'https://www.atlassian.com'
        }
        scraper = WorkdayScraper(config)
        jobs = scraper.scrape()
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize Workday scraper.

        Args:
            config: Configuration dict with:
                - company_id (str): Workday company ID (e.g., 'atlassian')
                - site_id (str): Workday site ID (e.g., 'Atlassian')
                - name (str): Company display name
                - company_website (str, optional): Company website URL
                - base_domain (str, optional): Workday domain (default: wd1.myworkdayjobs.com)
        """
        super().__init__(config)
        self.company_id = config.get("company_id")
        self.site_id = config.get("site_id")
        self.company_name = config.get("name", "Unknown")
        self.company_website = config.get("company_website", "")
        self.base_domain = config.get("base_domain", "wd1.myworkdayjobs.com")

        if not self.company_id or not self.site_id:
            raise ValueError("company_id and site_id are required for Workday scraper")

    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape jobs from Workday API.

        Returns:
            List of standardized job dictionaries.
        """
        jobs = []

        try:
            # Workday API endpoint
            # Example: https://atlassian.wd1.myworkdayjobs.com/wday/cxs/atlassian/Atlassian/jobs
            base_url = f"https://{self.company_id}.{self.base_domain}/wday/cxs/{self.company_id}/{self.site_id}/jobs"

            # Fetch jobs with pagination
            offset = 0
            limit = 20  # Workday typically uses 20 per page
            has_more = True

            logger.info(f"Fetching jobs from Workday: {self.company_name}")

            while has_more:
                params = {"limit": limit, "offset": offset}

                response = requests.get(base_url, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                job_list = data.get("jobPostings", [])

                if not job_list:
                    has_more = False
                    break

                logger.info(f"Fetched {len(job_list)} jobs (offset: {offset})")

                for job_data in job_list:
                    try:
                        job = self.parse_job(job_data)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.warning(f"Failed to parse job: {e}")
                        continue

                # Check if there are more results
                total = data.get("total", 0)
                offset += len(job_list)

                if offset >= total:
                    has_more = False

            logger.info(f"Total jobs found from {self.company_name}: {len(jobs)}")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch jobs from Workday ({self.company_name}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error scraping Workday ({self.company_name}): {e}")

        return jobs

    def parse_job(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a Workday job posting.

        Args:
            job_data: Raw job data from Workday API.

        Returns:
            Standardized job dictionary or None if parsing fails.
        """
        try:
            # Extract title
            title_obj = job_data.get("title", "")
            title = title_obj if isinstance(title_obj, str) else "Unknown"

            # Extract location
            location = self._extract_location(job_data)

            # Extract job ID and build URL
            bulletin_id = job_data.get("bulletinId", "")
            job_url = f"https://{self.company_id}.{self.base_domain}/{self.company_id}/{self.site_id}/job/{bulletin_id}"

            # Extract description
            description = self._extract_description(job_data)

            job = {
                "title": title,
                "company": self.company_name,
                "company_website": self.company_website,
                "location": location,
                "description": description,
                "url": job_url,
            }

            # Add optional fields only if present
            posted_date = job_data.get("postedOn", "")
            if posted_date:
                job["posted_date"] = posted_date
            # Note: Workday API typically doesn't provide salary or company info
            # Note: Job requisition metadata previously stored in keywords is now removed.
            #       ATS keywords are generated by AI analysis only.

            return job

        except Exception as e:
            logger.warning(f"Failed to parse Workday job: {e}")
            return None

    def _extract_location(self, job_data: Dict[str, Any]) -> str:
        """Extract location from job data.

        Args:
            job_data: Raw job data.

        Returns:
            Location string.
        """
        # Try different location fields
        location_list = job_data.get("locationsText", "")
        if location_list:
            return location_list

        # Try primary location
        primary_location = job_data.get("primaryLocation", {})
        if isinstance(primary_location, dict):
            location_name = primary_location.get("descriptor", "")
            if location_name:
                return location_name

        return "Unknown"

    def _extract_description(self, job_data: Dict[str, Any]) -> str:
        """Extract job description.

        Args:
            job_data: Raw job data.

        Returns:
            Job description text.
        """
        # Try to get job description
        job_description = job_data.get("jobDescription", "")

        if not job_description:
            # Build description from available fields
            parts = []

            title = job_data.get("title", "")
            if title:
                parts.append(f"Position: {title}")

            location = self._extract_location(job_data)
            if location:
                parts.append(f"Location: {location}")

            time_type = job_data.get("timeType", "")
            if time_type:
                parts.append(f"Employment Type: {time_type}")

            job_description = "\n\n".join(parts)

        return job_description or "No description available"


def create_scraper_for_company(
    company_name: str,
    company_id: str,
    site_id: str = None,
    company_website: str = "",
    base_domain: str = "wd1.myworkdayjobs.com",
) -> WorkdayScraper:
    """Helper function to create a Workday scraper for a specific company.

    Args:
        company_name: Name of the company (e.g., "Atlassian")
        company_id: Workday company ID (e.g., "atlassian")
        site_id: Workday site ID (defaults to company_name if not provided)
        company_website: Company website URL
        base_domain: Workday base domain (default: wd1.myworkdayjobs.com)

    Returns:
        Configured WorkdayScraper instance

    Example:
        >>> scraper = create_scraper_for_company("Atlassian", "atlassian", company_website="https://www.atlassian.com")
        >>> jobs = scraper.scrape()
    """
    if site_id is None:
        site_id = company_name

    config = {
        "company_id": company_id,
        "site_id": site_id,
        "name": company_name,
        "company_website": company_website,
        "base_domain": base_domain,
    }
    return WorkdayScraper(config)
