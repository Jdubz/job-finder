"""Tests for scraper intake helper."""

from unittest.mock import MagicMock

import pytest

from job_finder.job_queue.scraper_intake import ScraperIntake


@pytest.fixture
def mock_queue_manager():
    """Create mock queue manager."""
    return MagicMock()


@pytest.fixture
def scraper_intake(mock_queue_manager):
    """Create scraper intake with mock manager."""
    return ScraperIntake(queue_manager=mock_queue_manager)


def test_submit_jobs_success(scraper_intake, mock_queue_manager):
    """Test successful job submission."""
    jobs = [
        {
            "title": "Software Engineer",
            "url": "https://example.com/job/1",
            "company": "Test Corp",
            "description": "Build things",
        },
        {
            "title": "Senior Engineer",
            "url": "https://example.com/job/2",
            "company": "Test Corp",
            "description": "Lead things",
        },
    ]

    # Mock no duplicates
    mock_queue_manager.url_exists_in_queue.return_value = False
    mock_queue_manager.add_item.return_value = "doc-id"

    # Submit jobs
    count = scraper_intake.submit_jobs(jobs, source="scraper")

    # Should add both jobs
    assert count == 2
    assert mock_queue_manager.add_item.call_count == 2


def test_submit_jobs_with_duplicates(scraper_intake, mock_queue_manager):
    """Test job submission with duplicates."""
    jobs = [
        {"title": "Job 1", "url": "https://example.com/job/1", "company": "Test"},
        {"title": "Job 2", "url": "https://example.com/job/2", "company": "Test"},
        {"title": "Job 3", "url": "https://example.com/job/3", "company": "Test"},
    ]

    # Mock second job is duplicate
    def url_exists_side_effect(url):
        return url == "https://example.com/job/2"

    mock_queue_manager.url_exists_in_queue.side_effect = url_exists_side_effect
    mock_queue_manager.add_item.return_value = "doc-id"

    # Submit jobs
    count = scraper_intake.submit_jobs(jobs, source="scraper")

    # Should add 2 jobs (skip 1 duplicate)
    assert count == 2
    assert mock_queue_manager.add_item.call_count == 2


def test_submit_jobs_with_company_id(scraper_intake, mock_queue_manager):
    """Test job submission with company ID."""
    jobs = [
        {"title": "Job 1", "url": "https://example.com/job/1", "company": "Test"},
    ]

    mock_queue_manager.url_exists_in_queue.return_value = False
    mock_queue_manager.add_item.return_value = "doc-id"

    # Submit with company ID
    count = scraper_intake.submit_jobs(jobs, source="scraper", company_id="company-123")

    assert count == 1

    # Check that company_id was passed in queue item
    call_args = mock_queue_manager.add_item.call_args[0][0]
    assert call_args.company_id == "company-123"


def test_submit_jobs_handles_errors(scraper_intake, mock_queue_manager):
    """Test that submission continues on individual errors."""
    jobs = [
        {"title": "Job 1", "url": "https://example.com/job/1", "company": "Test"},
        {"title": "Job 2", "url": "https://example.com/job/2", "company": "Test"},
    ]

    mock_queue_manager.url_exists_in_queue.return_value = False

    # First add succeeds, second fails
    mock_queue_manager.add_item.side_effect = [
        "doc-id-1",
        Exception("Firestore error"),
    ]

    # Should continue and add first job
    count = scraper_intake.submit_jobs(jobs, source="scraper")

    assert count == 1  # Only first succeeded


def test_submit_company_success(scraper_intake, mock_queue_manager):
    """Test successful company submission with granular pipeline."""
    mock_queue_manager.url_exists_in_queue.return_value = False
    mock_queue_manager.add_item.return_value = "doc-id-123"

    result = scraper_intake.submit_company(
        company_name="Test Corp", company_website="https://testcorp.com", source="scraper"
    )

    assert result == "doc-id-123"
    mock_queue_manager.add_item.assert_called_once()

    # Check queue item
    call_args = mock_queue_manager.add_item.call_args[0][0]
    assert call_args.type == "company"
    assert call_args.company_name == "Test Corp"
    assert call_args.url == "https://testcorp.com"
    assert call_args.company_sub_task == "fetch"  # Should start with FETCH step


def test_submit_company_duplicate(scraper_intake, mock_queue_manager):
    """Test company submission with duplicate."""
    mock_queue_manager.url_exists_in_queue.return_value = True

    result = scraper_intake.submit_company(
        company_name="Test Corp", company_website="https://testcorp.com", source="scraper"
    )

    assert result is None
    mock_queue_manager.add_item.assert_not_called()


def test_submit_company_error(scraper_intake, mock_queue_manager):
    """Test company submission with error."""
    mock_queue_manager.url_exists_in_queue.return_value = False
    mock_queue_manager.add_item.side_effect = Exception("Firestore error")

    result = scraper_intake.submit_company(
        company_name="Test Corp", company_website="https://testcorp.com", source="scraper"
    )

    assert result is None


def test_submit_company_empty_url(scraper_intake, mock_queue_manager):
    """Test company submission with empty URL."""
    result = scraper_intake.submit_company(
        company_name="Test Corp", company_website="", source="scraper"
    )

    assert result is None
    mock_queue_manager.url_exists_in_queue.assert_not_called()
    mock_queue_manager.add_item.assert_not_called()


def test_submit_jobs_empty_list(scraper_intake, mock_queue_manager):
    """Test submitting empty job list."""
    count = scraper_intake.submit_jobs([], source="scraper")

    assert count == 0
    mock_queue_manager.add_item.assert_not_called()
