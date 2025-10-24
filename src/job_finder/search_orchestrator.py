"""Main job search orchestrator that coordinates scraping, matching, and storage."""

import logging
import os
import time
from typing import Any, Dict, List, Optional

from job_finder.ai import AIJobMatcher
from job_finder.ai.providers import create_provider
from job_finder.company_info_fetcher import CompanyInfoFetcher
from job_finder.exceptions import InitializationError
from job_finder.profile import FirestoreProfileLoader
from job_finder.profile.schema import Profile
from job_finder.scrapers.greenhouse_scraper import GreenhouseScraper
from job_finder.scrapers.rss_scraper import RSSJobScraper
from job_finder.storage import FirestoreJobStorage, JobSourcesManager
from job_finder.storage.companies_manager import CompaniesManager

logger = logging.getLogger(__name__)


class JobSearchOrchestrator:
    """Orchestrates job search across multiple sources with AI matching."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize job search orchestrator.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.profile: Optional[Profile] = None
        self.ai_matcher: Optional[AIJobMatcher] = None
        self.job_storage: Optional[FirestoreJobStorage] = None
        self.sources_manager: Optional[JobSourcesManager] = None
        self.companies_manager: Optional[CompaniesManager] = None
        self.company_info_fetcher: Optional[CompanyInfoFetcher] = None

    def run_search(self) -> Dict[str, Any]:
        """
        Run the complete job search pipeline.

        Returns:
            Dictionary with search results and statistics
        """
        logger.info("=" * 70)
        logger.info("STARTING JOB SEARCH")
        logger.info("=" * 70)

        # Step 1: Load profile
        logger.info("\n🔄 STEP 1: Loading profile...")
        self.profile = self._load_profile()
        logger.info(f"✓ Profile loaded: {self.profile.name}")
        logger.info(f"  - {len(self.profile.experience)} experiences")
        logger.info(f"  - {len(self.profile.skills)} skills")

        # Step 2: Initialize AI
        logger.info("\n🤖 STEP 2: Initializing AI matcher...")
        self.ai_matcher = self._initialize_ai()
        logger.info("✓ AI matcher initialized")

        # Step 3: Initialize storage
        logger.info("\n💾 STEP 3: Initializing Firestore storage...")
        self._initialize_storage()
        logger.info("✓ Storage initialized")

        # Step 4: Get active job sources
        logger.info("\n📋 STEP 4: Loading job sources...")
        listings = self._get_active_sources()
        logger.info(f"✓ Found {len(listings)} active job sources")

        # Step 5: Scrape and process each source
        stats = {
            "sources_scraped": 0,
            "total_jobs_found": 0,
            "jobs_after_remote_filter": 0,
            "jobs_filtered_by_role": 0,
            "duplicates_skipped": 0,
            "jobs_analyzed": 0,
            "jobs_matched": 0,
            "jobs_saved": 0,
            "errors": [],
        }

        max_total_jobs = self.config.get("search", {}).get("max_jobs", 10)
        jobs_saved = 0

        for listing in listings:
            if jobs_saved >= max_total_jobs:
                logger.info(f"\n⚠️  Reached maximum job limit ({max_total_jobs}), stopping search")
                break

            try:
                source_stats = self._process_listing(
                    listing, remaining_slots=max_total_jobs - jobs_saved
                )

                stats["sources_scraped"] += 1
                stats["total_jobs_found"] += source_stats["jobs_found"]
                stats["jobs_after_remote_filter"] += source_stats["remote_jobs"]
                stats["jobs_filtered_by_role"] += source_stats["jobs_filtered_by_role"]
                stats["duplicates_skipped"] += source_stats["duplicates_skipped"]
                stats["jobs_analyzed"] += source_stats["jobs_analyzed"]
                stats["jobs_matched"] += source_stats["jobs_matched"]
                stats["jobs_saved"] += source_stats["jobs_saved"]
                jobs_saved += source_stats["jobs_saved"]

            except Exception as e:
                error_msg = f"Error processing {listing.get('name')}: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

        # Final summary
        logger.info("\n" + "=" * 70)
        logger.info("✅ JOB SEARCH COMPLETE!")
        logger.info("=" * 70)
        logger.info("\n📊 STATISTICS:")
        logger.info(f"  Sources scraped: {stats['sources_scraped']}")
        logger.info(f"  Total jobs found: {stats['total_jobs_found']}")
        logger.info(f"  Remote jobs: {stats['jobs_after_remote_filter']}")
        logger.info(f"  Filtered by role/seniority: {stats['jobs_filtered_by_role']}")
        logger.info(f"  Duplicates skipped: {stats['duplicates_skipped']}")
        logger.info(f"  New jobs analyzed: {stats['jobs_analyzed']}")
        logger.info(f"  Jobs matched (>= threshold): {stats['jobs_matched']}")
        logger.info(f"  Jobs saved to Firestore: {stats['jobs_saved']}")

        if stats["errors"]:
            logger.warning(f"\n⚠️  Errors encountered: {len(stats['errors'])}")
            for error in stats["errors"]:
                logger.warning(f"  - {error}")

        return stats

    def _load_profile(self) -> Profile:
        """Load user profile from configured source."""
        profile_config = self.config.get("profile", {})
        source = profile_config.get("source", "json")

        if source == "firestore":
            firestore_config = profile_config.get("firestore", {})

            # Allow environment variable override for database name
            database_name = os.getenv(
                "PROFILE_DATABASE_NAME", firestore_config.get("database_name", "portfolio")
            )

            loader = FirestoreProfileLoader(database_name=database_name)
            profile = loader.load_profile(
                user_id=firestore_config.get("user_id"),
                name=firestore_config.get("name"),
                email=firestore_config.get("email"),
            )
        else:
            # JSON profile loading not yet implemented
            raise NotImplementedError("JSON profile loading not yet implemented")

        return profile

    def _initialize_ai(self) -> AIJobMatcher:
        """Initialize AI job matcher."""
        if not self.profile:
            raise InitializationError("Profile must be loaded before initializing AI matcher")

        ai_config = self.config.get("ai", {})

        provider = create_provider(
            provider_type=ai_config.get("provider", "claude"),
            model=ai_config.get("model", "claude-3-haiku-20240307"),
        )

        matcher = AIJobMatcher(
            provider=provider,
            profile=self.profile,
            min_match_score=ai_config.get("min_match_score", 70),
            generate_intake=ai_config.get("generate_intake_data", True),
            portland_office_bonus=ai_config.get("portland_office_bonus", 15),
            config=ai_config,
        )

        return matcher

    def _initialize_storage(self):
        """Initialize Firestore storage for job matches, sources, and companies."""
        storage_config = self.config.get("storage", {})

        # Allow environment variable override for database name
        database_name = os.getenv(
            "STORAGE_DATABASE_NAME", storage_config.get("database_name", "portfolio-staging")
        )

        self.job_storage = FirestoreJobStorage(database_name=database_name)
        self.sources_manager = JobSourcesManager(database_name=database_name)
        self.companies_manager = CompaniesManager(database_name=database_name)

        # Initialize company info fetcher with AI provider and config (shares same provider as AI matcher)
        self.company_info_fetcher = CompanyInfoFetcher(
            ai_provider=self.ai_matcher.provider if self.ai_matcher else None,
            ai_config=self.config.get("ai", {}) if self.ai_matcher else {},
        )

    def _get_active_sources(self) -> List[Dict[str, Any]]:
        """Get active job sources from Firestore with linked company data.

        Returns sources with company data joined in, sorted by priority:
        - Sources with companyId will have company data attached
        - Sources without companies (RSS feeds, job boards) are included as-is
        - Sorted by company priority score for sources with companies

        Returns:
            List of source dictionaries with company data joined
        """
        if not self.sources_manager:
            raise InitializationError("SourcesManager not initialized")
        if not self.companies_manager:
            raise InitializationError("CompaniesManager not initialized")

        sources = self.sources_manager.get_active_sources()

        # Batch fetch all company data to avoid N+1 queries
        company_ids = [s.get("companyId") for s in sources if s.get("companyId")]
        companies_map = {}
        if company_ids:
            companies_map = self.companies_manager.batch_get_companies(company_ids)
            logger.debug(
                f"Batch fetched {len(companies_map)} companies for {len(company_ids)} source IDs"
            )

        # Enrich sources with company data where applicable
        enriched_sources = []
        for source in sources:
            company_id = source.get("companyId")

            if company_id and company_id in companies_map:
                # Add company priority data to source
                company = companies_map[company_id]
                source["hasPortlandOffice"] = company.get("hasPortlandOffice", False)
                source["techStack"] = company.get("techStack", [])
                source["tier"] = company.get("tier", "D")
                source["priorityScore"] = company.get("priorityScore", 0)
                source["company_website"] = company.get("website", "")
            elif company_id:
                # Company ID provided but not found in batch fetch
                logger.warning(f"Company {company_id} not found for source {source.get('name')}")
                source["hasPortlandOffice"] = False
                source["techStack"] = []
                source["tier"] = "D"
                source["priorityScore"] = 0
            else:
                # No company link (RSS feed, job board) - assign default priority
                source["hasPortlandOffice"] = False
                source["techStack"] = []
                source["tier"] = "D"
                source["priorityScore"] = 0

            enriched_sources.append(source)

        # Sort by priority score (highest first), then by name for consistency
        sorted_sources = sorted(
            enriched_sources,
            key=lambda x: (
                -(x.get("priorityScore", 0)),  # Higher score first (negative for descending)
                x.get("name", ""),  # Then alphabetically by name
            ),
        )

        # Log tier distribution
        tier_counts: Dict[str, int] = {}
        for source in sorted_sources:
            tier = source.get("tier", "Unknown")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        logger.info("  Priority distribution:")
        tier_order = ["S", "A", "B", "C", "D"]
        for tier in tier_order:
            if tier in tier_counts:
                tier_name = {
                    "S": "Perfect Match",
                    "A": "Excellent Match",
                    "B": "Good Match",
                    "C": "Moderate Match",
                    "D": "Basic Match",
                }.get(tier, tier)
                logger.info(f"    Tier {tier} ({tier_name}): {tier_counts[tier]} sources")

        return sorted_sources

    def _ensure_managers_initialized(self) -> None:
        """Ensure all required managers are initialized."""
        if not self.sources_manager:
            raise InitializationError("SourcesManager not initialized")
        if not self.companies_manager:
            raise InitializationError("CompaniesManager not initialized")
        if not self.ai_matcher:
            raise InitializationError("AIJobMatcher not initialized")
        if not self.job_storage:
            raise InitializationError("JobStorage not initialized")
        if not self.company_info_fetcher:
            raise InitializationError("CompanyInfoFetcher not initialized")

    def _process_listing(self, listing: Dict[str, Any], remaining_slots: int) -> Dict[str, Any]:
        """
        Process a single job listing source.

        Args:
            listing: Job listing configuration
            remaining_slots: Number of job slots remaining

        Returns:
            Statistics for this source
        """
        self._ensure_managers_initialized()
        listing_name = listing.get("name", "Unknown")

        # Log listing header
        self._log_listing_header(listing)

        stats = {
            "jobs_found": 0,
            "remote_jobs": 0,
            "jobs_filtered_by_role": 0,
            "duplicates_skipped": 0,
            "jobs_analyzed": 0,
            "jobs_matched": 0,
            "jobs_saved": 0,
        }

        try:
            # Step 1: Scrape jobs from source
            jobs = self._scrape_jobs_from_listing(listing)
            stats["jobs_found"] = len(jobs)
            logger.info(f"✓ Found {len(jobs)} jobs")

            if not jobs:
                self.sources_manager.update_scrape_status(
                    doc_id=listing["id"], status="success", jobs_found=0
                )
                return stats

            # Step 2: Fetch and attach company info to jobs
            self._fetch_and_attach_company_info(listing, jobs)

            # Step 3: Filter for remote jobs or Portland on-site
            remote_jobs = self._filter_remote_only(jobs)
            stats["remote_jobs"] = len(remote_jobs)
            logger.info(f"✓ {len(remote_jobs)} remote/Portland jobs after location filtering")

            if not remote_jobs:
                self.sources_manager.update_scrape_status(
                    doc_id=listing["id"], status="success", jobs_found=len(jobs)
                )
                return stats

            # Step 3.5: Filter out jobs older than 1 week
            fresh_jobs = self._filter_by_age(remote_jobs, max_days=7)
            logger.info(f"✓ {len(fresh_jobs)} jobs after age filtering (<= 7 days)")

            if not fresh_jobs:
                self.sources_manager.update_scrape_status(
                    doc_id=listing["id"], status="success", jobs_found=len(jobs)
                )
                return stats

            # Step 3.75: Filter by job type and seniority (BEFORE AI analysis to save costs)
            role_filtered_jobs, filter_stats = self._filter_by_job_type(fresh_jobs)
            stats["jobs_filtered_by_role"] = sum(filter_stats.values())
            logger.info(f"✓ {len(role_filtered_jobs)} jobs after role/seniority filtering")

            if not role_filtered_jobs:
                self.sources_manager.update_scrape_status(
                    doc_id=listing["id"], status="success", jobs_found=len(jobs)
                )
                return stats

            # Step 4: Check for duplicates
            jobs_to_process = role_filtered_jobs[:remaining_slots]
            logger.info(f"✓ Processing {len(jobs_to_process)} jobs (limit: {remaining_slots})")

            existing_jobs, duplicates_count, new_jobs_count = self._check_for_duplicates(
                jobs_to_process
            )
            stats["duplicates_skipped"] = duplicates_count

            # Step 5: Match and save new jobs
            matched_stats = self._match_and_save_jobs(
                jobs_to_process, existing_jobs, new_jobs_count, listing
            )
            stats["jobs_analyzed"] = matched_stats["jobs_analyzed"]
            stats["jobs_matched"] = matched_stats["jobs_matched"]
            stats["jobs_saved"] = matched_stats["jobs_saved"]

            # Update source stats
            self.sources_manager.update_scrape_status(
                doc_id=listing["id"],
                status="success",
                jobs_found=len(jobs),
                jobs_matched=stats["jobs_matched"],
            )

            logger.info(f"✓ Completed {listing_name}: {stats['jobs_saved']} jobs saved")

        except Exception as e:
            logger.error(f"Error processing {listing_name}: {str(e)}")
            self.sources_manager.update_scrape_status(
                doc_id=listing["id"], status="error", error=str(e)
            )
            raise

        return stats

    def _log_listing_header(self, listing: Dict[str, Any]) -> None:
        """
        Log formatted header for a job listing source.

        Args:
            listing: Job listing configuration
        """
        listing_name = listing.get("name", "Unknown")
        source_type = listing.get("sourceType", "unknown")
        priority_score = listing.get("priorityScore", 0)
        tier = listing.get("tier", "?")

        # Add tier emoji
        tier_emoji = {"S": "⭐", "A": "🔷", "B": "🟢", "C": "🟡", "D": "⚪"}.get(tier, "❓")

        # Add Portland icon if applicable
        portland_icon = "🏙️ " if listing.get("hasPortlandOffice", False) else ""

        logger.info(
            f"\n{tier_emoji} {portland_icon}Processing: {listing_name} "
            f"(Tier {tier}, Score: {priority_score})"
        )
        logger.info(f"   Source Type: {source_type}")
        logger.info("-" * 70)

    def _scrape_jobs_from_listing(self, listing: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape jobs from a source based on its source type.

        Args:
            listing: Job source configuration (with company data joined)

        Returns:
            List of scraped job dictionaries

        Raises:
            ValueError: If source type is unsupported
        """
        source_type = listing.get("sourceType", "unknown")
        listing_name = listing.get("name", "Unknown")
        source_config = listing.get("config", {})

        if source_type == "rss":
            rss_scraper = RSSJobScraper(
                config=self.config.get("scraping", {}), listing_config=source_config
            )
            return rss_scraper.scrape()

        elif source_type == "greenhouse":
            # Get board_token from config
            board_token = source_config.get("board_token")
            greenhouse_config = {
                "board_token": board_token,
                "name": listing.get("companyName", listing.get("name", "Unknown")),
                "company_website": listing.get("company_website", ""),
            }
            greenhouse_scraper = GreenhouseScraper(greenhouse_config)
            return greenhouse_scraper.scrape()

        elif source_type == "api":
            logger.warning(f"API scraping not yet implemented for {listing_name}")
            return []

        elif source_type == "company-page":
            logger.warning(f"Company page scraping not yet implemented for {listing_name}")
            return []

        else:
            logger.warning(f"Unknown source type: {source_type}")
            return []

    def _fetch_and_attach_company_info(
        self, listing: Dict[str, Any], jobs: List[Dict[str, Any]]
    ) -> None:
        """
        Fetch company information and attach it to all jobs.

        Args:
            listing: Job source configuration (with company data joined if applicable)
            jobs: List of job dictionaries to update (modified in place)
        """
        company_id = listing.get("companyId")
        company_name = listing.get("companyName", listing.get("name", "Unknown"))
        company_website = listing.get("company_website", "")

        # If source has a company link, try to fetch from database first
        company_info = None
        if company_id:
            logger.info(f"🏢 Loading company info for {company_name} (ID: {company_id})...")
            company_info = self.companies_manager.get_company_by_id(company_id)

        # If no company link or not found, try to fetch by name/website
        if not company_info and company_website:
            logger.info(f"🏢 Fetching company info for {company_name}...")
            try:
                company_info = self.companies_manager.get_or_create_company(
                    company_name=company_name,
                    company_website=company_website,
                    fetch_info_func=self.company_info_fetcher.fetch_company_info,
                )
            except Exception as e:
                logger.warning(f"⚠️  Failed to fetch company info: {e}")

        # Build company info string
        if company_info:
            company_info_str = self._build_company_info_string(company_info)
            if company_info_str:
                logger.info(f"✓ Company info loaded ({len(company_info_str)} chars)")
            else:
                logger.info("⚠️  No company info found")
        else:
            company_info_str = ""
            logger.debug("No company info available")

        # Update all jobs with company info
        for job in jobs:
            job["company_info"] = company_info_str

    def _build_company_info_string(self, company_info: Dict[str, Any]) -> str:
        """
        Build a formatted company info string from company data.

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

    def _check_for_duplicates(self, jobs: List[Dict[str, Any]]) -> tuple[Dict[str, bool], int, int]:
        """
        Batch check which jobs already exist in the database.

        Args:
            jobs: List of jobs to check

        Returns:
            Tuple of (existing_jobs_dict, duplicates_count, new_jobs_count)
        """
        job_urls = [job.get("url", "") for job in jobs]
        existing_jobs = self.job_storage.batch_check_exists(job_urls)

        duplicates_count = sum(1 for exists in existing_jobs.values() if exists)
        new_jobs_count = sum(1 for exists in existing_jobs.values() if not exists)

        if duplicates_count > 0:
            logger.info(f"⏭️  Skipping {duplicates_count} duplicate jobs (already in database)")
        logger.info(f"✓ {new_jobs_count} new jobs to analyze")

        return existing_jobs, duplicates_count, new_jobs_count

    def _match_and_save_jobs(
        self,
        jobs: List[Dict[str, Any]],
        existing_jobs: Dict[str, bool],
        new_jobs_count: int,
        listing: Dict[str, Any],
    ) -> Dict[str, int]:
        """
        Run AI matching on new jobs and save matched results.

        Args:
            jobs: List of jobs to process
            existing_jobs: Dictionary mapping job URLs to existence status
            new_jobs_count: Number of new (non-duplicate) jobs
            listing: Job listing configuration

        Returns:
            Statistics dictionary with jobs_analyzed, jobs_matched, jobs_saved
        """
        stats = {"jobs_analyzed": 0, "jobs_matched": 0, "jobs_saved": 0}

        processed = 0
        for i, job in enumerate(jobs, 1):
            try:
                job_url = job.get("url", "")

                # Skip if already exists
                if existing_jobs.get(job_url, False):
                    logger.debug(f"  [{i}/{len(jobs)}] Duplicate: {job.get('title')}")
                    continue

                processed += 1
                stats["jobs_analyzed"] += 1

                # Run AI matching (pass Portland office status for bonus)
                logger.info(
                    f"  [{processed}/{new_jobs_count}] Analyzing: "
                    f"{job.get('title')} at {job.get('company')}"
                )
                has_portland_office = listing.get("hasPortlandOffice", False)
                result = self.ai_matcher.analyze_job(job, has_portland_office=has_portland_office)

                if result:
                    # Add companyId to job before saving (if source has a company link)
                    company_id = listing.get("companyId")
                    if company_id:
                        job["companyId"] = company_id

                    # Save to Firestore
                    doc_id = self.job_storage.save_job_match(job, result)
                    stats["jobs_matched"] += 1
                    stats["jobs_saved"] += 1
                    logger.info(
                        f"    ✓ Matched! Score: {result.match_score}, "
                        f"Priority: {result.application_priority} (ID: {doc_id})"
                    )
                else:
                    logger.debug("    ⚠️  Below match threshold")

                # Rate limiting
                delay = self.config.get("scraping", {}).get("delay_between_requests", 2)
                time.sleep(delay)

            except Exception as e:
                logger.warning(f"  Error processing job: {str(e)}")
                continue

        return stats

    def _filter_remote_only(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter jobs to only include remote positions or Portland, OR on-site/hybrid."""
        from job_finder.utils.common_filters import filter_remote_only

        return filter_remote_only(jobs)

    def _filter_by_age(self, jobs: List[Dict[str, Any]], max_days: int = 7) -> List[Dict[str, Any]]:
        """
        Filter jobs to only include those posted within the last N days.

        Args:
            jobs: List of jobs to filter
            max_days: Maximum age in days (default: 7)

        Returns:
            List of jobs posted within max_days
        """
        from job_finder.utils.common_filters import filter_by_age

        return filter_by_age(jobs, max_days=max_days, verbose=True)

    def _filter_by_job_type(
        self, jobs: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Filter jobs by role type and seniority before AI analysis to save costs.

        Args:
            jobs: List of jobs to filter

        Returns:
            Tuple of (filtered_jobs, filter_stats) where filter_stats contains
            counts of jobs filtered by each reason
        """
        from job_finder.utils.common_filters import filter_by_job_type

        filters_config = self.config.get("filters", {})
        return filter_by_job_type(jobs, filters_config, verbose=True)
