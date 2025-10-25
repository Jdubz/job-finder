#!/usr/bin/env python3
"""
Production Verification Script

Verifies that production is functioning correctly after data cleanup.

Usage:
    python scripts/verify_production.py --database portfolio
"""

import argparse
import logging
from google.cloud import firestore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verify_production(database_name: str):
    """Verify production database health."""

    logger.info("=" * 60)
    logger.info(f"PRODUCTION VERIFICATION - {database_name}")
    logger.info("=" * 60)

    db = firestore.Client(database=database_name)

    # Check collections exist and are accessible
    collections_to_check = [
        "job-queue",
        "job-matches",
        "companies",
        "job-sources",
        "job-finder-config"
    ]

    logger.info("\n1. Verifying collection access...")
    for coll_name in collections_to_check:
        try:
            # Try to read one document
            docs = db.collection(coll_name).limit(1).stream()
            doc_list = list(docs)
            logger.info(f"  ✅ {coll_name}: Accessible")
        except Exception as e:
            logger.error(f"  ❌ {coll_name}: Error - {e}")

    # Check queue items
    logger.info("\n2. Checking job-queue status...")
    queue_stats = {
        "pending": 0,
        "processing": 0,
        "success": 0,
        "failed": 0,
        "filtered": 0,
        "skipped": 0,
        "total": 0
    }

    for doc in db.collection("job-queue").stream():
        data = doc.to_dict()
        status = data.get("status", "unknown")
        queue_stats["total"] += 1
        if status in queue_stats:
            queue_stats[status] += 1

    logger.info(f"  Total items: {queue_stats['total']}")
    logger.info(f"  Pending: {queue_stats['pending']}")
    logger.info(f"  Processing: {queue_stats['processing']}")
    logger.info(f"  Success: {queue_stats['success']}")
    logger.info(f"  Failed: {queue_stats['failed']}")
    logger.info(f"  Filtered: {queue_stats['filtered']}")
    logger.info(f"  Skipped: {queue_stats['skipped']}")

    # Check job-matches
    logger.info("\n3. Checking job-matches...")
    matches_count = 0
    for doc in db.collection("job-matches").stream():
        matches_count += 1
    logger.info(f"  Total matches: {matches_count}")

    # Check companies
    logger.info("\n4. Checking companies...")
    companies_count = 0
    for doc in db.collection("companies").stream():
        companies_count += 1
    logger.info(f"  Total companies: {companies_count}")

    # Check job-sources
    logger.info("\n5. Checking job-sources...")
    sources_count = 0
    enabled_sources = 0
    for doc in db.collection("job-sources").stream():
        sources_count += 1
        data = doc.to_dict()
        if data.get("enabled", False):
            enabled_sources += 1
    logger.info(f"  Total sources: {sources_count}")
    logger.info(f"  Enabled sources: {enabled_sources}")

    # Check configuration
    logger.info("\n6. Checking configuration...")
    config_docs = ["ai-settings", "queue-settings", "stop-list"]
    for doc_id in config_docs:
        try:
            doc = db.collection("job-finder-config").document(doc_id).get()
            if doc.exists:
                logger.info(f"  ✅ {doc_id}: Exists")
            else:
                logger.warning(f"  ⚠️  {doc_id}: Not found")
        except Exception as e:
            logger.error(f"  ❌ {doc_id}: Error - {e}")

    logger.info("\n" + "=" * 60)
    logger.info("VERIFICATION COMPLETE")
    logger.info("=" * 60)

    # Summary
    logger.info("\nSummary:")
    logger.info(f"  Queue items: {queue_stats['total']}")
    logger.info(f"  Job matches: {matches_count}")
    logger.info(f"  Companies: {companies_count}")
    logger.info(f"  Job sources: {sources_count} ({enabled_sources} enabled)")

    if queue_stats['total'] == 0 and matches_count == 2:
        logger.info("\n✅ Production is clean and ready for fresh data!")
    elif queue_stats['processing'] > 0:
        logger.warning("\n⚠️  Queue has items processing - wait for completion")
    else:
        logger.info("\n✅ Production appears healthy")


def main():
    parser = argparse.ArgumentParser(description="Verify production database")
    parser.add_argument(
        "--database",
        required=True,
        help="Firestore database name (e.g., 'portfolio')"
    )

    args = parser.parse_args()
    verify_production(args.database)


if __name__ == "__main__":
    main()
