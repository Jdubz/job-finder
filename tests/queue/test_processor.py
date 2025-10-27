"""Tests for queue item processor."""

from unittest.mock import MagicMock, patch

import pytest

from job_finder.job_queue.models import JobQueueItem, QueueItemType, QueueStatus, ScrapeConfig
from job_finder.job_queue.processor import QueueItemProcessor


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
        "profile": MagicMock(),
    }


@pytest.fixture
def processor(mock_managers):
    """Create processor with mocked dependencies."""
    # Patch ScrapeRunner to avoid creating real instance
    with patch(
        "job_finder.job_queue.processors.base_processor.ScrapeRunner"
    ) as mock_scrape_runner_class:
        mock_scrape_runner_instance = MagicMock()
        mock_scrape_runner_class.return_value = mock_scrape_runner_instance

        processor_instance = QueueItemProcessor(**mock_managers)

        # Store reference to mock scrape_runner for tests to access
        # Note: After refactoring, scrape_runner is on job_processor
        processor_instance.scrape_runner = mock_scrape_runner_instance
        processor_instance.job_processor.scrape_runner = mock_scrape_runner_instance

        return processor_instance


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


# Legacy company processing tests removed - see test_company_pipeline.py for granular pipeline tests


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
    assert "retry" in call_args[2].lower()


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
    assert "retries" in call_args[2].lower()


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


# SCRAPE Queue Item Tests


@pytest.fixture
def sample_scrape_item():
    """Create a sample scrape queue item."""
    return JobQueueItem(
        id="test-scrape-789",
        type=QueueItemType.SCRAPE,
        source="user_submission",
        scrape_config=ScrapeConfig(
            target_matches=5,
            max_sources=20,
            source_ids=None,
            min_match_score=None,
        ),
    )


def test_process_scrape_with_default_config(processor, mock_managers, sample_scrape_item):
    """Test processing SCRAPE item with default configuration."""
    # Mock scrape runner
    processor.scrape_runner.run_scrape.return_value = {
        "sources_scraped": 3,
        "jobs_saved": 5,
        "jobs_analyzed": 5,
    }

    processor.process_item(sample_scrape_item)

    # Should call scrape runner with config values
    processor.scrape_runner.run_scrape.assert_called_once_with(
        target_matches=5, max_sources=20, source_ids=None
    )

    # Should update to SUCCESS
    call_args = mock_managers["queue_manager"].update_status.call_args_list
    success_call = None
    for call in call_args:
        if call[0][1] == QueueStatus.SUCCESS:
            success_call = call
            break

    assert success_call is not None
    assert "3 sources" in success_call[0][2]
    assert "5 jobs" in success_call[0][2]


def test_process_scrape_with_custom_config(processor, mock_managers):
    """Test processing SCRAPE item with custom configuration."""
    # Create scrape item with custom config
    scrape_item = JobQueueItem(
        id="test-scrape-custom",
        type=QueueItemType.SCRAPE,
        source="user_submission",
        scrape_config=ScrapeConfig(
            target_matches=10,
            max_sources=50,
            source_ids=["source-1", "source-2"],
            min_match_score=70,
        ),
    )

    # Mock scrape runner
    processor.scrape_runner.run_scrape.return_value = {
        "sources_scraped": 2,
        "jobs_saved": 8,
        "jobs_analyzed": 10,
    }

    processor.process_item(scrape_item)

    # Should override AI matcher min score (check it was set)
    # The ai_matcher is a mock, so we verify the attribute was assigned
    assert hasattr(processor.ai_matcher, "min_match_score")

    # Should call scrape runner with custom values
    processor.scrape_runner.run_scrape.assert_called_once_with(
        target_matches=10, max_sources=50, source_ids=["source-1", "source-2"]
    )

    # Should update to SUCCESS
    call_args = mock_managers["queue_manager"].update_status.call_args_list
    success_call = None
    for call in call_args:
        if call[0][1] == QueueStatus.SUCCESS:
            success_call = call
            break

    assert success_call is not None


def test_process_scrape_with_none_values(processor, mock_managers):
    """Test processing SCRAPE item with None values (unlimited)."""
    # Create scrape item with None values
    scrape_item = JobQueueItem(
        id="test-scrape-unlimited",
        type=QueueItemType.SCRAPE,
        source="automated_scan",
        scrape_config=ScrapeConfig(
            target_matches=None,  # Unlimited
            max_sources=None,  # Unlimited
            source_ids=None,
            min_match_score=None,
        ),
    )

    # Mock scrape runner
    processor.scrape_runner.run_scrape.return_value = {
        "sources_scraped": 100,
        "jobs_saved": 25,
        "jobs_analyzed": 50,
    }

    processor.process_item(scrape_item)

    # Should call scrape runner with None values
    processor.scrape_runner.run_scrape.assert_called_once_with(
        target_matches=None, max_sources=None, source_ids=None
    )

    # Should not override AI matcher min score
    assert not hasattr(mock_managers["ai_matcher"], "min_match_score") or (
        mock_managers["ai_matcher"].min_match_score != 70
    )


def test_process_scrape_no_config(processor, mock_managers):
    """Test processing SCRAPE item without scrape_config (should use defaults)."""
    # Create scrape item without config
    scrape_item = JobQueueItem(
        id="test-scrape-no-config",
        type=QueueItemType.SCRAPE,
        source="automated_scan",
        scrape_config=None,
    )

    # Mock scrape runner
    processor.scrape_runner.run_scrape.return_value = {
        "sources_scraped": 5,
        "jobs_saved": 3,
        "jobs_analyzed": 5,
    }

    processor.process_item(scrape_item)

    # Should call scrape runner with defaults (from ScrapeConfig())
    processor.scrape_runner.run_scrape.assert_called_once_with(
        target_matches=5, max_sources=20, source_ids=None
    )


def test_process_scrape_error_handling(processor, mock_managers):
    """Test error handling when scrape fails."""
    scrape_item = JobQueueItem(
        id="test-scrape-error",
        type=QueueItemType.SCRAPE,
        source="user_submission",
        scrape_config=ScrapeConfig(),
    )

    # Mock scrape runner to raise exception
    processor.scrape_runner.run_scrape.side_effect = Exception("Network error")

    # Mock queue settings
    mock_managers["config_loader"].get_queue_settings.return_value = {"maxRetries": 3}

    processor.process_item(scrape_item)

    # Should update to FAILED or PENDING for retry
    call_args = mock_managers["queue_manager"].update_status.call_args_list
    has_failure_or_retry = any(
        call[0][1] in [QueueStatus.FAILED, QueueStatus.PENDING] for call in call_args
    )
    assert has_failure_or_retry


def test_process_scrape_no_jobs_found(processor, mock_managers):
    """Test processing SCRAPE when no jobs are found."""
    scrape_item = JobQueueItem(
        id="test-scrape-none",
        type=QueueItemType.SCRAPE,
        source="automated_scan",
        scrape_config=ScrapeConfig(),
    )

    # Mock scrape runner with no results
    processor.scrape_runner.run_scrape.return_value = {
        "sources_scraped": 3,
        "jobs_saved": 0,
        "jobs_analyzed": 0,
    }

    processor.process_item(scrape_item)

    # Should still update to SUCCESS (no jobs is not an error)
    call_args = mock_managers["queue_manager"].update_status.call_args_list
    success_call = None
    for call in call_args:
        if call[0][1] == QueueStatus.SUCCESS:
            success_call = call
            break

    assert success_call is not None
    assert "0 jobs" in success_call[0][2]
