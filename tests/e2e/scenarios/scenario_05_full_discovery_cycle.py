"""
Scenario 5: Full Discovery Cycle (Integration Test)

Tests the complete intelligent data population cycle:
1. Submit company → Company pipeline discovers job board
2. Source discovery → Validates and configures Greenhouse source
3. Scrape → Finds jobs from discovered source
4. Job pipeline → Scrapes, filters, analyzes jobs
5. Match creation → Creates job-match documents for high scores
6. Verification → Complete data chain exists

This is the "golden path" that demonstrates the system filling itself
with valuable data automatically.
"""

import logging
from typing import Dict, List

from .base_scenario import BaseE2EScenario
from ..helpers import QueueMonitor, FirestoreHelper, CleanupHelper

logger = logging.getLogger(__name__)


class FullDiscoveryCycleScenario(BaseE2EScenario):
    """Test complete discovery cycle from company to matches."""

    def __init__(self, **kwargs):
        """Initialize scenario."""
        super().__init__(**kwargs)

        # Test data - Use a company we know has jobs
        self.company_name = "Datadog"
        self.company_website = "https://www.datadoghq.com"
        self.expected_board_token = "datadog"

        # State tracking
        self.company_queue_id = None
        self.company_id = None
        self.source_discovery_queue_id = None
        self.source_id = None
        self.scrape_queue_id = None
        self.job_queue_ids = []
        self.match_ids = []

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
        self.monitor = QueueMonitor(db, timeout=900.0)  # 15 min total
        self.firestore = FirestoreHelper(db, self.db_name)
        self.cleanup = CleanupHelper(db, self.db_name)

        self._log("Test dependencies initialized")

    def execute(self):
        """Execute the complete discovery cycle."""
        # ========================================================================
        # PHASE 1: Company Submission and Source Discovery
        # ========================================================================
        self._print("=" * 80)
        self._print("PHASE 1: Company Submission → Source Discovery")
        self._print("=" * 80)

        self._print(f"Submitting company: {self.company_name}")
        self.company_queue_id = self._create_company_queue_item(
            self.company_name, self.company_website
        )

        self.track_for_cleanup("job-queue", self.company_queue_id, "Company item")
        self._print(f"  → Company queue item: {self.company_queue_id}")

        # Wait for company processing
        self._print("  → Processing company...")
        self.monitor.wait_for_status(
            self.company_queue_id, expected_status="success", timeout=240.0
        )
        self._print("  ✓ Company processed")

        # Find source discovery item
        import time

        time.sleep(2)
        source_disc_items = self._find_queue_items(
            item_type="source_discovery", company_name=self.company_name
        )

        if source_disc_items:
            self.source_discovery_queue_id = source_disc_items[0]["id"]
            self.track_for_cleanup("job-queue", self.source_discovery_queue_id, "Source discovery")
            self._print(f"  → Source discovery item: {self.source_discovery_queue_id}")

            # Wait for source discovery
            self._print("  → Discovering source...")
            disc_data = self.monitor.wait_for_status(
                self.source_discovery_queue_id, expected_status="success", timeout=120.0
            )

            # Extract source ID from result
            result_msg = disc_data.get("result_message", "")
            if ":" in result_msg:
                self.source_id = result_msg.split(":")[-1].strip()
                self.track_for_cleanup("job-sources", self.source_id, "Discovered source")
                self._print(f"  ✓ Source discovered: {self.source_id}")
        else:
            self._print("  ! No source discovery spawned (may already exist)")

        # ========================================================================
        # PHASE 2: Automated Scraping
        # ========================================================================
        self._print("\n" + "=" * 80)
        self._print("PHASE 2: Automated Scraping from Discovered Source")
        self._print("=" * 80)

        # Submit scrape targeting our new source
        self._print("Submitting scrape request...")
        source_ids = [self.source_id] if self.source_id else None

        self.scrape_queue_id = self._create_scrape_queue_item(
            target_matches=5, max_sources=3, source_ids=source_ids
        )

        self.track_for_cleanup("job-queue", self.scrape_queue_id, "Scrape item")
        self._print(f"  → Scrape queue item: {self.scrape_queue_id}")

        # Wait for scraping
        self._print("  → Scraping jobs...")
        scrape_data = self.monitor.wait_for_status(
            self.scrape_queue_id, expected_status="success", timeout=480.0
        )

        result_msg = scrape_data.get("result_message", "")
        self._print(f"  ✓ Scrape complete: {result_msg}")

        # ========================================================================
        # PHASE 3: Job Processing and Matching
        # ========================================================================
        self._print("\n" + "=" * 80)
        self._print("PHASE 3: Job Processing → AI Matching")
        self._print("=" * 80)

        # Wait for job queue items to appear
        time.sleep(3)

        # Find job queue items from our scrape
        self._print("Finding jobs from scrape...")
        job_items = self._find_recent_job_items(company_name=self.company_name, limit=10)

        self._print(f"  → Found {len(job_items)} job queue items")

        # Track first few for monitoring
        for job_item in job_items[:5]:
            job_id = job_item.get("id")
            if job_id:
                self.job_queue_ids.append(job_id)
                self.track_for_cleanup("job-queue", job_id, f"Job item")

        # Wait for at least one job to complete (success or skipped/filtered)
        if self.job_queue_ids:
            self._print(f"  → Monitoring {len(self.job_queue_ids)} jobs...")

            for job_id in self.job_queue_ids[:3]:  # Monitor first 3
                try:
                    final_data = self.monitor.wait_for_completion(job_id, timeout=300.0)
                    status = final_data.get("status")
                    self._print(f"    Job {job_id[:8]}: {status}")
                except Exception as e:
                    self._log(f"    Job {job_id[:8]}: {str(e)}")

        # ========================================================================
        # PHASE 4: Match Verification
        # ========================================================================
        self._print("\n" + "=" * 80)
        self._print("PHASE 4: Match Verification")
        self._print("=" * 80)

        # Give matches time to be created
        time.sleep(2)

        # Find matches from our company
        self._print("Finding created matches...")
        matches = self._find_matches(company_name=self.company_name)

        self._print(f"  → Found {len(matches)} job matches")

        for match in matches[:5]:
            match_id = match.get("id")
            if match_id:
                self.match_ids.append(match_id)
                self.track_for_cleanup("job-matches", match_id, "Job match")

                score = match.get("match_score", 0)
                title = match.get("job_title", "Unknown")
                self._print(f"    {title}: {score}/100")

        self._print("\n✓ Full discovery cycle complete!")

    def verify(self):
        """Verify the complete data chain."""
        self._print("\n" + "=" * 80)
        self._print("VERIFICATION")
        self._print("=" * 80)

        # Verify company exists
        company_item = self.firestore.get_document("job-queue", self.company_queue_id)
        assert company_item["status"] == "success", "Company processing failed"
        self._log("✓ Company processed successfully")

        # Verify company document
        companies = self.firestore.query_documents(
            "companies", filters=[("name", "==", self.company_name)], limit=1
        )

        assert len(companies) > 0, "Company not found in database"
        company = companies[0]
        self._log(f"✓ Company document exists: {company.get('name')}")

        # Verify company has expected data
        assert company.get("website"), "Company missing website"
        self._log("✓ Company has required fields")

        # Verify source (if discovered)
        if self.source_id:
            source = self.firestore.get_document("job-sources", self.source_id)
            assert source is not None, "Source not found"
            assert source.get("enabled"), "Source not enabled"
            assert source.get("sourceType") == "greenhouse", "Source type incorrect"
            self._log(f"✓ Source configured: {source.get('name')}")

        # Verify scrape completed
        scrape_item = self.firestore.get_document("job-queue", self.scrape_queue_id)
        assert scrape_item["status"] == "success", "Scrape failed"
        self._log("✓ Scrape completed successfully")

        # Verify jobs were processed
        assert len(self.job_queue_ids) > 0, "No jobs were created"
        self._log(f"✓ {len(self.job_queue_ids)} jobs processed")

        # Verify matches were created
        assert len(self.match_ids) > 0, "No matches were created"
        self._log(f"✓ {len(self.match_ids)} matches created")

        # Verify match quality
        for match_id in self.match_ids[:3]:
            match = self.firestore.get_document("job-matches", match_id)
            score = match.get("match_score", 0)

            # Matches should have decent scores
            assert score >= 65, f"Match score too low: {score}"
            assert match.get("job_title"), "Match missing job title"
            assert match.get("match_reasons"), "Match missing reasons"

        self._log("✓ Matches have required quality")

        # Verify complete data chain
        self._print("\n✓ COMPLETE DATA CHAIN VERIFIED:")
        self._print(f"  Company → Source → Jobs → Matches")
        self._print(
            f"  {self.company_name} → {self.expected_board_token} → {len(self.job_queue_ids)} jobs → {len(self.match_ids)} matches"
        )
        self._print("\n✓ System successfully filled itself with valuable data!")

    def _create_company_queue_item(self, name: str, website: str) -> str:
        """Create company queue item."""
        from datetime import datetime, timezone

        data = {
            "type": "company",
            "company_sub_task": "fetch",
            "url": website,
            "company_name": name,
            "source": "automated_scan",
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "test_run_id": self.test_run_id,
        }

        doc_ref = self.firestore.db.collection("job-queue").add(data)
        return doc_ref[1].id

    def _create_scrape_queue_item(
        self, target_matches: int, max_sources: int, source_ids: List[str] = None
    ) -> str:
        """Create scrape queue item."""
        from datetime import datetime, timezone

        data = {
            "type": "scrape",
            "url": "",
            "company_name": "",
            "source": "automated_scan",
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "test_run_id": self.test_run_id,
            "scrape_config": {
                "target_matches": target_matches,
                "max_sources": max_sources,
                "source_ids": source_ids,
                "min_match_score": None,
            },
        }

        doc_ref = self.firestore.db.collection("job-queue").add(data)
        return doc_ref[1].id

    def _find_queue_items(self, item_type: str, company_name: str = None) -> List[Dict]:
        """Find queue items by type and optional company name."""
        filters = [("type", "==", item_type)]
        if company_name:
            filters.append(("company_name", "==", company_name))

        items = self.firestore.query_documents("job-queue", filters=filters, limit=10)

        # Add IDs
        result = []
        for item in items:
            item_id = item.get("id") or item.get("_id")
            if item_id:
                item["id"] = item_id
                result.append(item)

        return result

    def _find_recent_job_items(self, company_name: str, limit: int = 10) -> List[Dict]:
        """Find recent job queue items for a company."""
        items = self.firestore.query_documents(
            "job-queue",
            filters=[("type", "==", "job"), ("company_name", "==", company_name)],
            limit=limit,
        )

        result = []
        for item in items:
            item_id = item.get("id") or item.get("_id")
            if item_id:
                item["id"] = item_id
                result.append(item)

        return result

    def _find_matches(self, company_name: str) -> List[Dict]:
        """Find job matches for a company."""
        matches = self.firestore.query_documents(
            "job-matches", filters=[("company_name", "==", company_name)], limit=20
        )

        result = []
        for match in matches:
            match_id = match.get("id") or match.get("_id")
            if match_id:
                match["id"] = match_id
                result.append(match)

        return result
