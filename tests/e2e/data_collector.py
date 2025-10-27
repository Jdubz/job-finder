"""
E2E Test Data Collector

Automates periodic E2E testing with comprehensive data collection:
1. Backs up existing Firestore data
2. Clears test collections
3. Submits test jobs with known values
4. Records all results (logs, Firestore snapshots, metrics)
5. Generates analysis reports

Usage:
    python tests/e2e/data_collector.py \
        --database portfolio-staging \
        --output-dir ./test_results/run_001
"""

import json
import logging
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from job_finder.storage.firestore_client import FirestoreClient

logger = logging.getLogger(__name__)


@dataclass
class BackupMetadata:
    """Metadata for a Firestore backup."""

    timestamp: str
    database_name: str
    collections_backed_up: List[str] = field(default_factory=list)
    document_counts: Dict[str, int] = field(default_factory=dict)
    total_documents: int = 0
    backup_path: str = ""
    backup_size_bytes: int = 0


@dataclass
class TestJobSubmission:
    """Record of a submitted test job."""

    submission_id: str
    timestamp: str
    company_name: str
    job_title: str
    job_url: str
    source_type: str  # greenhouse, rss, api, etc.
    expected_status: str  # should_create, should_skip, should_merge
    actual_result: Optional[str] = None  # what actually happened
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)


@dataclass
class TestRunResult:
    """Complete results from a test run."""

    test_run_id: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: float = 0.0

    # Backup info
    backup_metadata: Optional[BackupMetadata] = None
    backup_restored: bool = False

    # Submission info
    jobs_submitted: int = 0
    jobs_succeeded: int = 0
    jobs_failed: int = 0
    submission_records: List[TestJobSubmission] = field(default_factory=list)

    # Final state
    final_collection_counts: Dict[str, int] = field(default_factory=dict)
    data_quality_score: float = 0.0
    issues_found: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.jobs_submitted == 0:
            return 0.0
        return (self.jobs_succeeded / self.jobs_submitted) * 100


