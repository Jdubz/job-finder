"""Tests for source health tracking."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from job_finder.utils.source_health import CompanyScrapeTracker, SourceHealthTracker


@pytest.fixture
def mock_db():
    """Create a mock Firestore client."""
    return MagicMock()


@pytest.fixture
def source_health_tracker(mock_db):
    """Create a SourceHealthTracker instance with mock DB."""
    return SourceHealthTracker(mock_db)


@pytest.fixture
def company_scrape_tracker(mock_db):
    """Create a CompanyScrapeTracker instance with mock DB."""
    return CompanyScrapeTracker(mock_db, window_days=30)


class TestSourceHealthTracker:
    """Test SourceHealthTracker functionality."""

    def test_init(self, mock_db):
        """Test tracker initialization."""
        tracker = SourceHealthTracker(mock_db)
        assert tracker.db == mock_db

    def test_update_after_successful_scrape(self, source_health_tracker, mock_db):
        """Test updating health after successful scrape."""
        # Mock source document
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "name": "Test Source",
            "health": {
                "successCount": 5,
                "failureCount": 2,
                "totalJobsFound": 100,
            },
        }

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Call method
        stats = {"jobs_found": 10}
        source_health_tracker.update_after_successful_scrape(
            "source-123", stats, duration_seconds=30.0
        )

        # Verify update was called
        mock_doc_ref.update.assert_called_once()
        update_data = mock_doc_ref.update.call_args[0][0]

        assert update_data["health.successCount"] == 6  # 5 + 1
        assert update_data["health.failureCount"] == 2  # unchanged
        assert update_data["health.totalJobsFound"] == 110  # 100 + 10
        assert update_data["health.lastScrapeDuration"] == 30.0
        assert "health.lastScrapedAt" in update_data
        assert "health.healthScore" in update_data
        assert "health.averageJobsPerScrape" in update_data

    def test_update_after_successful_scrape_empty_health(self, source_health_tracker, mock_db):
        """Test updating health when no previous health data exists."""
        # Mock source document with no health field
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"name": "Test Source"}

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Call method
        stats = {"jobs_found": 5}
        source_health_tracker.update_after_successful_scrape(
            "source-123", stats, duration_seconds=15.0
        )

        # Verify update was called
        mock_doc_ref.update.assert_called_once()
        update_data = mock_doc_ref.update.call_args[0][0]

        assert update_data["health.successCount"] == 1  # first success
        assert update_data["health.failureCount"] == 0
        assert update_data["health.totalJobsFound"] == 5

    def test_update_after_successful_scrape_source_not_found(self, source_health_tracker, mock_db):
        """Test handling when source document doesn't exist."""
        # Mock source document not existing
        mock_doc = Mock()
        mock_doc.exists = False

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Call method
        stats = {"jobs_found": 5}
        source_health_tracker.update_after_successful_scrape(
            "source-123", stats, duration_seconds=15.0
        )

        # Verify update was NOT called
        mock_doc_ref.update.assert_not_called()

    def test_update_after_successful_scrape_none_data(self, source_health_tracker, mock_db):
        """Test handling when source data is None."""
        # Mock source document with None data
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = None

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Call method
        stats = {"jobs_found": 5}
        source_health_tracker.update_after_successful_scrape(
            "source-123", stats, duration_seconds=15.0
        )

        # Verify update was NOT called
        mock_doc_ref.update.assert_not_called()

    def test_update_after_successful_scrape_exception_handling(
        self, source_health_tracker, mock_db
    ):
        """Test exception handling during update."""
        # Mock exception during get
        mock_db.collection.return_value.document.return_value.get.side_effect = Exception(
            "Test error"
        )

        # Call method - should not raise
        stats = {"jobs_found": 5}
        source_health_tracker.update_after_successful_scrape(
            "source-123", stats, duration_seconds=15.0
        )

    def test_health_score_calculation(self, source_health_tracker, mock_db):
        """Test health score calculation."""
        # Mock source with good health
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "name": "Test Source",
            "health": {
                "successCount": 9,
                "failureCount": 1,
                "totalJobsFound": 100,
            },
        }

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Call with fast scrape
        stats = {"jobs_found": 10}
        source_health_tracker.update_after_successful_scrape(
            "source-123", stats, duration_seconds=5.0
        )

        update_data = mock_doc_ref.update.call_args[0][0]
        # Success rate = 10/11 = 0.909
        # Time penalty = 5/60 = 0.083
        # Health = 0.909 * (1 - 0.083*0.2) = 0.909 * 0.983 ≈ 0.894
        assert update_data["health.healthScore"] > 0.85
        assert update_data["health.healthScore"] <= 1.0

    def test_average_jobs_calculation(self, source_health_tracker, mock_db):
        """Test average jobs per scrape calculation."""
        # Mock source with some history
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "name": "Test Source",
            "health": {
                "successCount": 4,
                "failureCount": 1,
                "totalJobsFound": 50,  # 4 successful scrapes with 50 total
            },
        }

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Add 20 more jobs
        stats = {"jobs_found": 20}
        source_health_tracker.update_after_successful_scrape(
            "source-123", stats, duration_seconds=30.0
        )

        update_data = mock_doc_ref.update.call_args[0][0]
        # Average = (50 + 20) / (5 + 1) = 70 / 6 = 11.67
        assert update_data["health.averageJobsPerScrape"] == pytest.approx(11.67, rel=0.01)

    def test_update_after_failed_scrape(self, source_health_tracker, mock_db):
        """Test updating health after failed scrape."""
        # Mock source document
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "name": "Test Source",
            "health": {
                "successCount": 5,
                "failureCount": 2,
                "totalJobsFound": 100,
            },
        }

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Call method
        source_health_tracker.update_after_failed_scrape(
            "source-123", "Connection timeout", duration_seconds=60.0
        )

        # Verify update was called
        mock_doc_ref.update.assert_called_once()
        update_data = mock_doc_ref.update.call_args[0][0]

        assert update_data["health.successCount"] == 5  # unchanged
        assert update_data["health.failureCount"] == 3  # 2 + 1
        assert update_data["health.totalJobsFound"] == 100  # unchanged
        assert update_data["health.lastScrapeDuration"] == 60.0
        assert update_data["health.lastScrapeError"] == "Connection timeout"
        assert "health.healthScore" in update_data

    def test_update_after_failed_scrape_health_score(self, source_health_tracker, mock_db):
        """Test health score calculation after failure."""
        # Mock source with one failure
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "name": "Test Source",
            "health": {
                "successCount": 5,
                "failureCount": 0,
                "totalJobsFound": 100,
            },
        }

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Call method
        source_health_tracker.update_after_failed_scrape(
            "source-123", "Error", duration_seconds=30.0
        )

        update_data = mock_doc_ref.update.call_args[0][0]
        # Success rate = 5/6 = 0.833
        # Health = 0.833 * 0.9 = 0.75
        assert update_data["health.healthScore"] == pytest.approx(0.75, rel=0.01)

    def test_update_after_failed_scrape_source_not_found(self, source_health_tracker, mock_db):
        """Test handling when source document doesn't exist."""
        # Mock source document not existing
        mock_doc = Mock()
        mock_doc.exists = False

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Call method
        source_health_tracker.update_after_failed_scrape(
            "source-123", "Error", duration_seconds=30.0
        )

        # Verify update was NOT called
        mock_doc_ref.update.assert_not_called()

    def test_update_after_failed_scrape_exception_handling(self, source_health_tracker, mock_db):
        """Test exception handling during failure update."""
        # Mock exception during get
        mock_db.collection.return_value.document.return_value.get.side_effect = Exception(
            "Test error"
        )

        # Call method - should not raise
        source_health_tracker.update_after_failed_scrape(
            "source-123", "Error", duration_seconds=30.0
        )


