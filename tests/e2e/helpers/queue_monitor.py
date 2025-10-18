"""Queue monitoring helper for E2E tests."""

import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueueMonitor:
    """Monitor job queue items through processing stages."""

    def __init__(
        self,
        db_client,
        collection: str = "job-queue",
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ):
        """
        Initialize queue monitor.

        Args:
            db_client: Firestore client instance
            collection: Queue collection name
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait
        """
        self.db = db_client
        self.collection = collection
        self.poll_interval = poll_interval
        self.timeout = timeout

    def wait_for_status(
        self,
        doc_id: str,
        expected_status: str,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Wait for queue item to reach expected status.

        Args:
            doc_id: Document ID to monitor
            expected_status: Target status to wait for
            timeout: Override default timeout

        Returns:
            Final document data

        Raises:
            TimeoutError: If status not reached within timeout
            ValueError: If document not found
        """
        timeout = timeout or self.timeout
        start_time = time.time()
        end_time = start_time + timeout

        logger.info(
            f"Waiting for {doc_id} to reach status: {expected_status} " f"(timeout: {timeout}s)"
        )

        while time.time() < end_time:
            doc_ref = self.db.collection(self.collection).document(doc_id)
            doc = doc_ref.get()

            if not doc.exists:
                raise ValueError(f"Document {doc_id} not found in {self.collection}")

            data = doc.to_dict()
            current_status = data.get("status")

            logger.debug(
                f"Current status: {current_status} (elapsed: {time.time() - start_time:.1f}s)"
            )

            if current_status == expected_status:
                elapsed = time.time() - start_time
                logger.info(f"✓ Reached status '{expected_status}' after {elapsed:.1f}s")
                return data

            # Check for error states
            if current_status in ["failed", "rejected", "error"]:
                error_msg = data.get("error", "Unknown error")
                logger.warning(f"Item reached error state: {current_status} - {error_msg}")
                return data

            time.sleep(self.poll_interval)

        # Timeout reached
        elapsed = time.time() - start_time
        raise TimeoutError(
            f"Timeout waiting for {doc_id} to reach '{expected_status}' "
            f"(waited {elapsed:.1f}s, last status: {current_status})"
        )

    def wait_for_completion(
        self,
        doc_id: str,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Wait for queue item to complete processing.

        Completion means reaching one of: completed, failed, rejected

        Args:
            doc_id: Document ID to monitor
            timeout: Override default timeout

        Returns:
            Final document data

        Raises:
            TimeoutError: If not completed within timeout
        """
        timeout = timeout or self.timeout
        start_time = time.time()
        end_time = start_time + timeout

        completion_statuses = ["completed", "failed", "rejected"]

        logger.info(f"Waiting for {doc_id} to complete (timeout: {timeout}s)")

        while time.time() < end_time:
            doc_ref = self.db.collection(self.collection).document(doc_id)
            doc = doc_ref.get()

            if not doc.exists:
                raise ValueError(f"Document {doc_id} not found in {self.collection}")

            data = doc.to_dict()
            current_status = data.get("status")

            if current_status in completion_statuses:
                elapsed = time.time() - start_time
                logger.info(f"✓ Completed with status '{current_status}' after {elapsed:.1f}s")
                return data

            logger.debug(
                f"Current status: {current_status} (elapsed: {time.time() - start_time:.1f}s)"
            )

            time.sleep(self.poll_interval)

        # Timeout reached
        elapsed = time.time() - start_time
        raise TimeoutError(
            f"Timeout waiting for {doc_id} to complete "
            f"(waited {elapsed:.1f}s, last status: {current_status})"
        )

    def get_status(self, doc_id: str) -> Optional[str]:
        """
        Get current status of queue item.

        Args:
            doc_id: Document ID

        Returns:
            Current status or None if not found
        """
        doc_ref = self.db.collection(self.collection).document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        return doc.to_dict().get("status")

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full document data.

        Args:
            doc_id: Document ID

        Returns:
            Document data or None if not found
        """
        doc_ref = self.db.collection(self.collection).document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        return doc.to_dict()

    def get_status_history(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Get status change history for item.

        Args:
            doc_id: Document ID

        Returns:
            List of status changes with timestamps
        """
        data = self.get_document(doc_id)
        if not data:
            return []

        # Status history stored in metadata.status_history
        metadata = data.get("metadata", {})
        return metadata.get("status_history", [])

    def wait_for_stage(
        self,
        doc_id: str,
        stage: str,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Wait for queue item to reach a specific pipeline stage.

        Args:
            doc_id: Document ID to monitor
            stage: Target pipeline stage (e.g., 'ai_filter', 'scrape')
            timeout: Override default timeout

        Returns:
            Document data when stage is reached

        Raises:
            TimeoutError: If stage not reached within timeout
        """
        timeout = timeout or self.timeout
        start_time = time.time()
        end_time = start_time + timeout

        logger.info(f"Waiting for {doc_id} to reach stage: {stage} (timeout: {timeout}s)")

        while time.time() < end_time:
            data = self.get_document(doc_id)

            if not data:
                raise ValueError(f"Document {doc_id} not found")

            current_stage = data.get("pipeline_stage")
            current_status = data.get("status")

            logger.debug(
                f"Stage: {current_stage}, Status: {current_status} "
                f"(elapsed: {time.time() - start_time:.1f}s)"
            )

            if current_stage == stage:
                elapsed = time.time() - start_time
                logger.info(f"✓ Reached stage '{stage}' after {elapsed:.1f}s")
                return data

            # Check for completion states
            if current_status in ["completed", "failed", "rejected"]:
                logger.warning(
                    f"Item completed before reaching stage '{stage}' "
                    f"(final stage: {current_stage}, status: {current_status})"
                )
                return data

            time.sleep(self.poll_interval)

        # Timeout reached
        elapsed = time.time() - start_time
        raise TimeoutError(
            f"Timeout waiting for {doc_id} to reach stage '{stage}' "
            f"(waited {elapsed:.1f}s, last stage: {current_stage})"
        )
