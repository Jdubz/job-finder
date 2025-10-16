"""Firestore-backed queue manager for job processing."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from google.cloud import firestore as gcloud_firestore

from job_finder.queue.models import JobQueueItem, QueueStatus
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
    ) -> None:
        """
        Update item status and optional message.

        Args:
            item_id: Queue item document ID
            status: New status
            result_message: Optional message describing result
            scraped_data: Optional scraped data to store
        """
        update_data = {
            "status": status.value,
            "updated_at": gcloud_firestore.SERVER_TIMESTAMP,
        }

        if result_message:
            update_data["result_message"] = result_message

        if scraped_data is not None:
            update_data["scraped_data"] = scraped_data

        # Set processed_at when starting processing
        if status == QueueStatus.PROCESSING:
            update_data["processed_at"] = gcloud_firestore.SERVER_TIMESTAMP

        # Set completed_at when finishing (success/failed/skipped)
        if status in [QueueStatus.SUCCESS, QueueStatus.FAILED, QueueStatus.SKIPPED]:
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
