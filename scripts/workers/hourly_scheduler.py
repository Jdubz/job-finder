#!/usr/bin/env python3
"""
Hourly job scraper scheduler with intelligent source rotation.

Runs every hour during daytime (6am-10pm PT), rotating through sources
by lastScrapedAt and stopping after finding 5 potential job matches or
scraping all sources.
"""
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import yaml  # type: ignore[import-untyped]
from dotenv import load_dotenv

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from job_finder.ai import AIJobMatcher  # noqa: E402
from job_finder.ai.providers import create_provider  # noqa: E402
from job_finder.company_info_fetcher import CompanyInfoFetcher  # noqa: E402
from job_finder.logging_config import setup_logging  # noqa: E402
from job_finder.profile import FirestoreProfileLoader  # noqa: E402
from job_finder.queue import ConfigLoader  # noqa: E402
from job_finder.scrapers.greenhouse_scraper import GreenhouseScraper  # noqa: E402
from job_finder.scrapers.rss_scraper import RSSJobScraper  # noqa: E402
from job_finder.storage import FirestoreJobStorage  # noqa: E402
from job_finder.storage.companies_manager import CompaniesManager  # noqa: E402
from job_finder.storage.job_sources_manager import JobSourcesManager  # noqa: E402
from job_finder.utils.job_type_filter import filter_job  # noqa: E402

# Load environment variables
load_dotenv()

# Configure logging
log_file = os.getenv("SCHEDULER_LOG_FILE", "/app/logs/hourly_scheduler.log")
setup_logging(log_file=log_file)
logger = logging.getLogger(__name__)

# Pacific timezone
PT = ZoneInfo("America/Los_Angeles")


def is_daytime_hours(scheduler_settings: Optional[Dict[str, Any]] = None) -> bool:
    """
    Check if current time is within daytime hours.

    Args:
        scheduler_settings: Optional scheduler settings from Firestore
                          If provided, uses daytime_hours and timezone from settings

    Returns:
        True if within daytime hours, False otherwise
    """
    if scheduler_settings:
        # Use settings from Firestore
        daytime_hours = scheduler_settings.get("daytime_hours", {"start": 6, "end": 22})
        timezone_str = scheduler_settings.get("timezone", "America/Los_Angeles")
        tz = ZoneInfo(timezone_str)
        start_hour = daytime_hours.get("start", 6)
        end_hour = daytime_hours.get("end", 22)
    else:
        # Use defaults
        tz = PT
        start_hour = 6
        end_hour = 22

    now = datetime.now(tz)
    hour = now.hour
    return start_hour <= hour < end_hour


