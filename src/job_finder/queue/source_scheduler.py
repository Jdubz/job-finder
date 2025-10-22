"""
Source scheduler for tier-based periodic scraping.

Schedules SCRAPE_SOURCE queue items based on company tier priorities:
- S/A tier: Every 1-2 days
- B tier: Weekly
- C tier: Bi-weekly
- D tier: Monthly
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from job_finder.queue.manager import QueueManager
from job_finder.queue.models import JobQueueItem, QueueItemType
from job_finder.storage.job_sources_manager import JobSourcesManager

logger = logging.getLogger(__name__)


class SourceScheduler:
    """
    Schedules periodic scraping of job sources based on tier priority.

    Implements tier-based scheduling:
    - S tier: Every 1 day (top priority companies)
    - A tier: Every 2 days (high priority)
    - B tier: Every 7 days (medium priority)
    - C tier: Every 14 days (low priority)
    - D tier: Every 30 days (minimal priority)
    """

    # Scrape intervals by tier (in days)
    TIER_INTERVALS = {
        "S": 1,
        "A": 2,
        "B": 7,
        "C": 14,
        "D": 30,
    }

    def __init__(
        self,
        sources_manager: JobSourcesManager,
        queue_manager: QueueManager,
    ):
        """
        Initialize source scheduler.

        Args:
            sources_manager: Job sources manager
            queue_manager: Queue manager for creating SCRAPE_SOURCE items
        """
        self.sources_manager = sources_manager
        self.queue_manager = queue_manager

    def get_sources_due_for_scraping(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get sources that are due for scraping based on tier schedule.

        Args:
            limit: Maximum number of sources to return (None = all)

        Returns:
            List of source documents that need scraping
        """
        # Get all enabled sources
        all_sources = self.sources_manager.get_all_sources()

        due_sources = []
        now = datetime.now()

        for source in all_sources:
            # Skip disabled sources
            if not source.get("enabled", False):
                continue

            # Get company tier (default to D if not set)
            company_id = source.get("company_id")
            tier = "D"  # Default tier

            if company_id:
                # Try to get company info for tier
                from job_finder.storage.companies_manager import CompaniesManager

                companies_manager = CompaniesManager(database_name="portfolio")
                company = companies_manager.get_company_by_id(company_id)
                if company:
                    tier = company.get("tier", "D")

            # Get scrape interval for tier
            interval_days = self.TIER_INTERVALS.get(tier, 30)

            # Check last scrape time
            last_scraped_at = source.get("last_scraped_at")

            if last_scraped_at is None:
                # Never scraped - add to queue
                due_sources.append(source)
            else:
                # Convert to datetime if needed
                if isinstance(last_scraped_at, str):
                    last_scraped_at = datetime.fromisoformat(last_scraped_at)

                # Check if interval has passed
                next_scrape_time = last_scraped_at + timedelta(days=interval_days)
                if now >= next_scrape_time:
                    due_sources.append(source)

        # Sort by priority (S > A > B > C > D)
        tier_priority = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}
        due_sources.sort(
            key=lambda s: (
                tier_priority.get(s.get("company", {}).get("tier", "D"), 4),
                s.get("last_scraped_at") or datetime.min,  # Older first
            )
        )

        if limit:
            return due_sources[:limit]
        return due_sources

    def schedule_scraping(self, max_sources: int = 10) -> int:
        """
        Schedule SCRAPE_SOURCE queue items for sources due for scraping.

        Args:
            max_sources: Maximum number of sources to schedule

        Returns:
            Number of SCRAPE_SOURCE items created
        """
        due_sources = self.get_sources_due_for_scraping(limit=max_sources)

        scheduled_count = 0
        for source in due_sources:
            try:
                # Create SCRAPE_SOURCE queue item
                scrape_item = JobQueueItem(
                    type=QueueItemType.SCRAPE_SOURCE,
                    url="",  # Not used for SCRAPE_SOURCE
                    company_name=source.get("company_name", "Unknown"),
                    source="scheduled_scraping",
                    scraped_data={"source_id": source.get("id")},
                    tracking_id=str(uuid.uuid4()),
                )

                item_id = self.queue_manager.add_item(scrape_item)
                logger.info(
                    f"Scheduled SCRAPE_SOURCE for {source.get('name')} "
                    f"(tier: {source.get('tier', 'D')}, id: {item_id})"
                )
                scheduled_count += 1

            except Exception as e:
                logger.error(f"Error scheduling scrape for {source.get('name')}: {e}")
                continue

        logger.info(f"Scheduled {scheduled_count} sources for scraping")
        return scheduled_count

    def get_scrape_schedule_summary(self) -> Dict[str, Any]:
        """
        Get summary of scraping schedule across all tiers.

        Returns:
            Dictionary with scheduling statistics
        """
        all_sources = self.sources_manager.get_all_sources()

        summary: Dict[str, Any] = {
            "total_sources": len(all_sources),
            "enabled_sources": 0,
            "disabled_sources": 0,
            "by_tier": {
                "S": {"count": 0, "interval_days": self.TIER_INTERVALS["S"]},
                "A": {"count": 0, "interval_days": self.TIER_INTERVALS["A"]},
                "B": {"count": 0, "interval_days": self.TIER_INTERVALS["B"]},
                "C": {"count": 0, "interval_days": self.TIER_INTERVALS["C"]},
                "D": {"count": 0, "interval_days": self.TIER_INTERVALS["D"]},
            },
            "due_for_scraping": 0,
        }

        for source in all_sources:
            if source.get("enabled", False):
                summary["enabled_sources"] += 1

                # Get tier from company
                tier = str(source.get("tier", "D"))
                if tier in summary["by_tier"]:
                    summary["by_tier"][tier]["count"] += 1
            else:
                summary["disabled_sources"] += 1

        # Count sources due for scraping
        due_sources = self.get_sources_due_for_scraping()
        summary["due_for_scraping"] = len(due_sources)

        return summary
