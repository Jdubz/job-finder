#!/usr/bin/env python3
"""
Job search scheduler - runs periodic job searches.

This script is designed to be run by cron or as a standalone daemon.
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml  # type: ignore[import-untyped]

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from job_finder.search_orchestrator import JobSearchOrchestrator  # noqa: E402

# Configure logging
log_file = os.getenv("LOG_FILE", "/app/logs/scheduler.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def run_scheduled_search():
    """Run a scheduled job search."""
    try:
        logger.info("=" * 70)
        logger.info(f"SCHEDULED JOB SEARCH - {datetime.now().isoformat()}")
        logger.info("=" * 70)

        # Load configuration
        config_path = os.getenv("CONFIG_PATH", "/app/config/config.yaml")
        logger.info(f"Loading configuration from: {config_path}")

        if not Path(config_path).exists():
            logger.error(f"Configuration file not found: {config_path}")
            return 1

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        logger.info("Configuration loaded successfully")
        logger.info(f"  - Profile source: {config.get('profile', {}).get('source')}")
        logger.info(f"  - Storage database: {config.get('storage', {}).get('database_name')}")
        logger.info(f"  - Max jobs: {config.get('search', {}).get('max_jobs')}")

        # Create and run orchestrator
        orchestrator = JobSearchOrchestrator(config)
        stats = orchestrator.run_search()

        logger.info("=" * 70)
        logger.info("SCHEDULED SEARCH COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)
        logger.info(f"Jobs saved: {stats['jobs_saved']}")
        logger.info(f"Duplicates skipped: {stats['duplicates_skipped']}")

        return 0

    except Exception as e:
        logger.error(f"Error during scheduled search: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(run_scheduled_search())
