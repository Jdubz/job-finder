"""Base class for E2E test scenarios."""

import logging
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test execution status."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """Test result data."""

    scenario_name: str
    status: TestStatus
    duration: float
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None

    @property
    def passed(self) -> bool:
        """Check if test passed."""
        return self.status == TestStatus.SUCCESS


class BaseE2EScenario:
    """Base class for E2E test scenarios."""

    def __init__(
        self,
        database_name: str = "portfolio-staging",
        verbose: bool = False,
        cleanup: bool = True,
    ):
        """
        Initialize base scenario.

        Args:
            database_name: Firestore database name
            verbose: Enable verbose logging
            cleanup: Clean up test data after execution
        """
        self.db_name = database_name
        self.verbose = verbose
        self.do_cleanup = cleanup
        self.test_run_id = self._generate_test_run_id()
        self.cleanup_items: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        # Configure logging
        if self.verbose:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
        else:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(levelname)s - %(message)s",
            )

    @property
    def name(self) -> str:
        """Get scenario name."""
        return self.__class__.__name__

    @property
    def duration(self) -> float:
        """Get scenario execution duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

    def _generate_test_run_id(self) -> str:
        """Generate unique test run ID."""
        return f"e2e_test_{uuid.uuid4().hex[:8]}"

    def _log(self, message: str, level: str = "info"):
        """Log message."""
        log_func = getattr(logger, level, logger.info)
        log_func(f"[{self.name}] {message}")

    def _print(self, message: str):
        """Print message to console."""
        print(f"[{self.name}] {message}")

    def setup(self):
        """
        Run before scenario execution.

        Override in subclasses for scenario-specific setup.
        """
        self._log("Setting up scenario...")

    def execute(self):
        """
        Run the scenario.

        Override in subclasses with scenario logic.
        """
        raise NotImplementedError(f"{self.name} must implement execute()")

    def verify(self):
        """
        Verify expected results.

        Override in subclasses with verification logic.
        """
        raise NotImplementedError(f"{self.name} must implement verify()")

    def cleanup(self):
        """
        Clean up test data.

        Override in subclasses to add scenario-specific cleanup.
        Default implementation handles items in self.cleanup_items.
        """
        if not self.do_cleanup:
            self._log("Cleanup disabled, skipping...")
            return

        self._log(f"Cleaning up {len(self.cleanup_items)} items...")

        from job_finder.storage.firestore_client import FirestoreClient

        db = FirestoreClient.get_client(self.db_name)

        for item in self.cleanup_items:
            try:
                collection = item.get("collection")
                doc_id = item.get("id")

                if collection and doc_id:
                    db.collection(collection).document(doc_id).delete()
                    self._log(f"Deleted {collection}/{doc_id}", level="debug")

            except Exception as e:
                self._log(f"Error cleaning up {item}: {e}", level="warning")

        self._log("Cleanup complete")

    def track_for_cleanup(
        self,
        collection: str,
        doc_id: str,
        description: Optional[str] = None,
    ):
        """
        Track document for cleanup.

        Args:
            collection: Firestore collection name
            doc_id: Document ID
            description: Optional description
        """
        self.cleanup_items.append(
            {
                "collection": collection,
                "id": doc_id,
                "description": description or f"{collection}/{doc_id}",
            }
        )

    def run(self) -> TestResult:
        """
        Execute full scenario.

        Returns:
            TestResult with execution details
        """
        self._print(f"Running scenario: {self.name}")
        self._print(f"Test run ID: {self.test_run_id}")
        self._print("-" * 70)

        self.start_time = time.time()

        try:
            # Setup
            self._print("[1/4] Setup...")
            self.setup()

            # Execute
            self._print("[2/4] Execute...")
            self.execute()

            # Verify
            self._print("[3/4] Verify...")
            self.verify()

            self.end_time = time.time()

            # Success
            result = TestResult(
                scenario_name=self.name,
                status=TestStatus.SUCCESS,
                duration=self.duration,
                message="Scenario completed successfully",
            )

            self._print(f"✓ {self.name} PASSED in {self.duration:.2f}s")

        except AssertionError as e:
            self.end_time = time.time()
            result = TestResult(
                scenario_name=self.name,
                status=TestStatus.FAILURE,
                duration=self.duration,
                message=str(e),
                error=e,
            )
            self._print(f"✗ {self.name} FAILED: {e}")

        except Exception as e:
            self.end_time = time.time()
            result = TestResult(
                scenario_name=self.name,
                status=TestStatus.ERROR,
                duration=self.duration,
                message=f"Unexpected error: {e}",
                error=e,
            )
            self._log(f"Error in scenario: {e}", level="error")
            self._print(f"✗ {self.name} ERROR: {e}")

        finally:
            # Cleanup
            self._print("[4/4] Cleanup...")
            try:
                self.cleanup()
            except Exception as e:
                self._log(f"Cleanup failed: {e}", level="warning")

        self._print("-" * 70)
        return result
