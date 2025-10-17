"""Tests for queue item processor."""

from unittest.mock import MagicMock

import pytest

from job_finder.queue.models import JobQueueItem, QueueItemType, QueueStatus
from job_finder.queue.processor import QueueItemProcessor


@pytest.fixture
def mock_managers():
    """Create mock managers for processor."""
    return {
        "queue_manager": MagicMock(),
        "config_loader": MagicMock(),
        "job_storage": MagicMock(),
        "companies_manager": MagicMock(),
        "sources_manager": MagicMock(),
        "company_info_fetcher": MagicMock(),
        "ai_matcher": MagicMock(),
    }


@pytest.fixture
def processor(mock_managers):
    """Create processor with mocked dependencies."""
    return QueueItemProcessor(**mock_managers)


@pytest.fixture
def sample_job_item():
    """Create a sample job queue item."""
    return JobQueueItem(
        id="test-job-123",
        type=QueueItemType.JOB,
        url="https://example.com/job/123",
        company_name="Test Company",
        source="scraper",
    )


@pytest.fixture
def sample_company_item():
    """Create a sample company queue item."""
    return JobQueueItem(
        id="test-company-456",
        type=QueueItemType.COMPANY,
        url="https://testcompany.com",
        company_name="Test Company",
        source="scraper",
    )


def test_process_item_without_id(processor, mock_managers):
    """Test that items without ID are rejected."""
    item = JobQueueItem(
        id=None,
        type=QueueItemType.JOB,
        url="https://example.com/job",
        company_name="Test Corp",
        source="scraper",
    )

    processor.process_item(item)

    # Should not update status since ID is None
    mock_managers["queue_manager"].update_status.assert_not_called()


def test_should_skip_by_stop_list_excluded_company(processor, mock_managers):
    """Test stop list filtering for excluded companies."""
    # Mock stop list
    mock_managers["config_loader"].get_stop_list.return_value = {
        "excludedCompanies": ["BadCorp"],
        "excludedKeywords": [],
        "excludedDomains": [],
    }

    item = JobQueueItem(
        id="test-123",
        type=QueueItemType.JOB,
        url="https://example.com/job",
        company_name="BadCorp Inc",
        source="scraper",
    )

    # Should be skipped
    assert processor._should_skip_by_stop_list(item) is True


def test_should_skip_by_stop_list_excluded_domain(processor, mock_managers):
    """Test stop list filtering for excluded domains."""
    # Mock stop list
    mock_managers["config_loader"].get_stop_list.return_value = {
        "excludedCompanies": [],
        "excludedKeywords": [],
        "excludedDomains": ["spam.com"],
    }

    item = JobQueueItem(
        id="test-123",
        type=QueueItemType.JOB,
        url="https://spam.com/job/123",
        company_name="Spam Corp",
        source="scraper",
    )

    # Should be skipped
    assert processor._should_skip_by_stop_list(item) is True


def test_should_skip_by_stop_list_excluded_keyword(processor, mock_managers):
    """Test stop list filtering for excluded keywords in URL."""
    # Mock stop list
    mock_managers["config_loader"].get_stop_list.return_value = {
        "excludedCompanies": [],
        "excludedKeywords": ["commission-only"],
        "excludedDomains": [],
    }

    item = JobQueueItem(
        id="test-123",
        type=QueueItemType.JOB,
        url="https://example.com/jobs/commission-only-position",
        company_name="Example Corp",
        source="scraper",
    )

    # Should be skipped
    assert processor._should_skip_by_stop_list(item) is True


def test_should_not_skip_by_stop_list(processor, mock_managers):
    """Test that valid items pass stop list filtering."""
    # Mock stop list
    mock_managers["config_loader"].get_stop_list.return_value = {
        "excludedCompanies": ["BadCorp"],
        "excludedKeywords": ["scam"],
        "excludedDomains": ["spam.com"],
    }

    item = JobQueueItem(
        id="test-123",
        type=QueueItemType.JOB,
        url="https://goodcompany.com/job/123",
        company_name="Good Company",
        source="scraper",
    )

    # Should not be skipped
    assert processor._should_skip_by_stop_list(item) is False


def test_process_job_already_exists(processor, mock_managers, sample_job_item):
    """Test that existing jobs are skipped."""
    # Mock stop list
    mock_managers["config_loader"].get_stop_list.return_value = {
        "excludedCompanies": [],
        "excludedKeywords": [],
        "excludedDomains": [],
    }

    # Mock job already exists
    mock_managers["job_storage"].job_exists.return_value = True

    processor.process_item(sample_job_item)

    # Should update to SKIPPED
    mock_managers["queue_manager"].update_status.assert_called()
    call_args = mock_managers["queue_manager"].update_status.call_args_list

    # Find the SKIPPED status call
    skipped_call = None
    for call in call_args:
        if call[0][1] == QueueStatus.SKIPPED:
            skipped_call = call
            break

    assert skipped_call is not None
    assert "already exists" in skipped_call[0][2].lower()


