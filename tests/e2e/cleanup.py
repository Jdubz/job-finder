#!/usr/bin/env python
"""
Cleanup script for E2E test data.

This script removes old test data from the staging database.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from job_finder.storage.firestore_client import FirestoreClient
from tests.e2e.helpers import CleanupHelper


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def print_separator():
    """Print separator line."""
    print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean up E2E test data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clean up all test data older than 24 hours
  python cleanup.py

  # Clean up data older than 1 hour
  python cleanup.py --max-age 1

  # Dry run (show what would be deleted)
  python cleanup.py --dry-run

  # Clean specific test run
  python cleanup.py --test-run-id e2e_test_abc123

  # Clean up failed items only
  python cleanup.py --failed-only

  # Verbose output
  python cleanup.py --verbose
        """,
    )

    parser.add_argument(
        "--database",
        default="portfolio-staging",
        help="Firestore database name (default: portfolio-staging)",
    )

    parser.add_argument(
        "--max-age",
        type=int,
        default=24,
        help="Maximum age in hours for test data (default: 24)",
    )

    parser.add_argument(
        "--test-run-id",
        help="Clean up specific test run ID",
    )

    parser.add_argument(
        "--failed-only",
        action="store_true",
        help="Only clean up failed queue items",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    print_separator()
    print("E2E TEST DATA CLEANUP")
    print_separator()
    print(f"Database: {args.database}")
    print(f"Max age: {args.max_age} hours")

    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)")

    print_separator()

    # Initialize Firestore and cleanup helper
    db = FirestoreClient.get_client(args.database)
    cleanup = CleanupHelper(db, args.database)

    # Perform cleanup based on arguments
    if args.test_run_id:
        print(f"\nCleaning up test run: {args.test_run_id}")

        if args.dry_run:
            # Just show what would be deleted
            for collection in ["job-queue", "job-matches"]:
                query = db.collection(collection).where("test_run_id", "==", args.test_run_id)
                docs = list(query.stream())
                print(f"  {collection}: {len(docs)} documents")
        else:
            results = cleanup.cleanup_by_test_run_id(args.test_run_id)
            for collection, count in results.items():
                print(f"  {collection}: {count} documents deleted")

    elif args.failed_only:
        print(f"\nCleaning up failed items older than {args.max_age} hours")

        if args.dry_run:
            candidates = cleanup.get_cleanup_candidates("job-queue", max_age_hours=args.max_age)
            failed = [c for c in candidates if c.get("status") == "failed"]
            print(f"  job-queue: {len(failed)} failed items")
        else:
            count = cleanup.cleanup_failed_items(max_age_hours=args.max_age)
            print(f"  Deleted: {count} failed items")

    else:
        print(f"\nCleaning up all test data older than {args.max_age} hours")

        if args.dry_run:
            # Show what would be deleted
            queue_candidates = cleanup.get_cleanup_candidates(
                "job-queue", max_age_hours=args.max_age
            )
            test_queue = [c for c in queue_candidates if c.get("source") == "e2e_test"]

            match_candidates = cleanup.get_cleanup_candidates(
                "job-matches", max_age_hours=args.max_age
            )
            test_matches = [c for c in match_candidates if c.get("company_name") == "Test Company"]

            print(f"  job-queue (e2e_test): {len(test_queue)} items")
            print(f"  job-matches (test): {len(test_matches)} items")

            # Show some examples
            if test_queue:
                print("\n  Example queue items:")
                for item in test_queue[:3]:
                    print(
                        f"    - {item.get('_id')}: {item.get('url')} "
                        f"(status: {item.get('status')})"
                    )

            if test_matches:
                print("\n  Example matches:")
                for item in test_matches[:3]:
                    print(
                        f"    - {item.get('_id')}: {item.get('title')} at "
                        f"{item.get('company_name')}"
                    )

        else:
            results = cleanup.cleanup_all_test_data(max_age_hours=args.max_age)

            print("\nResults:")
            for category, count in results.items():
                print(f"  {category}: {count} items deleted")

            total = sum(results.values())
            print(f"\nTotal deleted: {total} items")

    print_separator()

    if args.dry_run:
        print("DRY RUN COMPLETE - No changes were made")
    else:
        print("CLEANUP COMPLETE")

    print_separator()

    return 0


if __name__ == "__main__":
    sys.exit(main())
