"""Helper for scrapers to submit jobs to the queue."""

import logging
from typing import Any, Dict, List, Optional

from job_finder.queue.manager import QueueManager
from job_finder.queue.models import JobQueueItem, QueueItemType, QueueSource

logger = logging.getLogger(__name__)


class ScraperIntake:
    """
    Helper class for scrapers to submit jobs to the intake queue.

    This provides a simple interface for scrapers to add jobs without
    worrying about queue implementation details.
    """

    def __init__(self, queue_manager: QueueManager):
        """
        Initialize scraper intake.

        Args:
            queue_manager: Queue manager for adding items
        """
        self.queue_manager = queue_manager

    def submit_jobs(
        self,
        jobs: List[Dict[str, Any]],
        source: QueueSource = "scraper",
        company_id: Optional[str] = None,
    ) -> int:
        """
        Submit multiple jobs to the queue.

        Args:
            jobs: List of job dictionaries from scraper
            source: Source identifier (e.g., "greenhouse_scraper", "rss_feed")
            company_id: Optional company ID if known

        Returns:
            Number of jobs successfully added to queue
        """
        added_count = 0
        skipped_count = 0

        for job in jobs:
            try:
                # Validate URL exists and is non-empty
                url = job.get("url", "").strip()
                if not url:
                    skipped_count += 1
                    logger.debug("Skipping job with missing or empty URL")
                    continue

                # Check if URL already in queue
                if self.queue_manager.url_exists_in_queue(url):
                    skipped_count += 1
                    logger.debug(f"Job already in queue: {url}")
                    continue

                # Create queue item
                # Note: Full job data will be re-scraped during processing if not provided
                queue_item = JobQueueItem(
                    type=QueueItemType.JOB,
                    url=url,
                    company_name=job.get("company", ""),
                    company_id=company_id,
                    source=source,
                    scraped_data=(
                        job if len(job) > 2 else None
                    ),  # Include full job data if available
                )

                # Add to queue
                self.queue_manager.add_item(queue_item)
                added_count += 1

            except Exception as e:
                logger.error(f"Error adding job to queue: {e}")
                continue

        logger.info(
            f"Submitted {added_count} jobs to queue from {source} "
            f"({skipped_count} skipped as duplicates)"
        )
        return added_count

    def submit_company(
        self, company_name: str, company_website: str, source: QueueSource = "scraper"
    ) -> bool:
        """
        Submit a company for analysis to the queue.

        Args:
            company_name: Company name
            company_website: Company website URL
            source: Source identifier

        Returns:
            True if added successfully, False otherwise
        """
        try:
            # Validate URL exists and is non-empty
            url = company_website.strip()
            if not url:
                logger.debug(f"Skipping company {company_name} with missing or empty URL")
                return False

            # Check if URL already in queue
            if self.queue_manager.url_exists_in_queue(url):
                logger.debug(f"Company already in queue: {url}")
                return False

            # Create queue item
            queue_item = JobQueueItem(
                type=QueueItemType.COMPANY,
                url=url,
                company_name=company_name,
                source=source,
            )

            # Add to queue
            self.queue_manager.add_item(queue_item)
            logger.info(f"Submitted company to queue: {company_name}")
            return True

        except Exception as e:
            logger.error(f"Error adding company to queue: {e}")
            return False

    def submit_company_granular(
        self,
        company_name: str,
        company_website: str,
        source: QueueSource = "scraper",
    ) -> Optional[str]:
        """
        Submit a company for granular pipeline analysis to the queue.

        Uses the new 4-step granular pipeline (FETCH → EXTRACT → ANALYZE → SAVE).

        Args:
            company_name: Company name
            company_website: Company website URL
            source: Source identifier

        Returns:
            Document ID if added successfully, None otherwise
        """
        try:
            # Validate URL exists and is non-empty
            url = company_website.strip()
            if not url:
                logger.debug(f"Skipping company {company_name} with missing or empty URL")
                return None

            # Check if URL already in queue
            if self.queue_manager.url_exists_in_queue(url):
                logger.debug(f"Company already in queue: {url}")
                return None

            # Import CompanySubTask
            from job_finder.queue.models import CompanySubTask

            # Create granular pipeline item starting with FETCH
            queue_item = JobQueueItem(
                type=QueueItemType.COMPANY,
                url=url,
                company_name=company_name,
                source=source,
                company_sub_task=CompanySubTask.FETCH,
            )

            # Add to queue
            doc_id = self.queue_manager.add_item(queue_item)
            logger.info(f"Submitted company to granular pipeline: {company_name} (ID: {doc_id})")
            return doc_id

        except Exception as e:
            logger.error(f"Error adding company to granular pipeline: {e}")
            return None