class FirestoreBackupRestore:
    """Handles backing up and restoring Firestore collections."""

    def __init__(self, database_name: str):
        """Initialize backup/restore utility."""
        self.db = FirestoreClient.get_client(database_name)
        self.database_name = database_name

    def backup_collection(
        self, collection_name: str, limit: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Backup a Firestore collection to list of documents.

        Args:
            collection_name: Name of collection to backup
            limit: Maximum documents to fetch

        Returns:
            Tuple of (documents list, document count)
        """
        logger.info(f"Backing up collection: {collection_name}")

        docs = []
        query = self.db.collection(collection_name)

        if limit:
            query = query.limit(limit)

        for doc in query.stream():
            docs.append(
                {
                    "id": doc.id,
                    **doc.to_dict(),
                }
            )

        logger.info(f"  Backed up {len(docs)} documents from {collection_name}")
        return docs, len(docs)

    def backup_all(
        self,
        collections: List[str],
        backup_dir: Path,
    ) -> BackupMetadata:
        """
        Backup multiple collections to JSON files.

        Args:
            collections: List of collection names to backup
            backup_dir: Directory to save backup files

        Returns:
            BackupMetadata with backup info
        """
        backup_dir.mkdir(parents=True, exist_ok=True)

        metadata = BackupMetadata(
            timestamp=datetime.utcnow().isoformat(),
            database_name=self.database_name,
            collections_backed_up=collections,
            backup_path=str(backup_dir),
        )

        total_size = 0

        for collection_name in collections:
            docs, count = self.backup_collection(collection_name)
            metadata.document_counts[collection_name] = count
            metadata.total_documents += count

            # Save to JSON
            backup_file = backup_dir / f"{collection_name}.json"
            with open(backup_file, "w") as f:
                json.dump(docs, f, indent=2, default=str)

            file_size = backup_file.stat().st_size
            total_size += file_size
            logger.info(f"  Saved to {backup_file.name} ({file_size:,} bytes)")

        metadata.backup_size_bytes = total_size

        # Save metadata
        metadata_file = backup_dir / "backup_metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(asdict(metadata), f, indent=2)

        logger.info(f"Backup complete: {metadata.total_documents} documents")
        return metadata

    def clear_collection(self, collection_name: str, batch_size: int = 100) -> int:
        """
        Clear all documents from a collection.

        Args:
            collection_name: Name of collection to clear
            batch_size: Batch size for deletion

        Returns:
            Number of documents deleted
        """
        logger.info(f"Clearing collection: {collection_name}")

        deleted_count = 0
        batch = self.db.batch()

        for doc in self.db.collection(collection_name).stream():
            batch.delete(doc.reference)
            deleted_count += 1

            if deleted_count % batch_size == 0:
                batch.commit()
                logger.info(f"  Deleted {deleted_count} documents...")
                batch = self.db.batch()

        # Final batch
        if deleted_count % batch_size != 0:
            batch.commit()

        logger.info(f"  Cleared {deleted_count} documents from {collection_name}")
        return deleted_count

    def clear_collections(self, collections: List[str]) -> Dict[str, int]:
        """
        Clear multiple collections.

        Args:
            collections: List of collection names to clear

        Returns:
            Dictionary mapping collection names to document counts deleted
        """
        results = {}
        for collection_name in collections:
            results[collection_name] = self.clear_collection(collection_name)
        return results

    def restore_collection(self, collection_name: str, backup_file: Path) -> int:
        """
        Restore a collection from backup file.

        Args:
            collection_name: Collection to restore to
            backup_file: Backup JSON file

        Returns:
            Number of documents restored
        """
        logger.info(f"Restoring collection from {backup_file.name}")

        with open(backup_file, "r") as f:
            docs = json.load(f)

        batch = self.db.batch()
        restored_count = 0

        for doc_data in docs:
            doc_id = doc_data.pop("id", None)
            if doc_id:
                batch.set(
                    self.db.collection(collection_name).document(doc_id),
                    doc_data,
                )
                restored_count += 1

                if restored_count % 100 == 0:
                    batch.commit()
                    batch = self.db.batch()

        # Final batch
        if restored_count % 100 != 0:
            batch.commit()

        logger.info(f"  Restored {restored_count} documents to {collection_name}")
        return restored_count


class TestJobSubmitter:
    """Submits test jobs with known values for validation."""

    def __init__(self, database_name: str, test_count: int = 4, source_database: str = "portfolio"):
        """
        Initialize job submitter.

        Args:
            database_name: Name of database to use (test database)
            test_count: Number of test jobs to submit (1-4, default: 4)
            source_database: Database to fetch real job URLs from (default: portfolio)
        """
        from job_finder.queue import QueueManager
        from job_finder.job_queue.scraper_intake import ScraperIntake

        self.db = FirestoreClient.get_client(database_name)
        self.queue_manager = QueueManager(database_name)
        self.intake = ScraperIntake(self.queue_manager)

        # Fetch real job URLs from production database
        self.source_db = FirestoreClient.get_client(source_database)
        self.test_count = test_count
        self.TEST_JOBS = self._get_real_test_jobs()

    def _get_real_test_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch real job URLs from production database.

        Returns:
            List of test jobs with real URLs
        """
        logger.info(f"Fetching {self.test_count} real job URLs from production...")

        jobs = []

        try:
            # Get jobs from job-matches (no ordering to avoid index issues)
            # Just get the first few jobs we find
            query = self.source_db.collection("job-matches").limit(self.test_count * 3)

            for doc in query.stream():
                if len(jobs) >= self.test_count:
                    break

                data = doc.to_dict()
                if not data:
                    continue

                url = data.get("url")
                company = data.get("company")
                title = data.get("title")
                description = data.get("description", "")

                if url and company and title:
                    jobs.append(
                        {
                            "company_name": company,
                            "job_title": title,
                            "job_url": url,
                            "description": description,
                            "expected_behavior": "should_reprocess",
                        }
                    )
                    logger.info(f"  Found: {title} at {company}")

        except Exception as e:
            logger.error(f"Error fetching test jobs from production: {e}")

        logger.info(f"Found {len(jobs)} real job URLs for testing")

        if len(jobs) == 0:
            logger.warning("No jobs found in production database!")
            logger.warning("Check that job-matches collection has documents")

        return jobs

    def submit_test_job(self, test_job: Dict[str, Any], test_run_id: str) -> TestJobSubmission:
        """
        Submit a test job to the queue and record the result.

        Args:
            test_job: Test job data
            test_run_id: Test run identifier

        Returns:
            TestJobSubmission record
        """
        import time
        from uuid import uuid4

        submission_id = str(uuid4())[:8]
        start_time = time.time()

        logger.info(f"Submitting test job: {test_job['job_title']} at {test_job['company_name']}")

        record = TestJobSubmission(
            submission_id=submission_id,
            timestamp=datetime.utcnow().isoformat(),
            company_name=test_job["company_name"],
            job_title=test_job["job_title"],
            job_url=test_job["job_url"],
            source_type="e2e_test",
            expected_status=test_job["expected_behavior"],
        )

        try:
            # Check if URL already in queue or processed
            if self.queue_manager.url_exists_in_queue(test_job["job_url"]):
                record.actual_result = "already_in_queue"
                logger.info(f"  → Job already in queue")
            else:
                # Submit job through proper queue intake
                job_data = {
                    "url": test_job["job_url"],
                    "company": test_job["company_name"],
                    "title": test_job["job_title"],
                    "description": test_job.get("description", ""),
                }

                # Submit to queue (creates JOB_SCRAPE task for worker to process)
                submitted_count = self.intake.submit_jobs([job_data], source="automated_scan")

                if submitted_count > 0:
                    record.actual_result = "queued"
                    logger.info(f"  → Job submitted to queue successfully")
                else:
                    record.actual_result = "skipped_duplicate"
                    logger.info(f"  → Job skipped (duplicate)")

        except Exception as e:
            record.actual_result = "failed"
            record.errors.append(str(e))
            logger.error(f"  ✗ Error: {e}")

        record.duration_seconds = time.time() - start_time
        return record

    def wait_for_queue_completion(self, timeout: int = 180, poll_interval: int = 5) -> bool:
        """
        Wait for queue to complete (no pending/processing items).

        Args:
            timeout: Maximum seconds to wait
            poll_interval: Seconds between checks

        Returns:
            True if queue completed, False if timeout
        """
        import time

        start_time = time.time()
        logger.info("Waiting for queue to complete...")

        while True:
            elapsed = time.time() - start_time

            if elapsed > timeout:
                logger.error(f"Timeout waiting for queue completion ({timeout}s)")
                return False

            # Count active items
            pending_count = len(
                list(self.db.collection("job-queue").where("status", "==", "pending").stream())
            )
            processing_count = len(
                list(self.db.collection("job-queue").where("status", "==", "processing").stream())
            )

            active_count = pending_count + processing_count

            if active_count == 0:
                logger.info(f"✓ Queue complete in {elapsed:.1f}s")
                return True

            logger.info(
                f"  [{elapsed:.0f}s] Active: {active_count} (pending: {pending_count}, processing: {processing_count})"
            )
            time.sleep(poll_interval)

    def submit_all_test_jobs(self, test_run_id: str) -> List[TestJobSubmission]:
        """
        Submit test jobs one at a time, waiting for each to complete before submitting next.

        This sequential approach ensures:
        - Clear cause-and-effect for debugging
        - Each job's spawned items are processed before next job
        - Easy to identify which job caused issues
        - Better resource usage (no queue flooding)

        Args:
            test_run_id: Test run identifier

        Returns:
            List of submission records
        """
        records = []

        for i, test_job in enumerate(self.TEST_JOBS, 1):
            logger.info("=" * 80)
            logger.info(f"SUBMITTING JOB {i}/{len(self.TEST_JOBS)}")
            logger.info("=" * 80)

            # Submit job
            record = self.submit_test_job(test_job, test_run_id)
            records.append(record)

            if record.actual_result == "queued":
                # Wait for this job to complete before submitting next
                logger.info(f"Monitoring queue until job {i} completes...")
                completed = self.wait_for_queue_completion(timeout=180, poll_interval=5)

                if not completed:
                    logger.warning(f"Job {i} did not complete in time. Stopping test.")
                    break

                logger.info(f"✓ Job {i} complete. Ready for next job.\n")
            else:
                logger.info(f"Job {i} was not queued ({record.actual_result}). Moving to next.\n")

        logger.info("=" * 80)
        logger.info(f"ALL JOBS SUBMITTED: {len(records)}/{len(self.TEST_JOBS)}")
        logger.info("=" * 80)

        return records

    def _count_existing_jobs(self, test_job: Dict[str, Any]) -> int:
        """Count how many jobs already exist with this title and company."""
        try:
            query = (
                self.db.collection("job-matches")
                .where("title", "==", test_job["job_title"])
                .where("company", "==", test_job["company_name"])
            )
            docs = list(query.stream())
            return len(docs)
        except Exception as e:
            logger.warning(f"Error checking existing jobs: {e}")
            return 0


class TestResultsCollector:
    """Collects and records test results."""

    def __init__(self, database_name: str, output_dir: Path):
        """Initialize results collector."""
        self.db = FirestoreClient.get_client(database_name)
        self.database_name = database_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_collection_counts(self, collections: List[str]) -> Dict[str, int]:
        """Get document counts for collections."""
        counts = {}
        for collection_name in collections:
            count = len(list(self.db.collection(collection_name).stream()))
            counts[collection_name] = count
        return counts

    def save_collection_snapshot(self, collection_name: str, snapshot_name: str) -> int:
        """
        Save a snapshot of a collection.

        Args:
            collection_name: Collection to snapshot
            snapshot_name: Name for the snapshot file

        Returns:
            Number of documents saved
        """
        logger.info(f"Saving snapshot: {snapshot_name}")

        docs = []
        for doc in self.db.collection(collection_name).stream():
            docs.append(
                {
                    "id": doc.id,
                    **doc.to_dict(),
                }
            )

        snapshot_file = self.output_dir / f"{snapshot_name}.json"
        with open(snapshot_file, "w") as f:
            json.dump(docs, f, indent=2, default=str)

        logger.info(f"  Saved {len(docs)} documents to {snapshot_file.name}")
        return len(docs)

    def save_results(
        self,
        test_result: TestRunResult,
        collections_to_snapshot: List[str],
    ) -> None:
        """
        Save complete test results.

        Args:
            test_result: Test run results
            collections_to_snapshot: Collections to save snapshots of
        """
        # Save main results
        results_file = self.output_dir / "test_results.json"
        with open(results_file, "w") as f:
            json.dump(asdict(test_result), f, indent=2, default=str)
        logger.info(f"Saved results to {results_file.name}")

        # Save collection snapshots
        for collection_name in collections_to_snapshot:
            self.save_collection_snapshot(
                collection_name,
                f"final_{collection_name}",
            )

        # Save summary
        summary_file = self.output_dir / "summary.txt"
        self._write_summary(test_result, summary_file)

    def _write_summary(self, test_result: TestRunResult, summary_file: Path) -> None:
        """Write human-readable summary."""
        with open(summary_file, "w") as f:
            f.write("E2E TEST RUN SUMMARY\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Test Run ID:     {test_result.test_run_id}\n")
            f.write(f"Start Time:      {test_result.start_time}\n")
            f.write(f"End Time:        {test_result.end_time}\n")
            f.write(f"Duration:        {test_result.duration_seconds:.1f}s\n\n")

            f.write("JOB SUBMISSIONS\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Submitted: {test_result.jobs_submitted}\n")
            f.write(f"Succeeded:       {test_result.jobs_succeeded}\n")
            f.write(f"Failed:          {test_result.jobs_failed}\n")
            f.write(f"Success Rate:    {test_result.success_rate:.1f}%\n\n")

            f.write("FINAL COLLECTION COUNTS\n")
            f.write("-" * 80 + "\n")
            for collection, count in test_result.final_collection_counts.items():
                f.write(f"{collection:20} {count:6} documents\n")
            f.write("\n")

            if test_result.issues_found:
                f.write("ISSUES FOUND\n")
                f.write("-" * 80 + "\n")
                for issue in test_result.issues_found:
                    f.write(f"  - {issue}\n")
                f.write("\n")

            f.write(f"Data Quality Score: {test_result.data_quality_score:.1f}/100\n")

        logger.info(f"Saved summary to {summary_file.name}")


class E2ETestDataCollector:
    """Main coordinator for E2E test data collection."""

    def __init__(
        self,
        database_name: str,
        output_dir: str,
        verbose: bool = False,
        backup_dir: Optional[Path] = None,
        clean_before: bool = False,
        source_database: str = "portfolio",
        test_count: int = 2,
    ):
        """
        Initialize test data collector.

        Args:
            database_name: Firestore database name (staging - where tests run)
            output_dir: Output directory for results
            verbose: Enable verbose logging
            backup_dir: Directory to save backups (defaults to output_dir/backup)
            clean_before: Whether to clean collections before testing
            source_database: Database to copy initial data from (default: portfolio/production)
            test_count: Number of test jobs to submit (1-4, default: 2 for quick tests)
        """
        self.database_name = database_name  # Where tests run (staging)
        self.source_database = source_database  # Where to get initial data (production)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set backup directory
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = self.output_dir / "backup"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.clean_before = clean_before

        # Setup logging
        self._setup_logging(verbose)

        # Initialize components for TEST database (staging)
        self.backup_restore = FirestoreBackupRestore(database_name)
        self.job_submitter = TestJobSubmitter(
            database_name, test_count=test_count, source_database=source_database
        )
        self.results_collector = TestResultsCollector(database_name, self.output_dir)

        # Initialize separate client for SOURCE database (production) - READ ONLY
        self.source_backup = FirestoreBackupRestore(source_database)
        """
        Initialize test data collector.

        Args:
            database_name: Firestore database name
            output_dir: Output directory for results
            verbose: Enable verbose logging
            backup_dir: Directory to save backups (defaults to output_dir/backup)
            clean_before: Whether to clean collections before testing
        """
        self.database_name = database_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set backup directory
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = self.output_dir / "backup"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.clean_before = clean_before

        # Setup logging
        self._setup_logging(verbose)

        # Collections to manage
        self.TEST_COLLECTIONS = [
            "job-listings",
            "companies",
            "job-sources",
        ]
        self.OPERATIONAL_COLLECTIONS = [
            "job-queue",
            "job-matches",
        ]

    def _setup_logging(self, verbose: bool) -> None:
        """Setup logging to file and console."""
        log_file = self.output_dir / "test_run.log"

        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        level = logging.DEBUG if verbose else logging.INFO

        # Get root logger
        root_logger = logging.getLogger()

        # Clear any existing handlers to prevent duplicate logging
        # (handlers may exist from previous runs or imported modules)
        root_logger.handlers.clear()

        root_logger.setLevel(level)

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(console_handler)

        logger.info(f"Logging initialized: {log_file}")

    def run_collection(self) -> TestRunResult:
        """
        Run complete test data collection.

        Returns:
            TestRunResult with all collected data
        """
        import time

        test_run_id = f"e2e_collect_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = time.time()

        logger.info("=" * 80)
        logger.info("E2E TEST DATA COLLECTION STARTED")
        logger.info("=" * 80)
        logger.info(f"Test Run ID:     {test_run_id}")
        logger.info(f"Test Database:   {self.database_name} (where tests run)")
        logger.info(f"Source Database: {self.source_database} (where seed data comes from)")
        logger.info(f"Output:          {self.output_dir}")
        logger.info("")

        result = TestRunResult(
            test_run_id=test_run_id,
            start_time=datetime.utcnow().isoformat(),
        )

        try:
            # Step 1: Copy production data to staging (seed the test)
            logger.info("STEP 1: COPYING PRODUCTION DATA TO STAGING")
            logger.info("-" * 80)
            logger.info(f"Reading from: {self.source_database} (production - READ ONLY)")
            logger.info(f"Writing to:   {self.database_name} (staging - test environment)")
            logger.info("")

            # Backup production data (for records)
            prod_backup_dir = self.output_dir / "production_snapshot"
            logger.info(f"Saving production snapshot to: {prod_backup_dir}")
            prod_metadata = self.source_backup.backup_all(
                self.TEST_COLLECTIONS,
                prod_backup_dir,
            )
            logger.info(f"Production snapshot: {prod_metadata.total_documents} documents")
            logger.info("")

            # Backup current staging data (in case we need to rollback)
            logger.info(f"Backing up current staging data...")
            staging_backup_dir = self.output_dir / "staging_backup_before"
            result.backup_metadata = self.backup_restore.backup_all(
                self.TEST_COLLECTIONS,
                staging_backup_dir,
            )
            logger.info("")

            # Step 2: Clear staging collections
            logger.info("STEP 2: CLEARING STAGING COLLECTIONS")
            logger.info("-" * 80)
            logger.info(f"Clearing in {self.database_name} only (production untouched)")
            self.backup_restore.clear_collections(self.TEST_COLLECTIONS)
            self.backup_restore.clear_collection("job-queue")
            logger.info("")

            # Step 3: Restore production data to staging
            logger.info("STEP 3: RESTORING PRODUCTION DATA TO STAGING")
            logger.info("-" * 80)
            logger.info("This seeds the test with real production data")
            restored_count = 0
            for collection in self.TEST_COLLECTIONS:
                backup_file = prod_backup_dir / f"{collection}.json"
                if backup_file.exists():
                    count = self.backup_restore.restore_collection(collection, backup_file)
                    restored_count += count
            logger.info(f"Restored {restored_count} total documents to staging")
            logger.info("")

            # Step 4: Submit test jobs
            logger.info("STEP 4: SUBMITTING TEST JOBS")
            logger.info("-" * 80)
            submission_records = self.job_submitter.submit_all_test_jobs(test_run_id)
            result.jobs_submitted = len(submission_records)
            result.submission_records = submission_records

            succeeded = sum(
                1 for r in submission_records if r.actual_result and "failed" not in r.actual_result
            )
            failed = sum(1 for r in submission_records if r.actual_result == "failed")
            result.jobs_succeeded = succeeded
            result.jobs_failed = failed
            logger.info("")

            # Step 5: Collect final results
            logger.info("STEP 5: COLLECTING FINAL RESULTS")
            logger.info("-" * 80)
            logger.info("All jobs have been submitted and monitored to completion.")
            logger.info("Collecting final state from Firestore...")
            logger.info("")

            # Get final collection counts
            all_collections = self.TEST_COLLECTIONS + self.OPERATIONAL_COLLECTIONS
            result.final_collection_counts = self.results_collector.get_collection_counts(
                all_collections
            )

            logger.info("Final collection counts:")
            for collection, count in result.final_collection_counts.items():
                logger.info(f"  {collection}: {count} documents")
            logger.info("")

            # Step 6: Validate results
            logger.info("STEP 6: VALIDATING RESULTS")
            logger.info("-" * 80)
            result.issues_found = self._validate_results(result)

            if result.issues_found:
                logger.warning(f"Found {len(result.issues_found)} issues:")
                for issue in result.issues_found:
                    logger.warning(f"  - {issue}")
            else:
                logger.info("✓ No issues found!")
            logger.info("")

            # Step 7: Save all results
            logger.info("STEP 7: SAVING RESULTS")
            logger.info("-" * 80)
            result.end_time = datetime.utcnow().isoformat()
            result.duration_seconds = time.time() - start_time

            self.results_collector.save_results(
                result,
                all_collections,
            )
            logger.info("")

        except Exception as e:
            logger.error(f"Error during collection: {e}", exc_info=True)
            result.issues_found.append(f"Collection failed: {e}")

        # Final summary
        logger.info("=" * 80)
        logger.info("E2E TEST DATA COLLECTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Duration:       {result.duration_seconds:.1f} seconds")
        logger.info(f"Success Rate:   {result.success_rate:.1f}%")
        logger.info(f"Issues Found:   {len(result.issues_found)}")
        logger.info(f"Output Dir:     {self.output_dir}")
        logger.info("")

        return result

    def _validate_results(self, result: TestRunResult) -> List[str]:
        """
        Validate test results.

        Args:
            result: Test run result

        Returns:
            List of issues found
        """
        issues = []

        # Check queue status - jobs should be processed or in progress
        queue_count = result.final_collection_counts.get("job-queue", 0)
        logger.info(f"Queue items remaining: {queue_count}")

        # If queue still has items, worker may still be processing
        if queue_count > 0:
            issues.append(
                f"Queue still has {queue_count} items - worker may still be processing. "
                "Consider increasing wait time."
            )

        # Check job-matches were created
        # Note: Some jobs might already exist from previous runs
        matches_count = result.final_collection_counts.get("job-matches", 0)
        if matches_count < 4:  # At least 4 unique jobs
            issues.append(f"Too few job matches: {matches_count} (expected at least 4)")

        # Check companies were created (may take longer as worker processes ANALYZE phase)
        companies_count = result.final_collection_counts.get("companies", 0)
        if companies_count < 1:  # At least 1 company should be created
            issues.append(
                f"No companies created: {companies_count} "
                "(expected at least 1 after worker processes jobs)"
            )

        # Check success rate
        if result.success_rate < 80:
            issues.append(f"Low success rate: {result.success_rate:.1f}%")

        # Check for failed submissions
        if result.jobs_failed > 0:
            failed_jobs = [r for r in result.submission_records if r.actual_result == "failed"]
            for job in failed_jobs:
                issues.append(f"Job submission failed: {job.job_title} at {job.company_name}")

        return issues


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="E2E Test Data Collection Tool")
    parser.add_argument(
        "--database",
        default="portfolio-staging",
        help="Test database name - where tests run (default: portfolio-staging)",
    )
    parser.add_argument(
        "--source-database",
        default="portfolio",
        help="Source database - where to copy seed data from (default: portfolio)",
    )
    parser.add_argument(
        "--output-dir",
        default="./test_results",
        help="Output directory for results (default: ./test_results)",
    )
    parser.add_argument(
        "--backup-dir",
        default=None,
        help="Directory to save backups (default: {output-dir}/backup)",
    )
    parser.add_argument(
        "--clean-before",
        action="store_true",
        help="Clean collections before testing (default: False)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (default: False)",
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Allow running on production database (USE WITH EXTREME CAUTION)",
    )
    parser.add_argument(
        "--test-count",
        type=int,
        default=2,
        choices=[1, 2, 3, 4],
        help="Number of test jobs to submit (1-4, default: 2 for quick tests)",
    )
    parser.add_argument(
        "--test-mode",
        choices=["decision-tree", "full"],
        default="decision-tree",
        help="Test mode: decision-tree (1 job each type, fast) or full (all production data)",
    )

    args = parser.parse_args()

    # SAFETY CHECK: Prevent accidental production usage
    if args.database == "portfolio" and not args.allow_production:
        logger.error("=" * 80)
        logger.error("🚨 PRODUCTION DATABASE BLOCKED 🚨")
        logger.error("=" * 80)
        logger.error("")
        logger.error("This test would CLEAR and MODIFY the production database!")
        logger.error("Database specified: portfolio (PRODUCTION)")
        logger.error("")
        logger.error("This test is designed for staging only.")
        logger.error("Use --database portfolio-staging instead.")
        logger.error("")
        logger.error("If you REALLY need to run on production (not recommended):")
        logger.error("  python tests/e2e/data_collector.py --database portfolio --allow-production")
        logger.error("")
        logger.error("=" * 80)
        sys.exit(1)

    # Warning for production usage
    if args.database == "portfolio":
        logger.warning("=" * 80)
        logger.warning("⚠️  RUNNING ON PRODUCTION DATABASE ⚠️")
        logger.warning("=" * 80)
        logger.warning("This will CLEAR and MODIFY production data!")
        logger.warning("Press Ctrl+C within 10 seconds to abort...")
        logger.warning("=" * 80)
        import time

        time.sleep(10)

    # Safety check: warn if source database is not production
    if args.source_database != "portfolio":
        logger.warning("=" * 80)
        logger.warning(f"⚠️  Using non-production source database: {args.source_database}")
        logger.warning("=" * 80)
        logger.warning("Tests will not start with production data!")
        logger.warning("For best results, use --source-database portfolio")
        logger.warning("=" * 80)
        logger.warning("")

    collector = E2ETestDataCollector(
        database_name=args.database,
        output_dir=args.output_dir,
        verbose=args.verbose,
        backup_dir=args.backup_dir,
        clean_before=args.clean_before,
        source_database=args.source_database,
        test_count=args.test_count,
    )

    result = collector.run_collection()
    sys.exit(0 if result.issues_found == [] else 1)


if __name__ == "__main__":
    main()
