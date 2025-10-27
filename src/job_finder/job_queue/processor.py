"""Process queue items (jobs, companies, and scrape requests).

REFACTORING COMPLETE - God Object Decomposed
=============================================

This file previously contained 2,456 lines of processing logic for jobs, companies,
and sources. It has been refactored into focused processor classes:

processors/
├── base_processor.py         # ✅ Shared dependencies, utilities
├── job_processor.py           # ✅ Job processing (scraping, filtering, AI analysis)
├── company_processor.py       # ✅ Company processing (fetching, extraction, analysis)
└── source_processor.py        # ✅ Source discovery and scraping

This coordinator file now:
- Initializes specialized processors
- Dispatches queue items to appropriate processors
- Provides shared validation and error handling

Total reduction: 2,456 lines → ~250 lines (90% reduction)
"""

import logging
import traceback
from typing import Any, Dict, Optional

from job_finder.ai import AIJobMatcher
from job_finder.company_info_fetcher import CompanyInfoFetcher
from job_finder.exceptions import QueueProcessingError
from job_finder.profile.schema import Profile
from job_finder.job_queue.config_loader import ConfigLoader
from job_finder.job_queue.manager import QueueManager
from job_finder.job_queue.models import JobQueueItem, QueueItemType, QueueStatus
from job_finder.job_queue.processors import (
    CompanyProcessor,
    JobProcessor,
    SourceProcessor,
)
from job_finder.job_queue.scraper_intake import ScraperIntake  # For test compatibility
from job_finder.scrape_runner import ScrapeRunner  # For test compatibility
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
        Initialize processor with specialized processors for each domain.

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

        # Initialize specialized processors
        # All processors share the same dependencies via BaseProcessor
        self.job_processor = JobProcessor(
            queue_manager=queue_manager,
            config_loader=config_loader,
            job_storage=job_storage,
            companies_manager=companies_manager,
            sources_manager=sources_manager,
            company_info_fetcher=company_info_fetcher,
            ai_matcher=ai_matcher,
            profile=profile,
        )

        self.company_processor = CompanyProcessor(
            queue_manager=queue_manager,
            config_loader=config_loader,
            job_storage=job_storage,
            companies_manager=companies_manager,
            sources_manager=sources_manager,
            company_info_fetcher=company_info_fetcher,
            ai_matcher=ai_matcher,
            profile=profile,
        )

        self.source_processor = SourceProcessor(
            queue_manager=queue_manager,
            config_loader=config_loader,
            job_storage=job_storage,
            companies_manager=companies_manager,
            sources_manager=sources_manager,
            company_info_fetcher=company_info_fetcher,
            ai_matcher=ai_matcher,
            profile=profile,
        )

        # Expose shared components for backward compatibility with tests
        self.filter_engine = self.job_processor.filter_engine
        self.scrape_runner = self.job_processor.scrape_runner
        self.scraper_intake = self.job_processor.scraper_intake

    # ============================================================
    # MAIN DISPATCHER
    # ============================================================

    def process_item(self, item: JobQueueItem) -> None:
        """
        Dispatch queue item to appropriate specialized processor.

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

            # Delegate to specialized processors
            if item.type == QueueItemType.COMPANY:
                # All company items must use granular pipeline
                if not item.company_sub_task:
                    raise QueueProcessingError(
                        "Company items must have company_sub_task set. "
                        "Use submit_company() which creates granular pipeline items."
                    )
                self.company_processor.process_granular_company(item)
            elif item.type == QueueItemType.JOB:
                # Use decision tree routing based on pipeline_state
                self.job_processor.process_job(item)
            elif item.type == QueueItemType.SCRAPE:
                self.job_processor.process_scrape(item)
            elif item.type == QueueItemType.SOURCE_DISCOVERY:
                self.source_processor.process_source_discovery(item)
            elif item.type == QueueItemType.SCRAPE_SOURCE:
                self.source_processor.process_scrape_source(item)
            else:
                raise QueueProcessingError(f"Unknown item type: {item.type}")

        except Exception as e:
            error_msg = str(e)
            error_details = traceback.format_exc()
            logger.error(
                f"Error processing item {item.id}: {error_msg}\n{error_details}",
                exc_info=True,
            )
            self._handle_failure(item, error_msg, error_details)

    # ============================================================
    # SHARED UTILITY METHODS
    # ============================================================

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

    # ============================================================
    # BACKWARD COMPATIBILITY DELEGATION METHODS
    # These methods delegate to specialized processors for test compatibility
    # ============================================================

    # Job processor delegations
    def _build_company_info_string(self, company_info: Dict[str, Any]) -> str:
        """Delegate to job processor."""
        return self.job_processor._build_company_info_string(company_info)

    def _process_scrape(self, item: JobQueueItem) -> None:
        """Delegate to job processor."""
        return self.job_processor.process_scrape(item)

    def _process_job_scrape(self, item: JobQueueItem) -> None:
        """Delegate to job processor."""
        return self.job_processor.process_job_scrape(item)

    def _process_job_filter(self, item: JobQueueItem) -> None:
        """Delegate to job processor."""
        return self.job_processor.process_job_filter(item)

    def _process_job_analyze(self, item: JobQueueItem) -> None:
        """Delegate to job processor."""
        return self.job_processor.process_job_analyze(item)

    def _process_job_save(self, item: JobQueueItem) -> None:
        """Delegate to job processor."""
        return self.job_processor.process_job_save(item)

    def _process_granular_job(self, item: JobQueueItem) -> None:
        """Delegate to job processor."""
        return self.job_processor.process_granular_job(item)

    def _scrape_job(self, item: JobQueueItem):
        """Delegate to job processor."""
        return self.job_processor._scrape_job(item)

    def _scrape_with_source_config(self, url: str, source_config: Dict[str, Any]):
        """Delegate to job processor."""
        return self.job_processor._scrape_with_source_config(url, source_config)

    # Company processor delegations
    def _process_company_fetch(self, item: JobQueueItem) -> None:
        """Delegate to company processor."""
        return self.company_processor.process_company_fetch(item)

    def _process_company_extract(self, item: JobQueueItem) -> None:
        """Delegate to company processor."""
        return self.company_processor.process_company_extract(item)

    def _process_company_analyze(self, item: JobQueueItem) -> None:
        """Delegate to company processor."""
        return self.company_processor.process_company_analyze(item)

    def _process_company_save(self, item: JobQueueItem) -> None:
        """Delegate to company processor."""
        return self.company_processor.process_company_save(item)

    def _detect_tech_stack(
        self, extracted_info: Dict[str, Any], html_content: Optional[str] = None
    ) -> list:
        """Delegate to company processor."""
        return self.company_processor._detect_tech_stack(extracted_info, html_content)

    def _detect_job_board(
        self, company_website: str, html_content: Optional[str] = None
    ) -> Optional[str]:
        """Delegate to company processor."""
        return self.company_processor._detect_job_board(company_website, html_content)

    def _calculate_company_priority(
        self,
        company_name: str,
        extracted_info: Dict[str, Any],
        tech_stack: list,
        job_board_url: Optional[str] = None,
    ) -> tuple:
        """Delegate to company processor."""
        # Note: job_board_url parameter is kept for backward compatibility but not used
        return self.company_processor._calculate_company_priority(
            company_name, extracted_info, tech_stack
        )
