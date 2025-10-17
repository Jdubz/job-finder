#!/usr/bin/env python3
"""
Test full pipeline by submitting jobs through the API endpoint.

This script:
1. Backs up current job-matches
2. Clears staging database
3. Submits a sample of jobs through the /api/queue/submit endpoint
4. Monitors queue processing
5. Reports results
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from job_finder.storage.firestore_client import FirestoreClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_NAME = "portfolio-staging"
CREDENTIALS_PATH = ".firebase/static-sites-257923-firebase-adminsdk.json"
BACKUP_DIR = Path("data/backups")

# How many jobs to test with (to avoid overwhelming the system)
MAX_JOBS_TO_TEST = 1


class PipelineTester:
    """Test full job processing pipeline."""

    def __init__(self):
        """Initialize with Firestore client."""
        self.db = FirestoreClient.get_client(DATABASE_NAME, CREDENTIALS_PATH)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    def backup_current_data(self) -> Dict[str, Any]:
        """
        Backup current job-matches to JSON file.

        Returns:
            Dictionary with backed up data
        """
        logger.info("Backing up current job-matches...")

        docs = list(self.db.collection("job-matches").stream())
        jobs = []

        for doc in docs:
            data = doc.to_dict()
            data["_doc_id"] = doc.id
            jobs.append(data)

        backup_data = {
            "backup_timestamp": datetime.now().isoformat(),
            "database": DATABASE_NAME,
            "total_jobs": len(jobs),
            "jobs": jobs,
        }

        # Save backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"pipeline_test_backup_{timestamp}.json"

        with open(backup_file, "w") as f:
            json.dump(backup_data, f, indent=2, default=str)

        logger.info(f"Backed up {len(jobs)} jobs to: {backup_file}")
        return backup_data

    def clear_database(self):
        """Clear job-matches and job-queue collections."""
        logger.info("Clearing database collections...")

        # Clear job-matches
        batch = self.db.batch()
        count = 0
        for doc in self.db.collection("job-matches").stream():
            batch.delete(doc.reference)
            count += 1
            if count % 500 == 0:
                batch.commit()
                batch = self.db.batch()

        if count % 500 != 0:
            batch.commit()
        logger.info(f"Deleted {count} job-matches")

        # Clear job-queue
        batch = self.db.batch()
        count = 0
        for doc in self.db.collection("job-queue").stream():
            batch.delete(doc.reference)
            count += 1
            if count % 500 == 0:
                batch.commit()
                batch = self.db.batch()

        if count % 500 != 0:
            batch.commit()
        logger.info(f"Deleted {count} queue items")

    def submit_jobs_to_queue(self, jobs: List[Dict[str, Any]], max_jobs: int) -> List[str]:
        """
        Submit jobs directly to Firestore queue.

        Args:
            jobs: List of job data to submit
            max_jobs: Maximum number of jobs to submit

        Returns:
            List of queue item IDs
        """
        logger.info(f"Submitting up to {max_jobs} jobs to queue...")

        queue_ids = []

        # Select a diverse sample of jobs
        jobs_to_submit = jobs[:max_jobs]

        for i, job in enumerate(jobs_to_submit, 1):
            # Prepare queue item
            queue_item = {
                "url": job.get("url", ""),
                "company_name": job.get("company", ""),
                "type": "job",
                "status": "pending",
                "retry_count": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                # Include scraped data so processor doesn't need to scrape again
                "scraped_data": {
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "description": job.get("description", ""),
                    "location": job.get("location", ""),
                    "salary": job.get("salary", ""),
                    "posted_date": job.get("postedDate"),
                    "url": job.get("url", ""),
                    "company_website": job.get("companyWebsite", ""),
                },
            }

            try:
                doc_ref = self.db.collection("job-queue").document()
                doc_ref.set(queue_item)
                queue_id = doc_ref.id
                queue_ids.append(queue_id)

                logger.info(
                    f"[{i}/{len(jobs_to_submit)}] Queued: {job.get('title')} "
                    f"(Queue ID: {queue_id})"
                )

            except Exception as e:
                logger.error(f"[{i}/{len(jobs_to_submit)}] Error queueing {job.get('title')}: {e}")

        logger.info(f"Submitted {len(queue_ids)} jobs to queue")
        return queue_ids

    def monitor_queue_processing(self, queue_ids: List[str], timeout: int = 300) -> Dict[str, Any]:
        """
        Monitor queue processing until all items are processed or timeout.

        Args:
            queue_ids: List of queue item IDs to monitor
            timeout: Maximum time to wait in seconds

        Returns:
            Statistics about processing
        """
        logger.info(f"Monitoring {len(queue_ids)} queue items (timeout: {timeout}s)...")

        start_time = time.time()
        stats = {
            "total": len(queue_ids),
            "success": 0,
            "filtered": 0,
            "failed": 0,
            "skipped": 0,
            "pending": len(queue_ids),
            "processing": 0,
            "timeout": False,
        }

        while time.time() - start_time < timeout:
            # Check status of all queue items
            pending_count = 0
            processing_count = 0
            success_count = 0
            filtered_count = 0
            failed_count = 0
            skipped_count = 0

            for queue_id in queue_ids:
                doc = self.db.collection("job-queue").document(queue_id).get()

                if doc.exists:
                    data = doc.to_dict()
                    status = data.get("status", "unknown")

                    if status == "pending":
                        pending_count += 1
                    elif status == "processing":
                        processing_count += 1
                    elif status == "success":
                        success_count += 1
                    elif status == "filtered":
                        filtered_count += 1
                    elif status == "failed":
                        failed_count += 1
                    elif status == "skipped":
                        skipped_count += 1

            # Update stats
            stats["pending"] = pending_count
            stats["processing"] = processing_count
            stats["success"] = success_count
            stats["filtered"] = filtered_count
            stats["failed"] = failed_count
            stats["skipped"] = skipped_count

            # Log progress
            logger.info(
                f"Status: {success_count} success, {filtered_count} filtered, "
                f"{skipped_count} skipped, {failed_count} failed, "
                f"{processing_count} processing, {pending_count} pending"
            )

            # Check if all done
            if pending_count == 0 and processing_count == 0:
                logger.info("All queue items processed!")
                break

            # Wait before next check
            time.sleep(5)

        else:
            # Timeout reached
            logger.warning(f"Timeout reached after {timeout}s")
            stats["timeout"] = True

        return stats

    def analyze_results(self) -> Dict[str, Any]:
        """
        Analyze final results in job-matches collection.

        Returns:
            Analysis statistics
        """
        logger.info("Analyzing final results...")

        job_matches = list(self.db.collection("job-matches").stream())
        jobs_list = []

        for doc in job_matches:
            data = doc.to_dict()
            jobs_list.append(
                {
                    "title": data.get("title", ""),
                    "company": data.get("company", ""),
                    "match_score": data.get("matchScore", 0),
                    "priority": data.get("applicationPriority", "Unknown"),
                    "filter_strikes": data.get("filter_result", {}).get("strikes", 0),
                }
            )

        # Sort by match score
        jobs_list.sort(key=lambda x: x["match_score"], reverse=True)

        analysis = {
            "total_matched": len(jobs_list),
            "high_priority": sum(1 for j in jobs_list if j["priority"] == "High"),
            "medium_priority": sum(1 for j in jobs_list if j["priority"] == "Medium"),
            "low_priority": sum(1 for j in jobs_list if j["priority"] == "Low"),
            "avg_match_score": (
                sum(j["match_score"] for j in jobs_list) / len(jobs_list) if jobs_list else 0
            ),
            "jobs": jobs_list,
        }

        return analysis

    def run(self):
        """Run full pipeline test."""
        logger.info("=" * 80)
        logger.info("FULL PIPELINE TEST")
        logger.info("=" * 80)

        # Step 1: Backup
        backup_data = self.backup_current_data()
        original_jobs = backup_data["jobs"]

        # Step 2: Clear database
        self.clear_database()

        # Step 3: Submit jobs to queue
        queue_ids = self.submit_jobs_to_queue(original_jobs, MAX_JOBS_TO_TEST)

        if not queue_ids:
            logger.error("No jobs submitted successfully. Exiting.")
            return

        logger.info("\n⚠️  NOTE: Make sure the queue processor is running!")
        logger.info("If running locally: make run-local")
        logger.info("If using Docker: docker-compose up -d\n")

        # Step 4: Monitor processing
        queue_stats = self.monitor_queue_processing(queue_ids)

        # Step 5: Analyze results
        results = self.analyze_results()

        # Step 6: Report
        print("\n" + "=" * 80)
        print("PIPELINE TEST RESULTS")
        print("=" * 80)

        print(f"\nQueue Processing:")
        print(f"  Total submitted: {queue_stats['total']}")
        print(f"  Success: {queue_stats['success']}")
        print(f"  Filtered: {queue_stats['filtered']}")
        print(f"  Skipped: {queue_stats['skipped']}")
        print(f"  Failed: {queue_stats['failed']}")
        if queue_stats["timeout"]:
            print(f"  ⚠️  Processing timed out with {queue_stats['pending']} pending")

        print(f"\nFinal Job Matches:")
        print(f"  Total matched: {results['total_matched']}")
        print(f"  High priority: {results['high_priority']}")
        print(f"  Medium priority: {results['medium_priority']}")
        print(f"  Low priority: {results['low_priority']}")
        print(f"  Average match score: {results['avg_match_score']:.1f}")

        if results["jobs"]:
            print(f"\nTop Matches:")
            for job in results["jobs"][:5]:
                print(
                    f"  - {job['title']} at {job['company']} "
                    f"(Score: {job['match_score']}, Priority: {job['priority']}, "
                    f"Strikes: {job['filter_strikes']})"
                )

        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    tester = PipelineTester()
    tester.run()
