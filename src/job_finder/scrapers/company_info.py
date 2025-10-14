"""Utility to scrape company information from company websites."""
import logging
import re
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class CompanyInfoScraper:
    """Scrapes company culture and mission statements from company websites."""

    # Common paths where companies put about/culture pages
    CULTURE_PATHS = [
        "/about",
        "/about-us",
        "/culture",
        "/careers/culture",
        "/careers",
        "/mission",
        "/values",
        "/company/culture",
        "/company/about",
    ]

    def __init__(self, timeout: int = 10):
        """Initialize the company info scraper.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    def scrape_company_info(self, company_website: str) -> Optional[str]:
        """Scrape company culture and mission information.

        Args:
            company_website: Company website URL

        Returns:
            Company info text (culture/mission statements) or None
        """
        try:
            # Normalize URL
            if not company_website.startswith(('http://', 'https://')):
                company_website = f"https://{company_website}"

            # Try to find culture/about pages
            info_text = self._fetch_culture_pages(company_website)

            if info_text:
                # Clean up the text
                info_text = self._clean_text(info_text)

            return info_text

        except Exception as e:
            logger.warning(f"Error scraping company info from {company_website}: {str(e)}")
            return None

    def _fetch_culture_pages(self, base_url: str) -> Optional[str]:
        """Fetch content from common culture/about pages.

        Args:
            base_url: Base company website URL

        Returns:
            Combined text from culture pages or None
        """
        # This would require requests/beautifulsoup
        # For now, return None - this will be populated by scraper implementations
        # or we can use the WebFetch tool in the AI analysis stage
        logger.info(f"Company info scraping for {base_url} - to be implemented by scrapers")
        return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize scraped text.

        Args:
            text: Raw text from webpage

        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove common navigation/footer text patterns
        text = re.sub(r'(Cookie Policy|Privacy Policy|Terms of Service).*', '', text, flags=re.IGNORECASE)

        # Trim to reasonable length (first 1000 chars of culture info)
        if len(text) > 1000:
            text = text[:1000] + "..."

        return text.strip()

    def extract_company_domain(self, job_url: str) -> Optional[str]:
        """Extract company domain from job posting URL.

        For job boards (LinkedIn, Indeed, etc.), this won't work well.
        For company career pages, this extracts the base domain.

        Args:
            job_url: URL of job posting

        Returns:
            Company domain or None
        """
        try:
            parsed = urlparse(job_url)
            domain = parsed.netloc

            # Skip job board domains
            job_boards = ['linkedin.com', 'indeed.com', 'glassdoor.com', 'monster.com', 'ziprecruiter.com']
            if any(board in domain.lower() for board in job_boards):
                return None

            # Return base domain
            return f"https://{domain}"

        except Exception as e:
            logger.warning(f"Error extracting domain from {job_url}: {str(e)}")
            return None
