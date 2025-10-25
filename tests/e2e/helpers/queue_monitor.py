"""Queue monitoring helper for E2E tests."""

import logging
import time
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class QueueMonitor:
    """Monitor job queue items through processing stages."""

    def __init__(
        self,
        db_client,
        collection: str = "job-queue",
        poll_interval: float = 1.0,
        timeout: float = 300.0,
        adaptive_timeout: bool = True,
    ):
        """
        Initialize queue monitor.

        Args:
            db_client: Firestore client instance
            collection: Queue collection name
            poll_interval: Initial seconds between status checks (will adapt)
            timeout: Maximum seconds to wait (default)
            adaptive_timeout: Enable adaptive timeout based on queue item type
        """
        self.db = db_client
        self.collection = collection
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.adaptive_timeout = adaptive_timeout

    def wait_for_status(
        self,
        doc_id: str,
        expected_status: str,
        timeout: Optional[float] = None,
        adaptive: bool = True,
    ) -> Dict[str, Any]:
        """
        Wait for queue item to reach expected status with adaptive retry.

        Args:
            doc_id: Document ID to monitor
            expected_status: Target status to wait for
            timeout: Override default timeout
            adaptive: Enable adaptive timeout (adjust based on queue type)

        Returns:
            Final document data

        Raises:
            TimeoutError: If status not reached within timeout
            ValueError: If document not found
        """
        # Auto-detect timeout based on queue item type if adaptive
        actual_timeout = timeout or self.timeout
        if adaptive and self.adaptive_timeout:
            try:
                doc_ref = self.db.collection(self.collection).document(doc_id)
                doc = doc_ref.get()
                if doc.exists:
                    item_type = doc.to_dict().get("type", "job")
                    # Adjust timeout based on type
                    type_timeouts = {
                        "job": 300.0,  # 5 min - includes AI analysis
                        "scrape": 600.0,  # 10 min - multiple sources
                        "company": 180.0,  # 3 min - single company
                    }
                    actual_timeout = type_timeouts.get(item_type, self.timeout)
            except Exception as e:
                logger.warning(f"Could not determine item type for adaptive timeout: {e}")

        start_time = time.time()
        end_time = start_time + actual_timeout
        poll_interval = self.poll_interval
        attempt = 0

        logger.info(
            f"Waiting for {doc_id} to reach status: {expected_status} "
            f"(timeout: {actual_timeout}s, adaptive={adaptive})"
        )

        while time.time() < end_time:
            try:
                doc_ref = self.db.collection(self.collection).document(doc_id)
                doc = doc_ref.get()

                if not doc.exists:
                    logger.warning(f"Document not found, backing off: {doc_id}")
                    time.sleep(min(poll_interval, 10.0))
                    poll_interval *= 1.5
                    continue

                data = doc.to_dict()
                current_status = data.get("status")

                # Reset poll interval on successful read
                poll_interval = self.poll_interval

                logger.debug(
                    f"Status: {current_status} (elapsed: {time.time() - start_time:.1f}s, "
                    f"poll_interval: {poll_interval:.1f}s)"
                )

                if current_status == expected_status:
                    elapsed = time.time() - start_time
                    logger.info(f"✓ Reached status '{expected_status}' after {elapsed:.1f}s")
                    return data

                # Check for error states
                if current_status in ["failed", "rejected", "error"]:
                    elapsed = time.time() - start_time
                    return self._format_timeout_error(data, elapsed, expected_status)

                # Adaptive polling: fast initially, slower over time
                attempt += 1
                if attempt < 3:
                    poll_interval = 0.5  # Fast initial checks
                elif attempt < 10:
                    poll_interval = 1.0
                elif attempt < 20:
                    poll_interval = 2.0
                else:
                    poll_interval = min(5.0, poll_interval * 1.1)

            except Exception as e:
                logger.warning(f"Error polling document: {e}, backing off...")
                time.sleep(poll_interval)
                poll_interval = min(poll_interval * 2, 10.0)
                continue

            time.sleep(poll_interval)

        # Timeout reached - generate detailed diagnostic
        elapsed = time.time() - start_time
        final_doc = self.db.collection(self.collection).document(doc_id).get()
        final_data = final_doc.to_dict() if final_doc.exists else {}
        return self._format_timeout_error(final_data, elapsed, expected_status, final=True)

    def _format_timeout_error(
        self, data: Dict, elapsed: float, expected_status: str, final: bool = False
    ) -> Dict:
        """
        Format and log timeout error with detailed diagnostics.

        Args:
            data: Final document data
            elapsed: Elapsed time
            expected_status: Expected status
            final: Whether this is final timeout (vs error state)

        Returns:
            Document data (for compatibility)

        Raises:
            TimeoutError: Always raises with diagnostic info
        """
        current_status = data.get("status", "unknown")

        # Build detailed error message
        error_lines = [
            f"Timeout waiting for queue item to reach '{expected_status}'",
            f"  Document ID: {data.get('id', 'unknown')}",
            f"  Current status: {current_status}",
            f"  Elapsed time: {elapsed:.1f}s",
            f"  Item type: {data.get('type', 'unknown')}",
        ]

        # Add pipeline info
        if "pipeline_stage" in data:
            error_lines.append(f"  Pipeline stage: {data.get('pipeline_stage')}")

        # Add error details
        if data.get("error"):
            error_lines.append(f"  Error: {data.get('error')}")
        if data.get("result_message"):
            error_lines.append(f"  Message: {data.get('result_message')}")

        # Add status history if available
        metadata = data.get("metadata", {})
        if metadata.get("status_history"):
            error_lines.append(f"  Status history:")
            for entry in metadata.get("status_history", [])[-5:]:  # Last 5 entries
                error_lines.append(
                    f"    - {entry.get('status')} @ {entry.get('timestamp', 'unknown')}"
                )

        error_lines.append(f"  See Google Cloud Logging for worker details")

        error_message = "\n".join(error_lines)
        logger.error(error_message)

        raise TimeoutError(error_message)

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
