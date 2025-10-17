#!/usr/bin/env python3
"""
Queue worker daemon - continuously processes job queue items.

This worker polls the Firestore job-queue collection every 60 seconds
and processes pending items in FIFO order.
"""
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Tuple

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import yaml  # type: ignore  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from job_finder.ai import AIJobMatcher  # noqa: E402
from job_finder.ai.providers import create_provider  # noqa: E402
from job_finder.company_info_fetcher import CompanyInfoFetcher  # noqa: E402
from job_finder.profile import FirestoreProfileLoader  # noqa: E402
from job_finder.queue import ConfigLoader, QueueManager  # noqa: E402
from job_finder.queue.processor import QueueItemProcessor  # noqa: E402
from job_finder.storage import FirestoreJobStorage  # noqa: E402
from job_finder.storage.companies_manager import CompaniesManager  # noqa: E402
from job_finder.storage.job_sources_manager import JobSourcesManager  # noqa: E402

# Load environment variables
load_dotenv()

# Configure logging
log_file = os.getenv("QUEUE_WORKER_LOG_FILE", "/app/logs/queue_worker.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def load_config() -> dict:
    """Load configuration from file."""
    config_path = os.getenv("CONFIG_PATH", "config/config.yaml")
    logger.info(f"Loading configuration from: {config_path}")

    if not Path(config_path).exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def initialize_components(config: dict) -> Tuple[QueueManager, QueueItemProcessor, ConfigLoader]:
    """
    Initialize all required components for queue processing.

    Returns:
        Tuple of (queue_manager, processor, config_loader)
    """
    # Get database names from environment or config
    profile_db = os.getenv(
        "PROFILE_DATABASE_NAME",
        config.get("profile", {}).get("firestore", {}).get("database_name", "portfolio"),
    )
    storage_db = os.getenv(
        "STORAGE_DATABASE_NAME", config.get("storage", {}).get("database_name", "portfolio-staging")
    )

    logger.info("Initializing components...")
    logger.info(f"  Profile database: {profile_db}")
    logger.info(f"  Storage database: {storage_db}")

    # Initialize managers
    queue_manager = QueueManager(database_name=storage_db)
    config_loader = ConfigLoader(database_name=storage_db)
    job_storage = FirestoreJobStorage(database_name=storage_db)
    companies_manager = CompaniesManager(database_name=storage_db)
    sources_manager = JobSourcesManager(database_name=storage_db)

    # Load profile
    logger.info("Loading user profile...")
    profile_config = config.get("profile", {}).get("firestore", {})
    profile_loader = FirestoreProfileLoader(database_name=profile_db)
    profile = profile_loader.load_profile(
        user_id=profile_config.get("user_id"),
        name=profile_config.get("name", "User"),
        email=profile_config.get("email"),
    )
    logger.info(f"Profile loaded: {profile.name}")

    # Initialize AI components
    logger.info("Initializing AI components...")
    ai_config = config.get("ai", {})

    # Override AI config with Firestore settings if available
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
    )

    company_info_fetcher = CompanyInfoFetcher(ai_provider=provider)

    # Create processor
    processor = QueueItemProcessor(
        queue_manager=queue_manager,
        config_loader=config_loader,
        job_storage=job_storage,
        companies_manager=companies_manager,
        sources_manager=sources_manager,
        company_info_fetcher=company_info_fetcher,
        ai_matcher=ai_matcher,
    )

    logger.info("All components initialized successfully")
    return queue_manager, processor, config_loader


def run_worker_loop(
    queue_manager: QueueManager, processor: QueueItemProcessor, poll_interval: int = 60
):
    """
    Main worker loop that polls queue and processes items.

    Args:
        queue_manager: Queue manager for fetching items
        processor: Item processor
        poll_interval: Seconds between polls (default: 60)
    """
    logger.info("=" * 70)
    logger.info("QUEUE WORKER STARTED")
    logger.info("=" * 70)
    logger.info(f"Poll interval: {poll_interval} seconds")
    logger.info("Waiting for queue items...")
    logger.info("")

    iteration = 0
    items_processed_total = 0

    while not shutdown_requested:
        iteration += 1

        try:
            # Get pending items (FIFO order)
            items = queue_manager.get_pending_items(limit=10)

            if items:
                logger.info(f"[Iteration {iteration}] Found {len(items)} pending items")

                for item in items:
                    if shutdown_requested:
                        logger.info("Shutdown requested, stopping item processing")
                        break

                    try:
                        processor.process_item(item)
                        items_processed_total += 1
                    except Exception as e:
                        logger.error(f"Error processing item {item.id}: {e}", exc_info=True)

                # Get updated stats
                stats = queue_manager.get_queue_stats()
                logger.info(f"Queue stats: {stats}")
            else:
                # No items to process
                # Log every 10 iterations (~10 minutes)
                if iteration % 10 == 0:
                    logger.debug(
                        f"[Iteration {iteration}] No pending items. "
                        f"Total processed: {items_processed_total}"
                    )

            # Sleep before next poll
            time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in worker loop: {e}", exc_info=True)
            logger.info("Continuing after error...")
            time.sleep(poll_interval)

    logger.info("=" * 70)
    logger.info("QUEUE WORKER STOPPED")
    logger.info(f"Total items processed: {items_processed_total}")
    logger.info("=" * 70)


def main():
    """Main entry point."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Load config
        config = load_config()

        # Initialize components
        queue_manager, processor, _ = initialize_components(config)

        # Get poll interval from config (default 60 seconds)
        poll_interval = config.get("queue", {}).get("poll_interval", 60)

        # Run worker loop
        run_worker_loop(queue_manager, processor, poll_interval)

        return 0

    except Exception as e:
        logger.error(f"Fatal error in queue worker: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
