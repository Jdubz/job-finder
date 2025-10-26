"""Tests for granular pipeline processors."""

import pytest
from unittest.mock import MagicMock, patch

from job_finder.ai.matcher import JobMatchResult
from job_finder.filters.models import FilterResult
from job_finder.job_queue.models import JobQueueItem, JobSubTask, QueueItemType
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
    mock_managers["config_loader"].get_job_filters.return_value = {}
    mock_managers["config_loader"].get_technology_ranks.return_value = {}
    processor_instance = QueueItemProcessor(**mock_managers)
    return processor_instance


class TestGranularRouting:
    """Test routing to correct processor."""

    def test_routes_scrape_subtask(self, processor):
        """Should route SCRAPE sub_task to correct processor."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.SCRAPE,
        )

        with patch.object(processor.job_processor, "process_job_scrape") as mock:
            processor._process_granular_job(item)
            mock.assert_called_once()

    def test_routes_filter_subtask(self, processor):
        """Should route FILTER sub_task to correct processor."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.FILTER,
        )

        with patch.object(processor.job_processor, "process_job_filter") as mock:
            processor._process_granular_job(item)
            mock.assert_called_once()

    def test_routes_analyze_subtask(self, processor):
        """Should route ANALYZE sub_task to correct processor."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.ANALYZE,
        )

        with patch.object(processor.job_processor, "process_job_analyze") as mock:
            processor._process_granular_job(item)
            mock.assert_called_once()

    def test_routes_save_subtask(self, processor):
        """Should route SAVE sub_task to correct processor."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.SAVE,
        )

        with patch.object(processor.job_processor, "process_job_save") as mock:
            processor._process_granular_job(item)
            mock.assert_called_once()


class TestJobScrapeProcessor:
    """Test JOB_SCRAPE processor."""

    def test_spawns_filter_on_success(self, processor):
        """Should spawn FILTER step after successful scrape."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.SCRAPE,
        )

        job_data = {"title": "Engineer", "company": "Test", "description": "Desc"}

        processor.sources_manager.get_source_for_url.return_value = None
        with patch.object(processor.job_processor, "_scrape_job", return_value=job_data):
            processor._process_job_scrape(item)

        # Should spawn next step
        processor.queue_manager.spawn_next_pipeline_step.assert_called_once()
        args = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        assert args["next_sub_task"] == JobSubTask.FILTER

    def test_fails_when_no_data_scraped(self, processor):
        """Should fail when scraping returns no data."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.SCRAPE,
        )

        processor.sources_manager.get_source_for_url.return_value = None
        with patch.object(processor.job_processor, "_scrape_job", return_value=None):
            processor._process_job_scrape(item)

        # Should NOT spawn next step
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()


class TestJobFilterProcessor:
    """Test JOB_FILTER processor."""

    def test_spawns_analyze_when_passed(self, processor):
        """Should spawn ANALYZE when filter passes."""
        job_data = {"title": "Engineer", "description": "Python"}
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.FILTER,
            pipeline_state={"job_data": job_data},
        )

        filter_result = FilterResult(passed=True, total_strikes=2)
        with patch.object(processor.filter_engine, "evaluate_job", return_value=filter_result):
            processor._process_job_filter(item)

        # Should spawn ANALYZE
        processor.queue_manager.spawn_next_pipeline_step.assert_called_once()
        args = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        assert args["next_sub_task"] == JobSubTask.ANALYZE

    def test_marks_filtered_when_rejected(self, processor):
        """Should mark FILTERED when filter rejects."""
        job_data = {"title": "Engineer", "description": "COBOL"}
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.FILTER,
            pipeline_state={"job_data": job_data},
        )

        filter_result = FilterResult(passed=False, total_strikes=15)
        with patch.object(processor.filter_engine, "evaluate_job", return_value=filter_result):
            processor._process_job_filter(item)

        # Should NOT spawn next step
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()


class TestJobAnalyzeProcessor:
    """Test JOB_ANALYZE processor."""

    def test_spawns_save_when_score_passes(self, processor):
        """Should spawn SAVE when score meets threshold."""
        job_data = {"title": "Engineer", "description": "Python"}
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.ANALYZE,
            pipeline_state={"job_data": job_data},
        )

        # Create proper match result
        match_result = JobMatchResult(
            job_title="Engineer",
            job_company="Test",
            job_url="https://example.com/job",
            match_score=85,
            matched_skills=["Python"],
            skill_gaps=[],
            match_reasons=["Good fit"],
            application_priority="High",
        )

        processor.ai_matcher.analyze_job.return_value = match_result

        processor._process_job_analyze(item)

        # Should spawn SAVE
        processor.queue_manager.spawn_next_pipeline_step.assert_called_once()
        args = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        assert args["next_sub_task"] == JobSubTask.SAVE

    def test_skips_when_below_threshold(self, processor):
        """Should skip when score below threshold."""
        job_data = {"title": "Engineer", "description": "Python"}
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.ANALYZE,
            pipeline_state={"job_data": job_data},
        )

        processor.ai_matcher.analyze_job.return_value = None

        processor._process_job_analyze(item)

        # Should NOT spawn next step
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()


class TestJobSaveProcessor:
    """Test JOB_SAVE processor."""

    def test_saves_to_storage(self, processor):
        """Should save job match to storage."""
        job_data = {"title": "Engineer", "description": "Python"}
        match_dict = {
            "job_title": "Engineer",
            "job_company": "Test",
            "job_url": "https://example.com/job",
            "match_score": 85,
            "matched_skills": ["Python"],
            "skill_gaps": [],
            "match_reasons": ["Good fit"],
            "application_priority": "High",
        }

        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.SAVE,
            pipeline_state={"job_data": job_data, "match_result": match_dict},
        )

        processor.job_storage.save_job_match.return_value = "match-456"

        processor._process_job_save(item)

        # Should save
        processor.job_storage.save_job_match.assert_called_once()

    def test_requires_match_result(self, processor):
        """Should fail gracefully when match_result missing."""
        job_data = {"title": "Engineer"}
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.SAVE,
            pipeline_state={"job_data": job_data},  # Missing match_result
        )

        processor._process_job_save(item)

        # Should not save
        processor.job_storage.save_job_match.assert_not_called()


class TestPipelineStatePassthrough:
    """Test pipeline state is passed correctly."""

    def test_scrape_creates_pipeline_state(self, processor):
        """SCRAPE should create pipeline_state with job_data."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.SCRAPE,
        )

        job_data = {"title": "Engineer", "description": "Desc"}
        processor.sources_manager.get_source_for_url.return_value = None

        with patch.object(processor.job_processor, "_scrape_job", return_value=job_data):
            processor._process_job_scrape(item)

        args = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        pipeline_state = args["pipeline_state"]

        assert "job_data" in pipeline_state
        assert pipeline_state["job_data"] == job_data

    def test_filter_preserves_job_data(self, processor):
        """FILTER should preserve job_data in pipeline_state."""
        job_data = {"title": "Engineer", "description": "Python"}
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://example.com/job",
            company_name="Test",
            sub_task=JobSubTask.FILTER,
            pipeline_state={"job_data": job_data},
        )

        filter_result = FilterResult(passed=True, total_strikes=2)
        with patch.object(processor.filter_engine, "evaluate_job", return_value=filter_result):
            processor._process_job_filter(item)

        args = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        pipeline_state = args["pipeline_state"]

        # Should preserve original job_data
        assert pipeline_state["job_data"] == job_data
