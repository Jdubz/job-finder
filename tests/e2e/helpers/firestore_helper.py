"""Firestore operations helper for E2E tests."""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class FirestoreHelper:
    """Helper for Firestore operations in E2E tests."""

    def __init__(self, db_client, database_name: str = "portfolio-staging"):
        """
        Initialize Firestore helper.

        Args:
            db_client: Firestore client instance
            database_name: Database name
        """
        self.db = db_client
        self.db_name = database_name

    def create_queue_item(
        self,
        url: str,
        company_name: str = "Test Company",
        source: str = "automated_scan",
        **kwargs,
    ) -> str:
        """
        Create a queue item for testing.

        Args:
            url: Job URL
            company_name: Company name
            source: Source of submission (must be valid QueueSource value)
            **kwargs: Additional queue item fields

        Returns:
            Document ID of created item
        """
        import uuid

        data = {
            "type": "job",
            # NOTE: No sub_task field - using decision tree routing
            "url": url,
            "company_name": company_name,
            "source": source,
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            # Loop prevention fields
            "tracking_id": str(uuid.uuid4()),
            "ancestry_chain": [],
            "spawn_depth": 0,
            "max_spawn_depth": 10,
            **kwargs,
        }

        logger.debug(f"Creating queue item: {url}")
        doc_ref = self.db.collection("job-queue").add(data)
        doc_id = doc_ref[1].id

        logger.info(f"Created queue item: {doc_id}")
        return doc_id

    def get_document(
        self,
        collection: str,
        doc_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get document by ID.

        Args:
            collection: Collection name
            doc_id: Document ID

        Returns:
            Document data or None if not found
        """
        doc_ref = self.db.collection(collection).document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            logger.warning(f"Document not found: {collection}/{doc_id}")
            return None

        return doc.to_dict()

    def update_document(
        self,
        collection: str,
        doc_id: str,
        data: Dict[str, Any],
    ):
        """
        Update document fields.

        Args:
            collection: Collection name
            doc_id: Document ID
            data: Fields to update
        """
        doc_ref = self.db.collection(collection).document(doc_id)
        doc_ref.update(data)
        logger.debug(f"Updated {collection}/{doc_id}")

    def delete_document(
        self,
        collection: str,
        doc_id: str,
    ):
        """
        Delete document.

        Args:
            collection: Collection name
            doc_id: Document ID
        """
        doc_ref = self.db.collection(collection).document(doc_id)
        doc_ref.delete()
        logger.debug(f"Deleted {collection}/{doc_id}")

    def query_documents(
        self,
        collection: str,
        filters: Optional[List[tuple]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query documents with filters.

        Args:
            collection: Collection name
            filters: List of (field, operator, value) tuples
            order_by: Field to order by
            limit: Maximum results

        Returns:
            List of document data
        """
        query = self.db.collection(collection)

        if filters:
            for field, operator, value in filters:
                query = query.where(field, operator, value)

        if order_by:
            query = query.order_by(order_by)

        if limit:
            query = query.limit(limit)

        docs = query.stream()
        results = [doc.to_dict() for doc in docs]

        logger.debug(f"Query {collection} returned {len(results)} documents")
        return results

    def get_job_match(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job match by ID.

        Args:
            job_id: Job match document ID

        Returns:
            Job match data or None
        """
        return self.get_document("job-matches", job_id)

    def get_recent_matches(
        self,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get recent job matches.

        Args:
            limit: Maximum results

        Returns:
            List of recent matches
        """
        return self.query_documents(
            "job-matches",
            order_by="created_at",
            limit=limit,
        )

    def find_match_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Find job match by URL.

        Args:
            url: Job URL

        Returns:
            Job match data or None
        """
        results = self.query_documents(
            "job-matches",
            filters=[("url", "==", url)],
            limit=1,
        )

        return results[0] if results else None

    def get_queue_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get queue item by ID.

        Args:
            item_id: Queue item document ID

        Returns:
            Queue item data or None
        """
        return self.get_document("job-queue", item_id)

    def get_pending_queue_items(
        self,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get pending queue items.

        Args:
            limit: Maximum results

        Returns:
            List of pending items
        """
        return self.query_documents(
            "job-queue",
            filters=[("status", "==", "pending")],
            order_by="created_at",
            limit=limit,
        )

    def get_failed_queue_items(
        self,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get failed queue items.

        Args:
            limit: Maximum results

        Returns:
            List of failed items
        """
        return self.query_documents(
            "job-queue",
            filters=[("status", "==", "failed")],
            order_by="created_at",
            limit=limit,
        )

    def count_documents(
        self,
        collection: str,
        filters: Optional[List[tuple]] = None,
    ) -> int:
        """
        Count documents matching filters.

        Args:
            collection: Collection name
            filters: List of (field, operator, value) tuples

        Returns:
            Document count
        """
        docs = self.query_documents(collection, filters=filters)
        return len(docs)

    def batch_delete(
        self,
        collection: str,
        doc_ids: List[str],
    ):
        """
        Delete multiple documents in batch.

        Args:
            collection: Collection name
            doc_ids: List of document IDs to delete
        """
        logger.info(f"Batch deleting {len(doc_ids)} documents from {collection}")

        batch = self.db.batch()
        for doc_id in doc_ids:
            doc_ref = self.db.collection(collection).document(doc_id)
            batch.delete(doc_ref)

        batch.commit()
        logger.info(f"Batch delete complete")

    def create_test_match(
        self,
        url: str,
        title: str = "Test Job",
        company_name: str = "Test Company",
        match_score: int = 85,
        **kwargs,
    ) -> str:
        """
        Create a test job match.

        Args:
            url: Job URL
            title: Job title
            company_name: Company name
            match_score: Match score (0-100)
            **kwargs: Additional match fields

        Returns:
            Document ID of created match
        """
        data = {
            "url": url,
            "title": title,
            "company_name": company_name,
            "match_score": match_score,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            **kwargs,
        }

        logger.debug(f"Creating test match: {title} at {company_name}")
        doc_ref = self.db.collection("job-matches").add(data)
        doc_id = doc_ref[1].id

        logger.info(f"Created test match: {doc_id}")
        return doc_id

    def verify_document_exists(
        self,
        collection: str,
        doc_id: str,
    ) -> bool:
        """
        Verify document exists.

        Args:
            collection: Collection name
            doc_id: Document ID

        Returns:
            True if exists
        """
        doc = self.get_document(collection, doc_id)
        return doc is not None

    def verify_field_value(
        self,
        collection: str,
        doc_id: str,
        field: str,
        expected_value: Any,
    ) -> bool:
        """
        Verify document field has expected value.

        Args:
            collection: Collection name
            doc_id: Document ID
            field: Field name (supports dot notation)
            expected_value: Expected value

        Returns:
            True if value matches
        """
        doc = self.get_document(collection, doc_id)
        if not doc:
            return False

        # Support nested fields with dot notation
        value = doc
        for key in field.split("."):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return False

        matches = value == expected_value
        if not matches:
            logger.warning(f"Field mismatch: {field} = {value} (expected {expected_value})")

        return matches
