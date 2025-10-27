"""Base processor with shared dependencies and utilities.

This base class provides common functionality for all specialized processors:
- Dependency injection for shared managers
- Queue item status updates
- Stop list checking
- Logging utilities
- Error handling patterns
"""

import logging
from typing import Any, Dict, Optional

from job_finder.ai.matcher import AIJobMatcher
from job_finder.company_info_fetcher import CompanyInfoFetcher
from job_finder.filters.strike_filter_engine import StrikeFilterEngine
from job_finder.profile.schema import Profile
from job_finder.job_queue.config_loader import ConfigLoader
from job_finder.job_queue.manager import QueueManager
from job_finder.job_queue.models import JobQueueItem, QueueStatus
from job_finder.job_queue.scraper_intake import ScraperIntake
from job_finder.scrape_runner import ScrapeRunner
from job_finder.storage.companies_manager import CompaniesManager
from job_finder.storage.firestore_storage import FirestoreJobStorage
from job_finder.storage.job_sources_manager import JobSourcesManager

logger = logging.getLogger(__name__)


class BaseProcessor:
    """Base class for queue item processors with shared dependencies."""

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
        Initialize base processor with shared dependencies.

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

        # Initialize scraper intake for submitting jobs to queue
        self.scraper_intake = ScraperIntake(
            queue_manager=queue_manager,
            job_storage=job_storage,
            companies_manager=companies_manager,
        )

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

    def _update_item_status(
        self,
        item_id: str,
        status: QueueStatus,
        message: str = "",
        **kwargs: Any,
    ) -> None:
        """
        Update queue item status with logging.

        Args:
            item_id: Queue item ID
            status: New status
            message: Status message
            **kwargs: Additional fields to update
        """
        logger.info(f"Updating queue item {item_id} status to {status.value}: {message}")
        self.queue_manager.update_status(item_id, status, message, **kwargs)

    def _get_pipeline_state(self, item: JobQueueItem) -> Dict[str, Any]:
        """
        Get pipeline state from queue item.

        Args:
            item: Queue item

        Returns:
            Pipeline state dictionary (empty dict if not present)
        """
        return item.pipeline_state or {}
