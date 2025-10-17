#!/usr/bin/env python3
"""
CLI tool to trigger on-demand job scraping.

Creates a SCRAPE queue item with custom configuration.
The queue worker will pick it up and process it.
"""
import argparse
import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

from job_finder.queue import QueueManager
from job_finder.queue.models import JobQueueItem, QueueItemType, ScrapeConfig

# Load environment variables
load_dotenv()


def trigger_scrape(
    target_matches: int = 5,
    max_sources: int = 20,
    source_ids: list[str] | None = None,
    min_match_score: int | None = None,
    database: str = "portfolio-staging",
    force: bool = False,
) -> str:
    """
    Trigger a scrape by creating a queue item.

    Args:
        target_matches: Number of potential matches to find before stopping
        max_sources: Maximum number of sources to scrape
        source_ids: Specific source IDs to scrape (None = rotation)
        min_match_score: Override minimum match score threshold
        database: Database name
        force: Force trigger even if pending scrape exists

    Returns:
        Queue item ID
    """
    print("=" * 70)
    print("TRIGGERING ON-DEMAND SCRAPE")
    print("=" * 70)
    print(f"Database: {database}")
    print(f"Target matches: {target_matches}")
    print(f"Max sources: {max_sources}")
    if source_ids:
        print(f"Specific sources: {source_ids}")
    if min_match_score:
        print(f"Min match score override: {min_match_score}")
    print("")

    # Initialize queue manager
    queue_manager = QueueManager(database_name=database)

    # Check for existing pending scrape
    if not force and queue_manager.has_pending_scrape():
        print("⚠️  WARNING: There is already a pending SCRAPE in the queue.")
        print("   Use --force to create another one anyway.")
        sys.exit(1)

    # Create scrape configuration
    scrape_config = ScrapeConfig(
        target_matches=target_matches,
        max_sources=max_sources,
        source_ids=source_ids,
        min_match_score=min_match_score,
    )

    # Create queue item
    queue_item = JobQueueItem(
        type=QueueItemType.SCRAPE,
        source="user_submission",
        scrape_config=scrape_config,
    )

    # Add to queue
    item_id = queue_manager.add_item(queue_item)

    print(f"✅ Scrape request added to queue!")
    print(f"   Queue item ID: {item_id}")
    print("")
    print("The queue worker will process this request shortly.")
    print("Monitor logs to see progress:")
    print("  docker logs -f job-finder-worker")
    print("")

    return item_id


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Trigger on-demand job scraping with custom settings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default scrape (5 matches, 20 sources max)
  python scripts/trigger_scrape.py

  # Find 10 potential matches
  python scripts/trigger_scrape.py --target-matches 10

  # Scrape specific sources
  python scripts/trigger_scrape.py --sources source-id-1 source-id-2

  # Override min match score
  python scripts/trigger_scrape.py --min-score 75

  # Production database
  python scripts/trigger_scrape.py --database portfolio

  # Force create even if pending scrape exists
  python scripts/trigger_scrape.py --force
        """,
    )

    parser.add_argument(
        "--target-matches",
        "-t",
        type=int,
        default=5,
        help="Stop after finding this many potential matches (default: 5)",
    )

    parser.add_argument(
        "--max-sources",
        "-m",
        type=int,
        default=20,
        help="Maximum number of sources to scrape (default: 20)",
    )

    parser.add_argument(
        "--sources",
        "-s",
        nargs="+",
        help="Specific source IDs to scrape (space-separated)",
    )

    parser.add_argument(
        "--min-score",
        type=int,
        help="Override minimum match score threshold (0-100)",
    )

    parser.add_argument(
        "--database",
        "-d",
        default=os.getenv("STORAGE_DATABASE_NAME", "portfolio-staging"),
        help="Database name (default: portfolio-staging or $STORAGE_DATABASE_NAME)",
    )

    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force trigger even if pending scrape already exists",
    )

    args = parser.parse_args()

    # Validate min_score range
    if args.min_score is not None and (args.min_score < 0 or args.min_score > 100):
        print("ERROR: --min-score must be between 0 and 100")
        sys.exit(1)

    try:
        trigger_scrape(
            target_matches=args.target_matches,
            max_sources=args.max_sources,
            source_ids=args.sources,
            min_match_score=args.min_score,
            database=args.database,
            force=args.force,
        )
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
