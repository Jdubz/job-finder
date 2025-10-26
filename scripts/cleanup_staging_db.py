#!/usr/bin/env python3
"""
Clean up staging database and reprocess job applications.

Steps:
1. Backup all existing job-matches to JSON
2. Delete job-matches collection
3. Delete job-queue collection (optional)
4. Re-add all jobs to queue for reprocessing through new filter pipeline
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from job_finder.job_queue.manager import QueueManager
from job_finder.job_queue.models import JobQueueItem, QueueItemType
from job_finder.storage.firestore_client import FirestoreClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_NAME = "portfolio-staging"
CREDENTIALS_PATH = ".firebase/static-sites-257923-firebase-adminsdk.json"
BACKUP_DIR = Path("data/backups")


class StagingDBCleanup:
    """Clean up and reset staging database."""

    def __init__(self):
        """Initialize with Firestore client and managers."""
        self.db = FirestoreClient.get_client(DATABASE_NAME, CREDENTIALS_PATH)
        self.queue_manager = QueueManager(CREDENTIALS_PATH, DATABASE_NAME)
        self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def backup_job_matches(self) -> List[Dict[str, Any]]:
        """
        Backup all job-matches to JSON file.

        Returns:
            List of job match documents
        """
        logger.info("Backing up job-matches collection...")

        # Get all job matches
        docs = self.db.collection("job-matches").stream()

        job_matches = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id

            # Convert timestamps to strings for JSON serialization
            for field in ["analyzed_at", "created_at"]:
                if field in data and data[field]:
                    data[field] = data[field].isoformat()

            job_matches.append(data)

        logger.info(f"Found {len(job_matches)} job matches to backup")

        # Save to file
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_file = BACKUP_DIR / f"job_matches_backup_{self.backup_timestamp}.json"

        with open(backup_file, "w") as f:
            json.dump(job_matches, f, indent=2)

        logger.info(f"Backed up to: {backup_file}")
        return job_matches

    def delete_collection(self, collection_name: str, batch_size: int = 100):
        """
        Delete all documents in a collection.

        Args:
            collection_name: Name of collection to delete
            batch_size: Number of documents to delete per batch
        """
        logger.info(f"Deleting {collection_name} collection...")

        collection_ref = self.db.collection(collection_name)

        deleted = 0
        while True:
            # Get batch of documents
            docs = list(collection_ref.limit(batch_size).stream())

            if not docs:
                break

            # Delete batch
            for doc in docs:
                doc.reference.delete()
                deleted += 1

            logger.info(f"Deleted {deleted} documents from {collection_name}...")

        logger.info(f"Deleted {deleted} total documents from {collection_name}")

    def requeue_jobs(self, job_matches: List[Dict[str, Any]]):
        """
        Add jobs back to queue for reprocessing.

        Args:
            job_matches: List of job match documents to requeue
        """
        logger.info("Re-adding jobs to queue...")

        queued = 0
        skipped = 0

        for match in job_matches:
            # Check if already in queue
            if self.queue_manager.url_exists_in_queue(match["url"]):
                logger.debug(f"Skipping {match['url']} - already in queue")
                skipped += 1
                continue

            # Create queue item
            queue_item = JobQueueItem(
                type=QueueItemType.JOB,
                url=match["url"],
                company_name=match.get("company_name", "Unknown"),
                company_id=match.get("company_id"),
                source="automated_scan",  # Original source lost, using generic
                submitted_by=match.get("submitted_by"),
            )

            # Add to queue
            try:
                self.queue_manager.add_item(queue_item)
                queued += 1
            except Exception as e:
                logger.error(f"Error queuing {match['url']}: {e}")

        logger.info(f"Queued {queued} jobs, skipped {skipped} duplicates")

    def run(self, delete_queue: bool = False, requeue: bool = True):
        """
        Run full cleanup process.

        Args:
            delete_queue: Whether to also delete job-queue collection
            requeue: Whether to re-add jobs to queue for reprocessing
        """
        logger.info("=" * 80)
        logger.info("STAGING DATABASE CLEANUP")
        logger.info("=" * 80)
        logger.info(f"Database: {DATABASE_NAME}")
        logger.info(f"Timestamp: {self.backup_timestamp}")
        logger.info("=" * 80)

        # Step 1: Backup
        job_matches = self.backup_job_matches()

        # Step 2: Delete job-matches
        input("\nPress Enter to DELETE job-matches collection (Ctrl+C to cancel)...")
        self.delete_collection("job-matches")

        # Step 3: Optionally delete queue
        if delete_queue:
            input("\nPress Enter to DELETE job-queue collection (Ctrl+C to cancel)...")
            self.delete_collection("job-queue")

        # Step 4: Requeue jobs
        if requeue:
            input("\nPress Enter to RE-QUEUE all jobs (Ctrl+C to cancel)...")
            self.requeue_jobs(job_matches)

        logger.info("=" * 80)
        logger.info("CLEANUP COMPLETE")
        logger.info("=" * 80)
        logger.info(
            f"Backup file: {BACKUP_DIR / f'job_matches_backup_{self.backup_timestamp}.json'}"
        )
        logger.info(f"Original job count: {len(job_matches)}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Review filter configuration in Firestore (job-finder-config/job-filters)")
        logger.info("2. Run queue processor to reprocess jobs with new filters")
        logger.info("3. Compare results with backup to see filtering impact")


if __name__ == "__main__":
    import sys

    cleanup = StagingDBCleanup()

    # Parse arguments
    delete_queue = "--delete-queue" in sys.argv
    no_requeue = "--no-requeue" in sys.argv

    print("\nOptions:")
    print(f"  Delete queue: {delete_queue}")
    print(f"  Requeue jobs: {not no_requeue}")
    print("\nUsage:")
    print("  python scripts/cleanup_staging_db.py [--delete-queue] [--no-requeue]")
    print()

    cleanup.run(delete_queue=delete_queue, requeue=not no_requeue)
