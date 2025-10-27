#!/usr/bin/env python3
"""
Migrate legacy queue items to granular pipeline.

This script converts existing JOB queue items (without sub_task) into
granular pipeline items starting with JOB_SCRAPE.

Usage:
    python scripts/migrate_to_granular_pipeline.py --dry-run
    python scripts/migrate_to_granular_pipeline.py --confirm
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from job_finder.job_queue.manager import QueueManager
from job_finder.job_queue.models import JobQueueItem, JobSubTask

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class GranularPipelineMigrator:
    """Migrates legacy queue items to granular pipeline."""

    def __init__(self, database_name: str = "portfolio-staging"):
        """
        Initialize migrator.

        Args:
            database_name: Firestore database name
        """
        self.queue_manager = QueueManager(database_name=database_name)
        logger.info(f"Connected to database: {database_name}")

    def find_legacy_items(self, status_filter: str = "pending") -> List[JobQueueItem]:
        """
        Find legacy queue items (no sub_task).

        Args:
            status_filter: Filter by status (pending, failed, etc.) or "all"

        Returns:
            List of legacy JOB items
        """
        logger.info(f"Searching for legacy items with status: {status_filter}")

        # Query queue collection
        query = self.queue_manager.db.collection("job-queue")

        # Filter by type (only JOB items)
        query = query.where("type", "==", "job")

        # Filter by status if not "all"
        if status_filter != "all":
            query = query.where("status", "==", status_filter)

        docs = query.stream()

        legacy_items = []
        for doc in docs:
            data = doc.to_dict()
            item = JobQueueItem.from_firestore(doc.id, data)

            # Check if legacy (no sub_task)
            if not item.sub_task:
                legacy_items.append(item)

        logger.info(f"Found {len(legacy_items)} legacy items")
        return legacy_items

    def migrate_item(self, item: JobQueueItem, dry_run: bool = True) -> bool:
        """
        Migrate a single legacy item to granular pipeline.

        Creates a new JOB_SCRAPE item and optionally deletes the old item.

        Args:
            item: Legacy queue item
            dry_run: If True, don't actually create/delete, just log

        Returns:
            True if migration would succeed/succeeded
        """
        if not item.id:
            logger.warning("Cannot migrate item without ID")
            return False

        if item.sub_task:
            logger.warning(f"Item {item.id} already has sub_task, skipping")
            return False

        logger.info(
            f"Migrating item {item.id}: {item.url[:50]}... "
            f"(status: {item.status.value if hasattr(item.status, 'value') else item.status})"
        )

        if dry_run:
            logger.info(f"  [DRY RUN] Would create JOB_SCRAPE item for: {item.url}")
            logger.info(f"  [DRY RUN] Would delete legacy item: {item.id}")
            return True

        try:
            # Create new JOB_SCRAPE item
            new_item_id = self.queue_manager.create_pipeline_item(
                url=item.url,
                sub_task=JobSubTask.SCRAPE,
                pipeline_state={},
                company_name=item.company_name,
                company_id=item.company_id,
                source=item.source,
            )

            logger.info(f"  ✓ Created JOB_SCRAPE item: {new_item_id}")

            # Delete legacy item
            self.queue_manager.delete_item(item.id)
            logger.info(f"  ✓ Deleted legacy item: {item.id}")

            return True

        except Exception as e:
            logger.error(f"  ✗ Error migrating item {item.id}: {e}")
            return False

    def migrate_all(
        self, status_filter: str = "pending", dry_run: bool = True, max_items: int = None
    ) -> Dict[str, int]:
        """
        Migrate all legacy items.

        Args:
            status_filter: Filter by status or "all"
            dry_run: If True, don't actually migrate
            max_items: Maximum number of items to migrate (None = all)

        Returns:
            Statistics dict with counts
        """
        items = self.find_legacy_items(status_filter)

        if max_items:
            items = items[:max_items]
            logger.info(f"Limiting migration to {max_items} items")

        stats = {"total": len(items), "succeeded": 0, "failed": 0, "skipped": 0}

        if not items:
            logger.info("No legacy items to migrate")
            return stats

        logger.info(f"\n{'='*60}")
        logger.info(f"Migration Plan:")
        logger.info(f"  Total items: {stats['total']}")
        logger.info(f"  Status filter: {status_filter}")
        logger.info(f"  Mode: {'DRY RUN' if dry_run else 'LIVE MIGRATION'}")
        logger.info(f"{'='*60}\n")

        for item in items:
            success = self.migrate_item(item, dry_run=dry_run)

            if success:
                stats["succeeded"] += 1
            else:
                stats["failed"] += 1

        logger.info(f"\n{'='*60}")
        logger.info(f"Migration Complete:")
        logger.info(f"  Total: {stats['total']}")
        logger.info(f"  Succeeded: {stats['succeeded']}")
        logger.info(f"  Failed: {stats['failed']}")
        logger.info(f"  Skipped: {stats['skipped']}")
        logger.info(f"{'='*60}\n")

        return stats

    def analyze_queue_composition(self) -> Dict[str, int]:
        """
        Analyze current queue composition.

        Returns:
            Statistics about legacy vs granular items
        """
        logger.info("Analyzing queue composition...")

        query = self.queue_manager.db.collection("job-queue")
        query = query.where("type", "==", "job")

        docs = query.stream()

        stats = {
            "total_job_items": 0,
            "legacy_items": 0,
            "granular_items": 0,
            "by_status": {},
            "by_subtask": {},
        }

        for doc in docs:
            data = doc.to_dict()
            stats["total_job_items"] += 1

            # Check if legacy or granular
            if data.get("sub_task"):
                stats["granular_items"] += 1
                subtask = data.get("sub_task", "unknown")
                stats["by_subtask"][subtask] = stats["by_subtask"].get(subtask, 0) + 1
            else:
                stats["legacy_items"] += 1

            # Count by status
            status = data.get("status", "unknown")
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

        logger.info(f"\nQueue Composition:")
        logger.info(f"  Total JOB items: {stats['total_job_items']}")
        logger.info(f"  Legacy items: {stats['legacy_items']}")
        logger.info(f"  Granular pipeline items: {stats['granular_items']}")

        logger.info(f"\n  By Status:")
        for status, count in sorted(stats["by_status"].items()):
            logger.info(f"    {status}: {count}")

        if stats["by_subtask"]:
            logger.info(f"\n  By Sub-Task:")
            for subtask, count in sorted(stats["by_subtask"].items()):
                logger.info(f"    {subtask}: {count}")

        return stats


def main():
    """Run migration."""
    parser = argparse.ArgumentParser(description="Migrate legacy queue items to granular pipeline")
    parser.add_argument(
        "--database",
        default="portfolio-staging",
        help="Firestore database name (default: portfolio-staging)",
    )
    parser.add_argument(
        "--status",
        default="pending",
        help="Status filter: pending, failed, all (default: pending)",
    )
    parser.add_argument("--max-items", type=int, help="Maximum number of items to migrate")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't actually migrate)")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm migration (required for live migration)",
    )
    parser.add_argument(
        "--analyze-only", action="store_true", help="Only analyze queue composition"
    )

    args = parser.parse_args()

    # Create migrator
    migrator = GranularPipelineMigrator(database_name=args.database)

    # Analyze only mode
    if args.analyze_only:
        migrator.analyze_queue_composition()
        return

    # Determine if this is a dry run
    dry_run = args.dry_run or not args.confirm

    if not dry_run:
        logger.warning("\n" + "=" * 60)
        logger.warning("LIVE MIGRATION MODE")
        logger.warning("This will DELETE legacy items and create new ones!")
        logger.warning("=" * 60 + "\n")

        confirm = input("Are you sure you want to proceed? (yes/no): ")
        if confirm.lower() != "yes":
            logger.info("Migration cancelled")
            return

    # Run migration
    migrator.migrate_all(status_filter=args.status, dry_run=dry_run, max_items=args.max_items)


if __name__ == "__main__":
    main()
