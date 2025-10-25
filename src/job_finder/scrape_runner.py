"""
Scrape runner - executes scraping operations with custom configuration.

This module provides the core scraping logic that can be used by:
- Queue worker (when processing SCRAPE queue items)
- Hourly scheduler (when running scheduled scrapes)
- CLI tools (for manual scraping)
"""

import logging
from typing import Any, Dict, List, Optional

from job_finder.ai import AIJobMatcher
from job_finder.company_info_fetcher import CompanyInfoFetcher
from job_finder.exceptions import ConfigurationError
from job_finder.profile.schema import Profile
from job_finder.scrapers.greenhouse_scraper import GreenhouseScraper
from job_finder.storage import FirestoreJobStorage
from job_finder.storage.companies_manager import CompaniesManager
from job_finder.storage.job_sources_manager import JobSourcesManager
from job_finder.utils.job_type_filter import filter_job, FilterDecision

logger = logging.getLogger(__name__)


class ScrapeRunner:
    """
    Runs scraping operations with custom configuration.

    Handles source selection, scraping, filtering, AI matching, and storage.
    """

    def __init__(
        self,
        ai_matcher: AIJobMatcher,
        job_storage: FirestoreJobStorage,
        companies_manager: CompaniesManager,
        sources_manager: JobSourcesManager,
        company_info_fetcher: CompanyInfoFetcher,
        profile: Profile,
    ):
        """
        Initialize scrape runner.

        Args:
            ai_matcher: AI job matcher
            job_storage: Job storage
            companies_manager: Companies manager
            sources_manager: Job sources manager
            company_info_fetcher: Company info fetcher
            profile: User profile
        """
        self.ai_matcher = ai_matcher
        self.job_storage = job_storage
        self.companies_manager = companies_manager
        self.sources_manager = sources_manager
        self.company_info_fetcher = company_info_fetcher
        self.profile = profile

    def run_scrape(
        self,
        target_matches: Optional[int] = 5,
        max_sources: Optional[int] = 20,
        source_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run a scraping operation.

        Args:
            target_matches: Stop after finding this many potential matches (None = no limit)
            max_sources: Maximum number of sources to scrape (None = unlimited)
            source_ids: Specific source IDs to scrape (None = all sources with rotation)

        Returns:
            Dictionary with scraping statistics
        """
        logger.info("=" * 70)
        logger.info("STARTING SCRAPE")
        logger.info("=" * 70)

        # Log configuration
        if target_matches is None:
            logger.info("Target matches: UNLIMITED (will scrape all allowed sources)")
        else:
            logger.info(f"Target matches: {target_matches}")

        if max_sources is None:
            logger.info("Max sources: UNLIMITED")
        else:
            logger.info(f"Max sources: {max_sources}")

        if source_ids:
            logger.info(f"Specific sources: {source_ids}")
        else:
            logger.info("Using all sources with rotation (oldest first)")

        # Get sources to scrape
        sources = self._get_sources(max_sources, source_ids)
        logger.info(f"✓ Found {len(sources)} sources to scrape")

        # Scraping stats
        stats = {
            "sources_scraped": 0,
            "total_jobs_found": 0,
            "remote_jobs": 0,
            "jobs_filtered_by_role": 0,
            "duplicates_skipped": 0,
            "jobs_analyzed": 0,
            "jobs_matched": 0,
            "jobs_saved": 0,
            "errors": [],
        }

        # Scrape until we find target potential matches or run out of sources
        potential_matches = 0

        for source in sources:
            # Check if we should stop (only if target_matches is set)
            if target_matches is not None and potential_matches >= target_matches:
                logger.info(f"\n✅ Reached target: {potential_matches} potential matches, stopping")
                break

            try:
                source_stats = self._scrape_source(source)

                # Update source's lastScrapedAt
                self.sources_manager.update_scrape_status(
                    source["id"],
                    status="success",
                    jobs_found=source_stats["jobs_found"],
                    jobs_matched=source_stats["jobs_matched"],
                )

                # Update totals
                stats["sources_scraped"] += 1
                stats["total_jobs_found"] += source_stats["jobs_found"]
                stats["remote_jobs"] += source_stats["remote_jobs"]
                stats["jobs_filtered_by_role"] += source_stats["jobs_filtered_by_role"]
                stats["duplicates_skipped"] += source_stats["duplicates_skipped"]
                stats["jobs_analyzed"] += source_stats["jobs_analyzed"]
                stats["jobs_matched"] += source_stats["jobs_matched"]
                stats["jobs_saved"] += source_stats["jobs_saved"]

                # Track potential matches
                potential_matches += source_stats["jobs_analyzed"]

            except Exception as e:
                error_msg = f"Error processing {source.get('name')}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                stats["errors"].append(error_msg)

                # Update source status with error
                self.sources_manager.update_scrape_status(
                    source["id"], status="error", error=str(e)
                )

        # Final summary
        logger.info("\n" + "=" * 70)
        logger.info("✅ SCRAPE COMPLETE")
        logger.info("=" * 70)
        logger.info(f"\n📊 STATISTICS:")
        logger.info(f"  Sources scraped: {stats['sources_scraped']}")
        logger.info(f"  Total jobs found: {stats['total_jobs_found']}")
        logger.info(f"  Remote jobs: {stats['remote_jobs']}")
        logger.info(f"  Filtered by role: {stats['jobs_filtered_by_role']}")
        logger.info(f"  Duplicates skipped: {stats['duplicates_skipped']}")
        logger.info(f"  Jobs analyzed (potential matches): {stats['jobs_analyzed']}")
        logger.info(f"  Jobs matched: {stats['jobs_matched']}")
        logger.info(f"  Jobs saved: {stats['jobs_saved']}")

        if stats["errors"]:
            logger.warning(f"\n⚠️  Errors: {len(stats['errors'])}")
            for error in stats["errors"]:
                logger.warning(f"  - {error}")

        return stats

    def _get_sources(
        self, max_sources: Optional[int], source_ids: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Get sources to scrape.

        Args:
            max_sources: Maximum number of sources (None = unlimited)
            source_ids: Specific source IDs (None = all sources with rotation)

        Returns:
            List of source documents
        """
        if source_ids:
            # Get specific sources by ID
            sources = []
            for source_id in source_ids:
                source = self.sources_manager.get_source_by_id(source_id)
                if source:
                    sources.append(source)
                else:
                    logger.warning(f"Source not found: {source_id}")
            return sources
        else:
            # Use rotation (oldest lastScrapedAt first)
            return self._get_next_sources_by_rotation(max_sources)

    def _get_next_sources_by_rotation(self, limit: Optional[int]) -> List[Dict[str, Any]]:
        """
        Get next sources by intelligent rotation.

        Priority order:
        1. Health score (sources with better health scraped first)
        2. Tier (S > A > B > C > D)
        3. Last scraped (oldest first, never scraped first)
        4. Company fairness (less frequently scraped companies first)

        Args:
            limit: Maximum number of sources (None = all sources)

        Returns:
            List of source documents sorted by rotation priority
        """
        from datetime import datetime, timezone

        sources = self.sources_manager.get_active_sources()

        # Score each source
        scored_sources = []

        for source in sources:
            health = source.get("health", {})

            # Get health score (0-1, default 1.0 for new sources)
            health_score = health.get("healthScore", 1.0)

            # Get tier priority (S=0, A=1, B=2, C=3, D=4)
            tier = source.get("tier", "D")
            tier_priority = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}.get(tier, 4)

            # Get last scraped timestamp (prefer older or never scraped)
            # Use epoch for sources that were never scraped
            last_scraped = source.get("lastScrapedAt") or source.get("scraped_at")
            if last_scraped is None:
                last_scraped = datetime(1970, 1, 1, tzinfo=timezone.utc)

            # Get company fairness score (less scraped companies get higher priority)
            company_id = source.get("company_id", "")
            try:
                from job_finder.utils.source_health import CompanyScrapeTracker

                tracker = CompanyScrapeTracker(self.job_storage.db)
                company_scrape_freq = tracker.get_scrape_frequency(company_id)
            except Exception as e:
                logger.warning(f"Error getting company scrape frequency: {e}")
                company_scrape_freq = 0.0

            scored_sources.append(
                {
                    "source": source,
                    "health_score": health_score,
                    "tier_priority": tier_priority,
                    "last_scraped": last_scraped,
                    "company_scrape_freq": company_scrape_freq,
                }
            )

        # Sort by: health_score DESC, tier priority ASC, last_scraped ASC, company_freq ASC
        scored_sources.sort(
            key=lambda x: (
                -x["health_score"],  # Higher health first
                x["tier_priority"],  # Better tier first (S before A, etc)
                x["last_scraped"],  # Oldest first (never scraped = epoch = first)
                x["company_scrape_freq"],  # Less scraped companies first
            )
        )

        logger.debug("Source rotation order:")
        for i, scored in enumerate(scored_sources[:5]):
            logger.debug(
                f"  {i + 1}. {scored['source'].get('name')} "
                f"(health={scored['health_score']:.2f}, tier={scored['source'].get('tier', 'D')})"
            )

        # Return limited or all sources
        if limit is None:
            return [s["source"] for s in scored_sources]
        else:
            return [s["source"] for s in scored_sources[:limit]]

    def _scrape_source(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape a single source and analyze jobs.

        Args:
            source: Source document from Firestore

        Returns:
            Dictionary with scraping stats
        """
        source_type = source.get("sourceType")
        source_name = source.get("name", "Unknown")
        config = source.get("config", {})

        logger.info(f"\n📡 Scraping source: {source_name} ({source_type})")

        stats = {
            "jobs_found": 0,
            "remote_jobs": 0,
            "jobs_filtered_by_role": 0,
            "duplicates_skipped": 0,
            "jobs_analyzed": 0,
            "jobs_matched": 0,
            "jobs_saved": 0,
        }

        # Create appropriate scraper and scrape jobs
        jobs = []
        if source_type == "greenhouse":
            board_token = config.get("board_token")
            if not board_token:
                raise ConfigurationError(f"Source {source_name} missing board_token in config")
            # Pass full config dict to scraper
            scraper = GreenhouseScraper(config)
            jobs = scraper.scrape()
        elif source_type == "rss":
            rss_url = config.get("url")
            if not rss_url:
                raise ConfigurationError(f"Source {source_name} missing url in config")
            # RSS scraper requires listing_config - create empty dict for now
            from job_finder.scrapers.rss_scraper import RSSJobScraper

            scraper_rss = RSSJobScraper(rss_url, listing_config={})
            jobs = scraper_rss.scrape()
        else:
            logger.warning(f"Unsupported source type: {source_type}")
            return stats
        stats["jobs_found"] = len(jobs)
        logger.info(f"  Found {len(jobs)} jobs")

        if not jobs:
            return stats

        # Process each job
        for job in jobs:
            # Step 1: Job type and seniority filter
            title = job.get("title", "")
            description = job.get("description", "")
            # Handle case where profile.preferences may be None
            strict_role_filter = (
                self.profile.preferences.get("strict_role_filter", True)
                if self.profile.preferences
                else True
            )
            min_seniority = (
                self.profile.preferences.get("min_seniority") if self.profile.preferences else None
            )

            filter_decision, filter_reason = filter_job(
                title=title,
                description=description,
                strict_role_filter=strict_role_filter,
                min_seniority=min_seniority,
            )

            if filter_decision == FilterDecision.REJECT:
                logger.debug(f"  ✗ Filtered: {job.get('title')} - {filter_reason}")
                stats["jobs_filtered_by_role"] += 1
                continue

            stats["remote_jobs"] += 1

            # Step 2: Check for duplicates
            if self.job_storage.job_exists(job.get("url", "")):
                logger.debug(f"  ⊘ Duplicate: {job.get('title')}")
                stats["duplicates_skipped"] += 1
                continue

            # Step 3: Ensure company exists
            company_name = job.get("company", "Unknown")
            company_website = job.get("company_website", "")

            if company_name and company_website:
                company = self.companies_manager.get_or_create_company(
                    company_name=company_name,
                    company_website=company_website,
                    fetch_info_func=self.company_info_fetcher.fetch_company_info,
                )
                job["companyId"] = company.get("id")
                job["company_info"] = self._build_company_info_string(company)

            # Step 4: AI matching
            stats["jobs_analyzed"] += 1
            result = self.ai_matcher.analyze_job(job)

            if not result:
                logger.debug(f"  ✗ Below threshold: {job.get('title')} at {company_name}")
                continue

            # Job matched!
            stats["jobs_matched"] += 1
            stats["jobs_saved"] += 1

            # Save to Firestore
            doc_id = self.job_storage.save_job_match(job, result)
            logger.info(
                f"  ✓ MATCH: {job.get('title')} at {company_name} "
                f"(Score: {result.match_score}, ID: {doc_id})"
            )

        return stats

    def _build_company_info_string(self, company_info: Dict[str, Any]) -> str:
        """Build formatted company info string."""
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
