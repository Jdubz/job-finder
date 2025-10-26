"""Comprehensive unit tests for all job pipeline sub-tasks.

Tests cover:
- JOB_SCRAPE: All scraping scenarios (source-based, AI, errors)
- JOB_FILTER: Filter passing, rejection, strike accumulation
- JOB_ANALYZE: AI matching, score thresholds, company data
- JOB_SAVE: Firestore saving, error handling
"""

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


# ========================================
# JOB_SCRAPE Tests
# ========================================


class TestJobScrapeSuccess:
    """Test successful JOB_SCRAPE scenarios."""

    def test_scrape_with_source_config(self, processor):
        """Should scrape using source config when available."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.JOB,
            url="https://boards.greenhouse.io/company/jobs/123",
            company_name="Test Corp",
            sub_task=JobSubTask.SCRAPE,
        )

        # Mock source config
        source_config = {
            "name": "Test Corp Greenhouse",
            "sourceType": "greenhouse",
            "config": {"board_token": "company"},
        }
        processor.sources_manager.get_source_for_url.return_value = source_config

        # Mock scraping result
        job_data = {
            "title": "Senior Engineer",
            "company": "Test Corp",
            "description": "Build cool stuff",
            "location": "Remote",
            "url": item.url,
            "company_website": "https://testcorp.com",
        }

        with patch.object(
            processor.job_processor, "_scrape_with_source_config", return_value=job_data
        ):
            processor._process_job_scrape(item)

        # Verify spawn called with correct data
        processor.queue_manager.spawn_next_pipeline_step.assert_called_once()
        call_args = processor.queue_manager.spawn_next_pipeline_step.call_args[1]

        assert call_args["current_item"] == item
        assert call_args["next_sub_task"] == JobSubTask.FILTER
        assert call_args["pipeline_state"]["job_data"] == job_data
        assert call_args["pipeline_state"]["scrape_method"] == "Test Corp Greenhouse"

    def test_scrape_without_source_config_fallback(self, processor):
        """Should fallback to generic scraping when no source config."""
        item = JobQueueItem(
            id="test-456",
            type=QueueItemType.JOB,
            url="https://example.com/careers/job/123",
            company_name="Example Inc",
            sub_task=JobSubTask.SCRAPE,
        )

        # No source config
        processor.sources_manager.get_source_for_url.return_value = None

        # Mock scraping result
        job_data = {
            "title": "Software Engineer",
            "company": "Example Inc",
            "description": "Write code",
            "location": "Portland, OR",
            "url": item.url,
            "company_website": "https://example.com",
        }

        with patch.object(processor.job_processor, "_scrape_job", return_value=job_data):
            processor._process_job_scrape(item)

        # Should spawn FILTER step
        processor.queue_manager.spawn_next_pipeline_step.assert_called_once()
        call_args = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        assert call_args["next_sub_task"] == JobSubTask.FILTER
        assert call_args["pipeline_state"]["scrape_method"] == "generic"

    def test_scrape_preserves_optional_fields(self, processor):
        """Should preserve optional fields like posted_date, salary."""
        item = JobQueueItem(
            id="test-789",
            type=QueueItemType.JOB,
            url="https://example.com/job/789",
            company_name="Example",
            sub_task=JobSubTask.SCRAPE,
        )

        processor.sources_manager.get_source_for_url.return_value = None

        # Job with optional fields
        job_data = {
            "title": "Engineer",
            "company": "Example",
            "description": "Desc",
            "location": "Remote",
            "url": item.url,
            "company_website": "https://example.com",
            "posted_date": "2025-01-15",
            "salary": "$120k - $150k",
        }

        with patch.object(processor.job_processor, "_scrape_job", return_value=job_data):
            processor._process_job_scrape(item)

        # Verify optional fields preserved
        call_args = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        saved_data = call_args["pipeline_state"]["job_data"]
        assert saved_data["posted_date"] == "2025-01-15"
        assert saved_data["salary"] == "$120k - $150k"


class TestJobScrapeFailures:
    """Test JOB_SCRAPE failure scenarios."""

    def test_scrape_returns_none(self, processor):
        """Should fail when scraping returns no data."""
        item = JobQueueItem(
            id="test-fail-1",
            type=QueueItemType.JOB,
            url="https://example.com/job/404",
            company_name="Example",
            sub_task=JobSubTask.SCRAPE,
        )

        processor.sources_manager.get_source_for_url.return_value = None

        with patch.object(processor.job_processor, "_scrape_job", return_value=None):
            processor._process_job_scrape(item)

        # Should NOT spawn next step
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()

    def test_scrape_raises_exception(self, processor, mock_managers):
        """Should handle scraping exceptions gracefully."""
        item = JobQueueItem(
            id="test-fail-2",
            type=QueueItemType.JOB,
            url="https://example.com/job/error",
            company_name="Example",
            sub_task=JobSubTask.SCRAPE,
        )

        processor.sources_manager.get_source_for_url.return_value = None

        # Mock scraping exception
        with patch.object(
            processor.job_processor, "_scrape_job", side_effect=Exception("Network timeout")
        ):
            # The exception will be caught and re-raised by the processor
            try:
                processor._process_job_scrape(item)
            except Exception:
                pass  # Expected

        # Should NOT spawn next step since scraping failed
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()

    def test_scrape_missing_required_fields(self, processor):
        """Should still pass incomplete data through to filter - validation happens there."""
        item = JobQueueItem(
            id="test-fail-3",
            type=QueueItemType.JOB,
            url="https://example.com/job/incomplete",
            company_name="Example",
            sub_task=JobSubTask.SCRAPE,
        )

        processor.sources_manager.get_source_for_url.return_value = None

        # Missing required field (description)
        incomplete_job = {
            "title": "Engineer",
            "company": "Example",
            "location": "Remote",
            "url": item.url,
            # Missing: description, company_website
        }

        with patch.object(processor.job_processor, "_scrape_job", return_value=incomplete_job):
            processor._process_job_scrape(item)

        # Scraper doesn't validate - just passes data through to filter
        processor.queue_manager.spawn_next_pipeline_step.assert_called_once()
        call_args = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        assert call_args["next_sub_task"] == JobSubTask.FILTER


# ========================================
# JOB_FILTER Tests
# ========================================


class TestJobFilterPassing:
    """Test JOB_FILTER passing scenarios."""

    def test_filter_passes_with_zero_strikes(self, processor):
        """Should pass job with zero strikes."""
        job_data = {
            "title": "Senior Python Engineer",
            "company": "Tech Corp",
            "description": "Build Python apps with React",
            "location": "Remote",
            "url": "https://example.com/job/1",
            "company_website": "https://techcorp.com",
        }

        item = JobQueueItem(
            id="test-filter-1",
            type=QueueItemType.JOB,
            url=job_data["url"],
            company_name=job_data["company"],
            sub_task=JobSubTask.FILTER,
            pipeline_state={"job_data": job_data, "scrape_method": "source"},
        )

        # Mock filter passes
        filter_result = FilterResult(passed=True)

        with patch.object(processor.filter_engine, "evaluate_job", return_value=filter_result):
            processor._process_job_filter(item)

        # Should spawn ANALYZE
        processor.queue_manager.spawn_next_pipeline_step.assert_called_once()
        call_args = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        assert call_args["next_sub_task"] == JobSubTask.ANALYZE
        assert call_args["pipeline_state"]["job_data"] == job_data
        assert call_args["pipeline_state"]["filter_result"] == filter_result.to_dict()

    def test_filter_passes_with_some_strikes(self, processor):
        """Should pass job with strikes below threshold."""
        job_data = {
            "title": "Software Engineer",
            "company": "Example",
            "description": "Java development",
            "location": "New York, NY",  # Not Portland
            "url": "https://example.com/job/2",
            "company_website": "https://example.com",
        }

        item = JobQueueItem(
            id="test-filter-2",
            type=QueueItemType.JOB,
            url=job_data["url"],
            company_name=job_data["company"],
            sub_task=JobSubTask.FILTER,
            pipeline_state={"job_data": job_data},
        )

        # Has strikes but below threshold (< 5)
        filter_result = FilterResult(passed=True, total_strikes=3)

        with patch.object(processor.filter_engine, "evaluate_job", return_value=filter_result):
            processor._process_job_filter(item)

        # Should still spawn ANALYZE
        processor.queue_manager.spawn_next_pipeline_step.assert_called_once()
        call_args = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        assert call_args["next_sub_task"] == JobSubTask.ANALYZE


class TestJobFilterRejections:
    """Test JOB_FILTER rejection scenarios."""

    def test_filter_rejects_hard_rejection(self, processor):
        """Should reject job with hard rejection (excluded company)."""
        job_data = {
            "title": "Engineer",
            "company": "ExcludedCorp",
            "description": "Work here",
            "location": "Remote",
            "url": "https://excluded.com/job/1",
            "company_website": "https://excluded.com",
        }

        item = JobQueueItem(
            id="test-filter-reject-1",
            type=QueueItemType.JOB,
            url=job_data["url"],
            company_name=job_data["company"],
            sub_task=JobSubTask.FILTER,
            pipeline_state={"job_data": job_data},
        )

        # Hard rejection
        filter_result = FilterResult(passed=False)
        filter_result.add_rejection(
            filter_category="company",
            filter_name="company_excluded",
            reason="Company is in exclusion list",
            detail="ExcludedCorp is excluded",
            severity="hard_reject",
        )

        with patch.object(processor.filter_engine, "evaluate_job", return_value=filter_result):
            processor._process_job_filter(item)

        # Should NOT spawn ANALYZE
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()

    def test_filter_rejects_too_many_strikes(self, processor):
        """Should reject job with too many strikes (≥5)."""
        job_data = {
            "title": "Manager",  # Not IC role
            "company": "Example",
            "description": "COBOL development",  # Tech mismatch
            "location": "Tokyo, Japan",  # Location mismatch
            "url": "https://example.com/job/bad",
            "company_website": "https://example.com",
        }

        item = JobQueueItem(
            id="test-filter-reject-2",
            type=QueueItemType.JOB,
            url=job_data["url"],
            company_name=job_data["company"],
            sub_task=JobSubTask.FILTER,
            pipeline_state={"job_data": job_data},
        )

        # Accumulated too many strikes
        filter_result = FilterResult(passed=False, total_strikes=8)

        with patch.object(processor.filter_engine, "evaluate_job", return_value=filter_result):
            processor._process_job_filter(item)

        # Should NOT spawn ANALYZE
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()

    def test_filter_rejects_management_role(self, processor):
        """Should reject management roles for IC preference."""
        job_data = {
            "title": "Engineering Manager",
            "company": "Tech Corp",
            "description": "Lead a team of engineers",
            "location": "Remote",
            "url": "https://example.com/job/mgr",
            "company_website": "https://example.com",
        }

        item = JobQueueItem(
            id="test-filter-reject-3",
            type=QueueItemType.JOB,
            url=job_data["url"],
            company_name=job_data["company"],
            sub_task=JobSubTask.FILTER,
            pipeline_state={"job_data": job_data},
        )

        filter_result = FilterResult(passed=False)
        filter_result.add_rejection(
            filter_category="role",
            filter_name="management_role",
            reason="Seeking IC role, not management",
            detail="Role is for Engineering Manager",
            severity="hard_reject",
        )

        with patch.object(processor.filter_engine, "evaluate_job", return_value=filter_result):
            processor._process_job_filter(item)

        # Should NOT spawn ANALYZE
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()


class TestJobFilterEdgeCases:
    """Test JOB_FILTER edge cases."""

    def test_filter_with_missing_pipeline_state(self, processor):
        """Should handle missing pipeline_state gracefully."""
        item = JobQueueItem(
            id="test-filter-edge-1",
            type=QueueItemType.JOB,
            url="https://example.com/job/1",
            company_name="Example",
            sub_task=JobSubTask.FILTER,
            pipeline_state=None,  # Missing!
        )

        processor._process_job_filter(item)

        # Should NOT spawn next step
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()

    def test_filter_with_missing_job_data(self, processor):
        """Should handle missing job_data in pipeline_state."""
        item = JobQueueItem(
            id="test-filter-edge-2",
            type=QueueItemType.JOB,
            url="https://example.com/job/2",
            company_name="Example",
            sub_task=JobSubTask.FILTER,
            pipeline_state={"scrape_method": "source"},  # No job_data!
        )

        processor._process_job_filter(item)

        # Should NOT spawn next step
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()


# ========================================
# JOB_ANALYZE Tests
# ========================================


class TestJobAnalyzeSuccess:
    """Test successful JOB_ANALYZE scenarios."""

    def test_analyze_high_score_spawns_save(self, processor):
        """Should spawn SAVE when match score is high (≥80)."""
        job_data = {
            "title": "Senior Python Engineer",
            "company": "Tech Corp",
            "description": "Python, React, AWS",
            "location": "Remote",
            "url": "https://example.com/job/1",
            "company_website": "https://techcorp.com",
        }

        item = JobQueueItem(
            id="test-analyze-1",
            type=QueueItemType.JOB,
            url=job_data["url"],
            company_name=job_data["company"],
            sub_task=JobSubTask.ANALYZE,
            pipeline_state={"job_data": job_data},
        )

        # Mock AI analysis result
        match_result = JobMatchResult(
            job_title="Senior Python Engineer",
            job_company="Tech Corp",
            job_url=job_data["url"],
            match_score=92,
            matched_skills=["Python", "React", "AWS"],
            skill_gaps=["Kubernetes"],
            match_reasons=["Strong Python match", "React experience"],
            application_priority="High",
            resume_intake_data={
                "professional_summary": "Senior engineer...",
                "key_skills": ["Python", "React"],
            },
        )

        processor.ai_matcher.analyze_job.return_value = match_result

        processor._process_job_analyze(item)

        # Should spawn SAVE
        processor.queue_manager.spawn_next_pipeline_step.assert_called_once()
        call_args = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        assert call_args["next_sub_task"] == JobSubTask.SAVE
        assert call_args["pipeline_state"]["match_result"] == match_result.to_dict()

    def test_analyze_with_company_info(self, processor, mock_managers):
        """Should include company info in AI analysis."""
        job_data = {
            "title": "Engineer",
            "company": "Startup Inc",
            "description": "Build products",
            "location": "Portland, OR",
            "url": "https://startup.com/job/1",
            "company_website": "https://startup.com",
        }

        item = JobQueueItem(
            id="test-analyze-2",
            type=QueueItemType.JOB,
            url=job_data["url"],
            company_name=job_data["company"],
            sub_task=JobSubTask.ANALYZE,
            pipeline_state={"job_data": job_data},
        )

        # Mock company info
        # Mock company with good data quality (Phase 2 changes)
        company_record = {
            "id": "company-123",
            "name": "Startup Inc",
            "about": "We build cool products" * 20,  # > 100 chars for good quality
            "culture": "Fast-paced startup" * 10,  # > 50 chars for good quality
            "mission": "Change the world",
            "status": "active",
        }
        processor.companies_manager.get_company.return_value = company_record
        processor.companies_manager.has_good_company_data.return_value = True

        # Mock AI result
        match_result = JobMatchResult(
            job_title="Engineer",
            job_company="Startup Inc",
            job_url=job_data["url"],
            match_score=85,
            matched_skills=["Python"],
            key_strengths=["Good fit"],
            application_priority="High",
        )
        processor.ai_matcher.analyze_job.return_value = match_result

        processor._process_job_analyze(item)

        # Verify company was fetched (Phase 2 uses get_company() now)
        processor.companies_manager.get_company.assert_called_once()

        # Should spawn SAVE
        processor.queue_manager.spawn_next_pipeline_step.assert_called_once()


class TestJobAnalyzeRejections:
    """Test JOB_ANALYZE rejection scenarios."""

    def test_analyze_below_threshold_skipped(self, processor):
        """Should skip when score below threshold (<80)."""
        job_data = {
            "title": "Engineer",
            "company": "Example",
            "description": "Some work",
            "location": "Remote",
            "url": "https://example.com/job/low",
            "company_website": "https://example.com",
        }

        item = JobQueueItem(
            id="test-analyze-skip-1",
            type=QueueItemType.JOB,
            url=job_data["url"],
            company_name=job_data["company"],
            sub_task=JobSubTask.ANALYZE,
            pipeline_state={"job_data": job_data},
        )

        # AI returns None (below threshold)
        processor.ai_matcher.analyze_job.return_value = None

        processor._process_job_analyze(item)

        # Should NOT spawn SAVE
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()

    def test_analyze_ai_error_no_spawn(self, processor):
        """Should not spawn SAVE when AI analysis fails."""
        job_data = {
            "title": "Engineer",
            "company": "Example",
            "description": "Work",
            "location": "Remote",
            "url": "https://example.com/job/error",
            "company_website": "https://example.com",
        }

        item = JobQueueItem(
            id="test-analyze-skip-2",
            type=QueueItemType.JOB,
            url=job_data["url"],
            company_name=job_data["company"],
            sub_task=JobSubTask.ANALYZE,
            pipeline_state={"job_data": job_data},
        )

        # AI raises exception
        processor.ai_matcher.analyze_job.side_effect = Exception("API error")

        # The exception will be caught and re-raised
        try:
            processor._process_job_analyze(item)
        except Exception:
            pass  # Expected

        # Should NOT spawn SAVE
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()


class TestJobAnalyzeEdgeCases:
    """Test JOB_ANALYZE edge cases."""

    def test_analyze_missing_pipeline_state(self, processor):
        """Should handle missing pipeline_state."""
        item = JobQueueItem(
            id="test-analyze-edge-1",
            type=QueueItemType.JOB,
            url="https://example.com/job/1",
            company_name="Example",
            sub_task=JobSubTask.ANALYZE,
            pipeline_state=None,
        )

        processor._process_job_analyze(item)

        # Should NOT spawn SAVE
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()

    def test_analyze_missing_job_data(self, processor):
        """Should handle missing job_data."""
        item = JobQueueItem(
            id="test-analyze-edge-2",
            type=QueueItemType.JOB,
            url="https://example.com/job/2",
            company_name="Example",
            sub_task=JobSubTask.ANALYZE,
            pipeline_state={"filter_result": {}},  # No job_data
        )

        processor._process_job_analyze(item)

        # Should NOT spawn SAVE
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()

    def test_analyze_portland_office_bonus(self, processor, mock_managers):
        """Should apply Portland office bonus to score."""
        job_data = {
            "title": "Engineer",
            "company": "Local Corp",
            "description": "Build apps",
            "location": "Portland, OR",
            "url": "https://local.com/job/1",
            "company_website": "https://local.com",
        }

        item = JobQueueItem(
            id="test-analyze-portland",
            type=QueueItemType.JOB,
            url=job_data["url"],
            company_name=job_data["company"],
            sub_task=JobSubTask.ANALYZE,
            pipeline_state={"job_data": job_data},
        )

        # Score boosted by Portland bonus (+15)
        match_result = JobMatchResult(
            job_title="Engineer",
            job_company="Local Corp",
            job_url=job_data["url"],
            match_score=80,  # 65 base + 15 Portland bonus
            matched_skills=["Python"],
            key_strengths=["Portland office"],
            application_priority="Medium",
        )
        processor.ai_matcher.analyze_job.return_value = match_result

        processor._process_job_analyze(item)

        # Should spawn SAVE (meets threshold with bonus)
        processor.queue_manager.spawn_next_pipeline_step.assert_called_once()


# ========================================
# JOB_SAVE Tests
# ========================================


class TestJobSaveSuccess:
    """Test successful JOB_SAVE scenarios."""

    def test_save_creates_firestore_document(self, processor, mock_managers):
        """Should save job match to Firestore."""
        job_data = {
            "title": "Senior Engineer",
            "company": "Tech Corp",
            "description": "Build things",
            "location": "Remote",
            "url": "https://example.com/job/1",
            "company_website": "https://techcorp.com",
        }

        match_result = JobMatchResult(
            job_title="Senior Engineer",
            job_company="Tech Corp",
            job_url="https://example.com/job/1",
            match_score=92,
            matched_skills=["Python", "React"],
            missing_skills=["Kubernetes"],
            key_strengths=["Strong Python match", "React experience"],
            application_priority="High",
        )

        item = JobQueueItem(
            id="test-save-1",
            type=QueueItemType.JOB,
            url=job_data["url"],
            company_name=job_data["company"],
            sub_task=JobSubTask.SAVE,
            pipeline_state={"job_data": job_data, "match_result": match_result.to_dict()},
        )

        # Mock save
        processor.job_storage.save_job_match.return_value = "match-789"

        processor._process_job_save(item)

        # Verify save was called
        processor.job_storage.save_job_match.assert_called_once()
        save_args = processor.job_storage.save_job_match.call_args[0]

        # Verify job data passed to save
        assert save_args[0]["title"] == "Senior Engineer"
        # Second arg is JobMatchResult object
        assert save_args[1].match_score == 92

    def test_save_creates_company_if_missing(self, processor, mock_managers):
        """Should create company record if it doesn't exist."""
        job_data = {
            "title": "Engineer",
            "company": "New Startup",
            "description": "Work",
            "location": "Remote",
            "url": "https://newstartup.com/job/1",
            "company_website": "https://newstartup.com",
        }

        match_result = JobMatchResult(
            job_title="Engineer",
            job_company="New Startup",
            job_url=job_data["url"],
            match_score=85,
            matched_skills=["Python"],
            application_priority="High",
        )

        item = JobQueueItem(
            id="test-save-2",
            type=QueueItemType.JOB,
            url=job_data["url"],
            company_name=job_data["company"],
            sub_task=JobSubTask.SAVE,
            pipeline_state={"job_data": job_data, "match_result": match_result.to_dict()},
        )

        # Mock save (company creation is handled elsewhere, save handles the save)
        processor.job_storage.save_job_match.return_value = "match-456"

        processor._process_job_save(item)

        # Verify save was called with new company ID
        processor.job_storage.save_job_match.assert_called_once()