def test_process_company_already_analyzed(processor, mock_managers, sample_company_item):
    """Test that already analyzed companies are skipped."""
    # Mock stop list
    mock_managers["config_loader"].get_stop_list.return_value = {
        "excludedCompanies": [],
        "excludedKeywords": [],
        "excludedDomains": [],
    }

    # Mock company already analyzed
    mock_managers["companies_manager"].get_company.return_value = {
        "name": "Test Company",
        "analysis_status": "complete",
    }

    processor.process_item(sample_company_item)

    # Should update to SKIPPED
    mock_managers["queue_manager"].update_status.assert_called()
    call_args = mock_managers["queue_manager"].update_status.call_args_list

    # Find the SKIPPED status call
    skipped_call = None
    for call in call_args:
        if call[0][1] == QueueStatus.SKIPPED:
            skipped_call = call
            break

    assert skipped_call is not None
    assert "already analyzed" in skipped_call[0][2].lower()


def test_process_company_success(processor, mock_managers, sample_company_item):
    """Test successful company processing."""
    # Mock stop list
    mock_managers["config_loader"].get_stop_list.return_value = {
        "excludedCompanies": [],
        "excludedKeywords": [],
        "excludedDomains": [],
    }

    # Mock company not yet analyzed
    mock_managers["companies_manager"].get_company.return_value = None

    # Mock company info fetcher
    mock_managers["company_info_fetcher"].fetch_company_info.return_value = {
        "name": "Test Company",
        "website": "https://testcompany.com",
        "about": "A great company",
    }

    # Mock save company
    mock_managers["companies_manager"].save_company.return_value = "company-doc-id"

    processor.process_item(sample_company_item)

    # Should fetch company info
    mock_managers["company_info_fetcher"].fetch_company_info.assert_called_once()

    # Should save company
    mock_managers["companies_manager"].save_company.assert_called_once()

    # Should update to SUCCESS
    call_args = mock_managers["queue_manager"].update_status.call_args_list
    success_call = None
    for call in call_args:
        if call[0][1] == QueueStatus.SUCCESS:
            success_call = call
            break

    assert success_call is not None


def test_process_company_fetch_failed(processor, mock_managers, sample_company_item):
    """Test company processing when fetch fails."""
    # Mock stop list
    mock_managers["config_loader"].get_stop_list.return_value = {
        "excludedCompanies": [],
        "excludedKeywords": [],
        "excludedDomains": [],
    }

    # Mock company not yet analyzed
    mock_managers["companies_manager"].get_company.return_value = None

    # Mock company info fetcher returns None (failure)
    mock_managers["company_info_fetcher"].fetch_company_info.return_value = None

    processor.process_item(sample_company_item)

    # Should update to FAILED
    call_args = mock_managers["queue_manager"].update_status.call_args_list
    failed_call = None
    for call in call_args:
        if call[0][1] == QueueStatus.FAILED:
            failed_call = call
            break

    assert failed_call is not None


def test_handle_failure_retry(processor, mock_managers):
    """Test failure handling with retry logic."""
    # Mock queue settings
    mock_managers["config_loader"].get_queue_settings.return_value = {"maxRetries": 3}

    item = JobQueueItem(
        id="test-123",
        type=QueueItemType.JOB,
        url="https://example.com/job",
        company_name="Test Corp",
        source="scraper",
        retry_count=1,  # First retry
    )

    processor._handle_failure(item, "Test error")

    # Should increment retry count
    mock_managers["queue_manager"].increment_retry.assert_called_with("test-123")

    # Should update to PENDING for retry
    call_args = mock_managers["queue_manager"].update_status.call_args[0]
    assert call_args[1] == QueueStatus.PENDING
    assert "Retry" in call_args[2]


def test_handle_failure_max_retries(processor, mock_managers):
    """Test failure handling when max retries exceeded."""
    # Mock queue settings
    mock_managers["config_loader"].get_queue_settings.return_value = {"maxRetries": 3}

    item = JobQueueItem(
        id="test-123",
        type=QueueItemType.JOB,
        url="https://example.com/job",
        company_name="Test Corp",
        source="scraper",
        retry_count=2,  # At max retries
    )

    processor._handle_failure(item, "Test error")

    # Should increment retry count
    mock_managers["queue_manager"].increment_retry.assert_called_with("test-123")

    # Should update to FAILED
    call_args = mock_managers["queue_manager"].update_status.call_args[0]
    assert call_args[1] == QueueStatus.FAILED
    assert "Max retries exceeded" in call_args[2]


def test_build_company_info_string(processor):
    """Test company info string builder."""
    company_info = {
        "about": "We build great software",
        "culture": "Remote-first, collaborative",
        "mission": "To make work better",
    }

    result = processor._build_company_info_string(company_info)

    assert "About: We build great software" in result
    assert "Culture: Remote-first, collaborative" in result
    assert "Mission: To make work better" in result


def test_build_company_info_string_partial(processor):
    """Test company info string with partial data."""
    company_info = {
        "about": "We build great software",
        "culture": "",
        "mission": None,
    }

    result = processor._build_company_info_string(company_info)

    assert "About: We build great software" in result
    assert "Culture:" not in result
    assert "Mission:" not in result
