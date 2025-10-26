"""Source queue item processor.

This processor handles all source-related queue items:
- Source discovery (Greenhouse, Workday, RSS, Generic HTML)
- Source scraping (fetch jobs from configured sources)

It supports multiple source types:
- Greenhouse: API-based job board (high confidence)
- Workday: ATS system (medium confidence, requires validation)
- RSS: RSS feed job boards (high confidence if valid)
- Generic: AI-powered CSS selector discovery (variable confidence)
"""

import logging
import traceback
import uuid
from typing import Any, Dict, Optional

from job_finder.exceptions import ConfigurationError, QueueProcessingError
from job_finder.job_queue.models import JobQueueItem, QueueItemType, QueueStatus

from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class SourceProcessor(BaseProcessor):
    """Processor for source discovery and scraping queue items."""

    # ============================================================
    # SOURCE DISCOVERY
    # ============================================================

    def process_source_discovery(self, item: JobQueueItem) -> None:
        """
        Process SOURCE_DISCOVERY queue item.

        Flow:
        1. Fetch URL and detect source type
        2. For known types (GH/WD/RSS): validate and create config
        3. For generic HTML: use AI selector discovery
        4. Test scrape to validate configuration
        5. Create job-source document if successful

        Args:
            item: Queue item with source_discovery_config
        """
        if not item.id or not item.source_discovery_config:
            logger.error("Cannot process SOURCE_DISCOVERY without ID or config")
            return

        config = item.source_discovery_config
        url = config.url

        logger.info(f"SOURCE_DISCOVERY: Processing {url}")

        try:
            from job_finder.utils.source_type_detector import SourceTypeDetector

            # Validate URL
            if not SourceTypeDetector.is_valid_url(url):
                self.queue_manager.update_status(
                    item.id,
                    QueueStatus.FAILED,
                    "Invalid URL format",
                    error_details=f"URL is not valid: {url}",
                )
                return

            # Detect source type
            source_type, source_config = SourceTypeDetector.detect(url, config.type_hint)

            logger.info(f"Detected source type: {source_type} for {url}")

            # Extract company name if not provided
            company_name = config.company_name or SourceTypeDetector.get_company_name_from_url(url)

            # Process based on detected type
            if source_type == "greenhouse":
                success, source_id, message = self._discover_greenhouse_source(
                    url, source_config, config, company_name, item
                )
            elif source_type == "workday":
                success, source_id, message = self._discover_workday_source(
                    url, source_config, config, company_name, item
                )
            elif source_type == "rss":
                success, source_id, message = self._discover_rss_source(
                    url, source_config, config, company_name, item
                )
            else:  # generic
                success, source_id, message = self._discover_generic_source(
                    url, source_config, config, company_name, item
                )

            if success:
                # Spawn SCRAPE_SOURCE queue item to immediately scrape the new source
                scrape_item = JobQueueItem(
                    type=QueueItemType.SCRAPE_SOURCE,
                    url="",  # Not used for SCRAPE_SOURCE
                    company_name=company_name or "Unknown",
                    source="automated_discovery",
                    scraped_data={"source_id": source_id},
                    tracking_id=str(uuid.uuid4()),  # Required for loop prevention
                )
                scrape_item_id = self.queue_manager.add_item(scrape_item)
                logger.info(f"Spawned SCRAPE_SOURCE item {scrape_item_id} for source {source_id}")

                # Update queue item with success
                self.queue_manager.update_status(
                    item.id,
                    QueueStatus.SUCCESS,
                    source_id,  # Return source ID in result_message for portfolio
                    scraped_data={"source_id": source_id, "source_type": source_type},
                )
                logger.info(f"SOURCE_DISCOVERY complete: Created source {source_id}")
            else:
                # Discovery failed
                self.queue_manager.update_status(
                    item.id, QueueStatus.FAILED, message, error_details=f"Source: {url}"
                )
                logger.warning(f"SOURCE_DISCOVERY failed: {message}")

        except Exception as e:
            logger.error(f"Error in SOURCE_DISCOVERY: {e}")
            raise

    def _discover_greenhouse_source(
        self,
        url: str,
        source_config: Dict[str, str],
        discovery_config: Any,
        company_name: Optional[str],
        item: "JobQueueItem",
    ) -> tuple[bool, Optional[str], str]:
        """
        Discover and validate Greenhouse source.

        Args:
            url: Greenhouse board URL
            source_config: Extracted config with board_token
            discovery_config: SourceDiscoveryConfig from queue item
            company_name: Company name
            item: Current queue item

        Returns:
            (success, source_id, message)
        """
        try:
            import requests

            board_token = source_config.get("board_token")
            if not board_token:
                return False, None, "Could not extract board_token from URL"

            # Validate by fetching Greenhouse API
            api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"

            response = requests.get(api_url, timeout=10)

            if response.status_code != 200:
                return (
                    False,
                    None,
                    f"Greenhouse board not found (HTTP {response.status_code})",
                )

            jobs = response.json().get("jobs", [])

            logger.info(f"Greenhouse board validated: {len(jobs)} jobs found")

            # Create source
            source_name = (
                f"{company_name or board_token} Greenhouse"
                if company_name
                else f"{board_token} Greenhouse"
            )

            source_id = self.sources_manager.create_from_discovery(
                name=source_name,
                source_type="greenhouse",
                config={"board_token": board_token},
                discovered_via=item.source or "user_submission",
                discovered_by=item.submitted_by,
                discovery_confidence="high",  # Greenhouse is reliable
                discovery_queue_item_id=item.id,
                company_id=discovery_config.company_id,
                company_name=company_name,
                enabled=discovery_config.auto_enable,
                validation_required=discovery_config.validation_required,
            )

            return True, source_id, f"Greenhouse source created ({len(jobs)} jobs available)"

        except Exception as e:
            logger.error(f"Error discovering Greenhouse source: {e}")
            return False, None, f"Error validating Greenhouse board: {str(e)}"

    def _discover_workday_source(
        self,
        url: str,
        source_config: Dict[str, str],
        discovery_config: Any,
        company_name: Optional[str],
        item: "JobQueueItem",
    ) -> tuple[bool, Optional[str], str]:
        """
        Discover and validate Workday source.

        Args:
            url: Workday board URL
            source_config: Extracted config with company_id, base_url
            discovery_config: SourceDiscoveryConfig from queue item
            company_name: Company name
            item: Current queue item

        Returns:
            (success, source_id, message)
        """
        try:
            # For Workday, we'll do basic validation
            # Full Workday scraping requires more complex logic
            company_id = source_config.get("company_id")
            base_url = source_config.get("base_url")

            if not company_id or not base_url:
                return False, None, "Could not extract company_id or base_url from URL"

            # Create source (enable with medium confidence - requires testing)
            source_name = f"{company_name or company_id} Workday"

            source_id = self.sources_manager.create_from_discovery(
                name=source_name,
                source_type="workday",
                config={"company_id": company_id, "base_url": base_url},
                discovered_via=item.source or "user_submission",
                discovered_by=item.submitted_by,
                discovery_confidence="medium",  # Workday needs validation
                discovery_queue_item_id=item.id,
                company_id=discovery_config.company_id,
                company_name=company_name,
                enabled=False,  # Workday requires manual validation
                validation_required=True,
            )

            return (
                True,
                source_id,
                "Workday source created (requires manual validation before enabling)",
            )

        except Exception as e:
            logger.error(f"Error discovering Workday source: {e}")
            return False, None, f"Error validating Workday board: {str(e)}"

    def _discover_rss_source(
        self,
        url: str,
        source_config: Dict[str, str],
        discovery_config: Any,
        company_name: Optional[str],
        item: "JobQueueItem",
    ) -> tuple[bool, Optional[str], str]:
        """
        Discover and validate RSS source.

        Args:
            url: RSS feed URL
            source_config: Config with RSS URL
            discovery_config: SourceDiscoveryConfig from queue item
            company_name: Company name
            item: Current queue item

        Returns:
            (success, source_id, message)
        """
        try:
            import feedparser

            # Parse RSS feed
            feed = feedparser.parse(url)

            if feed.bozo:  # Feed has errors
                return False, None, f"Invalid RSS feed: {feed.bozo_exception}"

            if not feed.entries:
                return False, None, "RSS feed is empty (no entries found)"

            logger.info(f"RSS feed validated: {len(feed.entries)} entries found")

            # Create source
            source_name = f"{company_name or 'RSS'} Feed"

            source_id = self.sources_manager.create_from_discovery(
                name=source_name,
                source_type="rss",
                config={"url": url, "parse_format": "standard"},
                discovered_via=item.source or "user_submission",
                discovered_by=item.submitted_by,
                discovery_confidence="high",  # RSS is reliable if valid
                discovery_queue_item_id=item.id,
                company_id=discovery_config.company_id,
                company_name=company_name,
                enabled=discovery_config.auto_enable,
                validation_required=discovery_config.validation_required,
            )

            return True, source_id, f"RSS source created ({len(feed.entries)} entries available)"

        except Exception as e:
            logger.error(f"Error discovering RSS source: {e}")
            return False, None, f"Error validating RSS feed: {str(e)}"

    def _discover_generic_source(
        self,
        url: str,
        source_config: Dict[str, str],
        discovery_config: Any,
        company_name: Optional[str],
        item: "JobQueueItem",
    ) -> tuple[bool, Optional[str], str]:
        """
        Discover generic HTML source using AI selector discovery.

        Args:
            url: Career page URL
            source_config: Config with base_url
            discovery_config: SourceDiscoveryConfig from queue item
            company_name: Company name
            item: Current queue item

        Returns:
            (success, source_id, message)
        """
        try:
            import requests
            from job_finder.ai.selector_discovery import SelectorDiscovery

            # Fetch HTML
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            html = response.text

            # Use AI to discover selectors
            discovery = SelectorDiscovery()
            result = discovery.discover_selectors(html, url)

            if not result:
                return False, None, "AI selector discovery failed (could not find job listings)"

            selectors = result.get("selectors", {})
            confidence = result.get("confidence", "medium")

            logger.info(f"AI discovered selectors with {confidence} confidence")

            # Create source
            source_name = f"{company_name or 'Generic'} Careers"

            # Lower confidence sources should require validation
            auto_enable = discovery_config.auto_enable and confidence == "high"
            validation_required = discovery_config.validation_required or confidence != "high"

            source_id = self.sources_manager.create_from_discovery(
                name=source_name,
                source_type="scraper",
                config={
                    "url": url,
                    "method": "requests",
                    "selectors": selectors,
                    "discovered_by_ai": True,
                },
                discovered_via=item.source or "user_submission",
                discovered_by=item.submitted_by,
                discovery_confidence=confidence,
                discovery_queue_item_id=item.id,
                company_id=discovery_config.company_id,
                company_name=company_name,
                enabled=auto_enable,
                validation_required=validation_required,
            )

            status = "enabled" if auto_enable else "pending validation"
            return (
                True,
                source_id,
                f"Generic scraper source created with {confidence} confidence ({status})",
            )

        except Exception as e:
            logger.error(f"Error discovering generic source: {e}")
            return False, None, f"Error discovering selectors: {str(e)}"

    # ============================================================
    # SOURCE SCRAPING
    # ============================================================

    def process_scrape_source(self, item: JobQueueItem) -> None:
        """
        Process SCRAPE_SOURCE queue item.

        Scrapes a specific job board source and submits found jobs to the queue.

        Flow:
        1. Fetch source configuration from job-sources collection
        2. Dispatch to appropriate scraper based on source_type
        3. Submit found jobs via ScraperIntake
        4. Update source health tracking (success/failure)

        Args:
            item: Queue item with source_id or source_url
        """
        if not item.id:
            logger.error("Cannot process SCRAPE_SOURCE without ID")
            return

        source_id = item.scraped_data.get("source_id") if item.scraped_data else None
        source_url = item.url if item.url else None

        logger.info(f"SCRAPE_SOURCE: Processing source {source_id or source_url}")

        try:
            # Fetch source configuration
            if source_id:
                source = self.sources_manager.get_source_by_id(source_id)
            elif source_url:
                source = self.sources_manager.get_source_for_url(source_url)
            else:
                raise QueueProcessingError("SCRAPE_SOURCE item must have source_id or url")

            if not source:
                self.queue_manager.update_status(
                    item.id,
                    QueueStatus.FAILED,
                    "Source not found",
                    error_details=f"source_id={source_id}, url={source_url}",
                )
                return

            # Check if source is enabled
            if not source.get("enabled", False):
                logger.info(f"Skipping disabled source: {source.get('name')}")
                self.queue_manager.update_status(
                    item.id,
                    QueueStatus.SKIPPED,
                    "Source is disabled",
                )
                return

            source_type = source.get("sourceType")
            source_name = source.get("name", "Unknown")
            config = source.get("config", {})

            logger.info(f"Scraping source: {source_name} ({source_type})")

            # Create appropriate scraper and scrape jobs
            jobs = []
            try:
                if source_type == "greenhouse":
                    from job_finder.scrapers.greenhouse_scraper import GreenhouseScraper

                    board_token = config.get("board_token")
                    if not board_token:
                        raise ConfigurationError(
                            f"Source {source_name} missing board_token in config"
                        )
                    gh_scraper = GreenhouseScraper(config)
                    jobs = gh_scraper.scrape()

                elif source_type == "rss":
                    from job_finder.scrapers.rss_scraper import RSSJobScraper

                    rss_url = config.get("url")
                    if not rss_url:
                        raise ConfigurationError(f"Source {source_name} missing url in config")
                    rss_scraper = RSSJobScraper(rss_url, listing_config={})
                    jobs = rss_scraper.scrape()

                elif source_type == "workday":
                    # TODO: Implement Workday scraper
                    logger.warning(f"Workday scraper not yet implemented for {source_name}")
                    self.queue_manager.update_status(
                        item.id,
                        QueueStatus.SKIPPED,
                        "Workday scraper not yet implemented",
                    )
                    return

                else:
                    logger.warning(f"Unsupported source type: {source_type}")
                    self.queue_manager.update_status(
                        item.id,
                        QueueStatus.FAILED,
                        f"Unsupported source type: {source_type}",
                    )
                    return

                logger.info(f"Found {len(jobs)} jobs from {source_name}")

                # Submit jobs to queue using ScraperIntake
                if jobs:
                    company_id = source.get("company_id")
                    source_label = f"{source_type}:{source_name}"
                    jobs_added = self.scraper_intake.submit_jobs(
                        jobs=jobs,
                        source=source_label,
                        company_id=company_id,
                    )
                    logger.info(f"Submitted {jobs_added} jobs to queue from {source_name}")

                    # Record success in source health tracking
                    self.sources_manager.record_scraping_success(
                        source_id=source.get("id"),
                        jobs_found=jobs_added,
                    )

                    # Mark queue item as success
                    self.queue_manager.update_status(
                        item.id,
                        QueueStatus.SUCCESS,
                        f"Scraped {len(jobs)} jobs, submitted {jobs_added} to queue",
                        scraped_data={
                            "jobs_found": len(jobs),
                            "jobs_submitted": jobs_added,
                            "source_name": source_name,
                        },
                    )
                else:
                    # No jobs found - still mark as success
                    logger.info(f"No jobs found from {source_name}")
                    self.queue_manager.update_status(
                        item.id,
                        QueueStatus.SUCCESS,
                        "No jobs found",
                        scraped_data={
                            "jobs_found": 0,
                            "source_name": source_name,
                        },
                    )

            except Exception as scrape_error:
                # Record failure in source health tracking
                logger.error(f"Error scraping source {source_name}: {scrape_error}")
                self.sources_manager.record_scraping_failure(
                    source_id=source.get("id"),
                    error_message=str(scrape_error),
                )

                # Mark queue item as failed
                self.queue_manager.update_status(
                    item.id,
                    QueueStatus.FAILED,
                    f"Scraping failed: {str(scrape_error)}",
                    error_details=traceback.format_exc(),
                )

        except Exception as e:
            logger.error(f"Error in SCRAPE_SOURCE: {e}")
            raise
