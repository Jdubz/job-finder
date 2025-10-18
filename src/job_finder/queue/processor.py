"""Process queue items (jobs, companies, and scrape requests)."""

import logging
import traceback
from typing import Any, Dict, Optional

from job_finder.ai import AIJobMatcher, AITask, create_provider
from job_finder.company_info_fetcher import CompanyInfoFetcher
from job_finder.filters import StrikeFilterEngine
from job_finder.profile.schema import Profile
from job_finder.queue.config_loader import ConfigLoader
from job_finder.queue.manager import QueueManager
from job_finder.queue.models import (
    CompanySubTask,
    JobQueueItem,
    JobSubTask,
    QueueItemType,
    QueueStatus,
)
from job_finder.scrape_runner import ScrapeRunner
from job_finder.storage import FirestoreJobStorage
from job_finder.storage.companies_manager import CompaniesManager
from job_finder.storage.job_sources_manager import JobSourcesManager

logger = logging.getLogger(__name__)


class QueueItemProcessor:
    """
    Processes individual queue items (jobs, companies, and scrape requests).

    Handles scraping, AI analysis, and storage based on item type.
    """

    def __init__(
        self,
        queue_manager: QueueManager,
        config_loader: ConfigLoader,
        job_storage: FirestoreJobStorage,
        companies_manager: CompaniesManager,
        sources_manager: JobSourcesManager,
        company_info_fetcher: CompanyInfoFetcher,
        ai_matcher: AIJobMatcher,
        profile: Profile,
    ):
        """
        Initialize processor with required managers.

        Args:
            queue_manager: Queue manager for updating item status
            config_loader: Configuration loader for stop lists and filters
            job_storage: Firestore job storage
            companies_manager: Company data manager
            sources_manager: Job sources manager
            company_info_fetcher: Company info scraper
            ai_matcher: AI job matcher
            profile: User profile (for scrape requests)
        """
        self.queue_manager = queue_manager
        self.config_loader = config_loader
        self.job_storage = job_storage
        self.companies_manager = companies_manager
        self.sources_manager = sources_manager
        self.company_info_fetcher = company_info_fetcher
        self.ai_matcher = ai_matcher
        self.profile = profile

        # Initialize strike-based filter engine
        filter_config = config_loader.get_job_filters()
        tech_ranks = config_loader.get_technology_ranks()
        self.filter_engine = StrikeFilterEngine(filter_config, tech_ranks)

        # Initialize scrape runner
        self.scrape_runner = ScrapeRunner(
            ai_matcher=ai_matcher,
            job_storage=job_storage,
            companies_manager=companies_manager,
            sources_manager=sources_manager,
            company_info_fetcher=company_info_fetcher,
            profile=profile,
        )

    def process_item(self, item: JobQueueItem) -> None:
        """
        Process a queue item based on its type.

        Args:
            item: Queue item to process
        """
        if not item.id:
            logger.error("Cannot process item without ID")
            return

        # Log differently for scrape requests
        if item.type == QueueItemType.SCRAPE:
            logger.info(f"Processing queue item {item.id}: SCRAPE request")
        else:
            logger.info(f"Processing queue item {item.id}: {item.type} - {item.url[:50]}...")

        try:
            # Update status to processing
            self.queue_manager.update_status(item.id, QueueStatus.PROCESSING)

            # Check stop list (skip for SCRAPE requests)
            if item.type != QueueItemType.SCRAPE and self._should_skip_by_stop_list(item):
                self.queue_manager.update_status(
                    item.id, QueueStatus.SKIPPED, "Excluded by stop list"
                )
                return

            # Check if URL already exists in job-matches
            if item.type == QueueItemType.JOB and self.job_storage.job_exists(item.url):
                self.queue_manager.update_status(
                    item.id, QueueStatus.SKIPPED, "Job already exists in database"
                )
                return

            # Process based on type and sub_task
            if item.type == QueueItemType.COMPANY:
                # All company items must use granular pipeline
                if not item.company_sub_task:
                    raise ValueError(
                        "Company items must have company_sub_task set. "
                        "Use submit_company() which creates granular pipeline items."
                    )
                self._process_granular_company(item)
            elif item.type == QueueItemType.JOB:
                # All job items must use granular pipeline
                if not item.sub_task:
                    raise ValueError(
                        "Job items must have sub_task set. "
                        "Legacy monolithic pipeline has been removed. "
                        "Use submit_job() which creates granular pipeline items (JOB_SCRAPE)."
                    )
                self._process_granular_job(item)
            elif item.type == QueueItemType.SCRAPE:
                self._process_scrape(item)
            elif item.type == QueueItemType.SOURCE_DISCOVERY:
                self._process_source_discovery(item)
            else:
                raise ValueError(f"Unknown item type: {item.type}")

        except Exception as e:
            error_msg = str(e)
            error_details = traceback.format_exc()
            logger.error(
                f"Error processing item {item.id}: {error_msg}\n{error_details}",
                exc_info=True,
            )
            self._handle_failure(item, error_msg, error_details)

    def _should_skip_by_stop_list(self, item: JobQueueItem) -> bool:
        """
        Check if item should be skipped based on stop list.

        Args:
            item: Queue item to check

        Returns:
            True if item should be skipped, False otherwise
        """
        stop_list = self.config_loader.get_stop_list()

        # Check excluded companies
        if item.company_name:
            for excluded in stop_list["excludedCompanies"]:
                if excluded.lower() in item.company_name.lower():
                    logger.info(f"Skipping due to excluded company: {item.company_name}")
                    return True

        # Check excluded domains
        for excluded_domain in stop_list["excludedDomains"]:
            if excluded_domain.lower() in item.url.lower():
                logger.info(f"Skipping due to excluded domain: {excluded_domain}")
                return True

        # Check excluded keywords in URL
        for keyword in stop_list["excludedKeywords"]:
            if keyword.lower() in item.url.lower():
                logger.info(f"Skipping due to excluded keyword in URL: {keyword}")
                return True

        return False

    # REMOVED: Legacy _process_job() method
    # All job processing now uses granular pipeline: _process_granular_job()
    # with sub-tasks: JOB_SCRAPE → JOB_FILTER → JOB_ANALYZE → JOB_SAVE

    def _scrape_job(self, item: JobQueueItem) -> Optional[Dict[str, Any]]:
        """
        Scrape job details from URL.

        Detects job board type from URL and uses appropriate scraper.

        Args:
            item: Job queue item

        Returns:
            Job data dictionary or None if scraping failed
        """
        # If we have scraped_data from a previous scraper run, use it
        if item.scraped_data:
            logger.debug(
                f"Using cached scraped data: {item.scraped_data.get('title')} "
                f"at {item.scraped_data.get('company')}"
            )
            return item.scraped_data

        # Detect job board type and scrape
        url = item.url
        job_data = None

        try:
            # Greenhouse (MongoDB, Spotify, etc.)
            if "greenhouse" in url or "gh_jid=" in url:
                job_data = self._scrape_greenhouse_url(url)

            # WeWorkRemotely
            elif "weworkremotely.com" in url:
                job_data = self._scrape_weworkremotely_url(url)

            # Remotive
            elif "remotive.com" in url or "remotive.io" in url:
                job_data = self._scrape_remotive_url(url)

            # Generic fallback - try basic scraping
            else:
                logger.warning(f"Unknown job board URL: {url}, using generic scraper")
                job_data = self._scrape_generic_url(url)

        except Exception as e:
            logger.error(f"Error scraping job from {url}: {e}")
            return None

        if job_data:
            # Ensure URL is set
            job_data["url"] = url
            logger.debug(f"Job scraped: {job_data.get('title')} at {job_data.get('company')}")
            return job_data

        return None

    def _scrape_greenhouse_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape job details from Greenhouse URL."""
        import re

        import requests
        from bs4 import BeautifulSoup

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract job details
            title_elem = soup.find("h1", class_="app-title")
            company_elem = soup.find("span", class_="company-name")
            location_elem = soup.find("div", class_="location")
            description_elem = soup.find("div", id="content")

            return {
                "title": title_elem.text.strip() if title_elem else "Unknown",
                "company": company_elem.text.strip() if company_elem else "Unknown",
                "location": location_elem.text.strip() if location_elem else "Unknown",
                "description": (
                    description_elem.get_text(separator="\n", strip=True)
                    if description_elem
                    else ""
                ),
                "company_website": self._extract_company_domain(url),
                "url": url,
            }
        except Exception as e:
            logger.error(f"Failed to scrape Greenhouse URL {url}: {e}")
            return None

    def _scrape_weworkremotely_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape job details from WeWorkRemotely URL."""
        import requests
        from bs4 import BeautifulSoup

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract job details
            title_elem = soup.find("h1")
            company_elem = soup.find("h2")
            description_elem = soup.find("div", class_="listing-container")

            return {
                "title": title_elem.text.strip() if title_elem else "Unknown",
                "company": company_elem.text.strip() if company_elem else "Unknown",
                "location": "Remote",
                "description": (
                    description_elem.get_text(separator="\n", strip=True)
                    if description_elem
                    else ""
                ),
                "company_website": self._extract_company_domain(url),
                "url": url,
            }
        except Exception as e:
            logger.error(f"Failed to scrape WeWorkRemotely URL {url}: {e}")
            return None

    def _scrape_remotive_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape job details from Remotive URL."""
        import requests
        from bs4 import BeautifulSoup

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract job details (adjust selectors based on actual Remotive HTML)
            title_elem = soup.find("h1")
            company_elem = soup.find("a", class_="company-name")
            description_elem = soup.find("div", class_="job-description")

            return {
                "title": title_elem.text.strip() if title_elem else "Unknown",
                "company": company_elem.text.strip() if company_elem else "Unknown",
                "location": "Remote",
                "description": (
                    description_elem.get_text(separator="\n", strip=True)
                    if description_elem
                    else ""
                ),
                "company_website": self._extract_company_domain(url),
                "url": url,
            }
        except Exception as e:
            logger.error(f"Failed to scrape Remotive URL {url}: {e}")
            return None

    def _scrape_generic_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Generic fallback scraper for unknown job boards."""
        import requests
        from bs4 import BeautifulSoup

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Try to extract basic info
            title = soup.find("h1")
            description = soup.find("body")

            return {
                "title": title.text.strip() if title else "Unknown",
                "company": "Unknown",
                "location": "Unknown",
                "description": (
                    description.get_text(separator="\n", strip=True) if description else ""
                ),
                "company_website": self._extract_company_domain(url),
                "url": url,
            }
        except Exception as e:
            logger.error(f"Failed to scrape generic URL {url}: {e}")
            return None

    def _extract_company_domain(self, url: str) -> str:
        """Extract company domain from job URL."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        # Remove www. prefix
        domain = parsed.netloc.replace("www.", "")
        # For job boards, try to find actual company domain in the content
        # For now, just return the job board domain
        return f"https://{domain}"

    def _build_company_info_string(self, company_info: Dict[str, Any]) -> str:
        """
        Build formatted company info string.

        Args:
            company_info: Company data dictionary

        Returns:
            Formatted company info string
        """
        company_about = company_info.get("about", "")
        company_culture = company_info.get("culture", "")
        company_mission = company_info.get("mission", "")

        company_info_parts = []
        if company_about:
            company_info_parts.append(f"About: {company_about}")
        if company_culture:
            company_info_parts.append(f"Culture: {company_culture}")
        if company_mission:
            company_info_parts.append(f"Mission: {company_mission}")

        return "\n\n".join(company_info_parts)

    def _handle_failure(
        self, item: JobQueueItem, error_message: str, error_details: Optional[str] = None
    ) -> None:
        """
        Handle item processing failure with retry logic.

        Args:
            item: Failed queue item
            error_message: Brief error description (shown in UI)
            error_details: Detailed error information including stack trace (for debugging)
        """
        if not item.id:
            logger.error("Cannot handle failure for item without ID")
            return

        queue_settings = self.config_loader.get_queue_settings()
        max_retries = queue_settings["maxRetries"]

        # Increment retry count
        self.queue_manager.increment_retry(item.id)

        # Build context for error details
        error_context = (
            f"Queue Item: {item.id}\n"
            f"Type: {item.type}\n"
            f"URL: {item.url}\n"
            f"Company: {item.company_name}\n"
            f"Retry Count: {item.retry_count + 1}/{max_retries}\n\n"
        )

        # Check if we should retry
        if item.retry_count + 1 < max_retries:
            # Reset to pending for retry
            retry_msg = f"Processing failed. Will retry ({item.retry_count + 1}/{max_retries})"
            retry_details = (
                f"{error_context}"
                f"Error: {error_message}\n\n"
                f"This item will be automatically retried.\n\n"
                f"{'Stack Trace:\n' + error_details if error_details else ''}"
            )
            self.queue_manager.update_status(
                item.id, QueueStatus.PENDING, retry_msg, error_details=retry_details
            )
            logger.info(f"Item {item.id} will be retried (attempt {item.retry_count + 1})")
        else:
            # Max retries exceeded, mark as failed
            failed_msg = f"Failed after {max_retries} retries: {error_message}"
            failed_details = (
                f"{error_context}"
                f"Error: {error_message}\n\n"
                f"Max retries ({max_retries}) exceeded. Manual intervention may be required.\n\n"
                f"Troubleshooting:\n"
                f"1. Check if the URL is still valid\n"
                f"2. Review error details below for specific issues\n"
                f"3. Verify network connectivity and API credentials\n"
                f"4. Check if the source website has changed structure\n\n"
                f"{'Stack Trace:\n' + error_details if error_details else ''}"
            )
            self.queue_manager.update_status(
                item.id, QueueStatus.FAILED, failed_msg, error_details=failed_details
            )
            logger.error(f"Item {item.id} failed after {max_retries} retries: {error_message}")

    def _process_scrape(self, item: JobQueueItem) -> None:
        """
        Process a scrape queue item.

        Runs a scraping operation with custom configuration.

        Args:
            item: Scrape queue item
        """
        if not item.id:
            logger.error("Cannot process scrape item without ID")
            return

        # Get scrape configuration
        scrape_config = item.scrape_config
        if not scrape_config:
            # Use defaults
            from job_finder.queue.models import ScrapeConfig

            scrape_config = ScrapeConfig()

        logger.info(f"Starting scrape with config: {scrape_config.model_dump()}")

        try:
            # Override AI match score if specified
            original_min_score = self.ai_matcher.min_match_score
            if scrape_config.min_match_score is not None:
                logger.info(
                    f"Overriding min_match_score: {original_min_score} -> "
                    f"{scrape_config.min_match_score}"
                )
                self.ai_matcher.min_match_score = scrape_config.min_match_score

            # Run scrape (pass None values through, don't use defaults here)
            stats = self.scrape_runner.run_scrape(
                target_matches=scrape_config.target_matches,
                max_sources=scrape_config.max_sources,
                source_ids=scrape_config.source_ids,
            )

            # Restore original min score
            self.ai_matcher.min_match_score = original_min_score

            # Update queue item with success
            result_message = (
                f"Scrape completed: {stats['jobs_saved']} jobs saved, "
                f"{stats['sources_scraped']} sources scraped"
            )

            self.queue_manager.update_status(
                item.id, QueueStatus.SUCCESS, result_message, scraped_data=stats
            )

            logger.info(f"Scrape completed successfully: {result_message}")

        except Exception as e:
            logger.error(f"Error processing scrape request: {e}")
            raise

    # ========================================================================
    # Granular Pipeline Processors
    # ========================================================================

    def _process_granular_job(self, item: JobQueueItem) -> None:
        """
        Route granular pipeline job to appropriate processor.

        Args:
            item: Job queue item with sub_task specified
        """
        if not item.sub_task:
            raise ValueError("sub_task required for granular processing")

        if item.sub_task == JobSubTask.SCRAPE:
            self._process_job_scrape(item)
        elif item.sub_task == JobSubTask.FILTER:
            self._process_job_filter(item)
        elif item.sub_task == JobSubTask.ANALYZE:
            self._process_job_analyze(item)
        elif item.sub_task == JobSubTask.SAVE:
            self._process_job_save(item)
        else:
            raise ValueError(f"Unknown sub_task: {item.sub_task}")

    def _process_job_scrape(self, item: JobQueueItem) -> None:
        """
        JOB_SCRAPE: Fetch HTML and extract basic job data.

        Uses Claude Haiku (cheap, fast) for structured data extraction.
        Spawns JOB_FILTER as next step.

        Args:
            item: Job queue item with sub_task=SCRAPE
        """
        if not item.id:
            logger.error("Cannot process item without ID")
            return

        logger.info(f"JOB_SCRAPE: Extracting job data from {item.url[:50]}...")

        try:
            # Get source configuration for this URL
            source = self.sources_manager.get_source_for_url(item.url)

            if source:
                # Use source-specific scraping method
                job_data = self._scrape_with_source_config(item.url, source)
            else:
                # Fall back to generic scraping (or use AI extraction)
                job_data = self._scrape_job(item)

            if not job_data:
                error_msg = "Could not scrape job details from URL"
                error_details = f"Failed to extract data from: {item.url}"
                self.queue_manager.update_status(
                    item.id, QueueStatus.FAILED, error_msg, error_details=error_details
                )
                return

            # Prepare pipeline state for next step
            pipeline_state = {
                "job_data": job_data,
                "scrape_method": source.get("name") if source else "generic",
            }

            # Mark this step complete
            self.queue_manager.update_status(
                item.id,
                QueueStatus.SUCCESS,
                "Job data scraped successfully",
            )

            # Spawn next pipeline step (FILTER)
            self.queue_manager.spawn_next_pipeline_step(
                current_item=item,
                next_sub_task=JobSubTask.FILTER,
                pipeline_state=pipeline_state,
            )

            logger.info(
                f"JOB_SCRAPE complete: {job_data.get('title')} at {job_data.get('company')}"
            )

        except Exception as e:
            logger.error(f"Error in JOB_SCRAPE: {e}")
            raise

    def _process_job_filter(self, item: JobQueueItem) -> None:
        """
        JOB_FILTER: Apply strike-based filtering.

        No AI used - pure rule-based filtering.
        Spawns JOB_ANALYZE if passed, or marks FILTERED if failed.

        Args:
            item: Job queue item with sub_task=FILTER
        """
        if not item.id or not item.pipeline_state:
            logger.error("Cannot process FILTER without ID or pipeline_state")
            return

        job_data = item.pipeline_state.get("job_data")
        if not job_data:
            logger.error("No job_data in pipeline_state")
            return

        logger.info(f"JOB_FILTER: Evaluating {job_data.get('title')} at {job_data.get('company')}")

        try:
            # Run strike-based filter
            filter_result = self.filter_engine.evaluate_job(job_data)

            if not filter_result.passed:
                # Job rejected by filters
                rejection_summary = filter_result.get_rejection_summary()
                rejection_data = filter_result.to_dict()

                logger.info(f"JOB_FILTER: Rejected - {rejection_summary}")

                self.queue_manager.update_status(
                    item.id,
                    QueueStatus.FILTERED,
                    f"Rejected by filters: {rejection_summary}",
                    scraped_data={"job_data": job_data, "filter_result": rejection_data},
                )
                return

            # Filter passed - prepare for AI analysis
            pipeline_state = {
                **item.pipeline_state,
                "filter_result": filter_result.to_dict(),
            }

            # Mark this step complete
            self.queue_manager.update_status(
                item.id,
                QueueStatus.SUCCESS,
                "Passed filtering",
            )

            # Spawn next pipeline step (ANALYZE)
            self.queue_manager.spawn_next_pipeline_step(
                current_item=item,
                next_sub_task=JobSubTask.ANALYZE,
                pipeline_state=pipeline_state,
            )

            logger.info(f"JOB_FILTER complete: Passed with {filter_result.total_strikes} strikes")

        except Exception as e:
            logger.error(f"Error in JOB_FILTER: {e}")
            raise

    def _process_job_analyze(self, item: JobQueueItem) -> None:
        """
        JOB_ANALYZE: Run AI matching and resume intake generation.

        Uses Claude Sonnet (expensive, high quality) for detailed analysis.
        Spawns JOB_SAVE if score meets threshold, or marks SKIPPED if below.

        Args:
            item: Job queue item with sub_task=ANALYZE
        """
        if not item.id or not item.pipeline_state:
            logger.error("Cannot process ANALYZE without ID or pipeline_state")
            return

        job_data = item.pipeline_state.get("job_data")
        if not job_data:
            logger.error("No job_data in pipeline_state")
            return

        logger.info(f"JOB_ANALYZE: Analyzing {job_data.get('title')} at {job_data.get('company')}")

        try:
            # Ensure company exists
            company_name = job_data.get("company", item.company_name)
            company_website = job_data.get("company_website", "")

            if company_name and company_website:
                company = self.companies_manager.get_or_create_company(
                    company_name=company_name,
                    company_website=company_website,
                    fetch_info_func=self.company_info_fetcher.fetch_company_info,
                )
                company_id = company.get("id")
                job_data["companyId"] = company_id
                job_data["company_info"] = self._build_company_info_string(company)

            # Run AI matching (uses configured model - Sonnet by default)
            result = self.ai_matcher.analyze_job(job_data)

            if not result:
                # Below match threshold
                self.queue_manager.update_status(
                    item.id,
                    QueueStatus.SKIPPED,
                    f"Job score below threshold (< {self.ai_matcher.min_match_score})",
                )
                return

            # Prepare pipeline state with analysis results
            pipeline_state = {
                **item.pipeline_state,
                "match_result": result.to_dict(),
            }

            # Mark this step complete
            self.queue_manager.update_status(
                item.id,
                QueueStatus.SUCCESS,
                f"AI analysis complete (score: {result.match_score})",
            )

            # Spawn next pipeline step (SAVE)
            self.queue_manager.spawn_next_pipeline_step(
                current_item=item,
                next_sub_task=JobSubTask.SAVE,
                pipeline_state=pipeline_state,
            )

            logger.info(
                f"JOB_ANALYZE complete: Score {result.match_score}, "
                f"Priority {result.application_priority}"
            )

        except Exception as e:
            logger.error(f"Error in JOB_ANALYZE: {e}")
            raise

    def _process_job_save(self, item: JobQueueItem) -> None:
        """
        JOB_SAVE: Save job match to Firestore.

        Final step - no further spawning.

        Args:
            item: Job queue item with sub_task=SAVE
        """
        if not item.id or not item.pipeline_state:
            logger.error("Cannot process SAVE without ID or pipeline_state")
            return

        job_data = item.pipeline_state.get("job_data")
        match_result_dict = item.pipeline_state.get("match_result")

        if not job_data or not match_result_dict:
            logger.error("Missing job_data or match_result in pipeline_state")
            return

        logger.info(f"JOB_SAVE: Saving {job_data.get('title')} at {job_data.get('company')}")

        try:
            # Reconstruct JobMatchResult from dict
            from job_finder.ai.matcher import JobMatchResult

            result = JobMatchResult(**match_result_dict)

            # Save to job-matches
            doc_id = self.job_storage.save_job_match(job_data, result)

            logger.info(
                f"Job matched and saved: {job_data.get('title')} at {job_data.get('company')} "
                f"(Score: {result.match_score}, ID: {doc_id})"
            )

            self.queue_manager.update_status(
                item.id,
                QueueStatus.SUCCESS,
                f"Job saved successfully (ID: {doc_id}, Score: {result.match_score})",
            )

        except Exception as e:
            logger.error(f"Error in JOB_SAVE: {e}")
            raise

    # ========================================================================
    # Granular Company Pipeline Processors
    # ========================================================================

    def _process_granular_company(self, item: JobQueueItem) -> None:
        """
        Route granular pipeline company to appropriate processor.

        Args:
            item: Company queue item with company_sub_task specified
        """
        if not item.company_sub_task:
            raise ValueError("company_sub_task required for granular processing")

        if item.company_sub_task == CompanySubTask.FETCH:
            self._process_company_fetch(item)
        elif item.company_sub_task == CompanySubTask.EXTRACT:
            self._process_company_extract(item)
        elif item.company_sub_task == CompanySubTask.ANALYZE:
            self._process_company_analyze(item)
        elif item.company_sub_task == CompanySubTask.SAVE:
            self._process_company_save(item)
        else:
            raise ValueError(f"Unknown company_sub_task: {item.company_sub_task}")

    def _process_company_fetch(self, item: JobQueueItem) -> None:
        """
        COMPANY_FETCH: Fetch website HTML content.

        Uses cheap AI (Haiku) for dynamic content if needed.
        Spawns COMPANY_EXTRACT as next step.

        Args:
            item: Company queue item with company_sub_task=FETCH
        """
        if not item.id:
            logger.error("Cannot process item without ID")
            return

        company_name = item.company_name or "Unknown Company"
        logger.info(f"COMPANY_FETCH: Fetching website content for {company_name}")

        try:
            if not item.url:
                error_msg = "No company website URL provided"
                self.queue_manager.update_status(item.id, QueueStatus.FAILED, error_msg)
                return

            # Fetch HTML content from company pages
            pages_to_try = [
                f"{item.url}/about",
                f"{item.url}/about-us",
                f"{item.url}/company",
                f"{item.url}/careers",
                item.url,  # Homepage as fallback
            ]

            html_content = {}
            for page_url in pages_to_try:
                try:
                    content = self.company_info_fetcher._fetch_page_content(page_url)
                    if content and len(content) > 200:
                        # Extract page type from URL
                        page_type = page_url.split("/")[-1] if "/" in page_url else "homepage"
                        html_content[page_type] = content
                        logger.debug(f"Fetched {len(content)} chars from {page_url}")
                except Exception as e:
                    logger.debug(f"Failed to fetch {page_url}: {e}")
                    continue

            if not html_content:
                error_msg = "Could not fetch any content from company website"
                error_details = f"Tried pages: {', '.join(pages_to_try)}"
                self.queue_manager.update_status(
                    item.id, QueueStatus.FAILED, error_msg, error_details=error_details
                )
                return

            # Prepare pipeline state for next step
            pipeline_state = {
                "company_name": company_name,
                "company_website": item.url,
                "html_content": html_content,
            }

            # Mark this step complete
            self.queue_manager.update_status(
                item.id,
                QueueStatus.SUCCESS,
                f"Fetched {len(html_content)} pages from company website",
            )

            # Spawn next pipeline step (EXTRACT)
            self.queue_manager.spawn_next_pipeline_step(
                current_item=item,
                next_sub_task=CompanySubTask.EXTRACT,
                pipeline_state=pipeline_state,
                is_company=True,
            )

            logger.info(
                f"COMPANY_FETCH complete: Fetched {len(html_content)} pages for {company_name}"
            )

        except Exception as e:
            logger.error(f"Error in COMPANY_FETCH: {e}")
            raise

    def _process_company_extract(self, item: JobQueueItem) -> None:
        """
        COMPANY_EXTRACT: Extract company info using AI.

        Uses expensive AI (Sonnet) for accurate extraction.
        Spawns COMPANY_ANALYZE as next step.

        Args:
            item: Company queue item with company_sub_task=EXTRACT
        """
        if not item.id or not item.pipeline_state:
            logger.error("Cannot process EXTRACT without ID or pipeline_state")
            return

        company_name = item.pipeline_state.get("company_name", "Unknown Company")
        html_content = item.pipeline_state.get("html_content", {})

        logger.info(f"COMPANY_EXTRACT: Extracting company info for {company_name}")

        try:
            # Combine all HTML content
            combined_content = " ".join(html_content.values())

            # Extract company information using AI
            extracted_info = self.company_info_fetcher._extract_company_info(
                combined_content, company_name
            )

            if not extracted_info:
                error_msg = "AI extraction failed to produce company information"
                self.queue_manager.update_status(item.id, QueueStatus.FAILED, error_msg)
                return

            # Prepare pipeline state with extracted info
            pipeline_state = {
                **item.pipeline_state,
                "extracted_info": extracted_info,
            }

            # Mark this step complete
            self.queue_manager.update_status(
                item.id,
                QueueStatus.SUCCESS,
                "Company information extracted successfully",
            )

            # Spawn next pipeline step (ANALYZE)
            self.queue_manager.spawn_next_pipeline_step(
                current_item=item,
                next_sub_task=CompanySubTask.ANALYZE,
                pipeline_state=pipeline_state,
                is_company=True,
            )

            logger.info(
                f"COMPANY_EXTRACT complete: Extracted {len(extracted_info.get('about', ''))} chars "
                f"about, {len(extracted_info.get('culture', ''))} chars culture for {company_name}"
            )

        except Exception as e:
            logger.error(f"Error in COMPANY_EXTRACT: {e}")
            raise

    def _process_company_analyze(self, item: JobQueueItem) -> None:
        """
        COMPANY_ANALYZE: Analyze tech stack, job board, and priority scoring.

        Rule-based analysis (no AI cost).
        Spawns COMPANY_SAVE as next step.
        May also spawn SOURCE_DISCOVERY if job board found.

        Args:
            item: Company queue item with company_sub_task=ANALYZE
        """
        if not item.id or not item.pipeline_state:
            logger.error("Cannot process ANALYZE without ID or pipeline_state")
            return

        company_name = item.pipeline_state.get("company_name", "Unknown Company")
        company_website = item.pipeline_state.get("company_website", "")
        extracted_info = item.pipeline_state.get("extracted_info", {})
        html_content = item.pipeline_state.get("html_content", {})

        logger.info(f"COMPANY_ANALYZE: Analyzing {company_name}")

        try:
            # Detect tech stack from company info
            tech_stack = self._detect_tech_stack(extracted_info, html_content)

            # Detect job board URLs
            job_board_url = self._detect_job_board(company_website, html_content)

            # Calculate priority score
            priority_score, tier = self._calculate_company_priority(
                company_name, extracted_info, tech_stack
            )

            # Prepare analysis results
            analysis_result = {
                "tech_stack": tech_stack,
                "job_board_url": job_board_url,
                "priority_score": priority_score,
                "tier": tier,
            }

            # Prepare pipeline state with analysis
            pipeline_state = {
                **item.pipeline_state,
                "analysis_result": analysis_result,
            }

            # Mark this step complete
            self.queue_manager.update_status(
                item.id,
                QueueStatus.SUCCESS,
                f"Company analyzed (Tier {tier}, Score: {priority_score})",
            )

            # If job board found, spawn SOURCE_DISCOVERY
            if job_board_url:
                logger.info(f"Found job board for {company_name}: {job_board_url}")
                # Will be handled in COMPANY_SAVE step

            # Spawn next pipeline step (SAVE)
            self.queue_manager.spawn_next_pipeline_step(
                current_item=item,
                next_sub_task=CompanySubTask.SAVE,
                pipeline_state=pipeline_state,
                is_company=True,
            )

            logger.info(
                f"COMPANY_ANALYZE complete: {company_name} - Tier {tier}, "
                f"Score {priority_score}, Tech Stack: {len(tech_stack)} items"
            )

        except Exception as e:
            logger.error(f"Error in COMPANY_ANALYZE: {e}")
            raise

    def _process_company_save(self, item: JobQueueItem) -> None:
        """
        COMPANY_SAVE: Save company to Firestore and spawn source discovery if needed.

        Final step - may spawn SOURCE_DISCOVERY if job board found.

        Args:
            item: Company queue item with company_sub_task=SAVE
        """
        if not item.id or not item.pipeline_state:
            logger.error("Cannot process SAVE without ID or pipeline_state")
            return

        company_name = item.pipeline_state.get("company_name", "Unknown Company")
        company_website = item.pipeline_state.get("company_website", "")
        extracted_info = item.pipeline_state.get("extracted_info", {})
        analysis_result = item.pipeline_state.get("analysis_result", {})

        logger.info(f"COMPANY_SAVE: Saving {company_name}")

        try:
            # Build complete company record
            company_info = {
                "name": company_name,
                "website": company_website,
                **extracted_info,
                "techStack": analysis_result.get("tech_stack", []),
                "tier": analysis_result.get("tier", "D"),
                "priorityScore": analysis_result.get("priority_score", 0),
                "analysis_status": "complete",
            }

            # Save to companies collection
            company_id = self.companies_manager.save_company(company_info)

            logger.info(f"Company saved: {company_name} (ID: {company_id})")

            # If job board found, spawn SOURCE_DISCOVERY
            job_board_url = analysis_result.get("job_board_url")
            if job_board_url:
                from job_finder.queue.models import SourceDiscoveryConfig, SourceTypeHint

                # Create source discovery queue item
                discovery_config = SourceDiscoveryConfig(
                    url=job_board_url,
                    type_hint=SourceTypeHint.AUTO,
                    company_id=company_id,
                    company_name=company_name,
                    auto_enable=True,
                    validation_required=False,
                )

                source_item = JobQueueItem(
                    type=QueueItemType.SOURCE_DISCOVERY,
                    url="",  # Not used for source_discovery
                    company_name=company_name,
                    company_id=company_id,
                    source="automated_scan",
                    source_discovery_config=discovery_config,
                )

                self.queue_manager.add_item(source_item)
                logger.info(f"Spawned SOURCE_DISCOVERY for {company_name}: {job_board_url}")

            self.queue_manager.update_status(
                item.id,
                QueueStatus.SUCCESS,
                f"Company saved successfully (ID: {company_id})",
            )

        except Exception as e:
            logger.error(f"Error in COMPANY_SAVE: {e}")
            raise

    # ========================================================================
    # Company Analysis Helper Methods
    # ========================================================================

    def _detect_tech_stack(
        self, extracted_info: Dict[str, Any], html_content: Dict[str, str]
    ) -> list:
        """
        Detect tech stack from company info.

        Args:
            extracted_info: Extracted company information
            html_content: Raw HTML content from company pages

        Returns:
            List of detected technologies
        """
        tech_stack = []

        # Combine all text for searching
        all_text = " ".join(
            [
                extracted_info.get("about", ""),
                extracted_info.get("culture", ""),
                extracted_info.get("mission", ""),
                *html_content.values(),
            ]
        ).lower()

        # Common tech keywords to detect
        tech_keywords = {
            # Languages
            "python": ["python", "django", "flask", "fastapi"],
            "javascript": ["javascript", "js", "typescript", "ts", "node.js", "nodejs"],
            "java": ["java ", " java", "spring", "springboot"],
            "go": ["golang", " go ", "go,"],
            "rust": ["rust"],
            "ruby": ["ruby", "rails"],
            "php": ["php", "laravel"],
            "c#": ["c#", ".net", "dotnet"],
            # Frontend
            "react": ["react", "reactjs"],
            "vue": ["vue", "vuejs"],
            "angular": ["angular"],
            "svelte": ["svelte"],
            # Backend/Infra
            "docker": ["docker", "container"],
            "kubernetes": ["kubernetes", "k8s"],
            "aws": ["aws", "amazon web services"],
            "gcp": ["gcp", "google cloud"],
            "azure": ["azure", "microsoft cloud"],
            # Databases
            "postgresql": ["postgresql", "postgres"],
            "mysql": ["mysql"],
            "mongodb": ["mongodb", "mongo"],
            "redis": ["redis"],
            # ML/AI
            "machine learning": ["machine learning", "ml", "ai", "artificial intelligence"],
            "tensorflow": ["tensorflow"],
            "pytorch": ["pytorch"],
        }

        for tech, keywords in tech_keywords.items():
            for keyword in keywords:
                if keyword in all_text:
                    if tech not in tech_stack:
                        tech_stack.append(tech)
                    break

        return tech_stack

    def _detect_job_board(
        self, company_website: str, html_content: Dict[str, str]
    ) -> Optional[str]:
        """
        Detect job board URL from company website.

        Args:
            company_website: Company website URL
            html_content: HTML content from company pages

        Returns:
            Job board URL if found, None otherwise
        """
        # Check if we have careers page content
        careers_content = html_content.get("careers", "")

        # Common job board patterns
        job_board_patterns = [
            "greenhouse.io",
            "lever.co",
            "workday",
            "myworkdayjobs.com",
            "jobvite.com",
            "smartrecruiters.com",
            "breezy.hr",
            "applytojob.com",
        ]

        # Search in careers page content
        for pattern in job_board_patterns:
            if pattern in careers_content.lower():
                # Try to construct job board URL
                if "greenhouse" in pattern:
                    # Try to extract Greenhouse board token
                    import re

                    match = re.search(r"boards\.greenhouse\.io/([a-zA-Z0-9_-]+)", careers_content)
                    if match:
                        return f"https://boards.greenhouse.io/{match.group(1)}"
                elif "workday" in pattern:
                    match = re.search(r"([a-zA-Z0-9_-]+)\.myworkdayjobs\.com", careers_content)
                    if match:
                        return f"https://{match.group(1)}.myworkdayjobs.com"
                # Add more patterns as needed

        # Try common careers page URLs
        common_careers_urls = [
            f"{company_website}/careers",
            f"{company_website}/jobs",
            f"{company_website}/join",
            f"{company_website}/opportunities",
        ]

        # Check if any of these exist in the fetched content
        for page_type, content in html_content.items():
            if page_type in ["careers", "jobs", "join", "opportunities"]:
                # Found a careers page - return its URL
                return f"{company_website}/{page_type}"

        return None

    def _calculate_company_priority(
        self,
        company_name: str,
        extracted_info: Dict[str, Any],
        tech_stack: list,
    ) -> tuple[int, str]:
        """
        Calculate company priority score and tier.

        Args:
            company_name: Company name
            extracted_info: Extracted company information
            tech_stack: Detected tech stack

        Returns:
            Tuple of (priority_score, tier)
        """
        score = 0

        # Portland office bonus (+50)
        location_text = " ".join(
            [
                extracted_info.get("about", ""),
                extracted_info.get("culture", ""),
            ]
        ).lower()

        if "portland" in location_text or "oregon" in location_text:
            score += 50
            logger.debug(f"{company_name}: +50 for Portland office")

        # Tech stack alignment (up to +100)
        # User's tech ranks from config
        tech_ranks = self.config_loader.get_technology_ranks()

        for tech in tech_stack:
            tech_lower = tech.lower()
            for rank_tech, rank_score in tech_ranks.items():
                if rank_tech.lower() in tech_lower or tech_lower in rank_tech.lower():
                    score += rank_score
                    logger.debug(f"{company_name}: +{rank_score} for {tech}")

        # Company attributes
        all_text = " ".join(
            [
                extracted_info.get("about", ""),
                extracted_info.get("culture", ""),
                extracted_info.get("mission", ""),
            ]
        ).lower()

        if any(keyword in all_text for keyword in ["remote-first", "remote first", "fully remote"]):
            score += 15
            logger.debug(f"{company_name}: +15 for remote-first")

        if any(
            keyword in all_text
            for keyword in ["ai", "machine learning", "artificial intelligence", "ml"]
        ):
            score += 10
            logger.debug(f"{company_name}: +10 for AI/ML focus")

        # Determine tier
        if score >= 150:
            tier = "S"
        elif score >= 100:
            tier = "A"
        elif score >= 70:
            tier = "B"
        elif score >= 50:
            tier = "C"
        else:
            tier = "D"

        return score, tier

    # ========================================================================
    # Job Scraping Helper Methods
    # ========================================================================

    def _scrape_with_source_config(
        self, url: str, source: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Scrape job using source-specific configuration.

        Args:
            url: Job URL
            source: Source configuration with selectors

        Returns:
            Job data dict or None if scraping failed
        """
        try:
            import requests
            from bs4 import BeautifulSoup

            config = source.get("config", {})
            selectors = config.get("selectors", {})

            if not selectors:
                # No selectors, fall back to generic
                logger.debug(f"No selectors for source {source.get('name')}, using generic scrape")
                return None

            # Fetch HTML
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract data using selectors
            job_data = {
                "url": url,
                "title": self._extract_with_selector(soup, selectors.get("title")),
                "company": self._extract_with_selector(soup, selectors.get("company")),
                "location": self._extract_with_selector(soup, selectors.get("location")),
                "description": self._extract_with_selector(soup, selectors.get("description")),
                "salary": self._extract_with_selector(soup, selectors.get("salary")),
                "posted_date": self._extract_with_selector(soup, selectors.get("posted_date")),
            }

            # Remove None values
            job_data = {k: v for k, v in job_data.items() if v is not None}

            if not job_data.get("title") or not job_data.get("description"):
                logger.warning("Missing required fields (title/description) from selector scrape")
                return None

            return job_data

        except Exception as e:
            logger.error(f"Error scraping with source config: {e}")
            return None

    def _extract_with_selector(self, soup: Any, selector: Optional[str]) -> Optional[str]:
        """
        Extract text using CSS selector.

        Args:
            soup: BeautifulSoup object
            selector: CSS selector string

        Returns:
            Extracted text or None
        """
        if not selector:
            return None

        try:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        except Exception as e:
            logger.debug(f"Failed to extract with selector '{selector}': {e}")

        return None

    # ========================================================================
    # Source Discovery Processor
    # ========================================================================

    def _process_source_discovery(self, item: JobQueueItem) -> None:
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
                    url, source_config, config, company_name
                )
            elif source_type == "workday":
                success, source_id, message = self._discover_workday_source(
                    url, source_config, config, company_name
                )
            elif source_type == "rss":
                success, source_id, message = self._discover_rss_source(
                    url, source_config, config, company_name
                )
            else:  # generic
                success, source_id, message = self._discover_generic_source(
                    url, source_config, config, company_name
                )

            if success:
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
    ) -> tuple[bool, Optional[str], str]:
        """
        Discover and validate Greenhouse source.

        Args:
            url: Greenhouse board URL
            source_config: Extracted config with board_token
            discovery_config: SourceDiscoveryConfig from queue item
            company_name: Company name

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
                discovered_via=discovery_config.source or "user_submission",
                discovered_by=discovery_config.submitted_by,
                discovery_confidence="high",  # Greenhouse is reliable
                discovery_queue_item_id=discovery_config.id,
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
    ) -> tuple[bool, Optional[str], str]:
        """
        Discover and validate Workday source.

        Args:
            url: Workday board URL
            source_config: Extracted config with company_id, base_url
            discovery_config: SourceDiscoveryConfig from queue item
            company_name: Company name

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
                discovered_via=discovery_config.source or "user_submission",
                discovered_by=discovery_config.submitted_by,
                discovery_confidence="medium",  # Workday needs validation
                discovery_queue_item_id=discovery_config.id,
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
    ) -> tuple[bool, Optional[str], str]:
        """
        Discover and validate RSS source.

        Args:
            url: RSS feed URL
            source_config: Config with RSS URL
            discovery_config: SourceDiscoveryConfig from queue item
            company_name: Company name

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
                discovered_via=discovery_config.source or "user_submission",
                discovered_by=discovery_config.submitted_by,
                discovery_confidence="high",  # RSS is reliable if valid
                discovery_queue_item_id=discovery_config.id,
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
    ) -> tuple[bool, Optional[str], str]:
        """
        Discover generic HTML source using AI selector discovery.

        Args:
            url: Career page URL
            source_config: Config with base_url
            discovery_config: SourceDiscoveryConfig from queue item
            company_name: Company name

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
                discovered_via=discovery_config.source or "user_submission",
                discovered_by=discovery_config.submitted_by,
                discovery_confidence=confidence,
                discovery_queue_item_id=discovery_config.id,
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
