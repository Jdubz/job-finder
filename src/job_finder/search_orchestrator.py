"""Main job search orchestrator that coordinates scraping, matching, and storage."""

import os
import logging
from typing import Dict, Any, List, Optional
import time

from job_finder.profile import FirestoreProfileLoader
from job_finder.profile.schema import Profile
from job_finder.ai import AIJobMatcher
from job_finder.ai.providers import create_provider
from job_finder.scrapers.rss_scraper import RSSJobScraper
from job_finder.scrapers.greenhouse_scraper import GreenhouseScraper
from job_finder.storage import FirestoreJobStorage, JobListingsManager
from job_finder.storage.companies_manager import CompaniesManager
from job_finder.company_info_fetcher import CompanyInfoFetcher

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
        self.listings_manager: Optional[JobListingsManager] = None
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

        # Step 4: Get active job listings
        logger.info("\n📋 STEP 4: Loading job source listings...")
        listings = self._get_active_listings()
        logger.info(f"✓ Found {len(listings)} active job sources")

        # Step 5: Scrape and process each source
        stats = {
            "sources_scraped": 0,
            "total_jobs_found": 0,
            "jobs_after_remote_filter": 0,
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
        logger.info(f"\n📊 STATISTICS:")
        logger.info(f"  Sources scraped: {stats['sources_scraped']}")
        logger.info(f"  Total jobs found: {stats['total_jobs_found']}")
        logger.info(f"  Remote jobs: {stats['jobs_after_remote_filter']}")
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
        )

        return matcher

    def _initialize_storage(self):
        """Initialize Firestore storage for job matches, listings, and companies."""
        storage_config = self.config.get("storage", {})

        # Allow environment variable override for database name
        database_name = os.getenv(
            "STORAGE_DATABASE_NAME", storage_config.get("database_name", "portfolio-staging")
        )

        self.job_storage = FirestoreJobStorage(database_name=database_name)
        self.listings_manager = JobListingsManager(database_name=database_name)
        self.companies_manager = CompaniesManager(database_name=database_name)

        # Initialize company info fetcher with AI provider (shares same provider as AI matcher)
        self.company_info_fetcher = CompanyInfoFetcher(
            ai_provider=self.ai_matcher.provider if self.ai_matcher else None
        )

    def _get_active_listings(self) -> List[Dict[str, Any]]:
        """Get active job source listings from Firestore, sorted by priority score.

        Returns listings in priority order:
        - Tier S (100+): Portland office + strong tech match
        - Tier A (70-99): Perfect tech matches
        - Tier B (50-69): Good matches
        - Tier C (30-49): Moderate matches
        - Tier D (0-29): Basic matches/job boards
        """
        listings = self.listings_manager.get_active_listings()

        # Sort by priority score (highest first), then by name for consistency
        sorted_listings = sorted(
            listings,
            key=lambda x: (
                -(x.get("priorityScore", 0)),  # Higher score first (negative for descending)
                x.get("name", ""),  # Then alphabetically by name
            ),
        )

        # Log tier distribution
        tier_counts = {}
        for listing in sorted_listings:
            tier = listing.get("tier", "Unknown")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        logger.info(f"  Priority distribution:")
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

        return sorted_listings

    def _process_listing(self, listing: Dict[str, Any], remaining_slots: int) -> Dict[str, Any]:
        """
        Process a single job listing source.

        Args:
            listing: Job listing configuration
            remaining_slots: Number of job slots remaining

        Returns:
            Statistics for this source
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
            f"\n{tier_emoji} {portland_icon}Processing: {listing_name} (Tier {tier}, Score: {priority_score})"
        )
        logger.info(f"   Source Type: {source_type}")
        logger.info("-" * 70)

        stats = {
            "jobs_found": 0,
            "remote_jobs": 0,
            "duplicates_skipped": 0,
            "jobs_analyzed": 0,
            "jobs_matched": 0,
            "jobs_saved": 0,
        }

        try:
            # Scrape based on source type
            jobs = []

            if source_type == "rss":
                scraper = RSSJobScraper(
                    config=self.config.get("scraping", {}), listing_config=listing.get("config", {})
                )
                jobs = scraper.scrape()

            elif source_type == "greenhouse":
                # Greenhouse ATS scraper
                greenhouse_config = {
                    "board_token": listing.get("board_token"),
                    "name": listing.get("name", "Unknown"),
                    "company_website": listing.get("company_website", ""),
                }
                scraper = GreenhouseScraper(greenhouse_config)
                jobs = scraper.scrape()

            elif source_type == "api":
                logger.warning(f"API scraping not yet implemented for {listing_name}")
                return stats

            elif source_type == "company-page":
                logger.warning(f"Company page scraping not yet implemented for {listing_name}")
                return stats

            else:
                logger.warning(f"Unknown source type: {source_type}")
                return stats

            stats["jobs_found"] = len(jobs)
            logger.info(f"✓ Found {len(jobs)} jobs")

            if not jobs:
                self.listings_manager.update_scrape_status(
                    doc_id=listing["id"], status="success", jobs_found=0
                )
                return stats

            # Fetch and cache company information
            company_name = listing.get("name", "Unknown")
            company_website = listing.get("company_website", "")

            if company_website:
                logger.info(f"🏢 Fetching company info for {company_name}...")
                try:
                    company_info = self.companies_manager.get_or_create_company(
                        company_name=company_name,
                        company_website=company_website,
                        fetch_info_func=self.company_info_fetcher.fetch_company_info,
                    )

                    # Extract about/culture fields
                    company_about = company_info.get("about", "")
                    company_culture = company_info.get("culture", "")
                    company_mission = company_info.get("mission", "")

                    # Combine into a single company_info string
                    company_info_parts = []
                    if company_about:
                        company_info_parts.append(f"About: {company_about}")
                    if company_culture:
                        company_info_parts.append(f"Culture: {company_culture}")
                    if company_mission:
                        company_info_parts.append(f"Mission: {company_mission}")

                    company_info_str = "\n\n".join(company_info_parts)

                    # Update all jobs with company info
                    for job in jobs:
                        job["company_info"] = company_info_str

                    if company_info_str:
                        logger.info(f"✓ Company info cached ({len(company_info_str)} chars)")
                    else:
                        logger.info(f"⚠️  No company info found")

                except Exception as e:
                    logger.warning(f"⚠️  Failed to fetch company info: {e}")
                    # Continue without company info
                    for job in jobs:
                        job["company_info"] = ""
            else:
                logger.debug("No company website available, skipping company info fetch")
                for job in jobs:
                    job["company_info"] = ""

            # Filter for remote jobs
            remote_jobs = self._filter_remote_only(jobs)
            stats["remote_jobs"] = len(remote_jobs)
            logger.info(f"✓ {len(remote_jobs)} remote jobs after filtering")

            if not remote_jobs:
                self.listings_manager.update_scrape_status(
                    doc_id=listing["id"], status="success", jobs_found=len(jobs)
                )
                return stats

            # Process up to remaining_slots
            jobs_to_process = remote_jobs[:remaining_slots]
            logger.info(f"✓ Processing {len(jobs_to_process)} jobs (limit: {remaining_slots})")

            # Batch check which jobs already exist
            job_urls = [job.get("url", "") for job in jobs_to_process]
            existing_jobs = self.job_storage.batch_check_exists(job_urls)

            duplicates_count = sum(1 for exists in existing_jobs.values() if exists)
            new_jobs_count = sum(1 for exists in existing_jobs.values() if not exists)

            stats["duplicates_skipped"] = duplicates_count

            if duplicates_count > 0:
                logger.info(f"⏭️  Skipping {duplicates_count} duplicate jobs (already in database)")
            logger.info(f"✓ {new_jobs_count} new jobs to analyze")

            # Run AI matching and save for new jobs only
            processed = 0
            for i, job in enumerate(jobs_to_process, 1):
                try:
                    job_url = job.get("url", "")

                    # Skip if already exists
                    if existing_jobs.get(job_url, False):
                        logger.debug(
                            f"  [{i}/{len(jobs_to_process)}] Duplicate: {job.get('title')}"
                        )
                        continue

                    processed += 1
                    stats["jobs_analyzed"] += 1

                    # Run AI matching (pass Portland office status for bonus)
                    logger.info(
                        f"  [{processed}/{new_jobs_count}] Analyzing: {job.get('title')} at {job.get('company')}"
                    )
                    has_portland_office = listing.get("hasPortlandOffice", False)
                    result = self.ai_matcher.analyze_job(
                        job, has_portland_office=has_portland_office
                    )

                    if result:
                        # Save to Firestore
                        doc_id = self.job_storage.save_job_match(job, result)
                        stats["jobs_matched"] += 1
                        stats["jobs_saved"] += 1
                        logger.info(
                            f"    ✓ Matched! Score: {result.match_score}, Priority: {result.application_priority} (ID: {doc_id})"
                        )

                    else:
                        logger.debug(f"    ⚠️  Below match threshold")

                    # Rate limiting
                    delay = self.config.get("scraping", {}).get("delay_between_requests", 2)
                    time.sleep(delay)

                except Exception as e:
                    logger.warning(f"  Error processing job: {str(e)}")
                    continue

            # Update listing stats
            self.listings_manager.update_scrape_status(
                doc_id=listing["id"],
                status="success",
                jobs_found=len(jobs),
                jobs_matched=stats["jobs_matched"],
            )

            logger.info(f"✓ Completed {listing_name}: {stats['jobs_saved']} jobs saved")

        except Exception as e:
            logger.error(f"Error processing {listing_name}: {str(e)}")
            self.listings_manager.update_scrape_status(
                doc_id=listing["id"], status="error", error=str(e)
            )
            raise

        return stats

    def _filter_remote_only(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter jobs to only include remote positions."""
        remote_keywords = ["remote", "work from home", "wfh", "anywhere", "distributed"]

        remote_jobs = []
        for job in jobs:
            location = job.get("location", "").lower()
            title = job.get("title", "").lower()
            description = job.get("description", "").lower()

            # Check if any remote keyword is in location, title, or description
            if any(keyword in location for keyword in remote_keywords):
                remote_jobs.append(job)
            elif any(keyword in title for keyword in remote_keywords):
                remote_jobs.append(job)
            elif any(keyword in description[:500] for keyword in remote_keywords):
                remote_jobs.append(job)

        return remote_jobs
