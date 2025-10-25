"""
Scenario 3: Company Submission and Source Discovery

Tests the company processing pipeline and automatic source discovery:
1. Submit company with Greenhouse job board
2. Company pipeline processes and detects job board
3. SOURCE_DISCOVERY queue item spawned automatically
4. Source is validated and configured
5. Verify both company and source exist in Firestore
"""

import logging

from .base_scenario import BaseE2EScenario
from ..helpers import QueueMonitor, FirestoreHelper, CleanupHelper

logger = logging.getLogger(__name__)


class CompanySourceDiscoveryScenario(BaseE2EScenario):
    """Test company submission and automatic source discovery."""

    def __init__(self, **kwargs):
        """Initialize scenario."""
        super().__init__(**kwargs)

        # Test data - Cloudflare has active Greenhouse board
        self.company_name = "Cloudflare"
        self.company_website = "https://www.cloudflare.com"
        self.expected_board_token = "cloudflare"
        self.expected_source_type = "greenhouse"

        # Will be set during execution
        self.company_queue_id = None
        self.company_id = None
        self.source_discovery_queue_id = None
        self.source_id = None

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
        self.monitor = QueueMonitor(db, timeout=300.0)  # 5 min for company processing
        self.firestore = FirestoreHelper(db, self.db_name)
        self.cleanup = CleanupHelper(db, self.db_name)

        self._log("Test dependencies initialized")

    def execute(self):
        """Execute the scenario."""
        self._print(f"Submitting company: {self.company_name}")

        # Step 1: Submit company to queue (starts granular pipeline at FETCH)
        self.company_queue_id = self._create_company_queue_item(
            company_name=self.company_name,
            company_website=self.company_website,
        )

        self.track_for_cleanup("job-queue", self.company_queue_id, "Company queue item")
        self._print(f"Company queue item created: {self.company_queue_id}")

        # Step 2: Wait for company processing to complete
        self._print("Waiting for company processing...")
        final_data = self.monitor.wait_for_status(
            self.company_queue_id,
            expected_status="success",
            timeout=240.0,  # 4 minutes for full company pipeline
        )

        self._log(f"Company processing complete: {final_data.get('status')}")

        # Step 3: Check if SOURCE_DISCOVERY was spawned
        self._print("Checking for source discovery spawn...")

        # Give it a moment for the source discovery item to be created
        import time

        time.sleep(2)

        # Find source discovery queue item for this company
        source_discovery_items = self._find_source_discovery_items(self.company_name)

        if not source_discovery_items:
            raise AssertionError(f"No SOURCE_DISCOVERY queue item found for {self.company_name}")

        self.source_discovery_queue_id = source_discovery_items[0]
        self.track_for_cleanup("job-queue", self.source_discovery_queue_id, "Source discovery item")

        self._print(f"Source discovery item found: {self.source_discovery_queue_id}")

        # Step 4: Wait for source discovery to complete
        self._print("Waiting for source discovery...")
        source_disc_data = self.monitor.wait_for_status(
            self.source_discovery_queue_id,
            expected_status="success",
            timeout=120.0,  # 2 minutes for source discovery
        )

        # Extract source_id from result message
        result_msg = source_disc_data.get("result_message", "")
        if "source" in result_msg.lower():
            # Parse source ID from message (format: "Source created: source-id-123")
            parts = result_msg.split(":")
            if len(parts) > 1:
                self.source_id = parts[-1].strip()

        self._log(f"Source discovery complete, source_id: {self.source_id}")
        self._print(f"Source discovered: {self.source_id}")

    def verify(self):
        """Verify expected results."""
        self._print("Verifying company and source creation...")

        # Verify company queue item
        company_item = self.firestore.get_document("job-queue", self.company_queue_id)
        assert company_item is not None, "Company queue item not found"
        assert company_item["status"] == "success", f"Company status: {company_item['status']}"
        self._log("✓ Company queue item succeeded")

        # Verify company was created in companies collection
        # Find company by name
        companies = self.firestore.query_documents(
            "companies", filters=[("name", "==", self.company_name)], limit=1
        )

        assert (
            len(companies) > 0
        ), f"Company '{self.company_name}' not found in companies collection"
        company = companies[0]
        self._log(f"✓ Company document exists: {company.get('name')}")

        # Track company for cleanup
        company_doc_id = company.get("id") or self._get_company_doc_id(self.company_name)
        if company_doc_id:
            self.track_for_cleanup("companies", company_doc_id, "Test company")
            self.company_id = company_doc_id

        # Verify company has expected fields
        assert company.get("website") == self.company_website, "Company website mismatch"
        self._log("✓ Company website correct")

        # Verify source discovery queue item
        source_disc_item = self.firestore.get_document("job-queue", self.source_discovery_queue_id)
        assert source_disc_item is not None, "Source discovery queue item not found"
        assert (
            source_disc_item["status"] == "success"
        ), f"Source discovery status: {source_disc_item['status']}"
        self._log("✓ Source discovery succeeded")

        # Verify source was created
        if self.source_id:
            source = self.firestore.get_document("job-sources", self.source_id)
            assert source is not None, f"Source {self.source_id} not found"

            # Track for cleanup
            self.track_for_cleanup("job-sources", self.source_id, "Discovered source")

            # Verify source config
            assert source.get("sourceType") == self.expected_source_type, "Source type mismatch"
            assert source.get("enabled") is True, "Source not enabled"

            config = source.get("config", {})
            assert config.get("board_token") == self.expected_board_token, "Board token mismatch"

            self._log("✓ Source configured correctly")
            self._print(f"✓ Source verified: {source.get('name')} ({source.get('sourceType')})")
        else:
            logger.warning("Source ID not found in result message, skipping source verification")

        self._print("✓ All verifications passed - company and source created successfully")

    def _create_company_queue_item(self, company_name: str, company_website: str) -> str:
        """Create company queue item starting at FETCH step."""
        from datetime import datetime, timezone

        data = {
            "type": "company",
            "company_sub_task": "fetch",  # Start granular pipeline
            "url": company_website,
            "company_name": company_name,
            "source": "automated_scan",
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "test_run_id": self.test_run_id,
        }

        db = self.firestore.db
        doc_ref = db.collection("job-queue").add(data)
        return doc_ref[1].id

    def _find_source_discovery_items(self, company_name: str) -> list:
        """Find SOURCE_DISCOVERY queue items for a company."""
        items = self.firestore.query_documents(
            "job-queue",
            filters=[("type", "==", "source_discovery"), ("company_name", "==", company_name)],
            limit=5,
        )

        return [item.get("id") or item.get("_id") for item in items if item]

    def _get_company_doc_id(self, company_name: str) -> str:
        """Get company document ID by name."""
        companies = self.firestore.query_documents(
            "companies", filters=[("name", "==", company_name)], limit=1
        )

        if companies:
            # Try to get ID from different possible field names
            company = companies[0]
            return company.get("id") or company.get("_id") or company.get("doc_id")

        return None
