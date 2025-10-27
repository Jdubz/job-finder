"""Job queue item processor.

This processor handles all job-related queue items and pipeline stages:
- Job scraping (extracting data from job URLs)
- Job filtering (strike-based rule engine)
- Job analysis (AI matching and resume intake generation)
- Job saving (persist to Firestore job-matches collection)

It supports both:
1. Decision tree routing (recommended) - auto-detects next stage from pipeline_state
2. Legacy subtask-based routing - explicit sub_task specification
"""

import logging
import traceback
from typing import Any, Dict, Optional

from google.cloud import firestore as gcloud_firestore

from job_finder.exceptions import QueueProcessingError
from job_finder.job_queue.models import (
    CompanyStatus,
    CompanySubTask,
    JobQueueItem,
    JobSubTask,
    QueueItemType,
    QueueStatus,
)

from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class JobProcessor(BaseProcessor):
    """Processor for job queue items."""

    # ============================================================
    # MAIN ROUTING
    # ============================================================

    def process_job(self, item: JobQueueItem) -> None:
        """
        Process job item using decision tree routing.

        Examines pipeline_state to determine next action:
        - No job_data → SCRAPE
        - Has job_data, no filter_result → FILTER
        - Has filter_result (passed), no match_result → ANALYZE
        - Has match_result → SAVE

        Args:
            item: Job queue item
        """
        if not item.id:
            logger.error("Cannot process item without ID")
            return

        # Get current pipeline state
        state = item.pipeline_state or {}

        # Decision tree: determine what action to take based on state
        has_job_data = "job_data" in state
        has_filter_result = "filter_result" in state
        has_match_result = "match_result" in state

        if not has_job_data:
            # Need to scrape job data
            logger.info(f"[DECISION TREE] {item.url[:50]} → SCRAPE (no job_data)")
            self._do_job_scrape(item)
        elif not has_filter_result:
            # Need to filter
            logger.info(f"[DECISION TREE] {item.url[:50]} → FILTER (has job_data)")
            self._do_job_filter(item)
        elif not has_match_result:
            # Need to analyze
            logger.info(f"[DECISION TREE] {item.url[:50]} → ANALYZE (passed filter)")
            self._do_job_analyze(item)
        else:
            # Need to save
            logger.info(f"[DECISION TREE] {item.url[:50]} → SAVE (has match_result)")
            self._do_job_save(item)

    def process_granular_job(self, item: JobQueueItem) -> None:
        """
        DEPRECATED: Route granular pipeline job to appropriate processor.

        This method is kept for backward compatibility but should not be used.
        Use process_job() instead which uses decision tree routing.

        Args:
            item: Job queue item with sub_task specified
        """
        if not item.sub_task:
            raise QueueProcessingError("sub_task required for granular processing")

        if item.sub_task == JobSubTask.SCRAPE:
            self.process_job_scrape(item)
        elif item.sub_task == JobSubTask.FILTER:
            self.process_job_filter(item)
        elif item.sub_task == JobSubTask.ANALYZE:
            self.process_job_analyze(item)
        elif item.sub_task == JobSubTask.SAVE:
            self.process_job_save(item)
        else:
            raise QueueProcessingError(f"Unknown sub_task: {item.sub_task}")

    # ============================================================
    # DECISION TREE ACTION METHODS
    # ============================================================

    def _do_job_scrape(self, item: JobQueueItem) -> None:
        """
        Scrape job data and update state.

        Sets pipeline_stage='scrape' and re-spawns same URL with job_data in state.
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

            # Update pipeline state with scraped data
            updated_state = {
                **(item.pipeline_state or {}),
                "job_data": job_data,
                "scrape_method": source.get("name") if source else "generic",
            }

            # Mark this step complete and set pipeline_stage
            self.queue_manager.update_status(
                item.id,
                QueueStatus.SUCCESS,
                "Job data scraped successfully",
                pipeline_stage="scrape",
            )

            # Re-spawn same URL with updated state
            self._respawn_job_with_state(item, updated_state, next_stage="filter")

            logger.info(
                f"JOB_SCRAPE complete: {job_data.get('title')} at {job_data.get('company')}"
            )

        except Exception as e:
            logger.error(f"Error in JOB_SCRAPE: {e}")
            raise

    def _do_job_filter(self, item: JobQueueItem) -> None:
        """
        Filter job and update state.

        Sets pipeline_stage='filter'. Re-spawns if passed, marks FILTERED if rejected.
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
                # Job rejected by filters - TERMINAL STATE
                rejection_summary = filter_result.get_rejection_summary()
                rejection_data = filter_result.to_dict()

                logger.info(f"JOB_FILTER: Rejected - {rejection_summary}")

                self.queue_manager.update_status(
                    item.id,
                    QueueStatus.FILTERED,
                    f"Rejected by filters: {rejection_summary}",
                    scraped_data={"job_data": job_data, "filter_result": rejection_data},
                    pipeline_stage="filter",
                )
                return

            # Filter passed - update state and continue
            updated_state = {
                **item.pipeline_state,
                "filter_result": filter_result.to_dict(),
            }

            # Mark this step complete
            self.queue_manager.update_status(
                item.id,
                QueueStatus.SUCCESS,
                "Passed filtering",
                pipeline_stage="filter",
            )

            # Re-spawn same URL with filter result
            self._respawn_job_with_state(item, updated_state, next_stage="analyze")

            logger.info(f"JOB_FILTER complete: Passed with {filter_result.total_strikes} strikes")

        except Exception as e:
            logger.error(f"Error in JOB_FILTER: {e}")
            raise

    def _do_job_analyze(self, item: JobQueueItem) -> None:
        """
        Analyze job with AI and update state.

        Sets pipeline_stage='analyze'. Re-spawns if matched, marks SKIPPED if low score.
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
                # Below match threshold - TERMINAL STATE
                self.queue_manager.update_status(
                    item.id,
                    QueueStatus.SKIPPED,
                    f"Job score below threshold (< {self.ai_matcher.min_match_score})",
                    pipeline_stage="analyze",
                )
                return

            # Match passed - update state and continue
            updated_state = {
                **item.pipeline_state,
                "match_result": result.to_dict(),
            }

            # Mark this step complete
            self.queue_manager.update_status(
                item.id,
                QueueStatus.SUCCESS,
                f"AI analysis complete (score: {result.match_score})",
                pipeline_stage="analyze",
            )

            # Re-spawn same URL with match result
            self._respawn_job_with_state(item, updated_state, next_stage="save")

            logger.info(
                f"JOB_ANALYZE complete: Score {result.match_score}, "
                f"Priority {result.application_priority}"
            )

        except Exception as e:
            logger.error(f"Error in JOB_ANALYZE: {e}")
            raise

    def _do_job_save(self, item: JobQueueItem) -> None:
        """
        Save job match to Firestore.

        Final step - marks item as SUCCESS, no re-spawning.
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
                pipeline_stage="save",
            )

        except Exception as e:
            logger.error(f"Error in JOB_SAVE: {e}")
            raise

    def _respawn_job_with_state(
        self,
        current_item: JobQueueItem,
        updated_state: dict,
        next_stage: str,
    ) -> None:
        """
        Requeue the same job item with updated state for next stage.

        Updates the current item's state and sets it back to PENDING so it gets
        processed again. This allows the SAME queue item to progress through all
        stages, making it easier for E2E tests to monitor.

        Args:
            current_item: Current queue item
            updated_state: Updated pipeline state
            next_stage: Next pipeline stage name (for logging)
        """
        if not current_item.id:
            logger.error("Cannot requeue item without ID")
            return

        # Update the same item with new state and mark as pending for re-processing
        update_data = {
            "pipeline_state": updated_state,
            "pipeline_stage": next_stage,
            "status": QueueStatus.PENDING.value,  # Requeue for processing
            "updated_at": gcloud_firestore.SERVER_TIMESTAMP,
        }

        try:
            doc_ref = self.queue_manager.db.collection("job-queue").document(current_item.id)
            doc_ref.update(update_data)

            logger.info(
                f"Requeued item {current_item.id} for {next_stage}: {current_item.url[:50]}"
            )
        except Exception as e:
            logger.error(f"Failed to requeue item {current_item.id}: {e}")
            raise

    # ============================================================
    # LEGACY SUBTASK-BASED METHODS
    # ============================================================

    def process_job_scrape(self, item: JobQueueItem) -> None:
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

    def process_job_filter(self, item: JobQueueItem) -> None:
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

    def process_job_analyze(self, item: JobQueueItem) -> None:
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
            # Ensure company exists and has good data
            company_name = job_data.get("company", item.company_name)
            company_website = job_data.get("company_website", "")

            if company_name and company_website:
                # Check if company exists in database
                company = self.companies_manager.get_company(company_name)

                # Handle company data quality and status
                if not company or not self.companies_manager.has_good_company_data(company):
                    # Company missing or has poor data - spawn COMPANY_FETCH for full analysis
                    logger.info(
                        f"Company {company_name} {'not found' if not company else 'has insufficient data'} "
                        f"- spawning COMPANY_FETCH queue item"
                    )

                    # Create stub if doesn't exist
                    if not company:
                        company = self.companies_manager.create_company_stub(
                            company_name=company_name,
                            company_website=company_website,
                        )

                    # Spawn COMPANY_FETCH queue item for full analysis
                    company_item = self.queue_manager.spawn_item_safely(
                        current_item=item,
                        new_item_data={
                            "type": QueueItemType.COMPANY.value,
                            "url": company_website,
                            "company_name": company_name,
                            "company_id": company.get("id"),
                            "company_sub_task": CompanySubTask.FETCH.value,
                            "source": "job_spawned",
                        },
                    )

                    if company_item:
                        logger.info(f"Spawned COMPANY_FETCH item {company_item} for {company_name}")

                    # Use stub data for now (will have minimal info)
                    company_id = company.get("id")
                    job_data["companyId"] = company_id
                    job_data["company_info"] = self._build_company_info_string(company)

                elif company.get("status") in [
                    CompanyStatus.PENDING.value,
                    CompanyStatus.ANALYZING.value,
                ]:
                    # Company is being analyzed - mark job as pending, will retry later
                    logger.info(
                        f"Company {company_name} is being analyzed (status={company.get('status')}) "
                        f"- marking job as PENDING for retry"
                    )
                    self.queue_manager.update_status(
                        item.id,
                        QueueStatus.PENDING,
                        f"Waiting for company analysis to complete (status={company.get('status')})",
                    )
                    return

                else:
                    # Company exists and has good data - use it
                    logger.info(f"Using existing company data for {company_name}")
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

    def process_job_save(self, item: JobQueueItem) -> None:
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

    # ============================================================
    # JOB SCRAPING METHODS
    # ============================================================

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

            # Extract company from URL (boards.greenhouse.io/{company}/jobs/...)
            company_match = re.search(r"boards\.greenhouse\.io/([^/]+)", url)
            company_name = (
                company_match.group(1).replace("-", " ").title() if company_match else "Unknown"
            )

            # Extract job details using updated selectors (Greenhouse HTML structure changed)
            title_elem = soup.find("h1", class_="section-header")
            location_elem = soup.find("div", class_="job__location")
            description_elem = soup.find("div", class_="job__description")

            return {
                "title": title_elem.text.strip() if title_elem else "Unknown",
                "company": company_name,
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

    # ============================================================
    # HELPER METHODS
    # ============================================================

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

    def handle_failure(
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

    # ============================================================
    # LEGACY SCRAPE PROCESSING
    # ============================================================

    def process_scrape(self, item: JobQueueItem) -> None:
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
            from job_finder.job_queue.models import ScrapeConfig

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
