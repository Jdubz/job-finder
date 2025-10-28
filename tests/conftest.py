"""Shared pytest fixtures for all tests."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture(autouse=True)
def set_test_environment(monkeypatch):
    """
    Automatically set ENVIRONMENT variable for all tests.

    This prevents ValueError from being raised when initializing
    StructuredLogger or calling setup_logging() in tests.
    """
    monkeypatch.setenv("ENVIRONMENT", "development")


@pytest.fixture
def sample_job():
    """
    Create a standardized sample job dictionary.

    Returns a job dict with all standard fields for testing.
    Individual tests can override specific fields by updating the returned dict.
    """
    return {
        "title": "Senior Software Engineer",
        "company": "Test Company",
        "company_website": "https://test.com",
        "location": "Remote",
        "description": "We are looking for a senior software engineer...",
        "url": "https://test.com/job/123",
        "posted_date": datetime.now(timezone.utc).isoformat(),
        "company_info": "About the company",
    }


@pytest.fixture
def mock_profile():
    """
    Create a standardized mock profile.

    Returns a Mock object with all Profile fields set to sensible defaults.
    Individual tests can override specific attributes as needed.
    """
    profile = Mock()
    profile.name = "Test User"
    profile.location = "Portland, OR"
    profile.email = "test@example.com"
    profile.phone = None
    profile.linkedin_url = None
    profile.github_url = None
    profile.portfolio_url = None
    profile.summary = "Experienced software engineer"
    profile.years_of_experience = 5.0
    profile.skills = []
    profile.experience = []
    profile.education = []
    profile.projects = []
    profile.certifications = []
    profile.languages = ["English"]
    profile.preferences = None
    profile.get_current_role = Mock(return_value=None)
    profile.get_all_skills = Mock(return_value=[])
    return profile


@pytest.fixture
def mock_firestore_client():
    """
    Create a standardized mock Firestore client.

    Returns a MagicMock configured for common Firestore operations.
    Individual tests should configure specific method return values as needed.
    """
    mock_db = MagicMock()

    # Setup default chaining behavior for common patterns:
    # db.collection().document().get()
    # db.collection().where().limit().stream()
    # db.collection().add()

    # Collection mock
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection

    # Document mock
    mock_document = MagicMock()
    mock_collection.document.return_value = mock_document

    # Query mocks (where, limit, order_by)
    mock_query = MagicMock()
    mock_collection.where.return_value = mock_query
    mock_query.where.return_value = mock_query  # Chain multiple where()
    mock_query.limit.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_collection.limit.return_value = mock_query
    mock_collection.order_by.return_value = mock_query

    # Stream mock (returns empty list by default)
    mock_query.stream.return_value = []

    # Add mock (returns (None, doc_ref) tuple)
    mock_doc_ref = MagicMock(id="test-doc-id")
    mock_collection.add.return_value = (None, mock_doc_ref)

    return mock_db
