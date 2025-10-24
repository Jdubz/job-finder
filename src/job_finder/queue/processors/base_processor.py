"""Base processor with shared dependencies and utilities."""

import logging
from typing import Any, Dict, Optional

from job_finder.ai import AIJobMatcher
from job_finder.company_info_fetcher import CompanyInfoFetcher
from job_finder.filters import StrikeFilterEngine
from job_finder.profile.schema import Profile
from job_finder.queue.config_loader import ConfigLoader
from job_finder.queue.manager import QueueManager
from job_finder.queue.models import JobQueueItem, QueueStatus
from job_finder.queue.scraper_intake import ScraperIntake
from job_finder.scrape_runner import ScrapeRunner
from job_finder.storage import FirestoreJobStorage
from job_finder.storage.companies_manager import CompaniesManager
from job_finder.storage.job_sources_manager import JobSourcesManager

logger = logging.getLogger(__name__)


class BaseProcessor:
    """
    Base processor with shared dependencies and utilities.

    All specialized processors inherit from this class to access
    common resources (managers, scrapers, filters, etc.).
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
            profile: User profile
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

        # Initialize scraper intake for submitting jobs to queue
        self.scraper_intake = ScraperIntake(
            queue_manager=queue_manager,
            job_storage=job_storage,
            companies_manager=companies_manager,
        )

    def _extract_company_domain(self, url: str) -> str:
        """
        Extract company domain from URL.

        Args:
            url: Job or company URL

        Returns:
            Company domain (e.g., 'stripe.com')
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain

    def _build_company_info_string(self, company_info: Dict[str, Any]) -> str:
        """
        Build formatted company info string for AI analysis.

        Args:
            company_info: Company information dictionary

        Returns:
            Formatted company info string
        """
        parts = []

        if company_info.get("about"):
            parts.append(f"About: {company_info['about']}")

        if company_info.get("culture"):
            parts.append(f"Culture: {company_info['culture']}")

        if company_info.get("mission"):
            parts.append(f"Mission: {company_info['mission']}")

        if company_info.get("industry"):
            parts.append(f"Industry: {company_info['industry']}")

        if company_info.get("size"):
            parts.append(f"Size: {company_info['size']}")

        if company_info.get("headquarters"):
            parts.append(f"Headquarters: {company_info['headquarters']}")

        return "\n".join(parts) if parts else "No company information available"

    def _handle_failure(
        self,
        item: JobQueueItem,
        error_msg: str,
        error_details: str,
        max_retries: int = 3,
    ) -> None:
        """
        Handle item processing failure with retry logic.

        Args:
            item: Failed queue item
            error_msg: Short error message
            error_details: Full error traceback
            max_retries: Maximum retry attempts (default: 3)
        """
        if not item.id:
            logger.error("Cannot handle failure for item without ID")
            return

        # Increment retry count
        retry_count = item.retry_count + 1

        # Check if we should retry
        if retry_count < max_retries:
            logger.warning(
                f"Item {item.id} failed (attempt {retry_count}/{max_retries}). "
                f"Will retry. Error: {error_msg}"
            )
            # Update retry count and reset to pending
            self.queue_manager.db.collection("job-queue").document(item.id).update(
                {
                    "retry_count": retry_count,
                    "status": QueueStatus.PENDING.value,
                    "result_message": f"Retry {retry_count}/{max_retries}: {error_msg}",
                }
            )
        else:
            # Max retries exceeded - mark as permanently failed
            logger.error(
                f"Item {item.id} permanently failed after {retry_count} attempts. "
                f"Error: {error_msg}"
            )
            self.queue_manager.update_status(
                item.id,
                QueueStatus.FAILED,
                f"Failed after {retry_count} attempts: {error_msg}",
            )

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