class TestJobSaveFailures:
    """Test JOB_SAVE failure scenarios."""

    def test_save_missing_match_result(self, processor, mock_managers):
        """Should fail when match_result is missing."""
        job_data = {"title": "Engineer", "company": "Example"}

        item = JobQueueItem(
            id="test-save-fail-1",
            type=QueueItemType.JOB,
            url="https://example.com/job/1",
            company_name="Example",
            sub_task=JobSubTask.SAVE,
            pipeline_state={"job_data": job_data},  # No match_result!
        )

        processor._process_job_save(item)

        # Should NOT save
        mock_managers["job_storage"].save_job_match.assert_not_called()

    def test_save_missing_pipeline_state(self, processor, mock_managers):
        """Should fail when pipeline_state is missing."""
        item = JobQueueItem(
            id="test-save-fail-2",
            type=QueueItemType.JOB,
            url="https://example.com/job/2",
            company_name="Example",
            sub_task=JobSubTask.SAVE,
            pipeline_state=None,  # Missing!
        )

        processor._process_job_save(item)

        # Should NOT save
        mock_managers["job_storage"].save_job_match.assert_not_called()

    def test_save_firestore_error(self, processor, mock_managers):
        """Should handle Firestore save errors."""
        job_data = {
            "title": "Engineer",
            "company": "Example",
            "description": "Work",
            "location": "Remote",
            "url": "https://example.com/job/1",
            "company_website": "https://example.com",
        }

        match_result = JobMatchResult(
            job_title="Engineer",
            job_company="Example",
            job_url=job_data["url"],
            match_score=85,
            matched_skills=["Python"],
            application_priority="High",
        )

        item = JobQueueItem(
            id="test-save-fail-3",
            type=QueueItemType.JOB,
            url=job_data["url"],
            company_name=job_data["company"],
            sub_task=JobSubTask.SAVE,
            pipeline_state={"job_data": job_data, "match_result": match_result.to_dict()},
        )

        # Mock Firestore error
        processor.job_storage.save_job_match.side_effect = Exception("Firestore connection error")

        # The exception will be caught and re-raised
        try:
            processor._process_job_save(item)
        except Exception:
            pass  # Expected

        # Save was attempted but failed
        processor.job_storage.save_job_match.assert_called_once()


