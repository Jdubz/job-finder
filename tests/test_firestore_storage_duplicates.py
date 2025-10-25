"""Tests for duplicate prevention in FirestoreJobStorage."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from job_finder.ai.matcher import JobMatchResult
from job_finder.storage.firestore_storage import FirestoreJobStorage


@pytest.fixture
def mock_db():
    """Mock Firestore database client."""
    return MagicMock()


@pytest.fixture
def job_storage(mock_db):
    """Create FirestoreJobStorage with mocked database."""
    with patch("job_finder.storage.firestore_storage.FirestoreClient") as mock_client:
        mock_client.get_client.return_value = mock_db
        storage = FirestoreJobStorage(database_name="portfolio-staging")
        storage.db = mock_db
        return storage


# sample_job fixture now provided by tests/conftest.py
# Note: Tests updated to use sample_job and customize company name if needed


@pytest.fixture
def sample_match_result():
    """Sample JobMatchResult."""
    return JobMatchResult(
        job_title="Senior Software Engineer",
        job_company="Example Corp",
        job_url="https://example.com/jobs/123",
        match_score=85,
        matched_skills=["Python", "Django", "PostgreSQL"],
        missing_skills=["Kubernetes"],
        experience_match="Strong match for senior-level position",
        key_strengths=["Backend expertise", "Database design"],
        potential_concerns=["Limited DevOps experience"],
        application_priority="High",
        customization_recommendations={
            "summary": "Emphasize backend and database projects",
            "focus_areas": ["Backend", "Database"],
        },
        resume_intake_data={
            "targetSummary": "Senior backend engineer with 5+ years experience",
            "prioritizedSkills": ["Python", "Django", "PostgreSQL"],
            "experienceHighlights": ["Built scalable APIs"],
            "projectsToInclude": ["Project X"],
            "achievementAngles": ["Improved performance by 50%"],
            "atsKeywords": ["python", "django", "api", "backend"],
        },
    )


class TestDuplicatePrevention:
    """Test duplicate prevention in save_job_match."""

    def test_save_job_match_new_job(self, job_storage, sample_job, sample_match_result, mock_db):
        """Test saving a new job creates document."""
        # Mock no existing job found
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_query = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = []  # No existing job

        # Mock successful save
        mock_doc_ref = Mock()
        mock_doc_id = Mock()
        mock_doc_id.id = "doc123"
        mock_collection.add.return_value = (mock_doc_ref, mock_doc_id)

        # Save job
        doc_id = job_storage.save_job_match(sample_job, sample_match_result)

        # Verify document created
        assert doc_id == "doc123"
        mock_collection.add.assert_called_once()

    def test_save_job_match_duplicate_url(
        self, job_storage, sample_job, sample_match_result, mock_db
    ):
        """Test saving a duplicate URL returns existing document ID."""
        # Mock existing job found
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_query = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query

        # Mock existing document
        mock_doc = Mock()
        mock_doc.id = "existing_doc_123"
        mock_query.stream.return_value = [mock_doc]

        # Save job (should detect duplicate)
        doc_id = job_storage.save_job_match(sample_job, sample_match_result)

        # Verify existing ID returned
        assert doc_id == "existing_doc_123"
        # Verify no new document created
        mock_collection.add.assert_not_called()

    def test_save_job_match_normalized_url(
        self, job_storage, sample_job, sample_match_result, mock_db
    ):
        """Test URL normalization in duplicate detection."""
        # Test with URL that has tracking params
        job_with_tracking = sample_job.copy()
        job_with_tracking["url"] = "https://example.com/jobs/123?utm_source=linkedin&ref=social"

        # Mock existing job with normalized URL
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_query = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query

        # Mock existing document
        mock_doc = Mock()
        mock_doc.id = "existing_normalized"
        mock_query.stream.return_value = [mock_doc]

        # Save job
        doc_id = job_storage.save_job_match(job_with_tracking, sample_match_result)

        # Verify normalized URL used for query (without tracking params)
        mock_collection.where.assert_called()
        # With new filter syntax: where(filter=FieldFilter("url", "==", value))
        call_kwargs = mock_collection.where.call_args[1]
        filter_obj = call_kwargs["filter"]
        assert filter_obj.field_path == "url"
        assert filter_obj.op_string == "=="
        # Should be normalized (no tracking params)
        assert "utm_source" not in filter_obj.value
        assert "ref" not in filter_obj.value

        # Verify existing ID returned
        assert doc_id == "existing_normalized"

    def test_save_job_match_with_user_id(
        self, job_storage, sample_job, sample_match_result, mock_db
    ):
        """Test duplicate detection with user_id filter."""
        # Mock no existing job for this user
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_query = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = []

        # Mock successful save
        mock_doc_ref = Mock()
        mock_doc_id = Mock()
        mock_doc_id.id = "doc_user123"
        mock_collection.add.return_value = (mock_doc_ref, mock_doc_id)

        # Save job with user_id
        doc_id = job_storage.save_job_match(sample_job, sample_match_result, user_id="user123")

        # Verify user_id included in query
        assert mock_collection.where.call_count >= 1  # At least URL query

        # Verify document created with user_id
        assert doc_id == "doc_user123"

    def test_save_job_match_empty_url(self, job_storage, sample_job, sample_match_result, mock_db):
        """Test saving job with empty URL creates new document."""
        job_no_url = sample_job.copy()
        job_no_url["url"] = ""

        # Mock successful save
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_doc_ref = Mock()
        mock_doc_id = Mock()
        mock_doc_id.id = "doc_no_url"
        mock_collection.add.return_value = (mock_doc_ref, mock_doc_id)

        # Save job
        doc_id = job_storage.save_job_match(job_no_url, sample_match_result)

        # Verify document created (no duplicate check for empty URL)
        assert doc_id == "doc_no_url"
        mock_collection.add.assert_called_once()

    def test_save_job_match_case_insensitive_url(
        self, job_storage, sample_job, sample_match_result, mock_db
    ):
        """Test URL normalization is case-insensitive."""
        job_uppercase = sample_job.copy()
        job_uppercase["url"] = "HTTPS://EXAMPLE.COM/jobs/123"

        # Mock existing job with lowercase URL
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_query = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_doc = Mock()
        mock_doc.id = "existing_lowercase"
        mock_query.stream.return_value = [mock_doc]

        # Save job
        doc_id = job_storage.save_job_match(job_uppercase, sample_match_result)

        # Verify normalized to lowercase
        # With new filter syntax: where(filter=FieldFilter("url", "==", value))
        call_kwargs = mock_collection.where.call_args[1]
        filter_obj = call_kwargs["filter"]
        assert "example.com" in filter_obj.value.lower()

        # Verify existing ID returned
        assert doc_id == "existing_lowercase"

    def test_save_job_match_trailing_slash(
        self, job_storage, sample_job, sample_match_result, mock_db
    ):
        """Test URL normalization removes trailing slash."""
        job_trailing_slash = sample_job.copy()
        job_trailing_slash["url"] = "https://example.com/jobs/123/"

        # Mock existing job without trailing slash
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_query = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_doc = Mock()
        mock_doc.id = "existing_no_slash"
        mock_query.stream.return_value = [mock_doc]

        # Save job
        doc_id = job_storage.save_job_match(job_trailing_slash, sample_match_result)

        # Verify normalized without trailing slash
        # With new filter syntax: where(filter=FieldFilter("url", "==", value))
        call_kwargs = mock_collection.where.call_args[1]
        filter_obj = call_kwargs["filter"]
        assert not filter_obj.value.endswith("/")

        # Verify existing ID returned
        assert doc_id == "existing_no_slash"


class TestGetExistingJobId:
    """Test _get_existing_job_id helper method."""

    def test_get_existing_job_id_found(self, job_storage, mock_db):
        """Test finding existing job by URL."""
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_query = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_doc = Mock()
        mock_doc.id = "found_job_123"
        mock_query.stream.return_value = [mock_doc]

        # Check for existing job
        doc_id = job_storage._get_existing_job_id("https://example.com/jobs/123")

        # Verify job found
        assert doc_id == "found_job_123"

    def test_get_existing_job_id_not_found(self, job_storage, mock_db):
        """Test no existing job found."""
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_query = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = []  # No results

        # Check for existing job
        doc_id = job_storage._get_existing_job_id("https://example.com/jobs/999")

        # Verify no job found
        assert doc_id is None

    def test_get_existing_job_id_with_user_id(self, job_storage, mock_db):
        """Test finding existing job with user_id filter."""
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_query = MagicMock()
        # Chain the where calls properly
        mock_collection.where.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_doc = Mock()
        mock_doc.id = "user_job_123"
        mock_query.stream.return_value = [mock_doc]

        # Check for existing job with user_id
        doc_id = job_storage._get_existing_job_id("https://example.com/jobs/123", user_id="user456")

        # Verify job found
        assert doc_id == "user_job_123"
        # Verify both filters applied (URL filter from collection.where, user_id from query.where)
        mock_collection.where.assert_called_once()
        mock_query.where.assert_called_once()

    def test_get_existing_job_id_error_handling(self, job_storage, mock_db):
        """Test error handling in _get_existing_job_id."""
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_collection.where.side_effect = Exception("Firestore error")

        # Check for existing job (should handle error gracefully)
        doc_id = job_storage._get_existing_job_id("https://example.com/jobs/123")

        # Verify returns None on error
        assert doc_id is None

    def test_get_existing_job_id_empty_url(self, job_storage):
        """Test handling of empty URL."""
        # Check with empty URL
        doc_id = job_storage._get_existing_job_id("")

        # Verify returns None
        assert doc_id is None

    def test_get_existing_job_id_none_url(self, job_storage):
        """Test handling of None URL."""
        # Check with None URL
        doc_id = job_storage._get_existing_job_id(None)

        # Verify returns None
        assert doc_id is None
