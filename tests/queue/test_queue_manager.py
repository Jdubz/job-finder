"""Tests for queue manager."""

from unittest.mock import MagicMock, patch

import pytest

from job_finder.job_queue.manager import QueueManager
from job_finder.job_queue.models import JobQueueItem, QueueItemType, QueueStatus


@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client."""
    with patch("job_finder.job_queue.manager.FirestoreClient") as mock_client:
        yield mock_client


@pytest.fixture
def queue_manager(mock_firestore_client):
    """Create queue manager with mocked Firestore."""
    mock_db = MagicMock()
    mock_firestore_client.get_client.return_value = mock_db
    manager = QueueManager(database_name="test-db")
    return manager


def test_add_item(queue_manager):
    """Test adding item to queue."""
    # Create test item
    item = JobQueueItem(
        type=QueueItemType.JOB,
        url="https://example.com/job/123",
        company_name="Test Company",
        source="scraper",
    )

    # Mock Firestore add operation
    mock_doc_ref = (None, MagicMock(id="test-doc-id"))
    queue_manager.db.collection.return_value.add.return_value = mock_doc_ref

    # Add item
    doc_id = queue_manager.add_item(item)

    # Assertions
    assert doc_id == "test-doc-id"
    queue_manager.db.collection.assert_called_with("job-queue")


def test_has_pending_scrape_returns_true_when_exists(queue_manager):
    """Test has_pending_scrape returns True when pending SCRAPE exists."""
    # Mock query that returns a document
    mock_doc = MagicMock()
    queue_manager.db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = [
        mock_doc
    ]

    result = queue_manager.has_pending_scrape()

    assert result is True
    # Verify correct query was made
    queue_manager.db.collection.assert_called_with("job-queue")


def test_has_pending_scrape_returns_false_when_none(queue_manager):
    """Test has_pending_scrape returns False when no pending SCRAPE."""
    # Mock query that returns empty list
    queue_manager.db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = (
        []
    )

    result = queue_manager.has_pending_scrape()

    assert result is False


def test_has_pending_scrape_handles_errors(queue_manager):
    """Test has_pending_scrape handles errors gracefully."""
    # Mock query that raises exception
    queue_manager.db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.side_effect = Exception(
        "Firestore error"
    )

    result = queue_manager.has_pending_scrape()

    # Should return False on error (safe default)
    assert result is False


def test_get_pending_items(queue_manager):
    """Test getting pending items."""
    # Mock Firestore query
    mock_doc1 = MagicMock()
    mock_doc1.id = "doc-1"
    mock_doc1.to_dict.return_value = {
        "type": "job",
        "status": "pending",
        "url": "https://example.com/job/1",
        "company_name": "Company 1",
        "source": "scraper",
        "retry_count": 0,
        "max_retries": 3,
    }

    mock_doc2 = MagicMock()
    mock_doc2.id = "doc-2"
    mock_doc2.to_dict.return_value = {
        "type": "job",
        "status": "pending",
        "url": "https://example.com/job/2",
        "company_name": "Company 2",
        "source": "scraper",
        "retry_count": 0,
        "max_retries": 3,
    }

    mock_query = MagicMock()
    mock_query.stream.return_value = [mock_doc1, mock_doc2]

    limit_mock = (
        queue_manager.db.collection.return_value.where.return_value.order_by.return_value.limit
    )
    limit_mock.return_value = mock_query

    # Get pending items
    items = queue_manager.get_pending_items(limit=10)

    # Assertions
    assert len(items) == 2
    assert all(isinstance(item, JobQueueItem) for item in items)
    assert items[0].id == "doc-1"
    assert items[1].id == "doc-2"


def test_update_status(queue_manager):
    """Test updating item status."""
    # Mock Firestore update operation
    mock_doc = MagicMock()
    queue_manager.db.collection.return_value.document.return_value = mock_doc

    # Update status
    queue_manager.update_status(
        "test-doc-id", QueueStatus.SUCCESS, result_message="Job matched successfully"
    )

    # Assertions
    queue_manager.db.collection.assert_called_with("job-queue")
    queue_manager.db.collection.return_value.document.assert_called_with("test-doc-id")
    mock_doc.update.assert_called_once()

    # Check update data
    call_args = mock_doc.update.call_args[0][0]
    assert call_args["status"] == "success"
    assert call_args["result_message"] == "Job matched successfully"
    assert "completed_at" in call_args


def test_url_exists_in_queue(queue_manager):
    """Test checking if URL exists in queue."""
    # Mock Firestore query for existing URL
    mock_doc = MagicMock()
    mock_query = MagicMock()
    mock_query.stream.return_value = [mock_doc]
    queue_manager.db.collection.return_value.where.return_value.limit.return_value = mock_query

    # Check existing URL
    exists = queue_manager.url_exists_in_queue("https://example.com/job/123")

    assert exists is True

    # Mock Firestore query for non-existing URL
    mock_query.stream.return_value = []

    # Check non-existing URL
    exists = queue_manager.url_exists_in_queue("https://example.com/job/999")

    assert exists is False


def test_retry_item_success(queue_manager):
    """Test successfully retrying a failed item."""
    # Mock get_item to return a failed item
    failed_item = JobQueueItem(
        id="test-doc-id",
        type=QueueItemType.JOB,
        url="https://example.com/job/123",
        company_name="Test Company",
        source="scraper",
        status=QueueStatus.FAILED,
    )

    with patch.object(queue_manager, "get_item", return_value=failed_item):
        mock_doc = MagicMock()
        queue_manager.db.collection.return_value.document.return_value = mock_doc

        # Retry the item
        result = queue_manager.retry_item("test-doc-id")

        # Assertions
        assert result is True
        queue_manager.db.collection.assert_called_with("job-queue")
        queue_manager.db.collection.return_value.document.assert_called_with("test-doc-id")
        mock_doc.update.assert_called_once()

        # Check update data
        call_args = mock_doc.update.call_args[0][0]
        assert call_args["status"] == "pending"
        assert "updated_at" in call_args
        # Verify fields are deleted
        from google.cloud import firestore as gcloud_firestore

        assert call_args["processed_at"] == gcloud_firestore.DELETE_FIELD
        assert call_args["completed_at"] == gcloud_firestore.DELETE_FIELD
        assert call_args["error_details"] == gcloud_firestore.DELETE_FIELD


def test_retry_item_not_found(queue_manager):
    """Test retrying an item that doesn't exist."""
    # Mock get_item to return None
    with patch.object(queue_manager, "get_item", return_value=None):
        result = queue_manager.retry_item("nonexistent-id")

        # Should return False when item not found
        assert result is False


