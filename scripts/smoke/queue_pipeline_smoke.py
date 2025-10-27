#!/usr/bin/env python3
"""
Queue Pipeline Smoke Test

End-to-end smoke test that validates the queue pipeline by:
1. Loading representative job fixtures
2. Submitting them to the queue via ScraperIntake
3. Polling Firestore until all jobs reach terminal state
4. Validating data quality (duplicates, scoring fields, references)
5. Generating structured reports (markdown + JSON)

Usage:
    python scripts/smoke/queue_pipeline_smoke.py --env staging
    python scripts/smoke/queue_pipeline_smoke.py --env local --dry-run
    python scripts/smoke/queue_pipeline_smoke.py --fixtures tests/fixtures/smoke_jobs
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add src to path - noqa: E402
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from job_finder.job_queue.manager import QueueManager  # noqa: E402
from job_finder.job_queue.models import QueueStatus  # noqa: E402
from job_finder.job_queue.scraper_intake import ScraperIntake  # noqa: E402
from job_finder.storage.firestore_storage import FirestoreJobStorage  # noqa: E402
from job_finder.utils.url_utils import normalize_url  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SmokeTestRunner:
    """Runs smoke tests for the queue pipeline."""

    def __init__(
        self,
        env: str = "staging",
        fixtures_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        dry_run: bool = False,
    ):
        """
        Initialize smoke test runner.

        Args:
            env: Environment to test (staging, local, production)
            fixtures_dir: Directory containing job fixture JSON files
            output_dir: Directory to write test results
            dry_run: If True, don't actually submit jobs
        """
        self.env = env
        self.dry_run = dry_run

        # Set default fixtures directory
        if fixtures_dir is None:
            repo_root = Path(__file__).parent.parent.parent
            fixtures_dir = repo_root / "tests" / "fixtures" / "smoke_jobs"
        self.fixtures_dir = Path(fixtures_dir)

        # Set output directory with timestamp
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path("test_results") / "queue_smoke" / timestamp
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Determine database name based on environment
        database_map = {
            "staging": "portfolio-staging",
            "local": "portfolio-staging",  # Local uses staging DB
            "production": "portfolio",
        }
        self.database_name = database_map.get(env, "portfolio-staging")

        # Initialize clients (will be None in dry-run mode)
        self.queue_manager: Optional[QueueManager] = None
        self.job_storage: Optional[FirestoreJobStorage] = None
        self.scraper_intake: Optional[ScraperIntake] = None

        if not dry_run:
            self._initialize_clients()

        # Track submitted jobs
        self.submitted_jobs: List[Dict[str, Any]] = []
        self.job_doc_ids: Dict[str, str] = {}  # url -> doc_id mapping

    def _initialize_clients(self):
        """Initialize Firestore clients."""
        try:
            # Check for credentials
            creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if not creds_path:
                logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set")

            self.queue_manager = QueueManager(database_name=self.database_name)
            self.job_storage = FirestoreJobStorage(database_name=self.database_name)
            self.scraper_intake = ScraperIntake(
                queue_manager=self.queue_manager,
                job_storage=self.job_storage,
            )
            logger.info(f"Initialized clients for database: {self.database_name}")
        except Exception as e:
            logger.error(f"Failed to initialize clients: {e}")
            raise

    def load_fixtures(self) -> List[Dict[str, Any]]:
        """
        Load job fixtures from JSON files.

        Returns:
            List of job dictionaries
        """
        fixtures = []

        if not self.fixtures_dir.exists():
            raise FileNotFoundError(f"Fixtures directory not found: {self.fixtures_dir}")

        json_files = sorted(self.fixtures_dir.glob("*.json"))

        for json_file in json_files:
            try:
                with open(json_file, "r") as f:
                    fixture = json.load(f)
                    # Validate required fields
                    required_fields = [
                        "title",
                        "company",
                        "company_website",
                        "location",
                        "description",
                        "url",
                    ]
                    missing_fields = [f for f in required_fields if f not in fixture]
                    if missing_fields:
                        logger.warning(f"Fixture {json_file.name} missing fields: {missing_fields}")
                        continue

                    fixture["_fixture_file"] = json_file.name
                    fixtures.append(fixture)
                    logger.info(f"Loaded fixture: {json_file.name}")
            except Exception as e:
                logger.error(f"Error loading fixture {json_file}: {e}")
                continue

        logger.info(f"Loaded {len(fixtures)} fixtures from {self.fixtures_dir}")
        return fixtures

    def submit_jobs(self, jobs: List[Dict[str, Any]]) -> int:
        """
        Submit jobs to the queue via ScraperIntake.

        Args:
            jobs: List of job dictionaries to submit

        Returns:
            Number of jobs successfully submitted
        """
        if self.dry_run:
            logger.info(f"DRY RUN: Would submit {len(jobs)} jobs")
            for job in jobs:
                logger.info(f"  - {job.get('title')} at {job.get('company')}")
            return len(jobs)

        if not self.scraper_intake:
            raise RuntimeError("ScraperIntake not initialized")

        # Submit jobs one at a time to track doc IDs
        submitted_count = 0
        for job in jobs:
            try:
                # Remove test metadata before submission
                job_data = {k: v for k, v in job.items() if not k.startswith("_")}

                # Check if already in queue
                normalized_url = normalize_url(job_data["url"])
                if self.queue_manager.url_exists_in_queue(normalized_url):
                    logger.warning(f"Job already in queue: {job_data.get('title')}")
                    continue

                # Submit via scraper intake
                count = self.scraper_intake.submit_jobs([job_data], source="smoke_test")

                if count > 0:
                    # Find the doc ID for this job
                    # Query queue for this URL to get doc ID
                    query = (
                        self.queue_manager.db.collection("job-queue")
                        .where("url", "==", normalized_url)
                        .where("source", "==", "smoke_test")
                        .limit(1)
                    )

                    docs = list(query.stream())
                    if docs:
                        doc_id = docs[0].id
                        self.job_doc_ids[normalized_url] = doc_id
                        logger.info(f"Submitted: {job_data.get('title')} (doc_id: {doc_id})")

                    self.submitted_jobs.append(job)
                    submitted_count += 1

            except Exception as e:
                logger.error(f"Error submitting job {job.get('title')}: {e}")
                continue

        logger.info(f"Successfully submitted {submitted_count}/{len(jobs)} jobs")
        return submitted_count

    def poll_until_complete(
        self, timeout_seconds: int = 600, poll_interval: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Poll Firestore until all submitted jobs reach terminal state.

        Args:
            timeout_seconds: Maximum time to wait
            poll_interval: Seconds between polls

        Returns:
            List of final job states with metadata
        """
        if self.dry_run:
            logger.info("DRY RUN: Would poll for job completion")
            return []

        start_time = time.time()
        terminal_states = {
            QueueStatus.SUCCESS,
            QueueStatus.FAILED,
            QueueStatus.FILTERED,
            QueueStatus.SKIPPED,
        }

        results = []
        pending_urls = set(self.job_doc_ids.keys())

        logger.info(f"Polling for completion of {len(pending_urls)} jobs...")
        logger.info(f"Timeout: {timeout_seconds}s, Poll interval: {poll_interval}s")

        while pending_urls and (time.time() - start_time) < timeout_seconds:
            for url in list(pending_urls):
                doc_id = self.job_doc_ids.get(url)
                if not doc_id:
                    continue

                try:
                    doc = self.queue_manager.db.collection("job-queue").document(doc_id).get()

                    if not doc.exists:
                        logger.warning(f"Queue item disappeared: {doc_id}")
                        pending_urls.remove(url)
                        continue

                    data = doc.to_dict()
                    status = data.get("status")

                    if status in terminal_states:
                        elapsed = time.time() - start_time
                        logger.info(
                            f"Job complete: {data.get('company_name')} - "
                            f"Status: {status} (elapsed: {elapsed:.1f}s)"
                        )

                        result = {
                            "url": url,
                            "doc_id": doc_id,
                            "status": status,
                            "company_name": data.get("company_name"),
                            "elapsed_seconds": elapsed,
                            "queue_data": data,
                        }
                        results.append(result)
                        pending_urls.remove(url)

                except Exception as e:
                    logger.error(f"Error checking job {doc_id}: {e}")

            if pending_urls:
                time.sleep(poll_interval)

        # Report timeout if any jobs still pending
        if pending_urls:
            logger.warning(f"Timeout reached with {len(pending_urls)} jobs still pending")
            for url in pending_urls:
                doc_id = self.job_doc_ids.get(url)
                results.append(
                    {
                        "url": url,
                        "doc_id": doc_id,
                        "status": "TIMEOUT",
                        "elapsed_seconds": timeout_seconds,
                    }
                )

        return results

    def validate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate results for data quality issues.

        Checks:
        - No duplicate normalized URLs
        - Required scoring fields present
        - Document references exist (if applicable)

        Args:
            results: List of job results

        Returns:
            Validation report with issues and summary
        """
        validation_report = {
            "passed": True,
            "issues": [],
            "checks": {
                "duplicate_urls": {"passed": True, "details": []},
                "scoring_fields": {"passed": True, "details": []},
                "document_references": {"passed": True, "details": []},
            },
        }

        # Check for duplicate URLs (works in dry-run mode too)
        seen_urls = set()
        for result in results:
            url = result.get("url")
            if url:
                normalized = normalize_url(url)
                if normalized in seen_urls:
                    validation_report["checks"]["duplicate_urls"]["passed"] = False
                    validation_report["checks"]["duplicate_urls"]["details"].append(
                        f"Duplicate URL: {url}"
                    )
                    validation_report["passed"] = False
                seen_urls.add(normalized)

        # Skip Firestore-dependent checks in dry-run mode
        if self.dry_run:
            return validation_report

        # Check scoring fields for successful jobs
        required_fields = [
            "matchScore",
            "matchedSkills",
            "applicationPriority",
            "resumeIntakeData",
        ]

        for result in results:
            if result.get("status") == QueueStatus.SUCCESS:
                try:
                    # Check job-matches collection
                    matches = (
                        self.job_storage.db.collection("job-matches")
                        .where("url", "==", result["url"])
                        .limit(1)
                        .stream()
                    )

                    match_docs = list(matches)
                    if not match_docs:
                        validation_report["checks"]["scoring_fields"]["passed"] = False
                        validation_report["checks"]["scoring_fields"]["details"].append(
                            f"No job-matches document for: {result.get('company_name')}"
                        )
                        validation_report["passed"] = False
                        continue

                    match_data = match_docs[0].to_dict()
                    missing_fields = [f for f in required_fields if f not in match_data]

                    if missing_fields:
                        validation_report["checks"]["scoring_fields"]["passed"] = False
                        validation_report["checks"]["scoring_fields"]["details"].append(
                            f"Missing fields in {result.get('company_name')}: "
                            f"{', '.join(missing_fields)}"
                        )
                        validation_report["passed"] = False

                except Exception as e:
                    logger.error(f"Error validating {result.get('doc_id')}: {e}")
                    validation_report["checks"]["scoring_fields"]["passed"] = False
                    validation_report["checks"]["scoring_fields"]["details"].append(
                        f"Validation error for {result.get('company_name')}: {str(e)}"
                    )
                    validation_report["passed"] = False

        # Document references check (if document generation is enabled)
        # For now, just note if documents should be checked
        validation_report["checks"]["document_references"]["details"].append(
            "Document generation validation not yet implemented"
        )

        return validation_report

    def generate_report(
        self, results: List[Dict[str, Any]], validation_report: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Generate markdown and JSON reports.

        Args:
            results: List of job results
            validation_report: Validation results

        Returns:
            Tuple of (markdown_path, json_path)
        """
        timestamp = datetime.now().isoformat()

        # Generate summary statistics
        status_counts = {}
        for result in results:
            status = result.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1

        total_jobs = len(results)
        avg_time = (
            sum(r.get("elapsed_seconds", 0) for r in results) / total_jobs if total_jobs > 0 else 0
        )

        # Create markdown report
        markdown_lines = [
            "# Queue Pipeline Smoke Test Report",
            "",
            f"**Generated:** {timestamp}",
            f"**Environment:** {self.env}",
            f"**Database:** {self.database_name}",
            f"**Dry Run:** {self.dry_run}",
            "",
            "## Summary",
            "",
            f"- **Total Jobs:** {total_jobs}",
            f"- **Average Processing Time:** {avg_time:.1f}s",
            "",
            "### Status Breakdown",
            "",
        ]

        for status, count in sorted(status_counts.items()):
            markdown_lines.append(f"- **{status}:** {count}")

        markdown_lines.extend(
            [
                "",
                "## Validation Results",
                "",
                f"**Overall:** {'✅ PASSED' if validation_report['passed'] else '❌ FAILED'}",
                "",
            ]
        )

        for check_name, check_data in validation_report["checks"].items():
            passed = check_data.get("passed", True)
            details = check_data.get("details", [])

            markdown_lines.append(
                f"### {check_name.replace('_', ' ').title()}: "
                f"{'✅ PASSED' if passed else '❌ FAILED'}"
            )

            if details:
                markdown_lines.append("")
                for detail in details:
                    markdown_lines.append(f"- {detail}")

            markdown_lines.append("")

        # Add individual job results
        markdown_lines.extend(["## Job Results", ""])

        for i, result in enumerate(results, 1):
            job_data = next(
                (
                    j
                    for j in self.submitted_jobs
                    if normalize_url(j["url"]) == normalize_url(result["url"])
                ),
                {},
            )

            markdown_lines.extend(
                [
                    f"### {i}. {job_data.get('title', 'Unknown')} at "
                    f"{result.get('company_name', 'Unknown')}",
                    "",
                    f"- **Status:** {result.get('status')}",
                    f"- **Processing Time:** {result.get('elapsed_seconds', 0):.1f}s",
                    f"- **URL:** {result.get('url')}",
                    f"- **Doc ID:** {result.get('doc_id')}",
                    f"- **Fixture:** {job_data.get('_fixture_file', 'Unknown')}",
                    "",
                ]
            )

        markdown_content = "\n".join(markdown_lines)

        # Create JSON report
        json_report = {
            "metadata": {
                "timestamp": timestamp,
                "environment": self.env,
                "database": self.database_name,
                "dry_run": self.dry_run,
                "fixtures_dir": str(self.fixtures_dir),
            },
            "summary": {
                "total_jobs": total_jobs,
                "status_counts": status_counts,
                "average_processing_time": avg_time,
            },
            "validation": validation_report,
            "results": results,
            "submitted_jobs": [
                {k: v for k, v in j.items() if not k.startswith("_")} for j in self.submitted_jobs
            ],
        }

        # Write reports
        markdown_path = self.output_dir / "report.md"
        json_path = self.output_dir / "report.json"

        with open(markdown_path, "w") as f:
            f.write(markdown_content)

        with open(json_path, "w") as f:
            json.dump(json_report, f, indent=2, default=str)

        logger.info("Reports generated:")
        logger.info("  Markdown: %s", markdown_path)
        logger.info("  JSON: %s", json_path)

        return str(markdown_path), str(json_path)

    def run(self) -> int:
        """
        Run the complete smoke test.

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            logger.info("=== Starting Queue Pipeline Smoke Test ===")
            logger.info(f"Environment: {self.env}")
            logger.info(f"Database: {self.database_name}")
            logger.info(f"Dry run: {self.dry_run}")
            logger.info(f"Output dir: {self.output_dir}")

            # Load fixtures
            jobs = self.load_fixtures()
            if not jobs:
                logger.error("No fixtures loaded")
                return 1

            # Submit jobs
            submitted_count = self.submit_jobs(jobs)
            if submitted_count == 0 and not self.dry_run:
                logger.error("No jobs submitted")
                return 1

            # Poll for completion
            results = self.poll_until_complete()

            # Validate results
            validation_report = self.validate_results(results)

            # Generate reports
            markdown_path, json_path = self.generate_report(results, validation_report)

            # Print summary
            logger.info("=== Smoke Test Complete ===")
            logger.info(f"Total jobs: {len(results)}")
            logger.info(f"Validation: {'PASSED' if validation_report['passed'] else 'FAILED'}")
            logger.info(f"Reports: {self.output_dir}")

            return 0 if validation_report["passed"] else 1

        except Exception as e:
            logger.error(f"Smoke test failed with error: {e}", exc_info=True)
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Queue pipeline smoke test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--env",
        choices=["staging", "local", "production"],
        default="staging",
        help="Environment to test (default: staging)",
    )

    parser.add_argument(
        "--fixtures",
        help="Directory containing fixture JSON files " "(default: tests/fixtures/smoke_jobs)",
    )

    parser.add_argument(
        "--output",
        help="Output directory for results (default: test_results/queue_smoke/<timestamp>)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually submit jobs, just validate fixtures",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in seconds for job completion (default: 600)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create runner
    runner = SmokeTestRunner(
        env=args.env,
        fixtures_dir=args.fixtures,
        output_dir=args.output,
        dry_run=args.dry_run,
    )

    # Run test
    exit_code = runner.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