def get_next_sources(sources_manager: JobSourcesManager, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get next sources to scrape, ordered by lastScrapedAt (oldest first).

    Args:
        sources_manager: Job sources manager
        limit: Maximum number of sources to return

    Returns:
        List of source documents sorted by lastScrapedAt
    """
    sources = sources_manager.get_active_sources()

    # Sort by lastScrapedAt (None values first, then oldest to newest)
    def sort_key(source):
        last_scraped = source.get("lastScrapedAt")
        if last_scraped is None:
            # Never scraped - highest priority (use epoch)
            return datetime(1970, 1, 1, tzinfo=timezone.utc)
        return last_scraped

    sources_sorted = sorted(sources, key=sort_key)
    return sources_sorted[:limit]


def scrape_source(
    source: Dict[str, Any],
    ai_matcher: AIJobMatcher,
    job_storage: FirestoreJobStorage,
    companies_manager: CompaniesManager,
    company_info_fetcher: CompanyInfoFetcher,
    profile,
) -> Dict[str, Any]:
    """
    Scrape a single source and analyze jobs.

    Args:
        source: Source document from Firestore
        ai_matcher: AI job matcher
        job_storage: Job storage
        companies_manager: Companies manager
        company_info_fetcher: Company info fetcher
        profile: User profile

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

    try:
        # Create appropriate scraper
        scraper = None
        if source_type == "greenhouse":
            board_token = config.get("board_token")
            if not board_token:
                raise ValueError(f"Source {source_name} missing board_token in config")
            scraper = GreenhouseScraper(board_token)
        elif source_type == "rss":
            rss_url = config.get("url")
            if not rss_url:
                raise ValueError(f"Source {source_name} missing url in config")
            scraper = RSSJobScraper(rss_url)
        else:
            logger.warning(f"Unsupported source type: {source_type}")
            return stats

        # Scrape jobs
        jobs = scraper.scrape()
        stats["jobs_found"] = len(jobs)
        logger.info(f"  Found {len(jobs)} jobs")

        if not jobs:
            return stats

        # Process each job
        for job in jobs:
            # Step 1: Remote filter
            filter_result = filter_job(job, profile.preferences)
            if not filter_result.passed:
                logger.debug(f"  ✗ Filtered: {job.get('title')} - {filter_result.reason}")
                stats["jobs_filtered_by_role"] += 1
                continue

            stats["remote_jobs"] += 1

            # Step 2: Check for duplicates
            if job_storage.job_exists(job.get("url", "")):
                logger.debug(f"  ⊘ Duplicate: {job.get('title')}")
                stats["duplicates_skipped"] += 1
                continue

            # Step 3: Ensure company exists
            company_name = job.get("company", "Unknown")
            company_website = job.get("company_website", "")

            if company_name and company_website:
                company = companies_manager.get_or_create_company(
                    company_name=company_name,
                    company_website=company_website,
                    fetch_info_func=company_info_fetcher.fetch_company_info,
                )
                job["companyId"] = company.get("id")
                job["company_info"] = _build_company_info_string(company)

            # Step 4: AI matching
            stats["jobs_analyzed"] += 1
            result = ai_matcher.analyze_job(job)

            if not result:
                logger.debug(f"  ✗ Below threshold: {job.get('title')} at {company_name}")
                continue

            # Job matched!
            stats["jobs_matched"] += 1
            stats["jobs_saved"] += 1

            # Save to Firestore
            doc_id = job_storage.save_job_match(job, result)
            logger.info(
                f"  ✓ MATCH: {job.get('title')} at {company_name} "
                f"(Score: {result.match_score}, ID: {doc_id})"
            )

        return stats

    except Exception as e:
        logger.error(f"Error scraping source {source_name}: {e}", exc_info=True)
        raise


def _build_company_info_string(company_info: Dict[str, Any]) -> str:
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


def run_hourly_scrape(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run hourly scraping pass with rotation and early exit.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary with scraping statistics
    """
    logger.info("=" * 70)
    logger.info(f"HOURLY SCRAPE - {datetime.now(PT).isoformat()}")
    logger.info("=" * 70)

    # Get database name
    storage_db = os.getenv(
        "STORAGE_DATABASE_NAME",
        config.get("storage", {}).get("database_name", "portfolio-staging"),
    )
    profile_db = os.getenv(
        "PROFILE_DATABASE_NAME",
        config.get("profile", {}).get("firestore", {}).get("database_name", "portfolio"),
    )

    logger.info(f"Storage database: {storage_db}")
    logger.info(f"Profile database: {profile_db}")

    # Initialize config loader first to get scheduler settings
    config_loader = ConfigLoader(database_name=storage_db)
    
    # Load scheduler settings from Firestore
    logger.info("\n⚙️  Loading scheduler settings from Firestore...")
    scheduler_settings = config_loader.get_scheduler_settings()
    
    # Check if scheduler settings exist
    if scheduler_settings is None:
        logger.error("❌ Scheduler settings not found in Firestore!")
        logger.error("   The scheduler requires configuration to run.")
        logger.error("   Please run: python scripts/setup_firestore_config.py")
        logger.error(f"   Database: {storage_db}")
        logger.error(f"   Expected document: job-finder-config/scheduler-settings")
        return {"status": "error", "reason": "scheduler_settings_missing"}
    
    # Check if scheduler is enabled
    if not scheduler_settings.get("enabled", True):
        logger.info("🚫 Scheduler is DISABLED in Firestore config (scheduler-settings.enabled=false)")
        logger.info("   To enable: Update job-finder-config/scheduler-settings in Firestore")
        return {"status": "skipped", "reason": "scheduler_disabled"}
    
    logger.info(f"✓ Scheduler is enabled")
    logger.info(f"  Target matches: {scheduler_settings.get('target_matches', 5)}")
    logger.info(f"  Max sources: {scheduler_settings.get('max_sources', 10)}")
    logger.info(f"  Min match score: {scheduler_settings.get('min_match_score', 80)}")
    
    # Check if within daytime hours (using settings from Firestore)
    if not is_daytime_hours(scheduler_settings):
        daytime_hours = scheduler_settings.get("daytime_hours", {"start": 6, "end": 22})
        timezone_str = scheduler_settings.get("timezone", "America/Los_Angeles")
        logger.info(
            f"⏸️  Outside daytime hours "
            f"({daytime_hours['start']}:00-{daytime_hours['end']}:00 {timezone_str}), "
            f"skipping scrape"
        )
        return {"status": "skipped", "reason": "outside_daytime_hours"}

    # Initialize managers
    sources_manager = JobSourcesManager(database_name=storage_db)
    job_storage = FirestoreJobStorage(database_name=storage_db)
    companies_manager = CompaniesManager(database_name=storage_db)

    # Load profile
    logger.info("\n🔄 Loading profile...")
    profile_config = config.get("profile", {}).get("firestore", {})
    profile_loader = FirestoreProfileLoader(database_name=profile_db)
    profile = profile_loader.load_profile(
        user_id=profile_config.get("user_id"),
        name=profile_config.get("name", "User"),
        email=profile_config.get("email"),
    )
    logger.info(f"✓ Profile loaded: {profile.name}")

    # Initialize AI
    logger.info("\n🤖 Initializing AI matcher...")
    ai_config = config.get("ai", {})
    firestore_ai_settings = config_loader.get_ai_settings()
    ai_provider_type = firestore_ai_settings.get("provider", ai_config.get("provider", "claude"))
    ai_model = firestore_ai_settings.get("model", ai_config.get("model", "claude-3-haiku-20240307"))
    min_match_score = firestore_ai_settings.get(
        "minMatchScore", ai_config.get("min_match_score", 70)
    )

    provider = create_provider(provider_type=ai_provider_type, model=ai_model)
    ai_matcher = AIJobMatcher(
        provider=provider,
        profile=profile,
        min_match_score=min_match_score,
        generate_intake=ai_config.get("generate_intake_data", True),
        portland_office_bonus=ai_config.get("portland_office_bonus", 15),
        config=ai_config,
    )
    company_info_fetcher = CompanyInfoFetcher(ai_provider=provider, ai_config=ai_config)
    company_info_fetcher = CompanyInfoFetcher(ai_provider=provider, ai_config=ai_config)
    logger.info("✓ AI matcher initialized")

    # Get scheduler settings from Firestore (already loaded above)
    max_sources = scheduler_settings.get("max_sources", 10)
    target_matches = scheduler_settings.get("target_matches", 5)
    
    # Override min_match_score if specified in scheduler settings
    scheduler_min_score = scheduler_settings.get("min_match_score")
    if scheduler_min_score is not None:
        ai_matcher.min_match_score = scheduler_min_score
        logger.info(f"  Overriding min_match_score from scheduler: {scheduler_min_score}")

    # Get next sources to scrape (rotation)
    logger.info("\n📋 Getting next sources to scrape...")
    sources = get_next_sources(sources_manager, limit=max_sources)
    logger.info(f"✓ Found {len(sources)} sources in rotation")
    logger.info(f"  Target matches: {target_matches}")
    logger.info(f"  Max sources: {max_sources}")

    # Scraping stats
    total_stats = {
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
    potential_matches = 0  # Tracks jobs that went to AI analysis

    for source in sources:
        if potential_matches >= target_matches:
            logger.info(f"\n✅ Found {potential_matches} potential matches, stopping early")
            break

        try:
            source_stats = scrape_source(
                source,
                ai_matcher,
                job_storage,
                companies_manager,
                company_info_fetcher,
                profile,
            )

            # Update source's lastScrapedAt
            sources_manager.update_scrape_status(
                source["id"],
                status="success",
                jobs_found=source_stats["jobs_found"],
                jobs_matched=source_stats["jobs_matched"],
            )

            # Update totals
            total_stats["sources_scraped"] += 1
            total_stats["total_jobs_found"] += source_stats["jobs_found"]
            total_stats["remote_jobs"] += source_stats["remote_jobs"]
            total_stats["jobs_filtered_by_role"] += source_stats["jobs_filtered_by_role"]
            total_stats["duplicates_skipped"] += source_stats["duplicates_skipped"]
            total_stats["jobs_analyzed"] += source_stats["jobs_analyzed"]
            total_stats["jobs_matched"] += source_stats["jobs_matched"]
            total_stats["jobs_saved"] += source_stats["jobs_saved"]

            # Track potential matches (jobs that made it to AI analysis)
            potential_matches += source_stats["jobs_analyzed"]

        except Exception as e:
            error_msg = f"Error processing {source.get('name')}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            total_stats["errors"].append(error_msg)

            # Update source status with error
            sources_manager.update_scrape_status(source["id"], status="error", error=str(e))

    # Final summary
    logger.info("\n" + "=" * 70)
    logger.info("✅ HOURLY SCRAPE COMPLETE")
    logger.info("=" * 70)
    logger.info(f"\n📊 STATISTICS:")
    logger.info(f"  Sources scraped: {total_stats['sources_scraped']}")
    logger.info(f"  Total jobs found: {total_stats['total_jobs_found']}")
    logger.info(f"  Remote jobs: {total_stats['remote_jobs']}")
    logger.info(f"  Filtered by role: {total_stats['jobs_filtered_by_role']}")
    logger.info(f"  Duplicates skipped: {total_stats['duplicates_skipped']}")
    logger.info(f"  Jobs analyzed (potential matches): {total_stats['jobs_analyzed']}")
    logger.info(f"  Jobs matched: {total_stats['jobs_matched']}")
    logger.info(f"  Jobs saved: {total_stats['jobs_saved']}")

    if total_stats["errors"]:
        logger.warning(f"\n⚠️  Errors: {len(total_stats['errors'])}")
        for error in total_stats["errors"]:
            logger.warning(f"  - {error}")

    return total_stats


def main():
    """Main entry point."""
    try:
        # Load config
        config_path = os.getenv("CONFIG_PATH", "config/config.yaml")
        logger.info(f"Loading configuration from: {config_path}")

        if not Path(config_path).exists():
            logger.error(f"Configuration file not found: {config_path}")
            return 1

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Run hourly scrape
        stats = run_hourly_scrape(config)

        if stats.get("status") == "skipped":
            return 0

        # Return error code if there were errors
        if stats.get("errors"):
            return 1

        return 0

    except Exception as e:
        logger.error(f"Fatal error in hourly scheduler: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
