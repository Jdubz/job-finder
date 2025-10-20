#!/usr/bin/env python3
"""
Setup script to initialize job-queue collection in production database.

This script:
1. Verifies connection to production database
2. Creates a test queue item to initialize the collection
3. Verifies the item was created successfully
4. Optionally cleans up the test item

SAFETY: Requires --database flag and confirmation for production.
"""
import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

from job_finder.queue import JobQueueItem, QueueItemType, QueueManager

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def setup_queue_collection(database_name: str = "portfolio", cleanup: bool = True):
    """
    Initialize job-queue collection in production database.

    Args:
        database_name: Database name (default: portfolio)
        cleanup: Whether to delete test item after creation (default: True)
    """
    print("=" * 70)
    print(f"SETTING UP JOB-QUEUE COLLECTION: {database_name}")
    print("=" * 70)
    print()

    try:
        # 1. Verify credentials
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path or not Path(creds_path).exists():
            print("❌ Firebase credentials not found")
            print("   Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
            return False

        print(f"✅ Credentials: {creds_path}")
        print()

        # 2. Initialize queue manager
        print(f"Connecting to database: {database_name}")
        queue_manager = QueueManager(database_name=database_name)
        print(f"✅ Connected to database: {database_name}")
        print()

        # 3. Create test queue item
        print("Creating test queue item to initialize collection...")
        test_item = JobQueueItem(
            type=QueueItemType.JOB,
            url="https://example.com/test-job",
            company_name="Test Company",
            source="user_submission",
        )

        try:
            doc_id = queue_manager.add_item(test_item)
            print(f"✅ Test item created with ID: {doc_id}")
            print()

            # 4. Verify item was created
            print("Verifying test item...")
            retrieved_item = queue_manager.get_item(doc_id)

            if retrieved_item:
                print(f"✅ Test item verified:")
                print(f"   ID: {retrieved_item.id}")
                print(
                    f"   Type: {retrieved_item.type.value if hasattr(retrieved_item.type, 'value') else retrieved_item.type}"
                )
                print(f"   URL: {retrieved_item.url}")
                print(
                    f"   Status: {retrieved_item.status.value if hasattr(retrieved_item.status, 'value') else retrieved_item.status}"
                )
                print()

                # 5. Clean up test item if requested
                if cleanup:
                    print("Cleaning up test item...")
                    if queue_manager.delete_item(doc_id):
                        print("✅ Test item deleted")
                    else:
                        print("⚠️  Failed to delete test item (manual cleanup needed)")
                else:
                    print(f"⚠️  Test item left in queue (ID: {doc_id})")
                    print("   Delete manually or run with --cleanup")

                print()
                print("=" * 70)
                print("✅ JOB-QUEUE COLLECTION SETUP COMPLETE")
                print("=" * 70)
                print()
                print("The job-queue collection now exists in the production database.")
                print("job-finder-FE frontend should now be able to write queue items.")
                print()
                print("NEXT STEPS:")
                print("1. Verify job-finder-FE frontend is configured to use 'portfolio' database")
                print("2. Test document generation from job-finder-FE UI")
                print("3. Run diagnostic script to confirm items are being created:")
                print("   python scripts/diagnose_production_queue.py")
                print()

                return True
            else:
                print("❌ Failed to retrieve test item")
                return False

        except Exception as e:
            print(f"❌ Error creating test item: {e}")
            logger.exception("Detailed error:")
            return False

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        logger.exception("Detailed error:")
        return False


def main():
    """Main entry point with safety confirmation."""
    parser = argparse.ArgumentParser(
        description="Setup job-queue collection (creates test item to initialize)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
NOTE: This script creates and optionally deletes a single test item.
It is designed for initial database setup and is relatively safe.

Examples:
  # Setup staging
  python scripts/setup_production_queue.py --database portfolio-staging
  
  # Setup production (with confirmation)
  python scripts/setup_production_queue.py --database portfolio
        """,
    )
    parser.add_argument(
        "--database",
        required=True,
        choices=["portfolio-staging", "portfolio"],
        help="Database name to setup",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Leave test item in queue (don't delete after creation)",
    )

    args = parser.parse_args()

    # Add confirmation for production
    if args.database == "portfolio":
        print("=" * 70)
        print("⚠️  PRODUCTION DATABASE SETUP ⚠️")
        print("=" * 70)
        print(f"This will create a test item in {args.database} database.")
        print("This is relatively safe (only creates/deletes 1 test item).")
        print()
        response = input("Continue? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("Cancelled by user")
            sys.exit(0)
        print()

    success = setup_queue_collection(database_name=args.database, cleanup=not args.no_cleanup)

    if success:
        print()
        print("🎉 Setup successful! The job-queue collection is ready.")
        print()
        if args.database == "portfolio":
            print("⚠️  IMPORTANT: This only initializes the collection.")
            print("   You still need to verify job-finder-FE frontend configuration:")
            print()
            print("   1. Check job-finder-FE's Firestore database configuration")
            print("   2. Ensure it uses 'portfolio' database in production")
            print("   3. Verify Firestore security rules allow writes to job-queue")
            print()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
