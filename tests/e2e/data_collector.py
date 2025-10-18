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
import os
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

    # Known test data - simple jobs for basic testing
    TEST_JOBS = [
        {
            "company_name": "MongoDB",
            "job_title": "Senior Backend Engineer",
            "job_url": "https://test.example.com/mongodb/12345",
            "description": "Build scalable backend systems",
            "expected_behavior": "should_create",
        },
        {
            "company_name": "Netflix",
            "job_title": "Machine Learning Engineer",
            "job_url": "https://test.example.com/netflix/12345",
            "description": "Work on recommendation systems",
            "expected_behavior": "should_create",
        },
        {
            "company_name": "Shopify",
            "job_title": "Full Stack Engineer",
            "job_url": "https://test.example.com/shopify/12345",
            "description": "Build customer-facing features",
            "expected_behavior": "should_create",
        },
        {
            "company_name": "Stripe",
            "job_title": "Platform Engineer",
            "job_url": "https://test.example.com/stripe/12345",
            "description": "Build platform infrastructure",
            "expected_behavior": "should_create",
        },
    ]

    def __init__(self, database_name: str):
        """Initialize job submitter."""
        self.db = FirestoreClient.get_client(database_name)

    def submit_test_job(self, test_job: Dict[str, Any], test_run_id: str) -> TestJobSubmission:
        """
        Submit a test job and record the result.

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
            source_type="test",
            expected_status=test_job["expected_behavior"],
        )

        try:
            # Check if job already exists
            existing_count = self._count_existing_jobs(test_job)

            if existing_count > 0:
                record.actual_result = "found_existing"
                logger.info(f"  → Job already exists in collection")
            else:
                # Create new job-matches document directly
                job_match = {
                    "title": test_job["job_title"],
                    "company": test_job["company_name"],
                    "link": test_job["job_url"],
                    "description": test_job["description"],
                    "sourceId": "test",
                    "scrapedAt": datetime.utcnow().isoformat(),
                    "test_run_id": test_run_id,
                    "created_at": datetime.utcnow().isoformat(),
                }

                # Save directly to Firestore
                doc_ref = self.db.collection("job-matches").document()
                doc_ref.set(job_match)

                record.actual_result = "created_new"
                logger.info(f"  → Job created successfully (ID: {doc_ref.id})")

        except Exception as e:
            record.actual_result = "failed"
            record.errors.append(str(e))
            logger.error(f"  ✗ Error: {e}")

        record.duration_seconds = time.time() - start_time
        return record

    def submit_all_test_jobs(self, test_run_id: str) -> List[TestJobSubmission]:
        """
        Submit all test jobs.

        Args:
            test_run_id: Test run identifier

        Returns:
            List of submission records
        """
        records = []
        for test_job in self.TEST_JOBS:
            record = self.submit_test_job(test_job, test_run_id)
            records.append(record)
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
        output_dir: Path,
        verbose: bool = False,
        backup_dir: Optional[Path] = None,
        clean_before: bool = False,
    ):
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

        # Initialize components
        self.backup_restore = FirestoreBackupRestore(database_name)
        self.job_submitter = TestJobSubmitter(database_name)
        self.results_collector = TestResultsCollector(database_name, output_dir)

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

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(log_format))

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(log_format))

        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.addHandler(file_handler)
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
        logger.info(f"Database:        {self.database_name}")
        logger.info(f"Output:          {self.output_dir}")
        logger.info("")

        result = TestRunResult(
            test_run_id=test_run_id,
            start_time=datetime.utcnow().isoformat(),
        )

        try:
            # Step 1: Backup existing data
            logger.info("STEP 1: BACKING UP EXISTING DATA")
            logger.info("-" * 80)
            backup_dir = self.output_dir / "backup_original"
            result.backup_metadata = self.backup_restore.backup_all(
                self.TEST_COLLECTIONS,
                backup_dir,
            )
            logger.info("")

            # Step 2: Clear collections
            logger.info("STEP 2: CLEARING TEST COLLECTIONS")
            logger.info("-" * 80)
            self.backup_restore.clear_collections(self.TEST_COLLECTIONS)
            self.backup_restore.clear_collection("job-queue")
            logger.info("")

            # Step 3: Submit test jobs
            logger.info("STEP 3: SUBMITTING TEST JOBS")
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

            # Step 4: Wait for processing and collect results
            logger.info("STEP 4: COLLECTING RESULTS")
            logger.info("-" * 80)
            import time

            logger.info("Waiting for job processing (10 seconds)...")
            time.sleep(10)

            # Get final collection counts
            all_collections = self.TEST_COLLECTIONS + self.OPERATIONAL_COLLECTIONS
            result.final_collection_counts = self.results_collector.get_collection_counts(
                all_collections
            )

            logger.info("Final collection counts:")
            for collection, count in result.final_collection_counts.items():
                logger.info(f"  {collection}: {count} documents")
            logger.info("")

            # Step 5: Validate results
            logger.info("STEP 5: VALIDATING RESULTS")
            logger.info("-" * 80)
            result.issues_found = self._validate_results(result)

            if result.issues_found:
                logger.warning(f"Found {len(result.issues_found)} issues:")
                for issue in result.issues_found:
                    logger.warning(f"  - {issue}")
            else:
                logger.info("✓ No issues found!")
            logger.info("")

            # Step 6: Save all results
            logger.info("STEP 6: SAVING RESULTS")
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

        # Check job-matches were created
        matches_count = result.final_collection_counts.get("job-matches", 0)
        if matches_count < 4:  # At least 4 unique jobs
            issues.append(f"Too few job matches: {matches_count} (expected at least 4)")

        # Check companies were created
        companies_count = result.final_collection_counts.get("companies", 0)
        if companies_count < 3:  # At least 3 unique companies
            issues.append(f"Too few companies: {companies_count} (expected at least 3)")

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
        help="Firestore database name (default: portfolio-staging)",
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

    args = parser.parse_args()

    collector = E2ETestDataCollector(
        database_name=args.database,
        output_dir=args.output_dir,
        verbose=args.verbose,
        backup_dir=args.backup_dir,
        clean_before=args.clean_before,
    )

    result = collector.run_collection()
    sys.exit(0 if result.issues_found == [] else 1)


if __name__ == "__main__":
    main()
