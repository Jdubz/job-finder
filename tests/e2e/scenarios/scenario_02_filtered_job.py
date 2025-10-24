"""
Scenario 2: Filtered Job Rejection

Tests that jobs failing filter criteria are correctly rejected before AI analysis.
Verifies cost optimization - rejected jobs should never reach expensive AI analysis.
"""

import logging

from .base_scenario import BaseE2EScenario
from ..helpers import QueueMonitor, FirestoreHelper, CleanupHelper

logger = logging.getLogger(__name__)


class FilteredJobScenario(BaseE2EScenario):
    """Test job filtering and rejection flow."""

    def __init__(self, **kwargs):
        """Initialize scenario."""
        super().__init__(**kwargs)

        # Test data - This job should be filtered out
        # (Using a job that's likely on-site or has excluded keywords)
        self.test_job_url = "https://www.linkedin.com/jobs/view/test-job"  # Placeholder
        self.test_company = "Test Filter Company"

        # Custom job data that will trigger filter rejection
        self.custom_job_data = {
            "title": "Senior Sales Manager",  # Non-technical role
            "company": self.test_company,
            "location": "New York, NY (On-site)",  # On-site location
            "description": "We are looking for an experienced sales manager...",
            "url": self.test_job_url,
            "posted_date": "2025-10-17",
        }

        # Will be set during execution
        self.queue_item_id = None

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
        self.monitor = QueueMonitor(db, timeout=180.0)  # 3 min timeout
        self.firestore = FirestoreHelper(db, self.db_name)
        self.cleanup = CleanupHelper(db, self.db_name)

        self._log("Test dependencies initialized")

    def execute(self):
        """Execute the scenario."""
        self._print(f"Submitting job that should be filtered: {self.test_job_url}")

        # Step 1: Create queue item with pre-populated job data
        # This simulates a scraped job that will go directly to filtering
        self.queue_item_id = self.firestore.create_queue_item(
            url=self.test_job_url,
            company_name=self.test_company,
            source="automated_scan",
            test_run_id=self.test_run_id,
            sub_task="filter",  # Skip scraping, go straight to filter
            pipeline_state={"job_data": self.custom_job_data},
        )

        # Track for cleanup
        self.track_for_cleanup("job-queue", self.queue_item_id, "Test filter item")

        self._log(f"Created queue item: {self.queue_item_id}")
        self._print(f"Queue item created: {self.queue_item_id}")

        # Step 2: Wait for filtering to complete
        self._print("Waiting for filtering to reject job...")
        final_data = self.monitor.wait_for_status(
            self.queue_item_id,
            expected_status="filtered",
            timeout=30.0,
        )

        filter_result = final_data.get("pipeline_state", {}).get("filter_result", {})
        strikes = filter_result.get("strikes", [])

        self._log(f"Filtering complete, strikes: {len(strikes)}")
        self._print(f"Job filtered with {len(strikes)} strike(s)")

        # Log strike reasons
        for strike in strikes:
            reason = strike.get("reason", "Unknown")
            category = strike.get("category", "Unknown")
            self._log(f"  - Strike: {category} - {reason}")
            self._print(f"  • {category}: {reason}")

    def verify(self):
        """Verify expected results."""
        self._print("Verifying filter rejection...")

        # Verify queue item exists
        queue_item = self.firestore.get_queue_item(self.queue_item_id)
        assert queue_item is not None, "Queue item not found"
        self._log("✓ Queue item exists")

        # Verify status is 'filtered'
        status = queue_item.get("status")
        assert status == "filtered", f"Expected status 'filtered', got '{status}'"
        self._log("✓ Status is 'filtered'")

        # Verify filter result exists
        pipeline_state = queue_item.get("pipeline_state", {})
        filter_result = pipeline_state.get("filter_result", {})

        assert filter_result, "No filter result in pipeline state"
        self._log("✓ Filter result exists")

        # Verify job did not pass filter
        passed = filter_result.get("passed")
        assert passed is False, f"Expected passed=False, got {passed}"
        self._log("✓ Filter correctly rejected job")

        # Verify strikes were recorded
        strikes = filter_result.get("strikes", [])
        assert len(strikes) > 0, "No strikes recorded for filtered job"
        self._log(f"✓ {len(strikes)} strike(s) recorded")

        # Verify specific strike reasons
        strike_categories = [s.get("category") for s in strikes]

        # Should have location strike (on-site in non-Portland location)
        assert "work_location" in strike_categories, "Expected work_location strike for on-site job"
        self._log("✓ Work location strike present")

        # Verify pipeline stopped (no match_result)
        assert "match_result" not in pipeline_state, "AI analysis ran on filtered job!"
        self._log("✓ Pipeline correctly stopped before AI analysis")

        # Verify no match was created
        match = self.firestore.find_match_by_url(self.test_job_url)
        assert match is None, "Match created for filtered job (should not happen)"
        self._log("✓ No match created for filtered job")

        # Verify metadata
        metadata = queue_item.get("metadata", {})
        processing_time = metadata.get("processing_time_ms", 0)

        # Processing should be fast (< 5 seconds) since no AI involved
        assert (
            processing_time < 5000
        ), f"Processing took too long: {processing_time}ms (AI may have run)"
        self._log(f"✓ Fast processing: {processing_time}ms (no AI)")

        self._print("✓ All verifications passed - job correctly filtered")
        self._print(f"✓ Cost optimization verified: no AI analysis for filtered job")
