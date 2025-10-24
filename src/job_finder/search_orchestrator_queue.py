"""
Queue-enabled search orchestrator that scrapes jobs and submits to queue.

This version of the orchestrator scrapes jobs from sources and submits them
to the queue for asynchronous processing by the queue worker.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from job_finder.queue import QueueManager
from job_finder.queue.scraper_intake import ScraperIntake
from job_finder.scrapers.greenhouse_scraper import GreenhouseScraper
from job_finder.scrapers.rss_scraper import RSSJobScraper
from job_finder.storage import JobSourcesManager
from job_finder.storage.companies_manager import CompaniesManager
from job_finder.utils.job_type_filter import FilterDecision, filter_job

logger = logging.getLogger(__name__)


class QueueEnabledOrchestrator:
    """
    Orchestrates job scraping and queue submission.

    This orchestrator scrapes jobs from sources and submits them to the
    queue for processing. It does NOT do AI analysis directly - that's
    handled by the queue worker.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize queue-enabled orchestrator.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.sources_manager: Optional[JobSourcesManager] = None
        self.companies_manager: Optional[CompaniesManager] = None
        self.queue_manager: Optional[QueueManager] = None
        self.scraper_intake: Optional[ScraperIntake] = None

    def run_search(self) -> Dict[str, Any]:
        """
        Run scraping and submit jobs to queue.

        Returns:
            Dictionary with search statistics
        """
        logger.info("=" * 70)
        logger.info("STARTING JOB SEARCH (QUEUE MODE)")
        logger.info("=" * 70)

        # Initialize components
        logger.info("\n💾 Initializing components...")
        self._initialize_components()
        logger.info("✓ Components initialized")

        # Get active sources
        logger.info("\n📋 Loading job sources...")
        listings = self._get_active_sources()
        logger.info(f"✓ Found {len(listings)} active job sources")

        # Scrape and submit to queue
        stats: Dict[str, Any] = {
            "sources_scraped": 0,
            "total_jobs_found": 0,
            "jobs_submitted_to_queue": 0,
            "jobs_skipped": 0,
            "errors": [],
        }

        for listing in listings:
            try:
                source_stats = self._process_listing(listing)

                stats["sources_scraped"] += 1
                stats["total_jobs_found"] += source_stats["jobs_found"]
                stats["jobs_submitted_to_queue"] += source_stats["jobs_submitted"]
                stats["jobs_skipped"] += source_stats["jobs_skipped"]

            except Exception as e:
                error_msg = f"Error processing {listing.get('name')}: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

        # Final summary
        logger.info("\n" + "=" * 70)
        logger.info("✅ SCRAPING COMPLETE (Jobs submitted to queue)")
        logger.info("=" * 70)
        logger.info("\n📊 STATISTICS:")
        logger.info(f"  Sources scraped: {stats['sources_scraped']}")
        logger.info(f"  Total jobs found: {stats['total_jobs_found']}")
        logger.info(f"  Jobs submitted to queue: {stats['jobs_submitted_to_queue']}")
        logger.info(f"  Jobs skipped (duplicates/filters): {stats['jobs_skipped']}")

        if stats["errors"]:
            logger.warning(f"\n⚠️  Errors encountered: {len(stats['errors'])}")
            for error in stats["errors"]:
                logger.warning(f"  - {error}")

        logger.info("\n✓ Jobs are now in queue for processing by queue worker")

        return stats

    def _initialize_components(self):
        """Initialize Firestore managers."""
        storage_db = os.getenv(
            "STORAGE_DATABASE_NAME",
            self.config.get("storage", {}).get("database_name", "portfolio-staging"),
        )

        self.sources_manager = JobSourcesManager(database_name=storage_db)
        self.companies_manager = CompaniesManager(database_name=storage_db)
        self.queue_manager = QueueManager(database_name=storage_db)
        self.scraper_intake = ScraperIntake(self.queue_manager)

    def _get_active_sources(self) -> List[Dict[str, Any]]:
        """Get active job sources from Firestore."""
        if not self.sources_manager:
            raise RuntimeError("Components not initialized")

        sources = self.sources_manager.get_active_sources()

        # Enrich with company data
        enriched_sources = []
        for source in sources:
            company_id = source.get("companyId")

            if company_id and self.companies_manager:
                company = self.companies_manager.get_company_by_id(company_id)
                if company:
                    source["hasPortlandOffice"] = company.get("hasPortlandOffice", False)
                    source["techStack"] = company.get("techStack", [])
                    source["tier"] = company.get("tier", "D")
                    source["priorityScore"] = company.get("priorityScore", 0)
                    source["company_website"] = company.get("website", "")

            enriched_sources.append(source)

        # Sort by priority
        sorted_sources = sorted(
            enriched_sources,
            key=lambda x: (-(x.get("priorityScore", 0)), x.get("name", "")),
        )

        return sorted_sources

    def _process_listing(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single job listing source.

        Args:
            listing: Job listing configuration

        Returns:
            Statistics for this source
        """
        if not self.sources_manager or not self.scraper_intake:
            raise RuntimeError("Components not initialized")

        listing_name = listing.get("name", "Unknown")
        logger.info(f"\n📋 Processing: {listing_name}")

        stats = {"jobs_found": 0, "jobs_submitted": 0, "jobs_skipped": 0}

        try:
            # Scrape jobs
            jobs = self._scrape_jobs_from_listing(listing)
            stats["jobs_found"] = len(jobs)
            logger.info(f"✓ Found {len(jobs)} jobs")

            if not jobs:
                self.sources_manager.update_scrape_status(
                    doc_id=listing["id"], status="success", jobs_found=0
                )
                return stats

            # Apply basic filters
            filtered_jobs = self._apply_filters(jobs)
            logger.info(f"✓ {len(filtered_jobs)} jobs after filtering")

            if not filtered_jobs:
                stats["jobs_skipped"] = len(jobs)
                self.sources_manager.update_scrape_status(
                    doc_id=listing["id"], status="success", jobs_found=len(jobs)
                )
                return stats

            # Submit to queue
            submitted_count = self.scraper_intake.submit_jobs(
                filtered_jobs,
                source=f"{listing.get('sourceType', 'unknown')}_scraper",
                company_id=listing.get("companyId"),
            )

            stats["jobs_submitted"] = submitted_count
            stats["jobs_skipped"] = len(filtered_jobs) - submitted_count

            # Update source stats
            self.sources_manager.update_scrape_status(
                doc_id=listing["id"], status="success", jobs_found=len(jobs)
            )

            logger.info(
                f"✓ Completed {listing_name}: " f"{submitted_count} jobs submitted to queue"
            )

        except Exception as e:
            logger.error(f"Error processing {listing_name}: {str(e)}")
            self.sources_manager.update_scrape_status(
                doc_id=listing["id"], status="error", error=str(e)
            )
            raise

        return stats

    def _scrape_jobs_from_listing(self, listing: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape jobs from a source based on its source type."""
        source_type = listing.get("sourceType", "unknown")
        source_config = listing.get("config", {})

        if source_type == "rss":
            rss_scraper = RSSJobScraper(
                config=self.config.get("scraping", {}), listing_config=source_config
            )
            return rss_scraper.scrape()

        elif source_type == "greenhouse":
            board_token = source_config.get("board_token")
            greenhouse_config = {
                "board_token": board_token,
                "name": listing.get("companyName", listing.get("name", "Unknown")),
                "company_website": listing.get("company_website", ""),
            }
            greenhouse_scraper = GreenhouseScraper(greenhouse_config)
            return greenhouse_scraper.scrape()

        else:
            logger.warning(f"Unknown source type: {source_type}")
            return []

    def _apply_filters(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply basic filters before submitting to queue."""
        # Filter for remote jobs
        remote_jobs = self._filter_remote_only(jobs)

        # Filter by age (last 7 days)
        fresh_jobs = self._filter_by_age(remote_jobs, max_days=7)

        # Filter by job type/seniority
        filtered_jobs, _ = self._filter_by_job_type(fresh_jobs)

        return filtered_jobs

    def _filter_remote_only(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter jobs to only include remote positions or Portland, OR."""
        from job_finder.utils.common_filters import filter_remote_only

        return filter_remote_only(jobs)

    def _filter_by_age(self, jobs: List[Dict[str, Any]], max_days: int = 7) -> List[Dict[str, Any]]:
        """Filter jobs to only include those posted within the last N days."""
        from job_finder.utils.common_filters import filter_by_age

        return filter_by_age(jobs, max_days=max_days, verbose=False)

    def _filter_by_job_type(
        self, jobs: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Filter jobs by role type and seniority."""
        from job_finder.utils.common_filters import filter_by_job_type

        filters_config = self.config.get("filters", {})
        return filter_by_job_type(jobs, filters_config, verbose=False)
