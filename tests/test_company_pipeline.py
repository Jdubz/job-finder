"""Tests for granular company processing pipeline."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from job_finder.queue.models import (
    CompanySubTask,
    JobQueueItem,
    QueueItemType,
    QueueStatus,
)
from job_finder.queue.processor import QueueItemProcessor


class TestCompanyPipeline:
    """Test granular company processing pipeline."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for processor."""
        return {
            "queue_manager": Mock(),
            "config_loader": Mock(),
            "job_storage": Mock(),
            "companies_manager": Mock(),
            "sources_manager": Mock(),
            "company_info_fetcher": Mock(),
            "ai_matcher": Mock(),
            "profile": Mock(),
        }

    @pytest.fixture
    def processor(self, mock_dependencies):
        """Create processor with mocked dependencies."""
        # Mock config_loader methods
        mock_dependencies["config_loader"].get_job_filters.return_value = {}
        mock_dependencies["config_loader"].get_technology_ranks.return_value = {
            "python": 30,
            "react": 25,
            "docker": 20,
        }

        return QueueItemProcessor(**mock_dependencies)

    def test_company_fetch_step(self, processor, mock_dependencies):
        """Test COMPANY_FETCH step fetches HTML content."""
        # Setup
        queue_item = JobQueueItem(
            id="test-id",
            type=QueueItemType.COMPANY,
            url="https://example.com",
            company_name="Example Corp",
            company_sub_task=CompanySubTask.FETCH,
        )

        # Mock _fetch_page_content to return content
        mock_dependencies["company_info_fetcher"]._fetch_page_content.return_value = (
            "Example Corp is a great company. We build software. " * 10  # >200 chars
        )

        # Execute
        processor._process_company_fetch(queue_item)

        # Verify status updated to SUCCESS
        assert mock_dependencies["queue_manager"].update_status.call_count >= 1
        success_call = [
            call
            for call in mock_dependencies["queue_manager"].update_status.call_args_list
            if call[0][1] == QueueStatus.SUCCESS
        ]
        assert len(success_call) > 0

        # Verify next step spawned (EXTRACT)
        assert mock_dependencies["queue_manager"].spawn_next_pipeline_step.called
        spawn_call = mock_dependencies["queue_manager"].spawn_next_pipeline_step.call_args
        assert spawn_call[1]["next_sub_task"] == CompanySubTask.EXTRACT
        assert spawn_call[1]["is_company"] is True
        assert "html_content" in spawn_call[1]["pipeline_state"]

    def test_company_extract_step(self, processor, mock_dependencies):
        """Test COMPANY_EXTRACT step uses AI to extract company info."""
        # Setup
        queue_item = JobQueueItem(
            id="test-id",
            type=QueueItemType.COMPANY,
            url="https://example.com",
            company_name="Example Corp",
            company_sub_task=CompanySubTask.EXTRACT,
            pipeline_state={
                "company_name": "Example Corp",
                "company_website": "https://example.com",
                "html_content": {
                    "about": "We are a software company",
                    "careers": "Join our team",
                },
            },
        )

        # Mock AI extraction
        mock_dependencies["company_info_fetcher"]._extract_company_info.return_value = {
            "about": "We are a software company",
            "culture": "Innovative and collaborative",
            "mission": "Build great software",
        }

        # Execute
        processor._process_company_extract(queue_item)

        # Verify AI extraction called
        assert mock_dependencies["company_info_fetcher"]._extract_company_info.called

        # Verify next step spawned (ANALYZE)
        assert mock_dependencies["queue_manager"].spawn_next_pipeline_step.called
        spawn_call = mock_dependencies["queue_manager"].spawn_next_pipeline_step.call_args
        assert spawn_call[1]["next_sub_task"] == CompanySubTask.ANALYZE
        assert "extracted_info" in spawn_call[1]["pipeline_state"]

    def test_company_analyze_step(self, processor, mock_dependencies):
        """Test COMPANY_ANALYZE step detects tech stack and job board."""
        # Setup
        queue_item = JobQueueItem(
            id="test-id",
            type=QueueItemType.COMPANY,
            url="https://example.com",
            company_name="Example Corp",
            company_sub_task=CompanySubTask.ANALYZE,
            pipeline_state={
                "company_name": "Example Corp",
                "company_website": "https://example.com",
                "html_content": {
                    "about": "We use Python and React to build software",
                    "careers": "https://boards.greenhouse.io/examplecorp",
                },
                "extracted_info": {
                    "about": "We use Python and React",
                    "culture": "Portland office",
                },
            },
        )

        # Execute
        processor._process_company_analyze(queue_item)

        # Verify tech stack detected
        spawn_call = mock_dependencies["queue_manager"].spawn_next_pipeline_step.call_args
        analysis_result = spawn_call[1]["pipeline_state"]["analysis_result"]
        assert "python" in analysis_result["tech_stack"]
        assert "react" in analysis_result["tech_stack"]

        # Verify priority score calculated (Portland bonus + tech stack)
        assert analysis_result["priority_score"] > 50  # At least Portland bonus
        assert analysis_result["tier"] in ["S", "A", "B", "C", "D"]

        # Verify job board detected
        assert analysis_result["job_board_url"] is not None

    def test_company_save_step(self, processor, mock_dependencies):
        """Test COMPANY_SAVE step saves company and spawns source discovery."""
        # Setup
        queue_item = JobQueueItem(
            id="test-id",
            type=QueueItemType.COMPANY,
            url="https://example.com",
            company_name="Example Corp",
            company_sub_task=CompanySubTask.SAVE,
            pipeline_state={
                "company_name": "Example Corp",
                "company_website": "https://example.com",
                "extracted_info": {
                    "about": "We build software",
                    "culture": "Innovative",
                },
                "analysis_result": {
                    "tech_stack": ["python", "react"],
                    "job_board_url": "https://boards.greenhouse.io/examplecorp",
                    "priority_score": 85,
                    "tier": "B",
                },
            },
        )

        # Mock companies_manager.save_company
        mock_dependencies["companies_manager"].save_company.return_value = "company-123"

        # Execute
        processor._process_company_save(queue_item)

        # Verify company saved
        assert mock_dependencies["companies_manager"].save_company.called
        save_call = mock_dependencies["companies_manager"].save_company.call_args[0][0]
        assert save_call["name"] == "Example Corp"
        assert save_call["tier"] == "B"
        assert save_call["priorityScore"] == 85
        assert save_call["techStack"] == ["python", "react"]

        # Verify SOURCE_DISCOVERY spawned
        assert mock_dependencies["queue_manager"].add_item.called
        source_item = mock_dependencies["queue_manager"].add_item.call_args[0][0]
        assert source_item.type == QueueItemType.SOURCE_DISCOVERY
        assert source_item.source_discovery_config.url == "https://boards.greenhouse.io/examplecorp"

    def test_detect_tech_stack(self, processor):
        """Test tech stack detection from company info."""
        extracted_info = {
            "about": "We use Python, React, and Docker",
            "culture": "Modern tech stack with Kubernetes",
        }
        html_content = {
            "careers": "Looking for Go developers",
        }

        tech_stack = processor._detect_tech_stack(extracted_info, html_content)

        assert "python" in tech_stack
        assert "react" in tech_stack
        assert "docker" in tech_stack
        assert "kubernetes" in tech_stack
        assert "go" in tech_stack

    def test_detect_job_board_greenhouse(self, processor):
        """Test Greenhouse job board detection."""
        html_content = {
            "careers": "Apply at https://boards.greenhouse.io/examplecorp/jobs/123456",
        }

        job_board_url = processor._detect_job_board("https://example.com", html_content)

        assert job_board_url == "https://boards.greenhouse.io/examplecorp"

    def test_calculate_company_priority(self, processor, mock_dependencies):
        """Test company priority score calculation."""
        # Portland office + Python + React should score high
        extracted_info = {
            "about": "Portland office",
            "culture": "Great team",
        }
        tech_stack = ["python", "react", "docker"]

        score, tier = processor._calculate_company_priority(
            "Example Corp", extracted_info, tech_stack
        )

        # Portland (+50) + Python (30) + React (25) + Docker (20) = 125
        assert score >= 100  # Should be in A tier range
        assert tier in ["S", "A"]

    def test_legacy_company_processing_still_works(self, processor, mock_dependencies):
        """Test that legacy monolithic company processing still works."""
        queue_item = JobQueueItem(
            id="test-id",
            type=QueueItemType.COMPANY,
            url="https://example.com",
            company_name="Example Corp",
            # No company_sub_task = legacy processing
        )

        # Mock company already exists
        mock_dependencies["companies_manager"].get_company.return_value = {
            "name": "Example Corp",
            "analysis_status": "complete",
        }

        # Execute
        processor._process_company(queue_item)

        # Verify skipped (already analyzed)
        assert mock_dependencies["queue_manager"].update_status.called
        status_call = mock_dependencies["queue_manager"].update_status.call_args
        assert status_call[0][1] == QueueStatus.SKIPPED
