"""Main entry point for the job finder application."""

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from job_finder.ai import AIJobMatcher, JobMatchResult
from job_finder.ai.providers import create_provider
from job_finder.filters import JobFilter
from job_finder.logging_config import get_logger, setup_logging
from job_finder.profile import FirestoreProfileLoader, Profile, ProfileLoader
from job_finder.storage import JobStorage

# Configure logging (will be called in main())
logger = get_logger(__name__)


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_profile(config: Dict[str, Any]) -> Optional[Profile]:
    """
    Load user profile if configured.

    Args:
        config: Application configuration.

    Returns:
        Profile instance or None if not configured.
    """
    profile_config = config.get("profile", {})
    source = profile_config.get("source", "json").lower()

    # Load from Firestore
    if source == "firestore":
        try:
            logger.info("Loading profile from Firestore...")
            firestore_config = profile_config.get("firestore", {})

            loader = FirestoreProfileLoader(
                database_name=firestore_config.get("database_name", "portfolio")
            )

            profile = loader.load_profile(
                user_id=firestore_config.get("user_id"),
                name=firestore_config.get("name", "User"),
                email=firestore_config.get("email"),
            )

            logger.info(f"Loaded profile from Firestore for {profile.name}")
            return profile

        except Exception as e:
            logger.error(f"Error loading profile from Firestore: {str(e)}")
            logger.info("Make sure GOOGLE_APPLICATION_CREDENTIALS is set in .env")
            return None

    # Load from JSON file
    elif source == "json":
        profile_path = profile_config.get("profile_path")

        if not profile_path:
            logger.info("No profile path configured, skipping AI matching")
            return None

        try:
            profile = ProfileLoader.load_from_json(profile_path)
            logger.info(f"Loaded profile from JSON for {profile.name}")
            return profile
        except FileNotFoundError:
            logger.warning(f"Profile file not found: {profile_path}")
            logger.info(
                "Run 'python -m job_finder.main --create-profile data/profile.json' to create a template"
            )
            return None
        except Exception as e:
            logger.error(f"Error loading profile: {str(e)}")
            return None

    else:
        logger.error(f"Unknown profile source: {source}. Use 'json' or 'firestore'")
        return None


def apply_ai_matching(
    jobs: List[Dict[str, Any]], profile: Profile, config: Dict[str, Any]
) -> List[JobMatchResult]:
    """
    Apply AI-powered job matching to filter and analyze jobs.

    Args:
        jobs: List of job postings.
        profile: User profile.
        config: Application configuration.

    Returns:
        List of JobMatchResult objects.
    """
    ai_config = config.get("ai", {})

    if not ai_config.get("enabled", False):
        logger.info("AI matching disabled in configuration")
        return []

    try:
        # Create AI provider
        provider_type = ai_config.get("provider", "claude")
        model = ai_config.get("model")
        provider = create_provider(provider_type, model=model)

        # Create matcher
        matcher = AIJobMatcher(
            provider=provider,
            profile=profile,
            min_match_score=ai_config.get("min_match_score", 70),
            generate_intake=ai_config.get("generate_intake_data", True),
        )

        # Analyze jobs
        logger.info(f"Analyzing {len(jobs)} jobs with AI matcher...")
        results = matcher.analyze_jobs(jobs)
        logger.info(f"AI matching complete: {len(results)} jobs meet criteria")

        return results

    except Exception as e:
        logger.error(f"Error during AI matching: {str(e)}")
        return []


def main() -> None:
    """Main execution function."""
    # Set up logging first (before any logging calls)
    setup_logging()

    parser = argparse.ArgumentParser(description="Job Finder - Scrape and filter job postings")
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)",
    )
    parser.add_argument("--output", help="Override output file path from config")
    parser.add_argument(
        "--create-profile", metavar="PATH", help="Create a profile template at the specified path"
    )
    args = parser.parse_args()

    # Handle profile template creation
    if args.create_profile:
        ProfileLoader.create_template(args.create_profile)
        print(f"Profile template created at: {args.create_profile}")
        print("Edit this file with your information, then set profile.profile_path in config.yaml")
        return

    # Load configuration
    config = load_config(args.config)

    if args.output:
        config["output"]["file_path"] = args.output

    logger.info("Starting job finder...")

    # Load profile if configured
    profile = load_profile(config)

    # TODO: Initialize and run scrapers for each enabled site
    # scrapers = initialize_scrapers(config)
    # all_jobs = []
    # for scraper in scrapers:
    #     jobs = scraper.scrape()
    #     all_jobs.extend(jobs)

    all_jobs = []  # Placeholder

    logger.info(f"Scraped {len(all_jobs)} total jobs")

    # Apply traditional filtering (if no AI or as pre-filter)
    job_filter = JobFilter(config)
    filtered_jobs = job_filter.filter_jobs(all_jobs)

    logger.info(f"After basic filtering: {len(filtered_jobs)} jobs")

    # Apply AI matching if profile is available
    ai_results = []
    if profile and config.get("ai", {}).get("enabled", False):
        ai_results = apply_ai_matching(filtered_jobs, profile, config)

        # Convert AI results to job dictionaries with analysis data
        jobs_with_analysis = []
        for result in ai_results:
            # Find the original job data
            original_job = next((j for j in filtered_jobs if j.get("url") == result.job_url), None)
            if original_job:
                # Add AI analysis to job data
                job_with_ai = original_job.copy()
                job_with_ai["ai_analysis"] = {
                    "match_score": result.match_score,
                    "matched_skills": result.matched_skills,
                    "missing_skills": result.missing_skills,
                    "experience_match": result.experience_match,
                    "key_strengths": result.key_strengths,
                    "potential_concerns": result.potential_concerns,
                    "application_priority": result.application_priority,
                    "customization_recommendations": result.customization_recommendations,
                    "resume_intake_data": result.resume_intake_data,
                }
                jobs_with_analysis.append(job_with_ai)

        logger.info(f"AI matching found {len(jobs_with_analysis)} high-quality matches")
        final_jobs = jobs_with_analysis
    else:
        final_jobs = filtered_jobs

    # Save results
    storage = JobStorage(config)
    storage.save(final_jobs)

    logger.info(f"Results saved to {config['output']['file_path']}")
    logger.info(f"Final count: {len(final_jobs)} jobs")

    # Print summary
    print("\n" + "=" * 60)
    print("JOB FINDER SUMMARY")
    print("=" * 60)
    print(f"Total jobs scraped: {len(all_jobs)}")
    print(f"After basic filtering: {len(filtered_jobs)}")
    if ai_results:
        print(f"After AI matching: {len(ai_results)}")
        print(f"\nApplication Priority Breakdown:")
        high = sum(1 for r in ai_results if r.application_priority == "High")
        medium = sum(1 for r in ai_results if r.application_priority == "Medium")
        low = sum(1 for r in ai_results if r.application_priority == "Low")
        print(f"  High:   {high}")
        print(f"  Medium: {medium}")
        print(f"  Low:    {low}")
    print(f"\nResults saved to: {config['output']['file_path']}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
