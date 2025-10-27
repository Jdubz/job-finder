"""Firestore-backed queue manager for job processing."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google.cloud import firestore as gcloud_firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from job_finder.exceptions import QueueProcessingError
from job_finder.job_queue.models import (
    CompanySubTask,
    JobQueueItem,
    JobSubTask,
    QueueItemType,
    QueueSource,
    QueueStatus,
)
from job_finder.storage.firestore_client import FirestoreClient

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Manages job queue in Firestore.

    Provides CRUD operations for queue items with FIFO ordering.
    Items are processed in order of created_at (oldest first).
    """

    def __init__(
        self, credentials_path: Optional[str] = None, database_name: str = "portfolio-staging"
    ):
        """
        Initialize queue manager.

        Args:
            credentials_path: Path to Firebase service account JSON
            database_name: Firestore database name
        """
        self.db = FirestoreClient.get_client(database_name, credentials_path)
        self.collection_name = "job-queue"

    def add_item(self, item: JobQueueItem) -> str:
        """
        Add item to queue.

        Args:
            item: Queue item to add

        Returns:
            Document ID of added item
        """
        # Set timestamps
        now = datetime.now(timezone.utc)
        item.created_at = now
        item.updated_at = now
        item.status = QueueStatus.PENDING

        # Convert to Firestore format
        data = item.to_firestore()
        data["created_at"] = gcloud_firestore.SERVER_TIMESTAMP
        data["updated_at"] = gcloud_firestore.SERVER_TIMESTAMP

        try:
            doc_ref = self.db.collection(self.collection_name).add(data)
            doc_id = doc_ref[1].id
            logger.info(
                f"Added queue item: {item.type} - {item.url[:50]}... "
                f"(ID: {doc_id}, source: {item.source})"
            )
            return doc_id

        except Exception as e:
            logger.error(f"Error adding queue item: {e}")
            raise

    def get_pending_items(self, limit: int = 10) -> List[JobQueueItem]:
        """
        Get pending items in FIFO order (oldest first).

        Args:
            limit: Maximum number of items to return

        Returns:
            List of pending queue items
        """
        try:
            query = (
                self.db.collection(self.collection_name)
                .where(filter=FieldFilter("status", "==", QueueStatus.PENDING.value))
                .order_by("created_at")
                .limit(limit)
            )

            docs = query.stream()

            items = []
            for doc in docs:
                data = doc.to_dict()
                item = JobQueueItem.from_firestore(doc.id, data)
                items.append(item)

            if items:
                logger.debug(f"Retrieved {len(items)} pending queue items")

            return items

        except Exception as e:
            logger.error(f"Error getting pending items: {e}")
            return []

    def update_status(
        self,
        item_id: str,
        status: QueueStatus,
        result_message: Optional[str] = None,
        scraped_data: Optional[dict] = None,
        error_details: Optional[str] = None,
        pipeline_stage: Optional[str] = None,
    ) -> None:
        """
        Update item status and optional message.

        Args:
            item_id: Queue item document ID
            status: New status
            result_message: Optional message describing result
            scraped_data: Optional scraped data to store
            error_details: Optional detailed error information for debugging
            pipeline_stage: Optional pipeline stage for E2E test monitoring (scrape/filter/analyze/save)
        """
        update_data = {
            "status": status.value,
            "updated_at": gcloud_firestore.SERVER_TIMESTAMP,
        }

        if result_message:
            update_data["result_message"] = result_message

        if scraped_data is not None:
            update_data["scraped_data"] = scraped_data

        if error_details is not None:
            update_data["error_details"] = error_details

        if pipeline_stage is not None:
            update_data["pipeline_stage"] = pipeline_stage

        # Set processed_at when starting processing
        if status == QueueStatus.PROCESSING:
            update_data["processed_at"] = gcloud_firestore.SERVER_TIMESTAMP

        # Set completed_at when finishing (success/failed/skipped/filtered)
        if status in [
            QueueStatus.SUCCESS,
            QueueStatus.FAILED,
            QueueStatus.SKIPPED,
            QueueStatus.FILTERED,
        ]:
            update_data["completed_at"] = gcloud_firestore.SERVER_TIMESTAMP

        try:
            self.db.collection(self.collection_name).document(item_id).update(update_data)
            logger.debug(f"Updated queue item {item_id}: {status.value}")

        except Exception as e:
            logger.error(f"Error updating queue item {item_id}: {e}")
            raise

    def increment_retry(self, item_id: str) -> None:
        """
        Increment retry count for an item.

        Args:
            item_id: Queue item document ID
        """
        try:
            self.db.collection(self.collection_name).document(item_id).update(
                {
                    "retry_count": gcloud_firestore.Increment(1),
                    "updated_at": gcloud_firestore.SERVER_TIMESTAMP,
                }
            )
            logger.debug(f"Incremented retry count for item {item_id}")

        except Exception as e:
            logger.error(f"Error incrementing retry for item {item_id}: {e}")
            raise

    def get_item(self, item_id: str) -> Optional[JobQueueItem]:
        """
        Get specific queue item by ID.

        Args:
            item_id: Queue item document ID

        Returns:
            JobQueueItem or None if not found
        """
        try:
            doc = self.db.collection(self.collection_name).document(item_id).get()

            if doc.exists:
                data = doc.to_dict()
                if data:
                    return JobQueueItem.from_firestore(doc.id, data)
                return None
            else:
                logger.warning(f"Queue item {item_id} not found")
                return None

        except Exception as e:
            logger.error(f"Error getting queue item {item_id}: {e}")
            return None

    def url_exists_in_queue(self, url: str) -> bool:
        """
        Check if URL already exists in queue (any status).

        Args:
            url: Job or company URL

        Returns:
            True if URL exists in queue, False otherwise
        """
        try:
            query = (
                self.db.collection(self.collection_name)
                .where(filter=FieldFilter("url", "==", url))
                .limit(1)
            )

            docs = list(query.stream())
            return len(docs) > 0

        except Exception as e:
            logger.error(f"Error checking URL existence: {e}")
            return False

    def get_queue_stats(self) -> dict:
        """
        Get statistics about queue.

        Returns:
            Dictionary with counts by status
        """
        stats = {
            "pending": 0,
            "processing": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "filtered": 0,
            "total": 0,
        }

        try:
            # Get all documents
            docs = self.db.collection(self.collection_name).stream()

            for doc in docs:
                data = doc.to_dict()
                status = data.get("status", "unknown")
                if status in stats:
                    stats[status] += 1
                stats["total"] += 1

            logger.info(f"Queue stats: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return stats

    def retry_item(self, item_id: str) -> bool:
        """
        Retry a failed queue item by resetting it to pending status.

        Resets the item status to PENDING and clears error details,
        allowing it to be picked up again by the queue processor.

        Args:
            item_id: Queue item document ID

        Returns:
            True if item was reset successfully, False otherwise
        """
        try:
            # First check if item exists
            item = self.get_item(item_id)
            if not item:
                logger.warning(f"Cannot retry: Queue item {item_id} not found")
                return False

            # Only retry failed items
            if item.status != QueueStatus.FAILED:
                logger.warning(
                    f"Cannot retry item {item_id}: status is {item.status.value}, not failed"
                )
                return False

            # Reset to pending
            update_data = {
                "status": QueueStatus.PENDING.value,
                "updated_at": gcloud_firestore.SERVER_TIMESTAMP,
                "processed_at": gcloud_firestore.DELETE_FIELD,
                "completed_at": gcloud_firestore.DELETE_FIELD,
                "error_details": gcloud_firestore.DELETE_FIELD,
            }

            self.db.collection(self.collection_name).document(item_id).update(update_data)
            logger.info(f"Reset queue item {item_id} to pending for retry")
            return True

        except Exception as e:
            logger.error(f"Error retrying queue item {item_id}: {e}")
            return False

    def delete_item(self, item_id: str) -> bool:
        """
        Delete a queue item from Firestore.

        Args:
            item_id: Queue item document ID

        Returns:
            True if item was deleted successfully, False otherwise
        """
        try:
            # Check if item exists first
            item = self.get_item(item_id)
            if not item:
                logger.warning(f"Cannot delete: Queue item {item_id} not found")
                return False

            # Delete the document
            self.db.collection(self.collection_name).document(item_id).delete()
            status_str = item.status.value if isinstance(item.status, QueueStatus) else item.status
            logger.info(f"Deleted queue item {item_id} (was {status_str})")
            return True

        except Exception as e:
            logger.error(f"Error deleting queue item {item_id}: {e}")
            return False

    def has_pending_scrape(self) -> bool:
        """
        Check if there is already a pending SCRAPE request in the queue.

        Returns:
            True if a pending SCRAPE exists, False otherwise
        """
        try:
            from job_finder.job_queue.models import QueueItemType

            query = (
                self.db.collection(self.collection_name)
                .where(filter=FieldFilter("type", "==", QueueItemType.SCRAPE.value))
                .where(filter=FieldFilter("status", "==", QueueStatus.PENDING.value))
                .limit(1)
            )

            docs = list(query.stream())
            return len(docs) > 0

        except Exception as e:
            logger.error(f"Error checking for pending scrape: {e}")
            return False

    # ========================================================================
    # Granular Pipeline Helper Methods
    # ========================================================================

    def create_pipeline_item(
        self,
        url: str,
        sub_task: JobSubTask,
        pipeline_state: Dict[str, Any],
        parent_item_id: Optional[str] = None,
        company_name: str = "",
        company_id: Optional[str] = None,
        source: QueueSource = "scraper",
    ) -> str:
        """
        DEPRECATED: Use spawn_item_safely() instead for loop prevention.

        Create a granular pipeline queue item.

        Args:
            url: Job URL
            sub_task: Pipeline step (scrape/filter/analyze/save)
            pipeline_state: State data from previous step
            parent_item_id: ID of parent item that spawned this
            company_name: Company name (optional)
            company_id: Company document ID (optional)
            source: Source of submission

        Returns:
            Document ID of created item
        """
        raise DeprecationWarning(
            "create_pipeline_item() is deprecated. Use spawn_item_safely() instead "
            "to ensure loop prevention with tracking_id, ancestry_chain, and spawn_depth."
        )

    def spawn_next_pipeline_step(
        self,
        current_item: JobQueueItem,
        next_sub_task: Optional[JobSubTask] = None,
        pipeline_state: Optional[Dict[str, Any]] = None,
        is_company: bool = False,
    ) -> Optional[str]:
        """
        Spawn the next step in the pipeline from current item.

        Uses spawn_item_safely() for loop prevention.
        Supports both job and company pipelines.

        Args:
            current_item: Current item that just completed
            next_sub_task: Next job pipeline step to create (for jobs)
            pipeline_state: Updated state to pass to next step
            is_company: If True, treat as company pipeline

        Returns:
            Document ID of spawned item, or None if blocked
        """
        if is_company:
            # Company pipeline
            if not isinstance(next_sub_task, CompanySubTask):
                raise QueueProcessingError(
                    "next_sub_task must be CompanySubTask for company pipelines"
                )

            new_item_data = {
                "type": QueueItemType.COMPANY,
                "url": current_item.url,
                "company_name": current_item.company_name,
                "company_id": current_item.company_id,
                "source": current_item.source,
                "company_sub_task": next_sub_task,
                "pipeline_state": pipeline_state,
            }

            doc_id = self.spawn_item_safely(current_item, new_item_data)
            if doc_id:
                logger.info(
                    f"Created company pipeline item: {next_sub_task.value} for {current_item.company_name}"
                )
            return doc_id
        else:
            # Job pipeline
            new_item_data = {
                "type": QueueItemType.JOB,
                "url": current_item.url,
                "company_name": current_item.company_name,
                "company_id": current_item.company_id,
                "source": current_item.source,
                "sub_task": next_sub_task,
                "pipeline_state": pipeline_state,
            }

            doc_id = self.spawn_item_safely(current_item, new_item_data)
            if doc_id:
                logger.info(
                    f"Created job pipeline item: {next_sub_task.value if next_sub_task else 'next'} for {current_item.url[:50]}..."
                )
            return doc_id

    def get_items_by_tracking_id(
        self,
        tracking_id: str,
        status_filter: Optional[List[QueueStatus]] = None,
    ) -> List[JobQueueItem]:
        """
        Get all items in the same tracking lineage.

        Used for loop detection and duplicate work prevention.

        Args:
            tracking_id: Tracking ID to query
            status_filter: Optional list of statuses to filter by

        Returns:
            List of queue items with matching tracking_id
        """
        try:
            query = self.db.collection(self.collection_name).where(
                filter=FieldFilter("tracking_id", "==", tracking_id)
            )

            docs = query.stream()
            items = []

            for doc in docs:
                data = doc.to_dict()
                item = JobQueueItem.from_firestore(doc.id, data)

                # Filter by status if specified
                if status_filter is None or item.status in status_filter:
                    items.append(item)

            return items

        except Exception as e:
            logger.error(f"Error getting items by tracking_id {tracking_id}: {e}")
            return []

    def has_pending_work_for_url(
        self,
        url: str,
        item_type: QueueItemType,
        tracking_id: str,
    ) -> bool:
        """
        Check if URL is already queued for processing in this tracking lineage.

        Args:
            url: URL to check
            item_type: Type of work (job, company, etc.)
            tracking_id: Tracking ID to scope the check

        Returns:
            True if work is pending or processing, False otherwise
        """
        try:
            # Note: Firestore compound queries require indexes
            # For now, get all items by tracking_id and filter in-memory
            items = self.get_items_by_tracking_id(
                tracking_id,
                status_filter=[QueueStatus.PENDING, QueueStatus.PROCESSING],
            )

            for item in items:
                if item.url == url and item.type == item_type:
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking pending work for {url}: {e}")
            return False

    def can_spawn_item(
        self,
        current_item: JobQueueItem,
        target_url: str,
        target_type: QueueItemType,
    ) -> tuple[bool, str]:
        """
        Check if spawning a new item would create a loop.

        Performs 4 checks:
        1. Spawn depth limit
        2. Circular dependency (URL already in ancestry)
        3. Duplicate pending work
        4. Already completed successfully

        Args:
            current_item: Current queue item attempting to spawn
            target_url: URL of item to spawn
            target_type: Type of item to spawn

        Returns:
            Tuple of (can_spawn, reason)
        """
        # Check 1: Depth limit
        if current_item.spawn_depth >= current_item.max_spawn_depth:
            return (
                False,
                f"Max spawn depth ({current_item.max_spawn_depth}) reached",
            )

        # Check 2: Circular dependency - DISABLED for granular pipelines
        # The same URL needs to progress through multiple sub-tasks (FETCH → EXTRACT → ANALYZE → SAVE)
        # Check 3 (duplicate pending work) handles actual duplicate prevention
        # Check 4 (terminal states) prevents re-processing completed items

        # Check 3: Duplicate pending work
        if self.has_pending_work_for_url(target_url, target_type, current_item.tracking_id):
            return (
                False,
                f"Duplicate work: {target_type.value} for {target_url} already queued",
            )

        # Check 4: Already reached terminal state
        # Only block if the URL has reached a FINAL state (save/filtered/skipped/failed)
        # Intermediate states (scrape/filter/analyze with SUCCESS) should allow re-spawning
        terminal_states = [
            QueueStatus.FILTERED,
            QueueStatus.SKIPPED,
            QueueStatus.FAILED,
        ]

        terminal_items = self.get_items_by_tracking_id(
            current_item.tracking_id,
            status_filter=terminal_states,
        )

        for item in terminal_items:
            if item.url == target_url and item.type == target_type:
                return (
                    False,
                    f"Already in terminal state ({item.status.value}): {target_type.value} for {target_url}",
                )

        # Also check for items that completed the SAVE stage (final SUCCESS state)
        completed_items = self.get_items_by_tracking_id(
            current_item.tracking_id,
            status_filter=[QueueStatus.SUCCESS],
        )

        for item in completed_items:
            if item.url == target_url and item.type == target_type:
                # Check if this is the final save stage
                if hasattr(item, "pipeline_stage") and item.pipeline_stage == "save":
                    return (
                        False,
                        f"Already saved: {target_type.value} for {target_url}",
                    )

        # All checks passed
        return (True, "OK")

    def spawn_item_safely(
        self,
        current_item: JobQueueItem,
        new_item_data: dict,
    ) -> Optional[str]:
        """
        Spawn a new queue item with loop prevention.

        Automatically inherits tracking_id, ancestry_chain, and spawn_depth from parent.
        Performs loop prevention checks before spawning.

        Args:
            current_item: Current item spawning the new one
            new_item_data: Data for new item (must include 'type' and 'url')

        Returns:
            Document ID of spawned item, or None if blocked
        """
        target_url = new_item_data.get("url", "")
        target_type = new_item_data.get("type")

        if not target_type:
            logger.error("Cannot spawn item without 'type' field")
            return None

        if not isinstance(target_type, QueueItemType):
            target_type = QueueItemType(target_type)

        # Check if spawning is allowed
        can_spawn, reason = self.can_spawn_item(current_item, target_url, target_type)

        if not can_spawn:
            logger.warning(
                f"Blocked spawn to prevent loop: {reason}. "
                f"Current item: {current_item.id}, tracking_id: {current_item.tracking_id}"
            )
            return None

        # Create new item with inherited tracking data
        new_item_data["tracking_id"] = current_item.tracking_id
        new_item_data["ancestry_chain"] = current_item.ancestry_chain + [current_item.id]
        new_item_data["spawn_depth"] = current_item.spawn_depth + 1
        new_item_data["parent_item_id"] = current_item.id

        new_item = JobQueueItem(**new_item_data)

        # Add to queue
        item_id = self.add_item(new_item)

        logger.info(
            f"Spawned item {item_id} (depth: {new_item.spawn_depth}, "
            f"tracking_id: {new_item.tracking_id}, "
            f"chain length: {len(new_item.ancestry_chain)})"
        )

        return item_id
