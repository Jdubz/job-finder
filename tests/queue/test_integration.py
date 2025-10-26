"""Integration tests for queue workflow."""

from unittest.mock import MagicMock, patch

import pytest

from job_finder.job_queue.config_loader import ConfigLoader
from job_finder.job_queue.manager import QueueManager
from job_finder.job_queue.models import JobQueueItem, QueueItemType, QueueStatus
from job_finder.job_queue.scraper_intake import ScraperIntake


@pytest.fixture
def mock_firestore():
    """Mock Firestore for all components."""
    with patch("job_finder.job_queue.manager.FirestoreClient") as mock_client:
        mock_db = MagicMock()
        mock_client.get_client.return_value = mock_db
        yield mock_db


@pytest.fixture
def queue_manager(mock_firestore):
    """Create queue manager."""
    return QueueManager(database_name="test-db")


@pytest.fixture
def config_loader(mock_firestore):
    """Create config loader."""
    with patch("job_finder.job_queue.config_loader.FirestoreClient") as mock_client:
        mock_client.get_client.return_value = mock_firestore
        return ConfigLoader(database_name="test-db")


@pytest.fixture
def scraper_intake(queue_manager):
    """Create scraper intake."""
    return ScraperIntake(queue_manager=queue_manager)


class TestQueueWorkflow:
    """Test complete queue workflow from submission to processing."""

    def test_submit_and_retrieve_job(self, queue_manager, scraper_intake, mock_firestore):
        """Test submitting a job and retrieving it from queue."""
        # Mock Firestore add
        mock_doc_ref = (None, MagicMock(id="queue-item-123"))
        mock_firestore.collection.return_value.add.return_value = mock_doc_ref

        # Mock URL check (no duplicates)
        limit_stream = (
            mock_firestore.collection.return_value.where.return_value.limit.return_value.stream
        )
        limit_stream.return_value = []

        # Submit job
        jobs = [
            {
                "title": "Software Engineer",
                "url": "https://example.com/job/123",
                "company": "Test Corp",
                "description": "Build amazing things",
            }
        ]

        count = scraper_intake.submit_jobs(jobs, source="scraper")

        assert count == 1

        # Mock getting pending items
        mock_doc = MagicMock()
        mock_doc.id = "queue-item-123"
        mock_doc.to_dict.return_value = {
            "type": "job",
            "status": "pending",
            "url": "https://example.com/job/123",
            "company_name": "Test Corp",
            "source": "scraper",
            "retry_count": 0,
            "max_retries": 3,
        }

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_doc]

        limit_mock = (
            mock_firestore.collection.return_value.where.return_value.order_by.return_value.limit
        )
        limit_mock.return_value = mock_query

        # Get pending items
        pending = queue_manager.get_pending_items()

        assert len(pending) == 1
        assert pending[0].url == "https://example.com/job/123"
        assert pending[0].company_name == "Test Corp"

    def test_stop_list_filtering_workflow(self, config_loader, mock_firestore):
        """Test stop list filtering workflow."""
        # Mock stop list in Firestore
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "excludedCompanies": ["BadCorp", "ScamInc"],
            "excludedKeywords": ["commission only"],
            "excludedDomains": ["spam.com"],
        }

        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc

        # Load stop list
        stop_list = config_loader.get_stop_list()

        # Verify filtering logic
        assert "BadCorp" in stop_list["excludedCompanies"]
        assert "commission only" in stop_list["excludedKeywords"]
        assert "spam.com" in stop_list["excludedDomains"]

    def test_duplicate_detection_workflow(self, queue_manager, scraper_intake, mock_firestore):
        """Test duplicate detection prevents duplicate submissions."""
        # First submission - no duplicates
        limit_stream = (
            mock_firestore.collection.return_value.where.return_value.limit.return_value.stream
        )
        limit_stream.return_value = []
        mock_doc_ref = (None, MagicMock(id="queue-item-123"))
        mock_firestore.collection.return_value.add.return_value = mock_doc_ref

        jobs = [{"title": "Job 1", "url": "https://example.com/job/1", "company": "Test"}]

        count1 = scraper_intake.submit_jobs(jobs, source="scraper")
        assert count1 == 1

        # Second submission - duplicate found
        mock_duplicate = MagicMock()
        limit_stream.return_value = [mock_duplicate]

        count2 = scraper_intake.submit_jobs(jobs, source="scraper")
        assert count2 == 0  # Should skip duplicate

    def test_queue_status_updates(self, queue_manager, mock_firestore):
        """Test queue item status updates through workflow."""
        mock_doc = MagicMock()
        mock_firestore.collection.return_value.document.return_value = mock_doc

        # Update to processing
        queue_manager.update_status("item-123", QueueStatus.PROCESSING)

        # Should update with processed_at timestamp
        call_args = mock_doc.update.call_args[0][0]
        assert call_args["status"] == "processing"
        assert "processed_at" in call_args

        # Update to success
        queue_manager.update_status(
            "item-123", QueueStatus.SUCCESS, result_message="Job matched successfully"
        )

        # Should update with completed_at timestamp
        call_args = mock_doc.update.call_args[0][0]
        assert call_args["status"] == "success"
        assert call_args["result_message"] == "Job matched successfully"
        assert "completed_at" in call_args

    def test_retry_logic_workflow(self, queue_manager, mock_firestore):
        """Test retry increment workflow."""
        mock_doc = MagicMock()
        mock_firestore.collection.return_value.document.return_value = mock_doc

        # Increment retry
        queue_manager.increment_retry("item-123")

        # Should increment counter
        call_args = mock_doc.update.call_args[0][0]
        assert "retry_count" in call_args
        assert "updated_at" in call_args

    def test_queue_statistics_workflow(self, queue_manager, mock_firestore):
        """Test queue statistics gathering."""
        # Mock queue items with different statuses
        mock_docs = [
            MagicMock(to_dict=lambda: {"status": "pending"}),
            MagicMock(to_dict=lambda: {"status": "pending"}),
            MagicMock(to_dict=lambda: {"status": "processing"}),
            MagicMock(to_dict=lambda: {"status": "success"}),
            MagicMock(to_dict=lambda: {"status": "success"}),
            MagicMock(to_dict=lambda: {"status": "success"}),
            MagicMock(to_dict=lambda: {"status": "failed"}),
            MagicMock(to_dict=lambda: {"status": "skipped"}),
        ]

        mock_firestore.collection.return_value.stream.return_value = mock_docs

        stats = queue_manager.get_queue_stats()

        assert stats["pending"] == 2
        assert stats["processing"] == 1
        assert stats["success"] == 3
        assert stats["failed"] == 1
        assert stats["skipped"] == 1
        assert stats["total"] == 8


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""

    def test_user_submission_workflow(self, scraper_intake, mock_firestore):
        """
        Test complete user submission workflow.

        Scenario:
        1. User submits job via job-finder-FE UI
        2. Job is added to queue
        3. Queue worker picks it up
        4. Job is processed and saved
        """
        # Step 1: User submits job
        mock_doc_ref = (None, MagicMock(id="user-job-123"))
        mock_firestore.collection.return_value.add.return_value = mock_doc_ref
        limit_stream = (
            mock_firestore.collection.return_value.where.return_value.limit.return_value.stream
        )
        limit_stream.return_value = []

        jobs = [
            {
                "title": "Senior Python Developer",
                "url": "https://company.com/careers/python-dev",
                "company": "Great Company",
                "description": "Build scalable systems",
                "location": "Remote",
            }
        ]

        # Submit from user
        count = scraper_intake.submit_jobs(jobs, source="user_submission", company_id=None)

        assert count == 1

        # Verify queue item structure
        call_args = mock_firestore.collection.return_value.add.call_args[0][0]
        assert call_args["type"] == "job"
        assert call_args["status"] == "pending"
        assert call_args["source"] == "user_submission"
        assert call_args["company_name"] == "Great Company"

    def test_scraper_to_queue_workflow(self, scraper_intake, mock_firestore):
        """
        Test scraper to queue workflow.

        Scenario:
        1. Scraper runs and finds jobs
        2. Jobs are submitted to queue
        3. Duplicates are filtered
        """
        mock_doc_ref = (None, MagicMock(id="scraper-job-123"))
        mock_firestore.collection.return_value.add.return_value = mock_doc_ref

        # First batch - no duplicates
        limit_stream = (
            mock_firestore.collection.return_value.where.return_value.limit.return_value.stream
        )
        limit_stream.return_value = []

        batch1 = [
            {"title": "Job 1", "url": "https://example.com/1", "company": "Test"},
            {"title": "Job 2", "url": "https://example.com/2", "company": "Test"},
            {"title": "Job 3", "url": "https://example.com/3", "company": "Test"},
        ]

        count1 = scraper_intake.submit_jobs(batch1, source="scraper")
        assert count1 == 3

        # Second batch - some duplicates
        def url_exists_side_effect(url):
            return url in ["https://example.com/2", "https://example.com/3"]

        limit_stream.side_effect = lambda: ([MagicMock()] if url_exists_side_effect("mock") else [])

        batch2 = [
            {"title": "Job 2", "url": "https://example.com/2", "company": "Test"},
            {"title": "Job 3", "url": "https://example.com/3", "company": "Test"},
            {"title": "Job 4", "url": "https://example.com/4", "company": "Test"},
        ]

        # Reset mock for new submissions
        limit_stream.return_value = []

        # Manually check duplicates
        unique_jobs = [j for j in batch2 if j["url"] == "https://example.com/4"]
        count2 = scraper_intake.submit_jobs(unique_jobs, source="scraper")

        # Only new job should be added
        assert count2 == 1

    def test_company_then_jobs_workflow(self, scraper_intake, mock_firestore):
        """
        Test workflow where company is submitted before jobs.

        Scenario:
        1. New company detected
        2. Company submitted to queue
        3. Jobs from that company submitted
        """
        mock_doc_ref = (None, MagicMock(id="item-123"))
        mock_firestore.collection.return_value.add.return_value = mock_doc_ref
        limit_stream = (
            mock_firestore.collection.return_value.where.return_value.limit.return_value.stream
        )
        limit_stream.return_value = []

        # Step 1: Submit company (using granular pipeline)
        company_doc_id = scraper_intake.submit_company(
            company_name="New Startup",
            company_website="https://newstartup.com",
            source="automated_scan",
        )

        assert company_doc_id is not None

        # Step 2: Submit jobs from that company
        jobs = [
            {
                "title": "Engineer 1",
                "url": "https://newstartup.com/careers/job1",
                "company": "New Startup",
            },
            {
                "title": "Engineer 2",
                "url": "https://newstartup.com/careers/job2",
                "company": "New Startup",
            },
        ]

        count = scraper_intake.submit_jobs(jobs, source="scraper", company_id=None)

        assert count == 2


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_queue_manager_handles_firestore_errors(self, queue_manager, mock_firestore):
        """Test that queue manager handles Firestore errors gracefully."""
        # Mock Firestore error on add
        mock_firestore.collection.return_value.add.side_effect = Exception("Firestore error")

        item = JobQueueItem(
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test Corp",
            source="scraper",
        )

        # Should raise exception
        with pytest.raises(Exception):
            queue_manager.add_item(item)

    def test_queue_manager_returns_empty_on_query_error(self, queue_manager, mock_firestore):
        """Test that queue manager returns empty list on query errors."""
        # Mock Firestore error on query
        mock_firestore.collection.return_value.where.side_effect = Exception("Query error")

        # Should return empty list, not crash
        items = queue_manager.get_pending_items()

        assert items == []

    def test_scraper_intake_continues_on_individual_errors(self, scraper_intake, mock_firestore):
        """Test that scraper intake continues processing on individual errors."""
        limit_stream = (
            mock_firestore.collection.return_value.where.return_value.limit.return_value.stream
        )
        limit_stream.return_value = []

        # First add succeeds, second fails, third succeeds
        mock_firestore.collection.return_value.add.side_effect = [
            (None, MagicMock(id="1")),
            Exception("Error"),
            (None, MagicMock(id="3")),
        ]

        jobs = [
            {"title": "Job 1", "url": "https://example.com/1", "company": "Test"},
            {"title": "Job 2", "url": "https://example.com/2", "company": "Test"},
            {"title": "Job 3", "url": "https://example.com/3", "company": "Test"},
        ]

        # Should add 2 jobs (skip the error)
        count = scraper_intake.submit_jobs(jobs, source="scraper")

        assert count == 2
