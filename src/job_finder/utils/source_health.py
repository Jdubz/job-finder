"""Health tracking for job sources during scraping operations."""

import logging
from datetime import datetime, timezone, timedelta

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