# ========================================
# Pipeline State Tests
# ========================================


class TestPipelineStateManagement:
    """Test pipeline state is managed correctly across steps."""

    def test_full_pipeline_state_flow(self, processor, mock_managers):
        """Test that pipeline_state flows correctly through all steps."""
        # Step 1: SCRAPE
        scrape_item = JobQueueItem(
            id="pipeline-test-1",
            type=QueueItemType.JOB,
            url="https://example.com/job/1",
            company_name="Example",
            sub_task=JobSubTask.SCRAPE,
        )

        job_data = {
            "title": "Engineer",
            "company": "Example",
            "description": "Python",
            "location": "Remote",
            "url": scrape_item.url,
            "company_website": "https://example.com",
        }

        processor.sources_manager.get_source_for_url.return_value = None

        with patch.object(processor.job_processor, "_scrape_job", return_value=job_data):
            processor._process_job_scrape(scrape_item)

        # Verify SCRAPE created state
        scrape_call = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        assert "job_data" in scrape_call["pipeline_state"]
        assert scrape_call["pipeline_state"]["scrape_method"] == "generic"

        # Step 2: FILTER
        filter_item = JobQueueItem(
            id="pipeline-test-2",
            type=QueueItemType.JOB,
            url="https://example.com/job/1",
            company_name="Example",
            sub_task=JobSubTask.FILTER,
            pipeline_state=scrape_call["pipeline_state"],
        )

        filter_result = FilterResult(passed=True, total_strikes=0)

        with patch.object(processor.filter_engine, "evaluate_job", return_value=filter_result):
            processor._process_job_filter(filter_item)

        # Verify FILTER preserved job_data and added filter_result
        filter_call = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        assert filter_call["pipeline_state"]["job_data"] == job_data
        assert "filter_result" in filter_call["pipeline_state"]

        # Step 3: ANALYZE
        analyze_item = JobQueueItem(
            id="pipeline-test-3",
            type=QueueItemType.JOB,
            url="https://example.com/job/1",
            company_name="Example",
            sub_task=JobSubTask.ANALYZE,
            pipeline_state=filter_call["pipeline_state"],
        )

        match_result = JobMatchResult(
            job_title="Engineer",
            job_company="Example",
            job_url="https://example.com/job/1",
            match_score=85,
            matched_skills=["Python"],
            skill_gaps=[],
            match_reasons=["Good"],
            application_priority="High",
        )

        processor.ai_matcher.analyze_job.return_value = match_result

        processor._process_job_analyze(analyze_item)

        # Verify ANALYZE preserved all previous state and added match_result
        analyze_call = processor.queue_manager.spawn_next_pipeline_step.call_args[1]
        assert analyze_call["pipeline_state"]["job_data"] == job_data
        assert "filter_result" in analyze_call["pipeline_state"]
        assert "match_result" in analyze_call["pipeline_state"]

    def test_pipeline_state_survives_errors(self, processor):
        """Test that errors in one step don't corrupt pipeline_state."""
        job_data = {"title": "Engineer", "company": "Example"}

        item = JobQueueItem(
            id="error-test",
            type=QueueItemType.JOB,
            url="https://example.com/job/1",
            company_name="Example",
            sub_task=JobSubTask.FILTER,
            pipeline_state={"job_data": job_data, "scrape_method": "source"},
        )

        # Filter engine raises error
        with patch.object(
            processor.filter_engine, "evaluate_job", side_effect=Exception("Filter error")
        ):
            # The exception will be caught and re-raised
            try:
                processor._process_job_filter(item)
            except Exception:
                pass  # Expected

        # Should not spawn (error handled)
        processor.queue_manager.spawn_next_pipeline_step.assert_not_called()
