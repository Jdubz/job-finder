#!/usr/bin/env python3
"""
Hourly cron job that triggers scraping by adding SCRAPE items to the queue.

This script runs every hour and:
1. Checks if it's daytime hours (6am-10pm PT)
2. Checks if there's already a pending SCRAPE in the queue
3. Creates a new SCRAPE queue item with configured settings

The queue worker handles the actual scraping.
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml  # type: ignore[import-untyped]
from dotenv import load_dotenv

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from job_finder.logging_config import setup_logging  # noqa: E402
from job_finder.queue import QueueManager  # noqa: E402
from job_finder.job_queue.models import JobQueueItem, QueueItemType, ScrapeConfig  # noqa: E402

# Load environment variables
load_dotenv()

# Configure logging
log_file = os.getenv("SCHEDULER_LOG_FILE", "/app/logs/hourly_cron.log")
setup_logging(log_file=log_file)
logger = logging.getLogger(__name__)

# Pacific timezone
PT = ZoneInfo("America/Los_Angeles")


def is_daytime_hours() -> bool:
    """
    Check if current time is within daytime hours (6am-10pm PT).

    Returns:
        True if within daytime hours, False otherwise
    """
    now_pt = datetime.now(PT)
    hour = now_pt.hour
    return 6 <= hour < 22  # 6am to 10pm (22:00 is 10pm)


def trigger_hourly_scrape(config: dict) -> dict:
    """
    Trigger hourly scrape by adding SCRAPE item to queue.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary with status
    """
    logger.info("=" * 70)
    logger.info(f"HOURLY CRON - {datetime.now(PT).isoformat()}")
    logger.info("=" * 70)

    # Check if within daytime hours
    if not is_daytime_hours():
        logger.info("⏸️  Outside daytime hours (6am-10pm PT), skipping")
        return {"status": "skipped", "reason": "outside_daytime_hours"}

    # Get database name
    storage_db = os.getenv(
        "STORAGE_DATABASE_NAME",
        config.get("storage", {}).get("database_name", "portfolio-staging"),
    )

    logger.info(f"Storage database: {storage_db}")

    # Initialize queue manager
    queue_manager = QueueManager(database_name=storage_db)

    # Check for existing pending scrape
    if queue_manager.has_pending_scrape():
        logger.info("⏭️  Skipping: There is already a pending SCRAPE in the queue")
        return {"status": "skipped", "reason": "pending_scrape_exists"}

    # Get scheduler settings
    scheduler_config = config.get("scheduler", {})
    target_matches = scheduler_config.get("target_matches", 5)
    max_sources = scheduler_config.get("max_sources_per_run", 20)

    logger.info(
        f"Creating SCRAPE request: target_matches={target_matches}, max_sources={max_sources}"
    )

    # Create scrape configuration
    scrape_config = ScrapeConfig(
        target_matches=target_matches,
        max_sources=max_sources,
        source_ids=None,  # Use rotation
        min_match_score=None,  # Use default from AI config
    )

    # Create queue item
    queue_item = JobQueueItem(
        type=QueueItemType.SCRAPE,
        source="automated_scan",
        scrape_config=scrape_config,
    )

    # Add to queue
    item_id = queue_manager.add_item(queue_item)

    logger.info(f"✅ SCRAPE request added to queue (ID: {item_id})")
    logger.info("Queue worker will process this request")

    return {"status": "triggered", "queue_item_id": item_id}


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

        # Trigger hourly scrape
        result = trigger_hourly_scrape(config)

        logger.info(f"Hourly cron result: {result}")
        return 0

    except Exception as e:
        logger.error(f"Fatal error in hourly cron: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
