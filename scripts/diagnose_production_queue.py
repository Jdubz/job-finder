#!/usr/bin/env python3
"""
Diagnostic script to check production database and job-queue collection.

This script verifies:
1. Connection to production database
2. Existence of job-queue collection
3. Recent queue items (if any)
4. Database configuration
"""
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

from job_finder.queue import QueueManager
from job_finder.storage.firestore_client import FirestoreClient

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def diagnose_database(database_name: str = "portfolio"):
    """
    Diagnose production database configuration.

    Args:
        database_name: Database to check (default: portfolio for production)
    """
    print("=" * 70)
    print(f"PRODUCTION DATABASE DIAGNOSTIC: {database_name}")
    print("=" * 70)
    print()

    try:
        # 1. Check credentials
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path:
            print("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
            print("   Set this environment variable to your service account JSON path")
            return False

        if not Path(creds_path).exists():
            print(f"❌ Credentials file not found: {creds_path}")
            return False

        print(f"✅ Credentials found: {creds_path}")
        print()

        # 2. Test database connection
        print(f"Connecting to database: {database_name}")
        try:
            db = FirestoreClient.get_client(database_name)
            print(f"✅ Connected to database: {database_name}")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            return False

        print()

        # 3. Check job-queue collection
        print("Checking job-queue collection...")
        try:
            queue_ref = db.collection("job-queue")

            # Count total items
            total_count = 0
            for _ in queue_ref.limit(1).stream():
                total_count = 1
                break

            if total_count == 0:
                print("⚠️  job-queue collection is EMPTY or DOES NOT EXIST")
                print(
                    "   This is why queue items are not appearing in production!"
                )
                print()
                print("   SOLUTION: Ensure job-finder-FE frontend is configured to write to")
                print(f"   database '{database_name}' in production")
            else:
                print("✅ job-queue collection exists and has items")

        except Exception as e:
            print(f"❌ Error checking job-queue collection: {e}")
            return False

        print()

        # 4. Get recent queue items (last 7 days)
        print("Checking recent queue items (last 7 days)...")
        try:
            queue_manager = QueueManager(database_name=database_name)

            # Get all items from last 7 days
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            recent_query = (
                db.collection("job-queue")
                .where("created_at", ">=", cutoff)
                .order_by("created_at", direction="DESCENDING")
                .limit(10)
            )

            recent_items = list(recent_query.stream())

            if not recent_items:
                print("⚠️  No queue items in last 7 days")
                print(
                    "   If you expect document generation requests, this confirms"
                )
                print("   they are not being written to this database")
            else:
                print(f"✅ Found {len(recent_items)} recent queue items:")
                print()
                for doc in recent_items[:5]:  # Show first 5
                    data = doc.to_dict()
                    created_at = data.get("created_at")
                    item_type = data.get("type", "unknown")
                    status = data.get("status", "unknown")
                    url = data.get("url", "N/A")[:50]

                    print(f"  - {created_at}: {item_type} ({status}) - {url}")

        except Exception as e:
            print(f"⚠️  Error querying recent items: {e}")

        print()

        # 5. Get queue statistics
        print("Queue statistics:")
        try:
            queue_manager = QueueManager(database_name=database_name)
            stats = queue_manager.get_queue_stats()

            print(f"  Total items: {stats['total']}")
            print(f"  Pending: {stats['pending']}")
            print(f"  Processing: {stats['processing']}")
            print(f"  Success: {stats['success']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Skipped: {stats['skipped']}")
            print(f"  Filtered: {stats['filtered']}")

        except Exception as e:
            print(f"⚠️  Error getting queue stats: {e}")

        print()
        print("=" * 70)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 70)

        return True

    except Exception as e:
        logger.error(f"Diagnostic failed: {e}", exc_info=True)
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Diagnose production database and job-queue collection"
    )
    parser.add_argument(
        "--database",
        default="portfolio",
        help="Database name to check (default: portfolio for production)",
    )

    args = parser.parse_args()

    success = diagnose_database(args.database)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
