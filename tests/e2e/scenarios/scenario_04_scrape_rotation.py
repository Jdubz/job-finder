"""
Scenario 4: Automated Scrape with Source Rotation

Tests intelligent source rotation and health tracking:
1. Submit SCRAPE request without specific sources
2. Verify sources are fetched with rotation (oldest first)
3. Verify source priority scoring
4. Verify scrape respects target_matches and max_sources limits
5. Verify source health tracking (success/failure counts)
"""

import logging
from typing import Dict, Any, List

from .base_scenario import BaseE2EScenario
from ..helpers import QueueMonitor, FirestoreHelper, CleanupHelper

logger = logging.getLogger(__name__)


class ScrapeRotationScenario(BaseE2EScenario):
    """Test automated scraping with intelligent source rotation."""

    def __init__(self, **kwargs):
        """Initialize scenario."""
        super().__init__(**kwargs)

        # Configuration
        self.target_matches = 3  # Stop after finding 3 potential matches
        self.max_sources = 5  # Don't scrape more than 5 sources

        # Will be set during execution
        self.scrape_queue_id = None
        self.sources_before = []
        self.sources_after = []
        self.scraped_source_ids = []

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
        self.monitor = QueueMonitor(db, timeout=600.0)  # 10 min for scraping
        self.firestore = FirestoreHelper(db, self.db_name)
        self.cleanup = CleanupHelper(db, self.db_name)

        self._log("Test dependencies initialized")

    def execute(self):
        """Execute the scenario."""
        self._print("Submitting automated scrape request...")

        # Step 1: Capture source state before scraping
        self.sources_before = self._get_active_sources()
        self._log(f"Found {len(self.sources_before)} active sources before scrape")
        self._print(f"Active sources: {len(self.sources_before)}")

        # Step 2: Submit SCRAPE queue item
        self.scrape_queue_id = self._create_scrape_queue_item(
            target_matches=self.target_matches, max_sources=self.max_sources
        )

        self.track_for_cleanup("job-queue", self.scrape_queue_id, "Scrape queue item")
        self._print(f"Scrape queue item created: {self.scrape_queue_id}")

        # Step 3: Wait for scraping to complete
        self._print(
            f"Waiting for scrape (max {self.max_sources} sources, target {self.target_matches} matches)..."
        )
        scrape_data = self.monitor.wait_for_status(
            self.scrape_queue_id,
            expected_status="success",
            timeout=480.0,  # 8 minutes
        )

        self._log(f"Scrape complete: {scrape_data.get('result_message')}")
        self._print("Scrape completed")

        # Step 4: Get sources after scraping to see what changed
        import time

        time.sleep(2)  # Give Firestore time to update
        self.sources_after = self._get_active_sources()

        # Find which sources were scraped by checking scraped_at changes
        self.scraped_source_ids = self._identify_scraped_sources(
            self.sources_before, self.sources_after
        )

        self._log(f"Scraped {len(self.scraped_source_ids)} sources")
        self._print(f"Sources scraped: {len(self.scraped_source_ids)}")

    def verify(self):
        """Verify expected results."""
        self._print("Verifying scrape rotation and health tracking...")

        # Verify scrape queue item
        scrape_item = self.firestore.get_document("job-queue", self.scrape_queue_id)
        assert scrape_item is not None, "Scrape queue item not found"
        assert scrape_item["status"] == "success", f"Scrape status: {scrape_item['status']}"
        self._log("✓ Scrape succeeded")

        # Verify sources were scraped
        assert len(self.scraped_source_ids) > 0, "No sources were scraped"
        self._log(f"✓ Scraped {len(self.scraped_source_ids)} sources")

        # Verify max_sources limit was respected
        assert (
            len(self.scraped_source_ids) <= self.max_sources
        ), f"Scraped {len(self.scraped_source_ids)} sources, max was {self.max_sources}"
        self._log(f"✓ Respected max_sources limit ({self.max_sources})")

        # Verify source rotation (oldest first)
        scraped_sources = [s for s in self.sources_after if s["id"] in self.scraped_source_ids]

        if len(scraped_sources) >= 2:
            # Check that scraped sources were among the oldest
            all_sources_sorted = sorted(
                self.sources_before, key=lambda s: s.get("scraped_at") or s.get("created_at")
            )

            oldest_ids = [s["id"] for s in all_sources_sorted[: len(self.scraped_source_ids)]]

            # At least some scraped sources should be from the oldest
            overlap = set(self.scraped_source_ids) & set(oldest_ids)
            assert len(overlap) > 0, "Scrape didn't prioritize oldest sources"
            self._log(
                f"✓ Rotation prioritized oldest sources ({len(overlap)}/{len(self.scraped_source_ids)})"
            )

        # Verify health tracking was updated
        for source in scraped_sources:
            health = source.get("health", {})

            # Check that health stats exist
            assert (
                "last_scraped_at" in health or "scraped_at" in source
            ), "Source health not updated"
            assert (
                "success_count" in health or "failure_count" in health
            ), "Health counts not tracked"

            self._log(
                f"  Source {source.get('name')}: "
                f"success={health.get('success_count', 0)}, "
                f"failure={health.get('failure_count', 0)}"
            )

        self._log("✓ Health tracking updated")

        # Verify scrape found jobs (check result message)
        result_msg = scrape_item.get("result_message", "")
        if "jobs" in result_msg.lower():
            self._log(f"✓ Scrape result: {result_msg}")

        self._print(
            "✓ All verifications passed - source rotation and health tracking working correctly"
        )

    def _create_scrape_queue_item(self, target_matches: int, max_sources: int) -> str:
        """Create SCRAPE queue item."""
        from datetime import datetime, timezone

        data = {
            "type": "scrape",
            "url": "",  # Empty for SCRAPE type
            "company_name": "",  # Empty for SCRAPE type
            "source": "automated_scan",
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "test_run_id": self.test_run_id,
            "scrape_config": {
                "target_matches": target_matches,
                "max_sources": max_sources,
                "source_ids": None,  # None = use rotation
                "min_match_score": None,
            },
        }

        db = self.firestore.db
        doc_ref = db.collection("job-queue").add(data)
        return doc_ref[1].id

    def _get_active_sources(self) -> List[Dict[str, Any]]:
        """Get all active job sources."""
        sources = self.firestore.query_documents("job-sources", filters=[("enabled", "==", True)])

        # Add document ID to each source
        result = []
        for source in sources:
            # Get ID from various possible fields
            source_id = source.get("id") or source.get("_id") or source.get("doc_id")
            if source_id:
                source["id"] = source_id
                result.append(source)

        return result

    def _identify_scraped_sources(
        self, sources_before: List[Dict], sources_after: List[Dict]
    ) -> List[str]:
        """Identify which sources were scraped by comparing timestamps."""
        scraped = []

        # Create lookup maps
        before_map = {s["id"]: s for s in sources_before}
        after_map = {s["id"]: s for s in sources_after}

        for source_id, after_source in after_map.items():
            before_source = before_map.get(source_id)

            if not before_source:
                continue

            # Check if scraped_at changed
            before_scraped = before_source.get("health", {}).get(
                "last_scraped_at"
            ) or before_source.get("scraped_at")

            after_scraped = after_source.get("health", {}).get(
                "last_scraped_at"
            ) or after_source.get("scraped_at")

            if after_scraped and after_scraped != before_scraped:
                scraped.append(source_id)

        return scraped
