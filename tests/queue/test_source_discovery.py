"""Integration tests for source discovery processor."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from job_finder.job_queue.models import (
    JobQueueItem,
    QueueItemType,
    QueueStatus,
    SourceDiscoveryConfig,
    SourceTypeHint,
)
from job_finder.job_queue.processor import QueueItemProcessor


@pytest.fixture
def mock_dependencies():
    """Create mocked dependencies for processor."""
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
def processor(mock_dependencies):
    """Create processor with mocked dependencies."""
    # Create processor with correct constructor signature
    return QueueItemProcessor(
        queue_manager=mock_dependencies["queue_manager"],
        config_loader=mock_dependencies["config_loader"],
        job_storage=mock_dependencies["job_storage"],
        companies_manager=mock_dependencies["companies_manager"],
        sources_manager=mock_dependencies["sources_manager"],
        company_info_fetcher=mock_dependencies["company_info_fetcher"],
        ai_matcher=mock_dependencies["ai_matcher"],
        profile=mock_dependencies["profile"],
    )


class TestSourceDiscoveryRouting:
    """Test that SOURCE_DISCOVERY items are routed correctly."""

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    def test_routes_source_discovery_type(self, processor, mock_dependencies):
        """Should route SOURCE_DISCOVERY type to discovery processor."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="https://boards.greenhouse.io/stripe",
                type_hint=SourceTypeHint.AUTO,
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Mock the discovery method to avoid actual HTTP requests
        with patch.object(
            processor, "_process_source_discovery", return_value=None
        ) as mock_discovery:
            processor.process_item(item)

            # Should have called discovery processor
            mock_discovery.assert_called_once_with(item)

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    def test_requires_source_discovery_config(self, processor, mock_dependencies):
        """Should fail if source_discovery_config is missing."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=None,  # Missing config
        )

        processor.process_item(item)

        # Should not have updated to processing (early return)
        mock_dependencies["queue_manager"].update_status.assert_not_called()


class TestGreenhouseDiscovery:
    """Test Greenhouse source discovery."""

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    @patch("requests.get")
    def test_discovers_greenhouse_source_successfully(self, mock_get, processor, mock_dependencies):
        """Should discover and create Greenhouse source."""
        # Setup
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            submitted_by="user-456",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="https://boards.greenhouse.io/stripe",
                type_hint=SourceTypeHint.AUTO,
                company_name="Stripe",
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Mock successful Greenhouse API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jobs": [{"id": 1}, {"id": 2}]}
        mock_get.return_value = mock_response

        # Mock source creation
        mock_dependencies["sources_manager"].create_from_discovery.return_value = "source-789"

        # Execute
        processor.process_item(item)

        # Verify API was called
        mock_get.assert_called_once()
        assert "boards-api.greenhouse.io/v1/boards/stripe/jobs" in mock_get.call_args[0][0]

        # Verify source was created
        mock_dependencies["sources_manager"].create_from_discovery.assert_called_once()
        call_kwargs = mock_dependencies["sources_manager"].create_from_discovery.call_args[1]
        assert call_kwargs["name"] == "Stripe Greenhouse"
        assert call_kwargs["source_type"] == "greenhouse"
        assert call_kwargs["config"]["board_token"] == "stripe"
        assert call_kwargs["discovery_confidence"] == "high"
        assert call_kwargs["enabled"] is True

        # Verify queue item updated to success
        mock_dependencies["queue_manager"].update_status.assert_called()
        status_call = mock_dependencies["queue_manager"].update_status.call_args
        assert status_call[0][0] == "test-123"  # item_id
        assert status_call[0][1] == QueueStatus.SUCCESS
        assert status_call[0][2] == "source-789"  # source_id in result_message

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    @patch("job_finder.job_queue.processor.requests")
    def test_handles_greenhouse_404(self, mock_requests, processor, mock_dependencies):
        """Should fail gracefully when Greenhouse board not found."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="https://boards.greenhouse.io/nonexistent",
                type_hint=SourceTypeHint.AUTO,
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        # Execute
        processor.process_item(item)

        # Should not create source
        mock_dependencies["sources_manager"].create_from_discovery.assert_not_called()

        # Should mark as failed
        mock_dependencies["queue_manager"].update_status.assert_called()
        status_call = mock_dependencies["queue_manager"].update_status.call_args
        assert status_call[0][1] == QueueStatus.FAILED
        assert "404" in status_call[0][2]  # Error message contains 404


