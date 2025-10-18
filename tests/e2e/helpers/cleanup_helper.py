"""Cleanup helper for E2E tests."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class CleanupHelper:
    """Helper for cleaning up test data."""

    def __init__(self, db_client, database_name: str = "portfolio-staging"):
        """
        Initialize cleanup helper.

        Args:
            db_client: Firestore client instance
            database_name: Database name
        """
        self.db = db_client
        self.db_name = database_name

    def cleanup_test_queue_items(
        self,
        source_filter: str = "e2e_test",
        max_age_hours: int = 24,
    ) -> int:
        """
        Clean up test queue items.

        Args:
            source_filter: Source value to filter by
            max_age_hours: Delete items older than this many hours

        Returns:
            Number of items deleted
        """
        logger.info(
            f"Cleaning up queue items with source='{source_filter}' "
            f"older than {max_age_hours} hours"
        )

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        # Query test items - filter by source only to avoid composite index requirement
        query = self.db.collection("job-queue").where("source", "==", source_filter)

        docs = query.stream()
        # Filter by created_at in memory to avoid needing composite index
        doc_ids = [
            doc.id
            for doc in docs
            if doc.to_dict().get("created_at") and doc.to_dict()["created_at"] < cutoff_time
        ]

        if not doc_ids:
            logger.info("No queue items to clean up")
            return 0

        # Batch delete
        logger.info(f"Deleting {len(doc_ids)} queue items...")
        self._batch_delete("job-queue", doc_ids)

        return len(doc_ids)

    def cleanup_test_matches(
        self,
        company_name_filter: str = "Test Company",
        max_age_hours: int = 24,
    ) -> int:
        """
        Clean up test job matches.

        Args:
            company_name_filter: Company name to filter by
            max_age_hours: Delete items older than this many hours

        Returns:
            Number of matches deleted
        """
        logger.info(
            f"Cleaning up matches with company='{company_name_filter}' "
            f"older than {max_age_hours} hours"
        )

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        # Query test matches - filter by company_name only to avoid composite index
        query = self.db.collection("job-matches").where("company_name", "==", company_name_filter)

        docs = query.stream()
        # Filter by created_at in memory
        doc_ids = [
            doc.id
            for doc in docs
            if doc.to_dict().get("created_at") and doc.to_dict()["created_at"] < cutoff_time
        ]

        if not doc_ids:
            logger.info("No matches to clean up")
            return 0

        # Batch delete
        logger.info(f"Deleting {len(doc_ids)} matches...")
        self._batch_delete("job-matches", doc_ids)

        return len(doc_ids)

    def cleanup_by_test_run_id(
        self,
        test_run_id: str,
        collections: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """
        Clean up all data for a specific test run.

        Args:
            test_run_id: Test run ID to clean up
            collections: List of collections to clean (default: all test collections)

        Returns:
            Dictionary of collection -> count deleted
        """
        if collections is None:
            collections = ["job-queue", "job-matches"]

        logger.info(f"Cleaning up test run: {test_run_id}")

        results = {}

        for collection in collections:
            query = self.db.collection(collection).where("test_run_id", "==", test_run_id)

            docs = query.stream()
            doc_ids = [doc.id for doc in docs]

            if doc_ids:
                logger.info(f"Deleting {len(doc_ids)} documents from {collection}...")
                self._batch_delete(collection, doc_ids)

            results[collection] = len(doc_ids)

        total = sum(results.values())
        logger.info(f"Cleaned up {total} total documents for test run {test_run_id}")

        return results

    def cleanup_failed_items(
        self,
        max_age_hours: int = 24,
    ) -> int:
        """
        Clean up failed queue items.

        Args:
            max_age_hours: Delete items older than this many hours

        Returns:
            Number of items deleted
        """
        logger.info(f"Cleaning up failed queue items older than {max_age_hours} hours")

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        # Filter by status only to avoid composite index
        query = self.db.collection("job-queue").where("status", "==", "failed")

        docs = query.stream()
        # Filter by created_at in memory
        doc_ids = [
            doc.id
            for doc in docs
            if doc.to_dict().get("created_at") and doc.to_dict()["created_at"] < cutoff_time
        ]

        if not doc_ids:
            logger.info("No failed items to clean up")
            return 0

        logger.info(f"Deleting {len(doc_ids)} failed items...")
        self._batch_delete("job-queue", doc_ids)

        return len(doc_ids)

    def cleanup_all_test_data(
        self,
        max_age_hours: int = 24,
    ) -> Dict[str, int]:
        """
        Clean up all test data across collections.

        Args:
            max_age_hours: Delete items older than this many hours

        Returns:
            Dictionary of what was cleaned
        """
        logger.info("Running comprehensive test data cleanup...")

        results = {
            "queue_items": self.cleanup_test_queue_items(max_age_hours=max_age_hours),
            "matches": self.cleanup_test_matches(max_age_hours=max_age_hours),
            "failed_items": self.cleanup_failed_items(max_age_hours=max_age_hours),
        }

        total = sum(results.values())
        logger.info(f"Cleanup complete: {total} total items deleted")

        return results

    def delete_specific_documents(
        self,
        items: List[Dict[str, str]],
    ) -> int:
        """
        Delete specific documents by collection and ID.

        Args:
            items: List of dicts with 'collection' and 'id' keys

        Returns:
            Number of documents deleted
        """
        logger.info(f"Deleting {len(items)} specific documents...")

        deleted = 0
        for item in items:
            collection = item.get("collection")
            doc_id = item.get("id")

            if collection and doc_id:
                try:
                    self.db.collection(collection).document(doc_id).delete()
                    deleted += 1
                    logger.debug(f"Deleted {collection}/{doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete {collection}/{doc_id}: {e}")

        logger.info(f"Deleted {deleted} documents")
        return deleted

    def get_cleanup_candidates(
        self,
        collection: str,
        max_age_hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Get documents that would be cleaned up.

        Args:
            collection: Collection name
            max_age_hours: Age threshold

        Returns:
            List of document data
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        query = self.db.collection(collection).where("created_at", "<", cutoff_time)

        docs = query.stream()
        results = []

        for doc in docs:
            data = doc.to_dict()
            data["_id"] = doc.id
            results.append(data)

        logger.info(
            f"Found {len(results)} cleanup candidates in {collection} "
            f"older than {max_age_hours} hours"
        )

        return results

    def _batch_delete(
        self,
        collection: str,
        doc_ids: List[str],
        batch_size: int = 500,
    ):
        """
        Delete documents in batches.

        Args:
            collection: Collection name
            doc_ids: List of document IDs
            batch_size: Maximum batch size (Firestore limit is 500)
        """
        total = len(doc_ids)
        deleted = 0

        for i in range(0, total, batch_size):
            batch = self.db.batch()
            batch_ids = doc_ids[i : i + batch_size]

            for doc_id in batch_ids:
                doc_ref = self.db.collection(collection).document(doc_id)
                batch.delete(doc_ref)

            batch.commit()
            deleted += len(batch_ids)

            logger.debug(f"Deleted batch {i // batch_size + 1}: " f"{deleted}/{total} documents")

        logger.info(f"Batch delete complete: {deleted} documents from {collection}")
