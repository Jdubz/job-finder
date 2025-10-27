#!/usr/bin/env python3
"""
Re-process all production job matches.

This script:
1. Backs up all existing job matches from production
2. Deletes the job-matches collection
3. Re-submits all jobs through the queue intake system

Usage:
    # Dry run (backup only, no deletion or re-submission)
    python scripts/reprocess_job_matches.py --dry-run

    # Full run (backup, delete, re-submit)
    python scripts/reprocess_job_matches.py

    # Backup only
    python scripts/reprocess_job_matches.py --backup-only

    # Use specific backup file
    python scripts/reprocess_job_matches.py --backup-file data/custom_backup.json
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


from job_finder.job_queue.manager import QueueManager
from job_finder.job_queue.scraper_intake import ScraperIntake
from job_finder.storage.firestore_client import FirestoreClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class JobMatchReprocessor:
    """Re-process all job matches from production."""

    def __init__(self, database_name: str = "portfolio", credentials_path: str | None = None):
        """
        Initialize reprocessor.

        Args:
            database_name: Firestore database name (default: "portfolio" for production)
            credentials_path: Path to service account credentials
        """
        self.database_name = database_name
        self.db = FirestoreClient.get_client(database_name, credentials_path)
        self.collection_name = "job-matches"

    def backup_job_matches(self, backup_file: Path) -> List[Dict[str, Any]]:
        """
        Backup all job matches to a JSON file.

        Args:
            backup_file: Path to backup file

        Returns:
            List of job match documents
        """
        logger.info(f"📥 Backing up job matches from {self.database_name}...")

        # Query all job matches
        job_matches = []
        docs = self.db.collection(self.collection_name).stream()

        for doc in docs:
            data = doc.to_dict()
            data["_id"] = doc.id  # Preserve document ID
            job_matches.append(data)

        logger.info(f"Found {len(job_matches)} job matches")

        # Save to file
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        with open(backup_file, "w") as f:
            json.dump(job_matches, f, indent=2, default=str)

        logger.info(f"✅ Backup saved to {backup_file}")
        return job_matches

    def delete_job_matches(self, dry_run: bool = False) -> int:
        """
        Delete all job matches from the collection.

        Args:
            dry_run: If True, don't actually delete

        Returns:
            Number of documents deleted
        """
        logger.info(f"🗑️  Deleting job matches from {self.database_name}...")

        if dry_run:
            logger.info("DRY RUN: Would delete all job matches")
            # Count docs
            docs = list(self.db.collection(self.collection_name).stream())
            logger.info(f"Would delete {len(docs)} documents")
            return len(docs)

        # Delete all documents in collection
        # Firestore has a limit of 500 docs per batch
        deleted_count = 0
        batch_size = 500

        while True:
            # Get a batch of documents
            docs = self.db.collection(self.collection_name).limit(batch_size).stream()

            doc_list = list(docs)
            if not doc_list:
                break

            # Delete batch
            batch = self.db.batch()
            for doc in doc_list:
                batch.delete(doc.reference)
            batch.commit()

            deleted_count += len(doc_list)
            logger.info(f"Deleted {deleted_count} documents...")

        logger.info(f"✅ Deleted {deleted_count} job matches")
        return deleted_count

    def resubmit_jobs(self, job_matches: List[Dict[str, Any]], dry_run: bool = False) -> int:
        """
        Re-submit all jobs through the queue intake system.

        Args:
            job_matches: List of job match documents from backup
            dry_run: If True, don't actually submit

        Returns:
            Number of jobs submitted
        """
        logger.info(f"📤 Re-submitting {len(job_matches)} jobs through queue...")

        if dry_run:
            logger.info("DRY RUN: Would re-submit all jobs")
            return len(job_matches)

        # Initialize queue manager and intake
        queue_manager = QueueManager(database_name=self.database_name)
        intake = ScraperIntake(queue_manager)

        # Convert job matches to job dictionaries for intake
        jobs = []
        for match in job_matches:
            job = {
                "url": match.get("url", match.get("jobUrl", "")),
                "company": match.get("company", ""),
                "title": match.get("title", match.get("jobTitle", "")),
                "description": match.get("description", ""),
                "location": match.get("location", ""),
                "salary": match.get("salary"),
                "company_website": match.get("companyWebsite", ""),
                "posted_date": match.get("postedDate"),
            }

            # Only submit if we have a URL
            if job["url"]:
                jobs.append(job)
            else:
                logger.warning(f"Skipping job match without URL: {match.get('_id')}")

        logger.info(f"Submitting {len(jobs)} jobs to queue...")

        # Submit jobs through intake
        submitted_count = intake.submit_jobs(jobs, source="automated_scan")

        logger.info(f"✅ Submitted {submitted_count} jobs to queue")
        return submitted_count


def main():
    """Main function with production safety checks."""
    parser = argparse.ArgumentParser(
        description="Re-process all job matches (backup, delete, re-submit)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Safe - dry run on staging (no changes)
  python scripts/reprocess_job_matches.py --database portfolio-staging --dry-run
  
  # Safe - full run on staging
  python scripts/reprocess_job_matches.py --database portfolio-staging
  
  # Blocked - production requires flag
  python scripts/reprocess_job_matches.py --database portfolio
  
  # Dangerous - explicit production override
  python scripts/reprocess_job_matches.py --database portfolio --allow-production
        """,
    )
    parser.add_argument(
        "--database",
        required=True,
        choices=["portfolio-staging", "portfolio"],
        help="Database to process (use portfolio-staging for safety)",
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="DANGER: Allow production database modification (not recommended)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Backup only, don't delete or re-submit",
    )
    parser.add_argument(
        "--backup-only",
        action="store_true",
        help="Only backup, don't delete or re-submit",
    )
    parser.add_argument(
        "--backup-file",
        type=Path,
        help="Path to backup file (default: data/backups/job_matches_TIMESTAMP.json)",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup step (use existing backup file)",
    )

    args = parser.parse_args()

    # SAFETY CHECK: Prevent accidental production usage
    if args.database == "portfolio" and not args.allow_production:
        print("=" * 80)
        print("🚨 PRODUCTION DATABASE BLOCKED 🚨")
        print("=" * 80)
        print("")
        print("This script would DELETE and RE-SUBMIT all job-matches in production!")
        print("Database specified: portfolio (PRODUCTION)")
        print("")
        print("This script is designed for staging only.")
        print("Use --database portfolio-staging instead.")
        print("")
        print("If you REALLY need to run on production (not recommended):")
        print("  python scripts/reprocess_job_matches.py --database portfolio --allow-production")
        print("")
        print("=" * 80)
        import sys

        sys.exit(1)

    # Warning for production usage
    if args.database == "portfolio":
        print("=" * 80)
        print("⚠️  RUNNING ON PRODUCTION DATABASE ⚠️")
        print("=" * 80)
        print("This will DELETE and RE-SUBMIT all job-matches from production!")
        print("Press Ctrl+C within 10 seconds to abort...")
        print("=" * 80)
        import time

        time.sleep(10)

    # Generate default backup file path with timestamp
    if not args.backup_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.backup_file = Path(f"data/backups/job-matches-{timestamp}.json")

    logger.info("=" * 80)
    logger.info("JOB MATCHES RE-PROCESSING")
    logger.info("=" * 80)
    logger.info(f"Database: {args.database}")
    logger.info(f"Backup file: {args.backup_file}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Backup only: {args.backup_only}")
    logger.info("=" * 80)

    # Confirm if not dry run
    if not args.dry_run and not args.backup_only:
        response = input(
            f"\n⚠️  WARNING: This will DELETE all job matches in {args.database} "
            "and re-submit them through the queue.\n"
            "Are you sure you want to continue? (yes/no): "
        )
        if response.lower() not in ["yes", "y"]:
            logger.info("Cancelled by user")
            return

    # Initialize reprocessor
    reprocessor = JobMatchReprocessor(
        database_name=args.database, credentials_path=args.credentials
    )

    # Step 1: Backup
    job_matches = reprocessor.backup_job_matches(args.backup_file)

    if args.backup_only:
        logger.info("\n✅ Backup complete (backup-only mode)")
        return

    # Step 2: Delete
    deleted_count = reprocessor.delete_job_matches(dry_run=args.dry_run)

    # Step 3: Re-submit
    submitted_count = reprocessor.resubmit_jobs(job_matches, dry_run=args.dry_run)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Backed up: {len(job_matches)} job matches")
    logger.info(f"Deleted: {deleted_count} documents")
    logger.info(f"Re-submitted: {submitted_count} jobs to queue")
    logger.info("=" * 80)

    if args.dry_run:
        logger.info("\n🔍 DRY RUN COMPLETE - No changes were made")
    else:
        logger.info("\n✅ RE-PROCESSING COMPLETE")
        logger.info(f"\nJobs are now in the queue and will be processed by the queue worker.")
        logger.info("Monitor the queue-worker logs to see progress.")


if __name__ == "__main__":
    main()
