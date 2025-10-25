"""
Scenario 1: Complete Job Submission Flow

Tests the full pipeline from job submission through AI analysis to match creation.
This is the happy path where everything succeeds.
"""

import logging

from .base_scenario import BaseE2EScenario
from ..helpers import QueueMonitor, FirestoreHelper, CleanupHelper

logger = logging.getLogger(__name__)


class JobSubmissionScenario(BaseE2EScenario):
    """Test complete job submission and processing flow."""

    def __init__(self, **kwargs):
        """Initialize scenario."""
        super().__init__(**kwargs)

        # Test data - using a real Cloudflare job that should exist
        self.test_job_url = "https://boards.greenhouse.io/cloudflare/jobs/7270583"
        self.expected_company = "Cloudflare"
        self.expected_title_contains = "Engineer"  # Generic enough to match most jobs

        # Will be set during execution
        self.queue_item_id = None
        self.match_id = None

        # Helpers
        self.monitor = None
        self.firestore = None
        self.cleanup = None

    def setup(self):
        """Set up test dependencies."""
        super().setup()

        from job_finder.storage.firestore_client import FirestoreClient

        # Initialize Firestore client
        db = FirestoreClient.get_client(self.db_name)

        # Initialize helpers
        self.monitor = QueueMonitor(db, timeout=300.0)  # 5 min timeout
        self.firestore = FirestoreHelper(db, self.db_name)
        self.cleanup = CleanupHelper(db, self.db_name)

        self._log("Test dependencies initialized")

    def execute(self):
        """Execute the scenario."""
        self._print(f"Submitting job: {self.test_job_url}")

        # Step 1: Submit job to queue
        self.queue_item_id = self.firestore.create_queue_item(
            url=self.test_job_url,
            company_name=self.expected_company,
            source="automated_scan",
            test_run_id=self.test_run_id,
        )

        # Track for cleanup
        self.track_for_cleanup("job-queue", self.queue_item_id, "Test queue item")

        self._log(f"Created queue item: {self.queue_item_id}")
        self._print(f"Queue item created: {self.queue_item_id}")

        # Step 2: Wait for scraping to complete
        self._print("Waiting for job scraping...")
        scrape_data = self.monitor.wait_for_stage(
            self.queue_item_id,
            stage="scrape",
            timeout=60.0,
        )

        self._log(f"Scraping complete, status: {scrape_data.get('status')}")

        # Step 3: Wait for filtering
        self._print("Waiting for filtering...")
        filter_data = self.monitor.wait_for_stage(
            self.queue_item_id,
            stage="filter",
            timeout=30.0,
        )

        filter_result = filter_data.get("pipeline_state", {}).get("filter_result", {})
        self._log(f"Filtering complete, passed: {filter_result.get('passed')}")

        # Step 4: Wait for AI analysis
        self._print("Waiting for AI analysis...")
        analyze_data = self.monitor.wait_for_stage(
            self.queue_item_id,
            stage="analyze",
            timeout=120.0,
        )

        match_result = analyze_data.get("pipeline_state", {}).get("match_result", {})
        match_score = match_result.get("match_score", 0)
        self._log(f"Analysis complete, score: {match_score}")
        self._print(f"Match score: {match_score}")

        # Step 5: Wait for save (if score high enough)
        if match_score >= 80:
            self._print("Waiting for match to be saved...")
            final_data = self.monitor.wait_for_status(
                self.queue_item_id,
                expected_status="success",
                timeout=30.0,
            )

            self.match_id = final_data.get("result_data", {}).get("match_id")
            self._log(f"Match saved: {self.match_id}")
            self._print(f"Match created: {self.match_id}")

            # Track match for cleanup
            if self.match_id:
                self.track_for_cleanup("job-matches", self.match_id, "Test match")
        else:
            self._print("Score below threshold, job skipped")
            final_data = self.monitor.wait_for_status(
                self.queue_item_id,
                expected_status="skipped",
                timeout=30.0,
            )

    def verify(self):
        """Verify expected results."""
        self._print("Verifying results...")

        # Verify queue item exists and completed
        queue_item = self.firestore.get_queue_item(self.queue_item_id)

        assert queue_item is not None, "Queue item not found"
        self._log("✓ Queue item exists")

        status = queue_item.get("status")
        assert status in [
            "success",
            "skipped",
        ], f"Expected success/skipped, got {status}"
        self._log(f"✓ Queue item status: {status}")

        # Verify pipeline stages were executed
        pipeline_state = queue_item.get("pipeline_state", {})

        # Check scrape data
        job_data = pipeline_state.get("job_data")
        assert job_data is not None, "No job data in pipeline state"
        self._log("✓ Job data scraped")

        # Check company name
        company = job_data.get("company")
        assert (
            company == self.expected_company
        ), f"Expected company {self.expected_company}, got {company}"
        self._log(f"✓ Company name: {company}")

        # Check title
        title = job_data.get("title", "")
        assert (
            self.expected_title_contains.lower() in title.lower()
        ), f"Expected title to contain '{self.expected_title_contains}', got '{title}'"
        self._log(f"✓ Job title: {title}")

        # Check filter result
        filter_result = pipeline_state.get("filter_result", {})
        assert filter_result.get("passed") is not None, "No filter result"
        self._log(f"✓ Filter executed, passed: {filter_result.get('passed')}")

        # If filtered, verify it didn't create a match
        if not filter_result.get("passed"):
            assert self.match_id is None, "Match created for filtered job (should not happen)"
            self._log("✓ Filtered job correctly skipped")
            self._print("Job was filtered (expected for some test jobs)")
            return

        # Check match result
        match_result = pipeline_state.get("match_result", {})
        match_score = match_result.get("match_score", 0)
        assert match_score > 0, "No match score generated"
        self._log(f"✓ Match score: {match_score}")

        # If score high enough, verify match was created
        if match_score >= 80:
            assert self.match_id is not None, "No match ID returned for high score"

            match_doc = self.firestore.get_job_match(self.match_id)
            assert match_doc is not None, "Match document not found"
            self._log("✓ Match document created")

            # Verify match fields
            assert match_doc.get("url") == self.test_job_url, "Match URL mismatch"
            assert match_doc.get("company_name") == self.expected_company, "Match company mismatch"
            assert match_doc.get("match_score") == match_score, "Match score mismatch"
            self._log("✓ Match document fields correct")

            self._print(f"Match verified: {match_score} score, saved to Firestore")
        else:
            assert self.match_id is None, "Match created despite score below threshold"
            self._log("✓ Low score job correctly skipped")
            self._print(f"Job skipped with score {match_score} (below threshold)")

        self._print("✓ All verifications passed")
