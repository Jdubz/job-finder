"""Health tracking for job sources during scraping operations."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from google.cloud import firestore as gcloud_firestore
from google.cloud.firestore_v1.base_query import FieldFilter

logger = logging.getLogger(__name__)


class SourceHealthTracker:
    """
    Track source health and scraping history.

    Maintains detailed statistics about each source including:
    - Last scrape timestamp and duration
    - Success/failure counts
    - Average jobs per scrape
    - Health score (affects rotation priority)
    """

    def __init__(self, db_client: gcloud_firestore.Client):
        """
        Initialize source health tracker.

        Args:
            db_client: Firestore client instance (google.cloud.firestore.Client)
        """
        self.db = db_client

    def update_after_successful_scrape(
        self,
        source_id: str,
        stats: Dict[str, Any],
        duration_seconds: float,
    ) -> None:
        """
        Update source health after successful scrape.

        Args:
            source_id: Source document ID
            stats: Scraping stats (jobs_found, jobs_matched, etc)
            duration_seconds: How long the scrape took
        """
        try:
            # Get current source data
            doc_ref = self.db.collection("job-sources").document(source_id)
            doc = doc_ref.get()

            if not doc.exists:
                logger.warning(f"Source not found for health update: {source_id}")
                return

            source_data = doc.to_dict()
            if not source_data:
                logger.warning(f"Source data is None for: {source_id}")
                return

            # Get or initialize health stats
            health = source_data.get("health", {})
            success_count = health.get("successCount", 0)
            failure_count = health.get("failureCount", 0)
            total_jobs_found = health.get("totalJobsFound", 0)
            total_scrapes = success_count + failure_count

            # Update health fields
            jobs_found = stats.get("jobs_found", 0)
            health_update = {
                "health.lastScrapedAt": datetime.now(timezone.utc),
                "health.lastScrapeDuration": duration_seconds,
                "health.successCount": success_count + 1,
                "health.failureCount": failure_count,
                "health.totalJobsFound": total_jobs_found + jobs_found,
                "health.averageJobsPerScrape": (
                    (total_jobs_found + jobs_found) / (total_scrapes + 1)
                    if (total_scrapes + 1) > 0
                    else 0
                ),
                "scraped_at": datetime.now(timezone.utc),  # Also update scraped_at field
            }

            # Calculate health score (0-1, higher is better)
            # Health score is based on success rate
            new_success_count = health_update["health.successCount"]
            new_failure_count = health_update["health.failureCount"]
            new_total = new_success_count + new_failure_count
            success_rate = new_success_count / new_total if new_total > 0 else 0

            # Penalize sources that take a long time
            time_penalty = min(1.0, duration_seconds / 60.0)  # -1 per 60 seconds
            health_update["health.healthScore"] = max(0, success_rate * (1 - time_penalty * 0.2))

            # Update Firestore
            doc_ref.update(health_update)

            logger.info(
                f"✓ Updated health for {source_data.get('name')}: "
                f"success_count={new_success_count}, "
                f"health_score={health_update['health.healthScore']:.2f}"
            )

        except Exception as e:
            logger.error(f"Error updating source health: {e}")

    def update_after_failed_scrape(
        self,
        source_id: str,
        error_message: str,
        duration_seconds: float,
    ) -> None:
        """
        Update source health after failed scrape.

        Args:
            source_id: Source document ID
            error_message: Error message from scrape failure
            duration_seconds: How long the attempted scrape took
        """
        try:
            # Get current source data
            doc_ref = self.db.collection("job-sources").document(source_id)
            doc = doc_ref.get()

            if not doc.exists:
                logger.warning(f"Source not found for health update: {source_id}")
                return

            source_data = doc.to_dict()
            if not source_data:
                logger.warning(f"Source data is None for: {source_id}")
                return

            # Get or initialize health stats
            health = source_data.get("health", {})
            success_count = health.get("successCount", 0)
            failure_count = health.get("failureCount", 0)
            total_jobs_found = health.get("totalJobsFound", 0)
            total_scrapes = success_count + failure_count

            # Update health fields
            health_update = {
                "health.lastScrapedAt": datetime.now(timezone.utc),
                "health.lastScrapeDuration": duration_seconds,
                "health.lastScrapeError": error_message,
                "health.successCount": success_count,
                "health.failureCount": failure_count + 1,
                "health.totalJobsFound": total_jobs_found,
                "health.averageJobsPerScrape": (
                    total_jobs_found / (total_scrapes + 1) if (total_scrapes + 1) > 0 else 0
                ),
            }

            # Calculate health score
            new_success_count = health_update["health.successCount"]
            new_failure_count = health_update["health.failureCount"]
            new_total = new_success_count + new_failure_count
            success_rate = (
                new_success_count / new_total if new_total > 0 else 0.5
            )  # Start at 0.5 for failures

            health_update["health.healthScore"] = max(
                0, success_rate * 0.9
            )  # 0.9 factor for penalties

            # Update Firestore
            doc_ref.update(health_update)

            logger.warning(
                f"✗ Updated health after failure for {source_data.get('name')}: "
                f"failure_count={health_update['health.failureCount']}, "
                f"health_score={health_update['health.healthScore']:.2f}"
            )

        except Exception as e:
            logger.error(f"Error updating source health after failure: {e}")


class CompanyScrapeTracker:
    """
    Track scraping frequency by company to ensure fairness.

    Prevents some companies from being over-scraped while others go unscraped.
    """

    def __init__(self, db_client: gcloud_firestore.Client, window_days: int = 30):
        """
        Initialize company scrape tracker.

        Args:
            db_client: Firestore client instance (google.cloud.firestore.Client)
            window_days: Look-back window for frequency calculation
        """
        self.db = db_client
        self.window = timedelta(days=window_days)

    def get_scrape_frequency(self, company_id: str) -> float:
        """
        Get scrapes per day for company in past N days.

        Args:
            company_id: Company ID to check

        Returns:
            Scrapes per day (float) in the look-back window
        """
        try:
            cutoff = datetime.now(timezone.utc) - self.window

            # Count recent scrapes from job-sources collection
            # (We store scraped_at timestamp when sources are scraped)
            query = (
                self.db.collection("job-sources")
                .where(filter=FieldFilter("company_id", "==", company_id))
                .where(filter=FieldFilter("scraped_at", ">", cutoff))
            )

            count = len(list(query.stream()))
            frequency = count / self.window.days

            return frequency

        except Exception as e:
            logger.warning(f"Error calculating company scrape frequency: {e}")
            return 0.0

    def get_company_scrape_counts(self) -> Dict[str, float]:
        """
        Get scrape frequency for all companies.

        Returns:
            Dictionary mapping company_id to scrape frequency
        """
        try:
            companies_collection = self.db.collection("companies")
            companies = list(companies_collection.stream())

            counts = {}
            for company_doc in companies:
                company_id = company_doc.id
                frequency = self.get_scrape_frequency(company_id)
                counts[company_id] = frequency

            return counts

        except Exception as e:
            logger.error(f"Error getting all company scrape counts: {e}")
            return {}
