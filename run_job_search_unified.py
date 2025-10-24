#!/usr/bin/env python3
"""Unified job search entry point with configurable options."""

import argparse
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from job_finder.logging_config import setup_logging
from job_finder.search_orchestrator import JobSearchOrchestrator


def main():
    """Run job search with command-line configuration."""
    parser = argparse.ArgumentParser(description="Run job finder search")
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        help="Override max jobs to analyze (default: use config value)",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "quick"],
        default="full",
        help="Output mode: 'full' (detailed) or 'quick' (summary only)",
    )
    parser.add_argument(
        "--no-env",
        action="store_true",
        help="Skip loading .env file",
    )

    args = parser.parse_args()

    # Load environment variables (unless --no-env)
    if not args.no_env:
        load_dotenv()

    # Configure logging
    setup_logging()

    # Print header for full mode
    if args.mode == "full":
        print("=" * 70)
        print("JOB SEARCH - FULL PIPELINE")
        print("=" * 70)

    # Load configuration
    if args.mode == "full":
        print(f"\n📋 Loading configuration from: {args.config}")

    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    # Override max_jobs if specified
    if args.max_jobs:
        config.setdefault("search", {})["max_jobs"] = args.max_jobs

    # Print config summary for full mode
    if args.mode == "full":
        print(f"✓ Configuration loaded")
        print(f"  - Profile source: {config.get('profile', {}).get('source')}")
        print(f"  - Storage database: {config.get('storage', {}).get('database_name')}")
        print(f"  - Max jobs: {config.get('search', {}).get('max_jobs')}")
        print(f"  - Remote only: {config.get('search', {}).get('remote_only')}")
        print(f"  - Min match score: {config.get('ai', {}).get('min_match_score')}")

    # Create and run orchestrator
    orchestrator = JobSearchOrchestrator(config)

    try:
        stats = orchestrator.run_search()

        # Print results
        print("\n" + "=" * 70)
        if args.mode == "full":
            print("🎉 JOB SEARCH COMPLETED SUCCESSFULLY!")
        else:
            print("SEARCH COMPLETE!")
        print("=" * 70)

        # Print stats
        print(f"Jobs saved: {stats['jobs_saved']}")
        print(f"Jobs matched: {stats['jobs_matched']}")
        print(f"Jobs analyzed: {stats['jobs_analyzed']}")

        # Print detailed instructions for full mode
        if args.mode == "full":
            database_name = config.get("storage", {}).get("database_name")
            print(f"\nTo view your job matches:")
            print(f"  1. Open Firebase Console")
            print(f"  2. Navigate to Firestore Database")
            print(f"  3. Select database: {database_name}")
            print(f"  4. View collection: job-matches")
            print(f"\nSaved {stats['jobs_saved']} job matches ready for document generation!")

        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error during job search: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
