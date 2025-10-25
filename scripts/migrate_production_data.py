#!/usr/bin/env python3
"""
Production Data Migration Script

Migrates Firestore data to match the cleaned-up data structure:
1. Removes job-level "keywords" field from job-matches
2. Migrates monolithic job queue items to granular pipeline
3. Cleans up stale queue items
4. Verifies data integrity

Usage:
    python scripts/migrate_production_data.py --database portfolio --dry-run
    python scripts/migrate_production_data.py --database portfolio --execute
"""

import argparse
import logging
from datetime import datetime, timedelta

from google.cloud import firestore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductionDataMigrator:
    """Migrates production Firestore data to cleaned-up structure."""

    def __init__(self, database_name: str, dry_run: bool = True):
        """
        Initialize migrator.

        Args:
            database_name: Firestore database name (e.g., "portfolio")
            dry_run: If True, only report changes without executing
        """
        self.db = firestore.Client(database=database_name)
        self.dry_run = dry_run
        self.stats = {
            "job_matches_migrated": 0,
            "job_matches_errors": 0,
            "queue_items_migrated": 0,
            "queue_items_deleted": 0,
            "queue_items_errors": 0,
        }

    def migrate_job_matches(self) -> None:
        """
        Migrate job-matches collection.

        Changes:
        - Remove job-level "keywords" field (if exists)
        - Verify resumeIntakeData.atsKeywords exists
        """
        logger.info("=" * 60)
        logger.info("Migrating job-matches collection...")
        logger.info("=" * 60)

        collection = self.db.collection("job-matches")
        docs = collection.stream()

        for doc in docs:
            try:
                data = doc.to_dict()
                updates = {}

                # Check if job-level keywords field exists
                if "keywords" in data:
                    logger.info(f"  [{doc.id}] Found job-level 'keywords' field: {data['keywords']}")

                    # Check if atsKeywords exists in resumeIntakeData
                    if "resumeIntakeData" in data and "atsKeywords" in data["resumeIntakeData"]:
                        logger.info(f"  [{doc.id}] resumeIntakeData.atsKeywords exists: {data['resumeIntakeData']['atsKeywords']}")
                        # Safe to remove job-level keywords
                        updates["keywords"] = firestore.DELETE_FIELD
                    else:
                        logger.warning(f"  [{doc.id}] WARNING: No atsKeywords in resumeIntakeData, keeping keywords for now")

                # Verify resumeIntakeData exists
                if "resumeIntakeData" not in data:
                    logger.warning(f"  [{doc.id}] WARNING: Missing resumeIntakeData (old job match?)")

                # Apply updates
                if updates:
                    if self.dry_run:
                        logger.info(f"  [{doc.id}] [DRY RUN] Would remove: {list(updates.keys())}")
                    else:
                        doc.reference.update(updates)
                        logger.info(f"  [{doc.id}] Removed fields: {list(updates.keys())}")

                    self.stats["job_matches_migrated"] += 1

            except Exception as e:
                logger.error(f"  [{doc.id}] Error migrating: {e}")
                self.stats["job_matches_errors"] += 1

        logger.info(f"\nJob Matches Migration Summary:")
        logger.info(f"  Migrated: {self.stats['job_matches_migrated']}")
        logger.info(f"  Errors: {self.stats['job_matches_errors']}")

    def migrate_queue_items(self, delete_stale_days: int = 30) -> None:
        """
        Migrate job-queue collection.

        Changes:
        - Migrate monolithic job items (sub_task=None) to granular pipeline
        - Delete stale completed/failed items older than N days

        Args:
            delete_stale_days: Delete completed/failed items older than this many days
        """
        logger.info("=" * 60)
        logger.info("Migrating job-queue collection...")
        logger.info("=" * 60)

        collection = self.db.collection("job-queue")

        # Find monolithic job items (no sub_task)
        logger.info("\n1. Finding monolithic job items (no sub_task)...")
        job_items = collection.where("type", "==", "job").stream()

        monolithic_count = 0
        for doc in job_items:
            data = doc.to_dict()

            # Check if sub_task is missing or None
            if "sub_task" not in data or data.get("sub_task") is None:
                monolithic_count += 1
                status = data.get("status", "unknown")

                logger.info(f"  [{doc.id}] Monolithic job item (status: {status})")

                # Only migrate pending items, delete others
                if status == "pending":
                    if self.dry_run:
                        logger.info(f"  [{doc.id}] [DRY RUN] Would convert to JOB_SCRAPE")
                    else:
                        # Update to use granular pipeline
                        doc.reference.update({
                            "sub_task": "scrape",
                            "pipeline_state": {},
                            "updated_at": firestore.SERVER_TIMESTAMP
                        })
                        logger.info(f"  [{doc.id}] Converted to granular pipeline (JOB_SCRAPE)")

                    self.stats["queue_items_migrated"] += 1
                else:
                    # Delete non-pending monolithic items
                    if self.dry_run:
                        logger.info(f"  [{doc.id}] [DRY RUN] Would delete (status: {status})")
                    else:
                        doc.reference.delete()
                        logger.info(f"  [{doc.id}] Deleted (status: {status})")

                    self.stats["queue_items_deleted"] += 1

        logger.info(f"\nFound {monolithic_count} monolithic job items")

        # Delete stale completed/failed items
        logger.info(f"\n2. Cleaning up stale queue items (older than {delete_stale_days} days)...")
        cutoff_date = datetime.now() - timedelta(days=delete_stale_days)

        stale_items = collection.where("status", "in", ["success", "failed", "skipped", "filtered"]).stream()

        stale_count = 0
        for doc in stale_items:
            data = doc.to_dict()
            completed_at = data.get("completed_at")

            if completed_at and completed_at.timestamp() < cutoff_date.timestamp():
                stale_count += 1

                if self.dry_run:
                    logger.info(f"  [{doc.id}] [DRY RUN] Would delete stale {data.get('status')} item from {completed_at}")
                else:
                    doc.reference.delete()
                    logger.info(f"  [{doc.id}] Deleted stale {data.get('status')} item from {completed_at}")

                self.stats["queue_items_deleted"] += 1

        logger.info(f"\nQueue Migration Summary:")
        logger.info(f"  Migrated to granular: {self.stats['queue_items_migrated']}")
        logger.info(f"  Deleted stale/monolithic: {self.stats['queue_items_deleted']}")
        logger.info(f"  Errors: {self.stats['queue_items_errors']}")

    def verify_data_integrity(self) -> None:
        """Verify data integrity after migration."""
        logger.info("=" * 60)
        logger.info("Verifying data integrity...")
        logger.info("=" * 60)

        # Verify job-matches have atsKeywords
        logger.info("\n1. Checking job-matches for atsKeywords...")
        job_matches = self.db.collection("job-matches").stream()

        missing_ats_keywords = 0
        total_matches = 0

        for doc in job_matches:
            total_matches += 1
            data = doc.to_dict()

            if "resumeIntakeData" not in data:
                logger.warning(f"  [{doc.id}] Missing resumeIntakeData")
                missing_ats_keywords += 1
            elif "atsKeywords" not in data.get("resumeIntakeData", {}):
                logger.warning(f"  [{doc.id}] Missing atsKeywords in resumeIntakeData")
                missing_ats_keywords += 1

        logger.info(f"\nJob Matches Integrity:")
        logger.info(f"  Total: {total_matches}")
        logger.info(f"  Missing atsKeywords: {missing_ats_keywords}")

        # Verify job queue items have sub_task
        logger.info("\n2. Checking job queue items for sub_task...")
        job_queue = self.db.collection("job-queue").where("type", "==", "job").stream()

        missing_sub_task = 0
        total_jobs = 0

        for doc in job_queue:
            total_jobs += 1
            data = doc.to_dict()

            if "sub_task" not in data or data.get("sub_task") is None:
                logger.warning(f"  [{doc.id}] Missing sub_task (status: {data.get('status')})")
                missing_sub_task += 1

        logger.info(f"\nJob Queue Integrity:")
        logger.info(f"  Total job items: {total_jobs}")
        logger.info(f"  Missing sub_task: {missing_sub_task}")

    def run_migration(self, clean_stale_days: int = 30) -> None:
        """
        Run full migration.

        Args:
            clean_stale_days: Delete stale queue items older than this many days
        """
        logger.info("=" * 60)
        logger.info("PRODUCTION DATA MIGRATION")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        logger.info(f"Database: {self.db._database}")
        logger.info("=" * 60)

        if not self.dry_run:
            response = input("\n⚠️  WARNING: This will modify production data. Type 'yes' to continue: ")
            if response.lower() != "yes":
                logger.info("Migration cancelled.")
                return

        # Run migrations
        self.migrate_job_matches()
        self.migrate_queue_items(delete_stale_days=clean_stale_days)
        self.verify_data_integrity()

        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("MIGRATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Job Matches:")
        logger.info(f"  Migrated: {self.stats['job_matches_migrated']}")
        logger.info(f"  Errors: {self.stats['job_matches_errors']}")
        logger.info(f"\nQueue Items:")
        logger.info(f"  Migrated: {self.stats['queue_items_migrated']}")
        logger.info(f"  Deleted: {self.stats['queue_items_deleted']}")
        logger.info(f"  Errors: {self.stats['queue_items_errors']}")

        if self.dry_run:
            logger.info("\n✅ Dry run complete. Run with --execute to apply changes.")


def main():
    parser = argparse.ArgumentParser(description="Migrate production Firestore data")
    parser.add_argument(
        "--database",
        required=True,
        help="Firestore database name (e.g., 'portfolio')"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview changes without executing (default: False, will execute)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute migration (opposite of --dry-run)"
    )
    parser.add_argument(
        "--clean-stale-days",
        type=int,
        default=30,
        help="Delete stale queue items older than N days (default: 30)"
    )

    args = parser.parse_args()

    # Determine dry_run mode
    dry_run = not args.execute if args.execute else args.dry_run

    migrator = ProductionDataMigrator(
        database_name=args.database,
        dry_run=dry_run
    )

    migrator.run_migration(clean_stale_days=args.clean_stale_days)


if __name__ == "__main__":
    main()