class TestWorkdayDiscovery:
    """Test Workday source discovery."""

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    def test_discovers_workday_source_with_validation_required(self, processor, mock_dependencies):
        """Should create Workday source but require manual validation."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            submitted_by="user-456",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="https://netflix.wd1.myworkdayjobs.com/External",
                type_hint=SourceTypeHint.AUTO,
                company_name="Netflix",
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Mock source creation
        mock_dependencies["sources_manager"].create_from_discovery.return_value = "source-789"

        # Execute
        processor.process_item(item)

        # Verify source was created with correct settings
        mock_dependencies["sources_manager"].create_from_discovery.assert_called_once()
        call_kwargs = mock_dependencies["sources_manager"].create_from_discovery.call_args[1]
        assert call_kwargs["name"] == "Netflix Workday"
        assert call_kwargs["source_type"] == "workday"
        assert call_kwargs["config"]["company_id"] == "netflix"
        assert "netflix.wd1.myworkdayjobs.com" in call_kwargs["config"]["base_url"]
        assert call_kwargs["discovery_confidence"] == "medium"
        assert call_kwargs["enabled"] is False  # Workday requires validation
        assert call_kwargs["validation_required"] is True

        # Verify success status
        status_call = mock_dependencies["queue_manager"].update_status.call_args
        assert status_call[0][1] == QueueStatus.SUCCESS
        assert "requires manual validation" in status_call[0][2]


class TestRSSDiscovery:
    """Test RSS feed discovery."""

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    @patch("job_finder.job_queue.processor.feedparser")
    def test_discovers_rss_source_successfully(self, mock_feedparser, processor, mock_dependencies):
        """Should discover and validate RSS feed."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="https://example.com/jobs.xml",
                type_hint=SourceTypeHint.AUTO,
                company_name="Example Corp",
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Mock valid RSS feed
        mock_feed = Mock()
        mock_feed.bozo = False  # No parse errors
        mock_feed.entries = [{"title": "Job 1"}, {"title": "Job 2"}]
        mock_feedparser.parse.return_value = mock_feed

        # Mock source creation
        mock_dependencies["sources_manager"].create_from_discovery.return_value = "source-789"

        # Execute
        processor.process_item(item)

        # Verify feed was parsed
        mock_feedparser.parse.assert_called_once_with("https://example.com/jobs.xml")

        # Verify source was created
        mock_dependencies["sources_manager"].create_from_discovery.assert_called_once()
        call_kwargs = mock_dependencies["sources_manager"].create_from_discovery.call_args[1]
        assert call_kwargs["name"] == "Example Corp Feed"
        assert call_kwargs["source_type"] == "rss"
        assert call_kwargs["config"]["url"] == "https://example.com/jobs.xml"
        assert call_kwargs["discovery_confidence"] == "high"
        assert call_kwargs["enabled"] is True

        # Verify success
        status_call = mock_dependencies["queue_manager"].update_status.call_args
        assert status_call[0][1] == QueueStatus.SUCCESS
        assert "2 entries" in status_call[0][2]

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    @patch("job_finder.job_queue.processor.feedparser")
    def test_handles_invalid_rss_feed(self, mock_feedparser, processor, mock_dependencies):
        """Should fail when RSS feed is invalid."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="https://example.com/invalid.xml",
                type_hint=SourceTypeHint.AUTO,
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Mock invalid RSS feed
        mock_feed = Mock()
        mock_feed.bozo = True  # Parse errors
        mock_feed.bozo_exception = Exception("Invalid XML")
        mock_feedparser.parse.return_value = mock_feed

        # Execute
        processor.process_item(item)

        # Should not create source
        mock_dependencies["sources_manager"].create_from_discovery.assert_not_called()

        # Should mark as failed
        status_call = mock_dependencies["queue_manager"].update_status.call_args
        assert status_call[0][1] == QueueStatus.FAILED
        assert "Invalid RSS feed" in status_call[0][2]

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    @patch("job_finder.job_queue.processor.feedparser")
    def test_handles_empty_rss_feed(self, mock_feedparser, processor, mock_dependencies):
        """Should fail when RSS feed has no entries."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="https://example.com/empty.xml",
                type_hint=SourceTypeHint.AUTO,
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Mock empty RSS feed
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = []  # No entries
        mock_feedparser.parse.return_value = mock_feed

        # Execute
        processor.process_item(item)

        # Should not create source
        mock_dependencies["sources_manager"].create_from_discovery.assert_not_called()

        # Should mark as failed
        status_call = mock_dependencies["queue_manager"].update_status.call_args
        assert status_call[0][1] == QueueStatus.FAILED
        assert "empty" in status_call[0][2].lower()


