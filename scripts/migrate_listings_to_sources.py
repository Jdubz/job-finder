#!/usr/bin/env python3
"""
Migration script to convert job-listings collection to job-sources collection.

This script:
1. Reads all existing job-listings documents
2. For each listing with company data, creates/updates company record
3. Creates new job-source document with companyId reference
4. Preserves all tracking data (scrape stats, etc.)

Usage:
    python scripts/migrate_listings_to_sources.py [--database DATABASE_NAME] [--dry-run]

Arguments:
    --database: Firestore database name (default: portfolio-staging)
    --dry-run: Show what would be migrated without making changes
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path (before other imports)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# noqa: E402 (module level imports after sys.path modification)
from job_finder.storage.companies_manager import CompaniesManager  # noqa: E402
from job_finder.storage.firestore_client import FirestoreClient  # noqa: E402
from job_finder.storage.job_sources_manager import JobSourcesManager  # noqa: E402
from job_finder.storage.listings_manager import JobListingsManager  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ListingsToSourcesMigrator:
    """Migrates job-listings to job-sources with company extraction."""

    def __init__(self, database_name: str, dry_run: bool = False):
        """
        Initialize migrator.

        Args:
            database_name: Firestore database name
            dry_run: If True, don't make any changes
        """
        self.database_name = database_name
        self.dry_run = dry_run

        # Initialize managers
        self.companies_manager = CompaniesManager(database_name=database_name)
        self.sources_manager = JobSourcesManager(database_name=database_name)
        self.listings_manager = JobListingsManager(database_name=database_name)

        # Track statistics
        self.stats = {
            "listings_read": 0,
            "companies_created": 0,
            "companies_updated": 0,
            "sources_created": 0,
            "errors": 0,
        }

        # Track created company IDs for linking
        self.company_id_map: Dict[str, str] = {}  # name -> document_id

    def migrate(self) -> Dict:
        """
        Run the migration.

        Returns:
            Statistics dictionary
        """
        logger.info("=" * 70)
        logger.info("STARTING MIGRATION: job-listings → job-sources")
        logger.info("Database: %s", self.database_name)
        logger.info(f"Dry run: {self.dry_run}")
        logger.info("=" * 70)

        # Get all listings
        listings = self._get_all_listings()
        self.stats["listings_read"] = len(listings)
        logger.info(f"\nFound {len(listings)} job listings to migrate")

        # Process each listing
        for i, listing in enumerate(listings, 1):
            logger.info(f"\n[{i}/{len(listings)}] Processing: {listing.get('name', 'Unknown')}")
            try:
                self._migrate_listing(listing)
            except Exception as e:
                logger.error(f"Error migrating listing: {str(e)}", exc_info=True)
                self.stats["errors"] += 1

        # Print summary
        self._print_summary()

        return self.stats

    def _get_all_listings(self) -> List[Dict]:
        """
        Get all job-listings documents from Firestore.

        Returns:
            List of listing dictionaries
        """
        db = FirestoreClient.get_client(self.database_name)
        docs = db.collection("job-listings").stream()

        listings = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            listings.append(data)

        return listings

    def _migrate_listing(self, listing: Dict) -> None:
        """
        Migrate a single listing to the new schema.

        Args:
            listing: Listing document to migrate
        """
        listing_name = listing.get("name", "Unknown")

        # Extract company data if applicable
        company_id = None
        company_name = None

        if self._should_extract_company(listing):
            company_name, company_id = self._extract_and_create_company(listing)

        # Create source document
        source_data = self._build_source_document(listing, company_id, company_name)

        if self.dry_run:
            logger.info(f"  [DRY RUN] Would create source: {listing_name}")
            if company_name:
                logger.info(f"  [DRY RUN] Linked to company: {company_name}")
        else:
            source_id = self.sources_manager.add_source(**source_data)
            self.stats["sources_created"] += 1
            logger.info(f"  ✓ Created source: {listing_name} (ID: {source_id})")
            if company_name:
                logger.info(f"    → Linked to company: {company_name} (ID: {company_id})")

    def _should_extract_company(self, listing: Dict) -> bool:
        """
        Determine if listing has company data to extract.

        Args:
            listing: Listing document

        Returns:
            True if listing has company data
        """
        source_type = listing.get("sourceType", "")
        config = listing.get("config", {})

        # Greenhouse sources have company data
        if source_type == "greenhouse":
            return bool(listing.get("name") or config.get("company_name"))

        # Company-page sources have company data
        if source_type == "company-page":
            return bool(config.get("company_name"))

        # Check for company-specific fields
        has_company_name = bool(listing.get("company_name") or config.get("company_name"))
        has_company_website = bool(listing.get("company_website") or config.get("company_website"))

        return has_company_name or has_company_website

    def _extract_and_create_company(self, listing: Dict) -> tuple[str, Optional[str]]:
        """
        Extract company data from listing and create/update company record.

        Args:
            listing: Listing document

        Returns:
            Tuple of (company_name, company_id)
        """
        config = listing.get("config", {})

        # Extract company name
        company_name = (
            listing.get("name", "")
            or config.get("company_name", "")
            or listing.get("company_name", "")
        )

        # For Greenhouse, clean up the name (remove " Greenhouse" suffix)
        if listing.get("sourceType") == "greenhouse":
            company_name = company_name.replace(" Greenhouse", "").strip()

        if not company_name:
            logger.warning("  ⚠️  Could not extract company name")
            return "", None

        # Check if company already exists (in our map or database)
        if company_name in self.company_id_map:
            logger.info(f"  ℹ️  Company already created in this migration: {company_name}")
            return company_name, self.company_id_map[company_name]

        # Extract company data
        company_data = {
            "name": company_name,
            "website": (
                listing.get("company_website", "")
                or config.get("company_website", "")
                or config.get("careers_url", "")
            ),
            "about": config.get("company_info", ""),
            "hasPortlandOffice": listing.get("hasPortlandOffice", False),
            "techStack": listing.get("techStack", []),
            "tier": listing.get("tier", ""),
            "priorityScore": listing.get("priorityScore", 0),
        }

        # Remove empty strings
        company_data = {
            k: v for k, v in company_data.items() if v or isinstance(v, (bool, int, list))
        }

        if self.dry_run:
            logger.info(f"  [DRY RUN] Would create/update company: {company_name}")
            return company_name, "dry_run_id"

        try:
            # Save company (creates or updates)
            company_id = self.companies_manager.save_company(company_data)

            # Check if it was created or updated
            if company_id not in self.company_id_map.values():
                self.stats["companies_created"] += 1
                logger.info(f"  ✓ Created company: {company_name} (ID: {company_id})")
            else:
                self.stats["companies_updated"] += 1
                logger.info(f"  ✓ Updated company: {company_name} (ID: {company_id})")

            # Track for future references
            self.company_id_map[company_name] = company_id

            return company_name, company_id

        except Exception as e:
            logger.error(f"  ✗ Error creating company {company_name}: {str(e)}")
            self.stats["errors"] += 1
            return company_name, None

    def _build_source_document(
        self, listing: Dict, company_id: Optional[str], company_name: Optional[str]
    ) -> Dict:
        """
        Build source document from listing data.

        Args:
            listing: Original listing document
            company_id: Company document ID (if applicable)
            company_name: Company name (if applicable)

        Returns:
            Dictionary of source fields for add_source()
        """
        source_type = listing.get("sourceType", "unknown")
        config = listing.get("config", {}).copy()

        # Clean up config - remove company-specific fields that now go in company record
        fields_to_remove = ["company_name", "company_website", "company_info"]
        for field in fields_to_remove:
            config.pop(field, None)

        # For greenhouse, extract board_token from config or listing
        if source_type == "greenhouse":
            if "board_token" not in config:
                config["board_token"] = listing.get("board_token", "")

        return {
            "name": listing.get("name", "Unknown"),
            "source_type": source_type,
            "config": config,
            "enabled": listing.get("enabled", True),
            "company_id": company_id,
            "company_name": company_name,
            "tags": listing.get("tags", []),
        }

    def _print_summary(self) -> None:
        """Print migration summary statistics."""
        logger.info("\n" + "=" * 70)
        logger.info("MIGRATION COMPLETE!")
        logger.info("=" * 70)
        logger.info("\n📊 STATISTICS:")
        logger.info(f"  Listings read: {self.stats['listings_read']}")
        logger.info(f"  Companies created: {self.stats['companies_created']}")
        logger.info(f"  Companies updated: {self.stats['companies_updated']}")
        logger.info(f"  Sources created: {self.stats['sources_created']}")
        logger.info(f"  Errors: {self.stats['errors']}")

        if self.dry_run:
            logger.info("\n⚠️  This was a DRY RUN - no changes were made")
        else:
            logger.info("\n✅ Migration successful!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate job-listings to job-sources with company extraction"
    )
    parser.add_argument(
        "--database",
        default="portfolio-staging",
        help="Firestore database name (default: portfolio-staging)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )

    args = parser.parse_args()

    # Run migration
    migrator = ListingsToSourcesMigrator(
        database_name=args.database,
        dry_run=args.dry_run,
    )

    try:
        stats = migrator.migrate()

        # Exit with error code if there were errors
        if stats["errors"] > 0:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
