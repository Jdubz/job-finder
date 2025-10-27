"""
Queue Monitor for E2E Tests

Monitors the job queue and exits when all jobs are complete.
Used by E2E tests to wait for pipeline completion.

Usage:
    python tests/e2e/queue_monitor.py \\
        --database portfolio-staging \\
        --timeout 300 \\
        --output monitor.log
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from job_finder.queue import QueueManager
from job_finder.job_queue.models import QueueStatus
from job_finder.storage.firestore_client import FirestoreClient

logger = logging.getLogger(__name__)


class QueueMonitor:
    """Monitors queue and waits for completion."""

    def __init__(
        self,
        database_name: str,
        timeout: int = 300,
        poll_interval: int = 5,
        stream_logs: bool = False,
    ):
        """
        Initialize queue monitor.

        Args:
            database_name: Database to monitor
            timeout: Maximum seconds to wait
            poll_interval: Seconds between checks
            stream_logs: Whether to stream real-time logs
        """
        self.database_name = database_name
        self.queue_manager = QueueManager(database_name)
        self.db = FirestoreClient.get_client(database_name)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.stream_logs = stream_logs

        self.start_time = None
        self.last_status: Dict[str, int] = {}

    def get_queue_status(self) -> Dict[str, int]:
        """
        Get current queue status counts.

        Returns:
            Dict of status -> count
        """
        status_counts = {
            "pending": 0,
            "processing": 0,
            "success": 0,
            "failed": 0,
            "filtered": 0,
            "skipped": 0,
        }

        # Count items by status
        for status in QueueStatus:
            query = self.db.collection("job-queue").where("status", "==", status.value)
            count = len(list(query.stream()))
            status_counts[status.value] = count

        return status_counts

    def is_queue_complete(self, status: Dict[str, int]) -> bool:
        """
        Check if queue processing is complete.

        Queue is complete when:
        - No pending items
        - No processing items
        - At least one completed item (success/failed/filtered/skipped)

        Args:
            status: Current status counts

        Returns:
            True if complete
        """
        active = status["pending"] + status["processing"]
        completed = status["success"] + status["failed"] + status["filtered"] + status["skipped"]

        return active == 0 and completed > 0

    def format_status(self, status: Dict[str, int]) -> str:
        """Format status for logging."""
        total = sum(status.values())
        active = status["pending"] + status["processing"]

        parts = [
            f"Total: {total}",
            f"Active: {active}",
            f"Pending: {status['pending']}",
            f"Processing: {status['processing']}",
            f"Success: {status['success']}",
            f"Failed: {status['failed']}",
            f"Filtered: {status['filtered']}",
            f"Skipped: {status['skipped']}",
        ]

        return " | ".join(parts)

    def get_recent_logs(self, limit: int = 10) -> List[str]:
        """
        Get recent queue item logs.

        Args:
            limit: Number of recent items to get logs from

        Returns:
            List of log messages
        """
        logs = []

        # Get recent completed items
        recent_items = (
            self.db.collection("job-queue")
            .order_by("updated_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )

        for doc in recent_items:
            data = doc.to_dict()
            status = data.get("status", "unknown")
            job_type = data.get("type", "unknown")
            url = data.get("url", "unknown")
            error = data.get("error", "")

            log_msg = f"[{status}] {job_type}: {url}"
            if error:
                log_msg += f" - Error: {error}"

            logs.append(log_msg)

        return logs

    def monitor_until_complete(self) -> bool:
        """
        Monitor queue until complete or timeout.

        Returns:
            True if completed successfully, False if timeout
        """
        self.start_time = time.time()

        logger.info("=" * 80)
        logger.info("QUEUE MONITORING STARTED")
        logger.info("=" * 80)
        logger.info(f"Database: {self.database_name}")
        logger.info(f"Timeout: {self.timeout} seconds")
        logger.info(f"Poll Interval: {self.poll_interval} seconds")
        logger.info("")

        iteration = 0

        while True:
            iteration += 1
            elapsed = time.time() - self.start_time

            # Check timeout
            if elapsed > self.timeout:
                logger.error("=" * 80)
                logger.error("TIMEOUT REACHED")
                logger.error("=" * 80)
                logger.error(f"Queue did not complete within {self.timeout} seconds")
                logger.error("")

                # Show final status
                final_status = self.get_queue_status()
                logger.error(f"Final Status: {self.format_status(final_status)}")

                return False

            # Get current status
            status = self.get_queue_status()

            # Check if complete
            if self.is_queue_complete(status):
                logger.info("=" * 80)
                logger.info("QUEUE COMPLETE!")
                logger.info("=" * 80)
                logger.info(f"Completed in {elapsed:.1f} seconds")
                logger.info(f"Final Status: {self.format_status(status)}")
                logger.info("")

                # Calculate success rate
                completed = (
                    status["success"] + status["failed"] + status["filtered"] + status["skipped"]
                )
                if completed > 0:
                    success_rate = (status["success"] / completed) * 100
                    logger.info(f"Success Rate: {success_rate:.1f}%")

                return True

            # Log status (every 5 iterations or if changed)
            if iteration % 5 == 1 or status != self.last_status:
                logger.info(f"[{elapsed:.0f}s] Iteration {iteration}: {self.format_status(status)}")
                self.last_status = status.copy()

            # Stream recent logs if enabled
            if self.stream_logs and iteration % 2 == 0:
                recent_logs = self.get_recent_logs(limit=3)
                if recent_logs:
                    for log in recent_logs:
                        logger.debug(f"  {log}")

            # Wait before next check
            time.sleep(self.poll_interval)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Queue Monitor for E2E Tests")
    parser.add_argument(
        "--database",
        default="portfolio-staging",
        help="Database to monitor (default: portfolio-staging)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Maximum seconds to wait (default: 300)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Seconds between checks (default: 5)",
    )
    parser.add_argument(
        "--stream-logs",
        action="store_true",
        help="Stream recent logs in real-time",
    )
    parser.add_argument(
        "--output",
        help="Output log file (default: console only)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    level = logging.DEBUG if args.verbose else logging.INFO

    handlers: List[logging.Handler] = [logging.StreamHandler()]

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(args.output))

    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=handlers,
    )

    # Run monitor
    monitor = QueueMonitor(
        database_name=args.database,
        timeout=args.timeout,
        poll_interval=args.poll_interval,
        stream_logs=args.stream_logs,
    )

    success = monitor.monitor_until_complete()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
