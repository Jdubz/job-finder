#!/usr/bin/env python3
"""
Job Source Status Migration Script

Adds status tracking fields to job-sources collection:
1. Adds "status" field (maps from "enabled" boolean to status enum)
2. Adds "consecutiveFailures" field (defaults to 0)
3. Adds "autoEnabled" field (defaults to false for manual sources)
4. Verifies data integrity

Status mapping:
- enabled=true → status="active"
- enabled=false → status="disabled"
- missing enabled → status="disabled"

This migration is safe to run multiple times (idempotent).

Usage:
    python scripts/database/002_add_source_status.py --database portfolio --dry-run
    python scripts/database/002_add_source_status.py --database portfolio --execute
"""

import argparse
import logging

from google.cloud import firestore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SourceStatusMigrator:
    """Adds status tracking to job-sources collection."""

    def __init__(self, database_name: str, dry_run: bool = True):
        """
        Initialize migrator.

        Args:
            database_name: Firestore database name (e.g., "portfolio")
            dry_run: If True, only report changes without executing
        """
        self.db = firestore.Client(database=database_name)
        self.dry_run = dry_run
        self.auto_approve = False  # Set by main() if --yes flag provided
        self.stats = {
            "sources_migrated": 0,
            "sources_skipped": 0,
            "sources_errors": 0,
        }

    def migrate_job_sources(self) -> None:
        """
        Migrate job-sources collection.

        Changes:
        - Add "status" field (maps from "enabled" boolean)
        - Add "consecutiveFailures" field (default: 0)
        - Add "autoEnabled" field (default: false)
        - Keep "enabled" field for backward compatibility
        """
        logger.info("=" * 60)
        logger.info("Migrating job-sources collection...")
        logger.info("=" * 60)

        collection = self.db.collection("job-sources")
        docs = collection.stream()

        for doc in docs:
            try:
                data = doc.to_dict()
                updates = {}

                # Check if status field is missing
                if "status" not in data:
                    # Map from enabled boolean to status enum
                    enabled = data.get("enabled", False)

                    if enabled:
                        updates["status"] = "active"
                        logger.info(f"  [{doc.id}] Mapping enabled=true → status='active'")
                    else:
                        updates["status"] = "disabled"
                        logger.info(f"  [{doc.id}] Mapping enabled=false → status='disabled'")

                # Check if consecutiveFailures is missing
                if "consecutiveFailures" not in data:
                    updates["consecutiveFailures"] = 0
                    logger.info(f"  [{doc.id}] Adding consecutiveFailures=0")

                # Check if autoEnabled is missing
                if "autoEnabled" not in data:
                    # Default to false (assume manually added unless proven otherwise)
                    updates["autoEnabled"] = False
                    logger.info(f"  [{doc.id}] Adding autoEnabled=false")

                # Apply updates
                if updates:
                    if self.dry_run:
                        logger.info(f"  [{doc.id}] [DRY RUN] Would add: {list(updates.keys())}")
                    else:
                        doc.reference.update(updates)
                        logger.info(f"  [{doc.id}] Added fields: {list(updates.keys())}")

                    self.stats["sources_migrated"] += 1
                else:
                    logger.debug(f"  [{doc.id}] Already has status fields, skipping")
                    self.stats["sources_skipped"] += 1

            except Exception as e:
                logger.error(f"  [{doc.id}] Error migrating: {e}")
                self.stats["sources_errors"] += 1

        logger.info(f"\nJob Sources Migration Summary:")
        logger.info(f"  Migrated: {self.stats['sources_migrated']}")
        logger.info(f"  Skipped (already migrated): {self.stats['sources_skipped']}")
        logger.info(f"  Errors: {self.stats['sources_errors']}")

    def verify_data_integrity(self) -> None:
        """Verify data integrity after migration."""
        logger.info("=" * 60)
        logger.info("Verifying data integrity...")
        logger.info("=" * 60)

        collection = self.db.collection("job-sources")
        docs = collection.stream()

        missing_status = 0
        missing_consecutive_failures = 0
        missing_auto_enabled = 0
        invalid_status = 0
        status_enabled_mismatch = 0
        total_sources = 0

        valid_statuses = {"pending_validation", "active", "disabled", "failed"}

        for doc in docs:
            total_sources += 1
            data = doc.to_dict()

            # Check for missing status
            if "status" not in data:
                logger.warning(f"  [{doc.id}] Missing 'status' field")
                missing_status += 1

            # Check for invalid status values
            elif data["status"] not in valid_statuses:
                logger.warning(f"  [{doc.id}] Invalid status value: {data['status']}")
                invalid_status += 1

            # Check for missing consecutiveFailures
            if "consecutiveFailures" not in data:
                logger.warning(f"  [{doc.id}] Missing 'consecutiveFailures' field")
                missing_consecutive_failures += 1

            # Check for missing autoEnabled
            if "autoEnabled" not in data:
                logger.warning(f"  [{doc.id}] Missing 'autoEnabled' field")
                missing_auto_enabled += 1

            # Check status/enabled consistency
            if "status" in data and "enabled" in data:
                status = data["status"]
                enabled = data["enabled"]

                # Active status should match enabled=true
                if status == "active" and not enabled:
                    logger.warning(f"  [{doc.id}] Mismatch: status='active' but enabled=false")
                    status_enabled_mismatch += 1
                # Disabled/failed status should match enabled=false
                elif status in {"disabled", "failed"} and enabled:
                    logger.warning(f"  [{doc.id}] Mismatch: status='{status}' but enabled=true")
                    status_enabled_mismatch += 1

        logger.info(f"\nJob Sources Integrity Check:")
        logger.info(f"  Total sources: {total_sources}")
        logger.info(f"  Missing 'status': {missing_status}")
        logger.info(f"  Invalid 'status': {invalid_status}")
        logger.info(f"  Missing 'consecutiveFailures': {missing_consecutive_failures}")
        logger.info(f"  Missing 'autoEnabled': {missing_auto_enabled}")
        logger.info(f"  Status/enabled mismatch: {status_enabled_mismatch}")

        if (missing_status == 0 and invalid_status == 0 and
            missing_consecutive_failures == 0 and missing_auto_enabled == 0 and
            status_enabled_mismatch == 0):
            logger.info("  ✅ All sources have valid status tracking fields")
        else:
            logger.warning("  ⚠️  Some sources are missing or have invalid fields")

    def run_migration(self) -> None:
        """Run full migration."""
        logger.info("=" * 60)
        logger.info("JOB SOURCE STATUS MIGRATION")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        logger.info(f"Database: {self.db._database}")
        logger.info("=" * 60)

        if not self.dry_run and not self.auto_approve:
            response = input("\n⚠️  WARNING: This will modify production data. Type 'yes' to continue: ")
            if response.lower() != "yes":
                logger.info("Migration cancelled.")
                return

        # Run migration
        self.migrate_job_sources()
        self.verify_data_integrity()

        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("MIGRATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Job Sources:")
        logger.info(f"  Migrated: {self.stats['sources_migrated']}")
        logger.info(f"  Skipped: {self.stats['sources_skipped']}")
        logger.info(f"  Errors: {self.stats['sources_errors']}")

        if self.dry_run:
            logger.info("\n✅ Dry run complete. Run with --execute to apply changes.")


def main():
    parser = argparse.ArgumentParser(description="Add status tracking to job-sources collection")
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
        "--yes",
        action="store_true",
        help="Auto-approve execution (skip confirmation prompt)"
    )

    args = parser.parse_args()

    # Determine dry_run mode
    dry_run = not args.execute if args.execute else args.dry_run

    migrator = SourceStatusMigrator(
        database_name=args.database,
        dry_run=dry_run
    )

    # Pass auto_approve flag
    migrator.auto_approve = args.yes

    migrator.run_migration()


if __name__ == "__main__":
    main()