class TestGenericDiscovery:
    """Test generic HTML source discovery with AI."""

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    @patch("job_finder.job_queue.processor.SelectorDiscovery")
    @patch("job_finder.job_queue.processor.requests")
    def test_discovers_generic_source_with_high_confidence(
        self, mock_requests, mock_selector_discovery, processor, mock_dependencies
    ):
        """Should discover generic source with AI selectors."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="https://example.com/careers",
                type_hint=SourceTypeHint.AUTO,
                company_name="Example Corp",
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Job listings here</html>"
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        # Mock AI selector discovery
        mock_discovery_instance = Mock()
        mock_discovery_instance.discover_selectors.return_value = {
            "selectors": {
                "title": ".job-title",
                "company": ".company-name",
                "description": ".job-desc",
            },
            "confidence": "high",
        }
        mock_selector_discovery.return_value = mock_discovery_instance

        # Mock source creation
        mock_dependencies["sources_manager"].create_from_discovery.return_value = "source-789"

        # Execute
        processor.process_item(item)

        # Verify HTML was fetched
        mock_requests.get.assert_called_once_with("https://example.com/careers", timeout=30)

        # Verify AI was used
        mock_discovery_instance.discover_selectors.assert_called_once()

        # Verify source was created
        mock_dependencies["sources_manager"].create_from_discovery.assert_called_once()
        call_kwargs = mock_dependencies["sources_manager"].create_from_discovery.call_args[1]
        assert call_kwargs["name"] == "Example Corp Careers"
        assert call_kwargs["source_type"] == "scraper"
        assert call_kwargs["config"]["url"] == "https://example.com/careers"
        assert call_kwargs["config"]["selectors"]["title"] == ".job-title"
        assert call_kwargs["discovery_confidence"] == "high"
        assert call_kwargs["enabled"] is True  # High confidence = auto-enabled

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    @patch("job_finder.job_queue.processor.SelectorDiscovery")
    @patch("job_finder.job_queue.processor.requests")
    def test_requires_validation_for_medium_confidence(
        self, mock_requests, mock_selector_discovery, processor, mock_dependencies
    ):
        """Should require validation for medium confidence discoveries."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="https://example.com/jobs",
                type_hint=SourceTypeHint.AUTO,
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Job listings</html>"
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        # Mock AI discovery with medium confidence
        mock_discovery_instance = Mock()
        mock_discovery_instance.discover_selectors.return_value = {
            "selectors": {"title": ".maybe-title"},
            "confidence": "medium",
        }
        mock_selector_discovery.return_value = mock_discovery_instance

        # Mock source creation
        mock_dependencies["sources_manager"].create_from_discovery.return_value = "source-789"

        # Execute
        processor.process_item(item)

        # Verify source requires validation
        call_kwargs = mock_dependencies["sources_manager"].create_from_discovery.call_args[1]
        assert call_kwargs["discovery_confidence"] == "medium"
        assert call_kwargs["enabled"] is False  # Medium = not auto-enabled
        assert call_kwargs["validation_required"] is True

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    @patch("job_finder.job_queue.processor.SelectorDiscovery")
    @patch("job_finder.job_queue.processor.requests")
    def test_handles_ai_discovery_failure(
        self, mock_requests, mock_selector_discovery, processor, mock_dependencies
    ):
        """Should fail when AI cannot discover selectors."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="https://example.com/careers",
                type_hint=SourceTypeHint.AUTO,
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>No job listings</html>"
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        # Mock AI discovery failure
        mock_discovery_instance = Mock()
        mock_discovery_instance.discover_selectors.return_value = None
        mock_selector_discovery.return_value = mock_discovery_instance

        # Execute
        processor.process_item(item)

        # Should not create source
        mock_dependencies["sources_manager"].create_from_discovery.assert_not_called()

        # Should mark as failed
        status_call = mock_dependencies["queue_manager"].update_status.call_args
        assert status_call[0][1] == QueueStatus.FAILED
        assert "AI selector discovery failed" in status_call[0][2]


class TestInvalidURLHandling:
    """Test handling of invalid URLs."""

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    def test_rejects_invalid_url(self, processor, mock_dependencies):
        """Should fail for invalid URL format."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="not a valid url",
                type_hint=SourceTypeHint.AUTO,
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Execute
        processor.process_item(item)

        # Should not create source
        mock_dependencies["sources_manager"].create_from_discovery.assert_not_called()

        # Should mark as failed
        status_call = mock_dependencies["queue_manager"].update_status.call_args
        assert status_call[0][1] == QueueStatus.FAILED
        assert "Invalid URL" in status_call[0][2]

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    def test_rejects_url_without_scheme(self, processor, mock_dependencies):
        """Should fail for URLs without http/https."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="example.com/careers",
                type_hint=SourceTypeHint.AUTO,
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Execute
        processor.process_item(item)

        # Should mark as failed
        status_call = mock_dependencies["queue_manager"].update_status.call_args
        assert status_call[0][1] == QueueStatus.FAILED


class TestCompanyAssociation:
    """Test company ID and name association."""

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    @patch("job_finder.job_queue.processor.requests")
    def test_associates_company_id(self, mock_requests, processor, mock_dependencies):
        """Should associate source with provided company ID."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="Stripe",
            company_id="company-456",
            source="user_submission",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="https://boards.greenhouse.io/stripe",
                type_hint=SourceTypeHint.AUTO,
                company_id="company-456",
                company_name="Stripe",
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Mock Greenhouse API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jobs": []}
        mock_requests.get.return_value = mock_response

        # Mock source creation
        mock_dependencies["sources_manager"].create_from_discovery.return_value = "source-789"

        # Execute
        processor.process_item(item)

        # Verify company association
        call_kwargs = mock_dependencies["sources_manager"].create_from_discovery.call_args[1]
        assert call_kwargs["company_id"] == "company-456"
        assert call_kwargs["company_name"] == "Stripe"

    @pytest.mark.skip(reason="Integration test - needs proper HTTP mocking")
    def test_infers_company_name_from_url(self, processor, mock_dependencies):
        """Should infer company name from URL if not provided."""
        item = JobQueueItem(
            id="test-123",
            type=QueueItemType.SOURCE_DISCOVERY,
            url="",
            company_name="",
            source="user_submission",
            retry_count=0,
            max_retries=3,
            status=QueueStatus.PENDING,
            source_discovery_config=SourceDiscoveryConfig(
                url="https://netflix.wd1.myworkdayjobs.com/External",
                type_hint=SourceTypeHint.AUTO,
                company_name=None,  # Not provided
                auto_enable=True,
                validation_required=False,
            ),
        )

        # Mock source creation
        mock_dependencies["sources_manager"].create_from_discovery.return_value = "source-789"

        # Execute
        processor.process_item(item)

        # Verify company name was inferred
        call_kwargs = mock_dependencies["sources_manager"].create_from_discovery.call_args[1]
        assert call_kwargs["company_name"] == "Netflix"
