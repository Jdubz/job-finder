#!/usr/bin/env python3
"""
Company Status Migration Script

Adds status tracking fields to companies collection:
1. Adds "status" field (defaults to "active" for existing companies)
2. Adds "last_analyzed_at" field (defaults to updatedAt or current time)
3. Verifies data integrity

This migration is safe to run multiple times (idempotent).

Usage:
    python scripts/database/001_add_company_status.py --database portfolio --dry-run
    python scripts/database/001_add_company_status.py --database portfolio --execute
"""

import argparse
import logging

from google.cloud import firestore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompanyStatusMigrator:
    """Adds status tracking to companies collection."""

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
            "companies_migrated": 0,
            "companies_skipped": 0,
            "companies_errors": 0,
        }

    def migrate_companies(self) -> None:
        """
        Migrate companies collection.

        Changes:
        - Add "status" field (default: "active")
        - Add "last_analyzed_at" field (default: updatedAt or now)
        """
        logger.info("=" * 60)
        logger.info("Migrating companies collection...")
        logger.info("=" * 60)

        collection = self.db.collection("companies")
        docs = collection.stream()

        for doc in docs:
            try:
                data = doc.to_dict()
                updates = {}

                # Check if status field is missing
                if "status" not in data:
                    # Default to "active" for existing companies
                    # (they exist, so they've been analyzed)
                    updates["status"] = "active"
                    logger.info(f"  [{doc.id}] Adding status='active'")

                # Check if last_analyzed_at is missing
                if "last_analyzed_at" not in data:
                    # Use updatedAt if available, otherwise current time
                    if "updatedAt" in data:
                        updates["last_analyzed_at"] = data["updatedAt"]
                        logger.info(f"  [{doc.id}] Adding last_analyzed_at from updatedAt")
                    else:
                        updates["last_analyzed_at"] = firestore.SERVER_TIMESTAMP
                        logger.info(f"  [{doc.id}] Adding last_analyzed_at (current time)")

                # Apply updates
                if updates:
                    if self.dry_run:
                        logger.info(f"  [{doc.id}] [DRY RUN] Would add: {list(updates.keys())}")
                    else:
                        doc.reference.update(updates)
                        logger.info(f"  [{doc.id}] Added fields: {list(updates.keys())}")

                    self.stats["companies_migrated"] += 1
                else:
                    logger.debug(f"  [{doc.id}] Already has status and last_analyzed_at, skipping")
                    self.stats["companies_skipped"] += 1

            except Exception as e:
                logger.error(f"  [{doc.id}] Error migrating: {e}")
                self.stats["companies_errors"] += 1

        logger.info(f"\nCompanies Migration Summary:")
        logger.info(f"  Migrated: {self.stats['companies_migrated']}")
        logger.info(f"  Skipped (already migrated): {self.stats['companies_skipped']}")
        logger.info(f"  Errors: {self.stats['companies_errors']}")

    def verify_data_integrity(self) -> None:
        """Verify data integrity after migration."""
        logger.info("=" * 60)
        logger.info("Verifying data integrity...")
        logger.info("=" * 60)

        collection = self.db.collection("companies")
        docs = collection.stream()

        missing_status = 0
        missing_last_analyzed = 0
        invalid_status = 0
        total_companies = 0

        valid_statuses = {"pending", "analyzing", "active", "failed"}

        for doc in docs:
            total_companies += 1
            data = doc.to_dict()

            # Check for missing status
            if "status" not in data:
                logger.warning(f"  [{doc.id}] Missing 'status' field")
                missing_status += 1

            # Check for invalid status values
            elif data["status"] not in valid_statuses:
                logger.warning(f"  [{doc.id}] Invalid status value: {data['status']}")
                invalid_status += 1

            # Check for missing last_analyzed_at
            if "last_analyzed_at" not in data:
                logger.warning(f"  [{doc.id}] Missing 'last_analyzed_at' field")
                missing_last_analyzed += 1

        logger.info(f"\nCompanies Integrity Check:")
        logger.info(f"  Total companies: {total_companies}")
        logger.info(f"  Missing 'status': {missing_status}")
        logger.info(f"  Invalid 'status': {invalid_status}")
        logger.info(f"  Missing 'last_analyzed_at': {missing_last_analyzed}")

        if missing_status == 0 and invalid_status == 0 and missing_last_analyzed == 0:
            logger.info("  ✅ All companies have valid status tracking fields")
        else:
            logger.warning("  ⚠️  Some companies are missing or have invalid fields")

    def run_migration(self) -> None:
        """Run full migration."""
        logger.info("=" * 60)
        logger.info("COMPANY STATUS MIGRATION")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        logger.info(f"Database: {self.db._database}")
        logger.info("=" * 60)

        if not self.dry_run and not self.auto_approve:
            response = input("\n⚠️  WARNING: This will modify production data. Type 'yes' to continue: ")
            if response.lower() != "yes":
                logger.info("Migration cancelled.")
                return

        # Run migration
        self.migrate_companies()
        self.verify_data_integrity()

        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("MIGRATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Companies:")
        logger.info(f"  Migrated: {self.stats['companies_migrated']}")
        logger.info(f"  Skipped: {self.stats['companies_skipped']}")
        logger.info(f"  Errors: {self.stats['companies_errors']}")

        if self.dry_run:
            logger.info("\n✅ Dry run complete. Run with --execute to apply changes.")


def main():
    parser = argparse.ArgumentParser(description="Add status tracking to companies collection")
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

    migrator = CompanyStatusMigrator(
        database_name=args.database,
        dry_run=dry_run
    )

    # Pass auto_approve flag
    migrator.auto_approve = args.yes

    migrator.run_migration()


if __name__ == "__main__":
    main()
