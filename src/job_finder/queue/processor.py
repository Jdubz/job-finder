"""Process queue items (jobs, companies, and scrape requests)."""

import logging
import traceback
from typing import Any, Dict, Optional

from job_finder.ai import AIJobMatcher
from job_finder.company_info_fetcher import CompanyInfoFetcher
from job_finder.filters import StrikeFilterEngine
from job_finder.profile.schema import Profile
from job_finder.queue.config_loader import ConfigLoader
from job_finder.queue.manager import QueueManager
from job_finder.queue.models import JobQueueItem, QueueItemType, QueueStatus
from job_finder.scrape_runner import ScrapeRunner
from job_finder.storage import FirestoreJobStorage
from job_finder.storage.companies_manager import CompaniesManager
from job_finder.storage.job_sources_manager import JobSourcesManager

logger = logging.getLogger(__name__)


class QueueItemProcessor:
    """
    Processes individual queue items (jobs, companies, and scrape requests).

    Handles scraping, AI analysis, and storage based on item type.
    """

    def __init__(
        self,
        queue_manager: QueueManager,
        config_loader: ConfigLoader,
        job_storage: FirestoreJobStorage,
        companies_manager: CompaniesManager,
        sources_manager: JobSourcesManager,
        company_info_fetcher: CompanyInfoFetcher,
        ai_matcher: AIJobMatcher,
        profile: Profile,
    ):
        """
        Initialize processor with required managers.

        Args:
            queue_manager: Queue manager for updating item status
            config_loader: Configuration loader for stop lists and filters
            job_storage: Firestore job storage
            companies_manager: Company data manager
            sources_manager: Job sources manager
            company_info_fetcher: Company info scraper
            ai_matcher: AI job matcher
            profile: User profile (for scrape requests)
        """
        self.queue_manager = queue_manager
        self.config_loader = config_loader
        self.job_storage = job_storage
        self.companies_manager = companies_manager
        self.sources_manager = sources_manager
        self.company_info_fetcher = company_info_fetcher
        self.ai_matcher = ai_matcher
        self.profile = profile

        # Initialize strike-based filter engine
        filter_config = config_loader.get_job_filters()
        tech_ranks = config_loader.get_technology_ranks()
        self.filter_engine = StrikeFilterEngine(filter_config, tech_ranks)

        # Initialize scrape runner
        self.scrape_runner = ScrapeRunner(
            ai_matcher=ai_matcher,
            job_storage=job_storage,
            companies_manager=companies_manager,
            sources_manager=sources_manager,
            company_info_fetcher=company_info_fetcher,
            profile=profile,
        )

    def process_item(self, item: JobQueueItem) -> None:
        """
        Process a queue item based on its type.

        Args:
            item: Queue item to process
        """
        if not item.id:
            logger.error("Cannot process item without ID")
            return

        # Log differently for scrape requests
        if item.type == QueueItemType.SCRAPE:
            logger.info(f"Processing queue item {item.id}: SCRAPE request")
        else:
            logger.info(f"Processing queue item {item.id}: {item.type} - {item.url[:50]}...")

        try:
            # Update status to processing
            self.queue_manager.update_status(item.id, QueueStatus.PROCESSING)

            # Check stop list (skip for SCRAPE requests)
            if item.type != QueueItemType.SCRAPE and self._should_skip_by_stop_list(item):
                self.queue_manager.update_status(
                    item.id, QueueStatus.SKIPPED, "Excluded by stop list"
                )
                return

            # Check if URL already exists in job-matches
            if item.type == QueueItemType.JOB and self.job_storage.job_exists(item.url):
                self.queue_manager.update_status(
                    item.id, QueueStatus.SKIPPED, "Job already exists in database"
                )
                return

            # Process based on type
            if item.type == QueueItemType.COMPANY:
                self._process_company(item)
            elif item.type == QueueItemType.JOB:
                self._process_job(item)
            elif item.type == QueueItemType.SCRAPE:
                self._process_scrape(item)
            else:
                raise ValueError(f"Unknown item type: {item.type}")

        except Exception as e:
            error_msg = str(e)
            error_details = traceback.format_exc()
            logger.error(
                f"Error processing item {item.id}: {error_msg}\n{error_details}",
                exc_info=True,
            )
            self._handle_failure(item, error_msg, error_details)

    def _should_skip_by_stop_list(self, item: JobQueueItem) -> bool:
        """
        Check if item should be skipped based on stop list.

        Args:
            item: Queue item to check

        Returns:
            True if item should be skipped, False otherwise
        """
        stop_list = self.config_loader.get_stop_list()

        # Check excluded companies
        if item.company_name:
            for excluded in stop_list["excludedCompanies"]:
                if excluded.lower() in item.company_name.lower():
                    logger.info(f"Skipping due to excluded company: {item.company_name}")
                    return True

        # Check excluded domains
        for excluded_domain in stop_list["excludedDomains"]:
            if excluded_domain.lower() in item.url.lower():
                logger.info(f"Skipping due to excluded domain: {excluded_domain}")
                return True

        # Check excluded keywords in URL
        for keyword in stop_list["excludedKeywords"]:
            if keyword.lower() in item.url.lower():
                logger.info(f"Skipping due to excluded keyword in URL: {keyword}")
                return True

        return False

    def _process_company(self, item: JobQueueItem) -> None:
        """
        Process a company queue item.

        Steps:
        1. Check if company already exists
        2. Scrape company website
        3. Run AI analysis
        4. Save to companies collection
        5. Look for job board URLs

        Args:
            item: Company queue item
        """
        company_name = item.company_name or "Unknown Company"

        # Check if company already analyzed
        existing_company = self.companies_manager.get_company(company_name)
        if existing_company and existing_company.get("analysis_status") == "complete":
            logger.info(f"Company {company_name} already analyzed, skipping")
            if item.id:
                self.queue_manager.update_status(
                    item.id, QueueStatus.SKIPPED, "Company already analyzed"
                )
            return

        # Scrape and analyze company
        try:
            company_info = self.company_info_fetcher.fetch_company_info(company_name, item.url)

            if not company_info:
                if item.id:
                    error_msg = "Could not fetch company information from website"
                    error_details = (
                        f"Failed to scrape company info from: {item.url}\n"
                        f"Company: {company_name}\n\n"
                        f"Possible causes:\n"
                        f"- Website is down or blocking requests\n"
                        f"- Company website structure has changed\n"
                        f"- Network connectivity issues\n"
                        f"- Rate limiting from target website"
                    )
                    self.queue_manager.update_status(
                        item.id, QueueStatus.FAILED, error_msg, error_details=error_details
                    )
                return

            # Add analysis status
            company_info["analysis_status"] = "complete"

            # Save to companies collection
            company_id = self.companies_manager.save_company(company_info)

            logger.info(f"Successfully processed company: {company_name} (ID: {company_id})")
            if item.id:
                self.queue_manager.update_status(
                    item.id,
                    QueueStatus.SUCCESS,
                    f"Company analyzed and saved (ID: {company_id})",
                    scraped_data=company_info,
                )

        except Exception as e:
            logger.error(f"Error processing company {company_name}: {e}")
            raise

    def _process_job(self, item: JobQueueItem) -> None:
        """
        Process a job queue item.

        Steps:
        1. Scrape job details from URL
        2. Run advanced filters (before AI to reduce costs)
        3. Ensure company exists and is analyzed
        4. Run AI matching
        5. Save to job-matches if score meets threshold

        Args:
            item: Job queue item
        """
        # Scrape job details
        job_data = self._scrape_job(item)

        if not job_data:
            if item.id:
                error_msg = "Could not scrape job details from URL"
                error_details = (
                    f"Failed to scrape job from: {item.url}\n"
                    f"Company: {item.company_name}\n\n"
                    f"Possible causes:\n"
                    f"- Job posting has been removed or expired\n"
                    f"- Job board URL structure has changed\n"
                    f"- Job board requires login or is blocking scraping\n"
                    f"- Network connectivity issues"
                )
                self.queue_manager.update_status(
                    item.id, QueueStatus.FAILED, error_msg, error_details=error_details
                )
            return

        # Run advanced filters BEFORE AI analysis (cost optimization)
        filter_result = self.filter_engine.evaluate_job(job_data)
        if not filter_result.passed:
            # Job rejected by filters
            rejection_summary = filter_result.get_rejection_summary()
            rejection_data = filter_result.to_dict()

            logger.info(
                f"Job filtered out: {job_data.get('title')} at {job_data.get('company')} - "
                f"{rejection_summary}"
            )

            if item.id:
                self.queue_manager.update_status(
                    item.id,
                    QueueStatus.FILTERED,
                    f"Rejected by filters: {rejection_summary}",
                    scraped_data={"job_data": job_data, "filter_result": rejection_data},
                )
            return

        # Ensure company exists
        company_name = job_data.get("company", item.company_name)
        company_website = job_data.get("company_website", "")

        if company_name and company_website:
            company = self.companies_manager.get_or_create_company(
                company_name=company_name,
                company_website=company_website,
                fetch_info_func=self.company_info_fetcher.fetch_company_info,
            )
            company_id = company.get("id")
            job_data["companyId"] = company_id
            job_data["company_info"] = self._build_company_info_string(company)

        # Run AI matching
        try:
            result = self.ai_matcher.analyze_job(job_data)

            if not result:
                # Below match threshold
                if item.id:
                    self.queue_manager.update_status(
                        item.id,
                        QueueStatus.SKIPPED,
                        f"Job score below threshold "
                        f"(likely < {self.ai_matcher.min_match_score})",
                    )
                return

            # Save to job-matches
            doc_id = self.job_storage.save_job_match(job_data, result)

            logger.info(
                f"Job matched and saved: {job_data.get('title')} at {company_name} "
                f"(Score: {result.match_score}, ID: {doc_id})"
            )
            if item.id:
                self.queue_manager.update_status(
                    item.id,
                    QueueStatus.SUCCESS,
                    f"Job matched with score {result.match_score} " f"and saved (ID: {doc_id})",
                )

        except Exception as e:
            logger.error(f"Error analyzing job: {e}")
            raise

    def _scrape_job(self, item: JobQueueItem) -> Optional[Dict[str, Any]]:
        """
        Scrape job details from URL.

        Detects job board type from URL and uses appropriate scraper.

        Args:
            item: Job queue item

        Returns:
            Job data dictionary or None if scraping failed
        """
        # If we have scraped_data from a previous scraper run, use it
        if item.scraped_data:
            logger.debug(
                f"Using cached scraped data: {item.scraped_data.get('title')} "
                f"at {item.scraped_data.get('company')}"
            )
            return item.scraped_data

        # Detect job board type and scrape
        url = item.url
        job_data = None

        try:
            # Greenhouse (MongoDB, Spotify, etc.)
            if "greenhouse" in url or "gh_jid=" in url:
                job_data = self._scrape_greenhouse_url(url)

            # WeWorkRemotely
            elif "weworkremotely.com" in url:
                job_data = self._scrape_weworkremotely_url(url)

            # Remotive
            elif "remotive.com" in url or "remotive.io" in url:
                job_data = self._scrape_remotive_url(url)

            # Generic fallback - try basic scraping
            else:
                logger.warning(f"Unknown job board URL: {url}, using generic scraper")
                job_data = self._scrape_generic_url(url)

        except Exception as e:
            logger.error(f"Error scraping job from {url}: {e}")
            return None

        if job_data:
            # Ensure URL is set
            job_data["url"] = url
            logger.debug(f"Job scraped: {job_data.get('title')} at {job_data.get('company')}")
            return job_data

        return None

    def _scrape_greenhouse_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape job details from Greenhouse URL."""
        import re

        import requests
        from bs4 import BeautifulSoup

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract job details
            title_elem = soup.find("h1", class_="app-title")
            company_elem = soup.find("span", class_="company-name")
            location_elem = soup.find("div", class_="location")
            description_elem = soup.find("div", id="content")

            return {
                "title": title_elem.text.strip() if title_elem else "Unknown",
                "company": company_elem.text.strip() if company_elem else "Unknown",
                "location": location_elem.text.strip() if location_elem else "Unknown",
                "description": (
                    description_elem.get_text(separator="\n", strip=True)
                    if description_elem
                    else ""
                ),
                "company_website": self._extract_company_domain(url),
                "url": url,
            }
        except Exception as e:
            logger.error(f"Failed to scrape Greenhouse URL {url}: {e}")
            return None

    def _scrape_weworkremotely_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape job details from WeWorkRemotely URL."""
        import requests
        from bs4 import BeautifulSoup

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract job details
            title_elem = soup.find("h1")
            company_elem = soup.find("h2")
            description_elem = soup.find("div", class_="listing-container")

            return {
                "title": title_elem.text.strip() if title_elem else "Unknown",
                "company": company_elem.text.strip() if company_elem else "Unknown",
                "location": "Remote",
                "description": (
                    description_elem.get_text(separator="\n", strip=True)
                    if description_elem
                    else ""
                ),
                "company_website": self._extract_company_domain(url),
                "url": url,
            }
        except Exception as e:
            logger.error(f"Failed to scrape WeWorkRemotely URL {url}: {e}")
            return None

    def _scrape_remotive_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape job details from Remotive URL."""
        import requests
        from bs4 import BeautifulSoup

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract job details (adjust selectors based on actual Remotive HTML)
            title_elem = soup.find("h1")
            company_elem = soup.find("a", class_="company-name")
            description_elem = soup.find("div", class_="job-description")

            return {
                "title": title_elem.text.strip() if title_elem else "Unknown",
                "company": company_elem.text.strip() if company_elem else "Unknown",
                "location": "Remote",
                "description": (
                    description_elem.get_text(separator="\n", strip=True)
                    if description_elem
                    else ""
                ),
                "company_website": self._extract_company_domain(url),
                "url": url,
            }
        except Exception as e:
            logger.error(f"Failed to scrape Remotive URL {url}: {e}")
            return None

    def _scrape_generic_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Generic fallback scraper for unknown job boards."""
        import requests
        from bs4 import BeautifulSoup

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Try to extract basic info
            title = soup.find("h1")
            description = soup.find("body")

            return {
                "title": title.text.strip() if title else "Unknown",
                "company": "Unknown",
                "location": "Unknown",
                "description": (
                    description.get_text(separator="\n", strip=True) if description else ""
                ),
                "company_website": self._extract_company_domain(url),
                "url": url,
            }
        except Exception as e:
            logger.error(f"Failed to scrape generic URL {url}: {e}")
            return None

    def _extract_company_domain(self, url: str) -> str:
        """Extract company domain from job URL."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        # Remove www. prefix
        domain = parsed.netloc.replace("www.", "")
        # For job boards, try to find actual company domain in the content
        # For now, just return the job board domain
        return f"https://{domain}"

    def _build_company_info_string(self, company_info: Dict[str, Any]) -> str:
        """
        Build formatted company info string.

        Args:
            company_info: Company data dictionary

        Returns:
            Formatted company info string
        """
        company_about = company_info.get("about", "")
        company_culture = company_info.get("culture", "")
        company_mission = company_info.get("mission", "")

        company_info_parts = []
        if company_about:
            company_info_parts.append(f"About: {company_about}")
        if company_culture:
            company_info_parts.append(f"Culture: {company_culture}")
        if company_mission:
            company_info_parts.append(f"Mission: {company_mission}")

        return "\n\n".join(company_info_parts)

    def _handle_failure(
        self, item: JobQueueItem, error_message: str, error_details: Optional[str] = None
    ) -> None:
        """
        Handle item processing failure with retry logic.

        Args:
            item: Failed queue item
            error_message: Brief error description (shown in UI)
            error_details: Detailed error information including stack trace (for debugging)
        """
        if not item.id:
            logger.error("Cannot handle failure for item without ID")
            return

        queue_settings = self.config_loader.get_queue_settings()
        max_retries = queue_settings["maxRetries"]

        # Increment retry count
        self.queue_manager.increment_retry(item.id)

        # Build context for error details
        error_context = (
            f"Queue Item: {item.id}\n"
            f"Type: {item.type}\n"
            f"URL: {item.url}\n"
            f"Company: {item.company_name}\n"
            f"Retry Count: {item.retry_count + 1}/{max_retries}\n\n"
        )

        # Check if we should retry
        if item.retry_count + 1 < max_retries:
            # Reset to pending for retry
            retry_msg = f"Processing failed. Will retry ({item.retry_count + 1}/{max_retries})"
            retry_details = (
                f"{error_context}"
                f"Error: {error_message}\n\n"
                f"This item will be automatically retried.\n\n"
                f"{'Stack Trace:\n' + error_details if error_details else ''}"
            )
            self.queue_manager.update_status(
                item.id, QueueStatus.PENDING, retry_msg, error_details=retry_details
            )
            logger.info(f"Item {item.id} will be retried (attempt {item.retry_count + 1})")
        else:
            # Max retries exceeded, mark as failed
            failed_msg = f"Failed after {max_retries} retries: {error_message}"
            failed_details = (
                f"{error_context}"
                f"Error: {error_message}\n\n"
                f"Max retries ({max_retries}) exceeded. Manual intervention may be required.\n\n"
                f"Troubleshooting:\n"
                f"1. Check if the URL is still valid\n"
                f"2. Review error details below for specific issues\n"
                f"3. Verify network connectivity and API credentials\n"
                f"4. Check if the source website has changed structure\n\n"
                f"{'Stack Trace:\n' + error_details if error_details else ''}"
            )
            self.queue_manager.update_status(
                item.id, QueueStatus.FAILED, failed_msg, error_details=failed_details
            )
            logger.error(f"Item {item.id} failed after {max_retries} retries: {error_message}")

    def _process_scrape(self, item: JobQueueItem) -> None:
        """
        Process a scrape queue item.

        Runs a scraping operation with custom configuration.

        Args:
            item: Scrape queue item
        """
        if not item.id:
            logger.error("Cannot process scrape item without ID")
            return

        # Get scrape configuration
        scrape_config = item.scrape_config
        if not scrape_config:
            # Use defaults
            from job_finder.queue.models import ScrapeConfig

            scrape_config = ScrapeConfig()

        logger.info(f"Starting scrape with config: {scrape_config.model_dump()}")

        try:
            # Override AI match score if specified
            original_min_score = self.ai_matcher.min_match_score
            if scrape_config.min_match_score is not None:
                logger.info(
                    f"Overriding min_match_score: {original_min_score} -> "
                    f"{scrape_config.min_match_score}"
                )
                self.ai_matcher.min_match_score = scrape_config.min_match_score

            # Run scrape (pass None values through, don't use defaults here)
            stats = self.scrape_runner.run_scrape(
                target_matches=scrape_config.target_matches,
                max_sources=scrape_config.max_sources,
                source_ids=scrape_config.source_ids,
            )

            # Restore original min score
            self.ai_matcher.min_match_score = original_min_score

            # Update queue item with success
            result_message = (
                f"Scrape completed: {stats['jobs_saved']} jobs saved, "
                f"{stats['sources_scraped']} sources scraped"
            )

            self.queue_manager.update_status(
                item.id, QueueStatus.SUCCESS, result_message, scraped_data=stats
            )

            logger.info(f"Scrape completed successfully: {result_message}")

        except Exception as e:
            logger.error(f"Error processing scrape request: {e}")
            raise
