"""Firestore-backed queue manager for job processing."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google.cloud import firestore as gcloud_firestore

from job_finder.queue.models import (
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
                .where("status", "==", QueueStatus.PENDING.value)
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
    ) -> None:
        """
        Update item status and optional message.

        Args:
            item_id: Queue item document ID
            status: New status
            result_message: Optional message describing result
            scraped_data: Optional scraped data to store
            error_details: Optional detailed error information for debugging
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
            query = self.db.collection(self.collection_name).where("url", "==", url).limit(1)

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

    def clean_old_completed(self, days_old: int = 7) -> int:
        """
        Delete completed items older than specified days.

        Args:
            days_old: Delete items completed more than this many days ago

        Returns:
            Number of items deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        try:
            # Query completed items older than cutoff
            query = (
                self.db.collection(self.collection_name)
                .where(
                    "status",
                    "in",
                    [
                        QueueStatus.SUCCESS.value,
                        QueueStatus.SKIPPED.value,
                        QueueStatus.FILTERED.value,
                    ],
                )
                .where("completed_at", "<", cutoff_date)
            )

            docs = query.stream()
            deleted_count = 0

            for doc in docs:
                doc.reference.delete()
                deleted_count += 1

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old completed queue items")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning old completed items: {e}")
            return 0

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
            from job_finder.queue.models import QueueItemType

            query = (
                self.db.collection(self.collection_name)
                .where("type", "==", QueueItemType.SCRAPE.value)
                .where("status", "==", QueueStatus.PENDING.value)
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
                raise ValueError("next_sub_task must be CompanySubTask for company pipelines")

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

    def update_pipeline_state(
        self,
        item_id: str,
        pipeline_state: Dict[str, Any],
    ) -> None:
        """
        Update pipeline state for an item.

        Args:
            item_id: Queue item document ID
            pipeline_state: New pipeline state data
        """
        try:
            self.db.collection(self.collection_name).document(item_id).update(
                {
                    "pipeline_state": pipeline_state,
                    "updated_at": gcloud_firestore.SERVER_TIMESTAMP,
                }
            )
            logger.debug(f"Updated pipeline state for item {item_id}")

        except Exception as e:
            logger.error(f"Error updating pipeline state for item {item_id}: {e}")
            raise

    def get_pipeline_items(
        self,
        parent_item_id: str,
        sub_task: Optional[JobSubTask] = None,
    ) -> List[JobQueueItem]:
        """
        Get all pipeline items for a parent item.

        Args:
            parent_item_id: Parent item document ID
            sub_task: Optional filter by specific sub-task

        Returns:
            List of pipeline items
        """
        try:
            query = self.db.collection(self.collection_name).where(
                "parent_item_id", "==", parent_item_id
            )

            if sub_task:
                query = query.where("sub_task", "==", sub_task.value)

            docs = query.stream()

            items = []
            for doc in docs:
                data = doc.to_dict()
                item = JobQueueItem.from_firestore(doc.id, data)
                items.append(item)

            return items

        except Exception as e:
            logger.error(f"Error getting pipeline items for parent {parent_item_id}: {e}")
            return []

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
            query = self.db.collection(self.collection_name).where("tracking_id", "==", tracking_id)

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

        # Check 2: Circular dependency - get all URLs in ancestry
        try:
            ancestor_items = self.get_items_by_tracking_id(current_item.tracking_id)
            ancestor_urls = {
                item.url for item in ancestor_items if item.id in current_item.ancestry_chain
            }

            if target_url in ancestor_urls:
                return (
                    False,
                    f"Circular dependency detected: {target_url} already in ancestry chain",
                )
        except Exception as e:
            logger.warning(f"Error checking ancestry chain: {e}")

        # Check 3: Duplicate pending work
        if self.has_pending_work_for_url(target_url, target_type, current_item.tracking_id):
            return (
                False,
                f"Duplicate work: {target_type.value} for {target_url} already queued",
            )

        # Check 4: Already completed successfully
        completed_items = self.get_items_by_tracking_id(
            current_item.tracking_id,
            status_filter=[QueueStatus.SUCCESS],
        )

        for item in completed_items:
            if item.url == target_url and item.type == target_type:
                return (
                    False,
                    f"Already completed: {target_type.value} for {target_url}",
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