class TestCompanyScrapeTracker:
    """Test CompanyScrapeTracker functionality."""

    def test_init(self, mock_db):
        """Test tracker initialization."""
        tracker = CompanyScrapeTracker(mock_db, window_days=30)
        assert tracker.db == mock_db
        assert tracker.window == timedelta(days=30)

    def test_init_default_window(self, mock_db):
        """Test default window days."""
        tracker = CompanyScrapeTracker(mock_db)
        assert tracker.window == timedelta(days=30)

    def test_get_scrape_frequency(self, company_scrape_tracker, mock_db):
        """Test getting scrape frequency for a company."""
        # Mock query results
        mock_source1 = Mock()
        mock_source2 = Mock()
        mock_source3 = Mock()

        mock_query = Mock()
        mock_query.stream.return_value = [mock_source1, mock_source2, mock_source3]

        mock_where = Mock()
        mock_where.where.return_value = mock_query

        mock_collection = Mock()
        mock_collection.where.return_value = mock_where

        mock_db.collection.return_value = mock_collection

        # Call method
        frequency = company_scrape_tracker.get_scrape_frequency("company-123")

        # Verify frequency calculation
        # 3 scrapes in 30 days = 0.1 scrapes/day
        assert frequency == pytest.approx(0.1, rel=0.01)

    def test_get_scrape_frequency_no_scrapes(self, company_scrape_tracker, mock_db):
        """Test frequency when company has no recent scrapes."""
        # Mock empty query results
        mock_query = Mock()
        mock_query.stream.return_value = []

        mock_where = Mock()
        mock_where.where.return_value = mock_query

        mock_collection = Mock()
        mock_collection.where.return_value = mock_where

        mock_db.collection.return_value = mock_collection

        # Call method
        frequency = company_scrape_tracker.get_scrape_frequency("company-123")

        # Verify frequency is 0
        assert frequency == 0.0

    def test_get_scrape_frequency_exception_handling(self, company_scrape_tracker, mock_db):
        """Test exception handling during frequency calculation."""
        # Mock exception during query
        mock_db.collection.side_effect = Exception("Test error")

        # Call method - should not raise
        frequency = company_scrape_tracker.get_scrape_frequency("company-123")

        # Should return 0 on error
        assert frequency == 0.0

    def test_get_company_scrape_counts(self, company_scrape_tracker, mock_db):
        """Test getting scrape counts for all companies."""
        # Mock company documents
        mock_company1 = Mock()
        mock_company1.id = "company-1"
        mock_company2 = Mock()
        mock_company2.id = "company-2"

        mock_companies_collection = Mock()
        mock_companies_collection.stream.return_value = [mock_company1, mock_company2]

        mock_db.collection.return_value = mock_companies_collection

        # Use patch to intercept get_scrape_frequency
        with patch.object(company_scrape_tracker, "get_scrape_frequency") as mock_freq:
            mock_freq.side_effect = lambda cid: (
                0.067 if cid == "company-1" else 0.033
            )  # 2/30 and 1/30

            # Call method
            counts = company_scrape_tracker.get_company_scrape_counts()

            # Verify results
            assert len(counts) == 2
            assert "company-1" in counts
            assert "company-2" in counts
            assert counts["company-1"] == pytest.approx(0.067, rel=0.01)
            assert counts["company-2"] == pytest.approx(0.033, rel=0.01)

    def test_get_company_scrape_counts_empty(self, company_scrape_tracker, mock_db):
        """Test getting counts when no companies exist."""
        # Mock empty companies collection
        mock_companies_collection = Mock()
        mock_companies_collection.stream.return_value = []

        mock_db.collection.return_value = mock_companies_collection

        # Call method
        counts = company_scrape_tracker.get_company_scrape_counts()

        # Verify empty dict
        assert counts == {}

    def test_get_company_scrape_counts_exception_handling(self, company_scrape_tracker, mock_db):
        """Test exception handling during get all counts."""
        # Mock exception during query
        mock_db.collection.side_effect = Exception("Test error")

        # Call method - should not raise
        counts = company_scrape_tracker.get_company_scrape_counts()

        # Should return empty dict on error
        assert counts == {}