def test_retry_item_not_failed(queue_manager):
    """Test retrying an item that is not in failed status."""
    # Mock get_item to return a pending item
    pending_item = JobQueueItem(
        id="test-doc-id",
        type=QueueItemType.JOB,
        url="https://example.com/job/123",
        company_name="Test Company",
        source="scraper",
        status=QueueStatus.PENDING,
    )

    with patch.object(queue_manager, "get_item", return_value=pending_item):
        result = queue_manager.retry_item("test-doc-id")

        # Should return False when item is not failed
        assert result is False


def test_retry_item_exception(queue_manager):
    """Test retry_item handles exceptions gracefully."""
    # Mock get_item to return a failed item
    failed_item = JobQueueItem(
        id="test-doc-id",
        type=QueueItemType.JOB,
        url="https://example.com/job/123",
        company_name="Test Company",
        source="scraper",
        status=QueueStatus.FAILED,
    )

    with patch.object(queue_manager, "get_item", return_value=failed_item):
        # Mock update to raise exception
        mock_doc = MagicMock()
        mock_doc.update.side_effect = Exception("Firestore error")
        queue_manager.db.collection.return_value.document.return_value = mock_doc

        result = queue_manager.retry_item("test-doc-id")

        # Should return False on exception
        assert result is False


def test_delete_item_success(queue_manager):
    """Test successfully deleting an item."""
    # Mock get_item to return an item
    item = JobQueueItem(
        id="test-doc-id",
        type=QueueItemType.JOB,
        url="https://example.com/job/123",
        company_name="Test Company",
        source="scraper",
        status=QueueStatus.SUCCESS,
    )

    with patch.object(queue_manager, "get_item", return_value=item):
        mock_doc = MagicMock()
        queue_manager.db.collection.return_value.document.return_value = mock_doc

        # Delete the item
        result = queue_manager.delete_item("test-doc-id")

        # Assertions
        assert result is True
        queue_manager.db.collection.assert_called_with("job-queue")
        queue_manager.db.collection.return_value.document.assert_called_with("test-doc-id")
        mock_doc.delete.assert_called_once()


def test_delete_item_not_found(queue_manager):
    """Test deleting an item that doesn't exist."""
    # Mock get_item to return None
    with patch.object(queue_manager, "get_item", return_value=None):
        result = queue_manager.delete_item("nonexistent-id")

        # Should return False when item not found
        assert result is False


def test_delete_item_exception(queue_manager):
    """Test delete_item handles exceptions gracefully."""
    # Mock get_item to return an item
    item = JobQueueItem(
        id="test-doc-id",
        type=QueueItemType.JOB,
        url="https://example.com/job/123",
        company_name="Test Company",
        source="scraper",
        status=QueueStatus.FAILED,
    )

    with patch.object(queue_manager, "get_item", return_value=item):
        # Mock delete to raise exception
        mock_doc = MagicMock()
        mock_doc.delete.side_effect = Exception("Firestore error")
        queue_manager.db.collection.return_value.document.return_value = mock_doc

        result = queue_manager.delete_item("test-doc-id")

        # Should return False on exception
        assert result is False
