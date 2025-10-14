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
from job_finder.storage import FirestoreJobStorage, JobListingsManager

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
            "errors": []
        }

        max_total_jobs = self.config.get("search", {}).get("max_jobs", 10)
        jobs_saved = 0

        for listing in listings:
            if jobs_saved >= max_total_jobs:
                logger.info(f"\n⚠️  Reached maximum job limit ({max_total_jobs}), stopping search")
                break

            try:
                source_stats = self._process_listing(
                    listing,
                    remaining_slots=max_total_jobs - jobs_saved
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
                "PROFILE_DATABASE_NAME",
                firestore_config.get("database_name", "portfolio")
            )

            loader = FirestoreProfileLoader(database_name=database_name)
            profile = loader.load_profile(
                user_id=firestore_config.get("user_id"),
                name=firestore_config.get("name"),
                email=firestore_config.get("email")
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
            model=ai_config.get("model", "claude-3-haiku-20240307")
        )

        matcher = AIJobMatcher(
            provider=provider,
            profile=self.profile,
            min_match_score=ai_config.get("min_match_score", 70),
            generate_intake=ai_config.get("generate_intake_data", True)
        )

        return matcher

    def _initialize_storage(self):
        """Initialize Firestore storage for job matches and listings."""
        storage_config = self.config.get("storage", {})

        # Allow environment variable override for database name
        database_name = os.getenv(
            "STORAGE_DATABASE_NAME",
            storage_config.get("database_name", "portfolio-staging")
        )

        self.job_storage = FirestoreJobStorage(database_name=database_name)
        self.listings_manager = JobListingsManager(database_name=database_name)

    def _get_active_listings(self) -> List[Dict[str, Any]]:
        """Get active job source listings from Firestore."""
        return self.listings_manager.get_active_listings()

    def _process_listing(
        self,
        listing: Dict[str, Any],
        remaining_slots: int
    ) -> Dict[str, Any]:
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

        logger.info(f"\n⚡ Processing: {listing_name} ({source_type})")
        logger.info("-" * 70)

        stats = {
            "jobs_found": 0,
            "remote_jobs": 0,
            "duplicates_skipped": 0,
            "jobs_analyzed": 0,
            "jobs_matched": 0,
            "jobs_saved": 0
        }

        try:
            # Scrape based on source type
            jobs = []

            if source_type == "rss":
                scraper = RSSJobScraper(
                    config=self.config.get("scraping", {}),
                    listing_config=listing.get("config", {})
                )
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
                    doc_id=listing["id"],
                    status="success",
                    jobs_found=0
                )
                return stats

            # Filter for remote jobs
            remote_jobs = self._filter_remote_only(jobs)
            stats["remote_jobs"] = len(remote_jobs)
            logger.info(f"✓ {len(remote_jobs)} remote jobs after filtering")

            if not remote_jobs:
                self.listings_manager.update_scrape_status(
                    doc_id=listing["id"],
                    status="success",
                    jobs_found=len(jobs)
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
                        logger.debug(f"  [{i}/{len(jobs_to_process)}] Duplicate: {job.get('title')}")
                        continue

                    processed += 1
                    stats["jobs_analyzed"] += 1

                    # Run AI matching
                    logger.info(f"  [{processed}/{new_jobs_count}] Analyzing: {job.get('title')} at {job.get('company')}")
                    result = self.ai_matcher.analyze_job(job)

                    if result:
                        # Save to Firestore
                        doc_id = self.job_storage.save_job_match(job, result)
                        stats["jobs_matched"] += 1
                        stats["jobs_saved"] += 1
                        logger.info(f"    ✓ Matched! Score: {result.match_score}, Priority: {result.application_priority} (ID: {doc_id})")

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
                jobs_matched=stats["jobs_matched"]
            )

            logger.info(f"✓ Completed {listing_name}: {stats['jobs_saved']} jobs saved")

        except Exception as e:
            logger.error(f"Error processing {listing_name}: {str(e)}")
            self.listings_manager.update_scrape_status(
                doc_id=listing["id"],
                status="error",
                error=str(e)
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
