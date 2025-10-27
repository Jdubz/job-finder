"""Manage job sources in Firestore - separate from companies."""

import logging
from typing import Any, Dict, List, Optional

from google.cloud import firestore as gcloud_firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from job_finder.exceptions import StorageError
from job_finder.job_queue.models import SourceStatus

from .firestore_client import FirestoreClient

logger = logging.getLogger(__name__)


class JobSourcesManager:
    """
    Manages job sources in Firestore.

    Job sources represent where jobs are scraped from (RSS feeds, APIs, company
    career pages, job boards, etc.). Sources can optionally reference a company
    but are separate entities.

    Example sources:
    - Greenhouse board for a specific company (links to company)
    - RSS feed from a job board (no company link)
    - Company career page scraper (links to company)
    - Indeed API (no company link)
    """

    def __init__(
        self, credentials_path: Optional[str] = None, database_name: str = "portfolio-staging"
    ):
        """
        Initialize job sources manager.

        Args:
            credentials_path: Path to Firebase service account JSON.
            database_name: Firestore database name (default: "portfolio-staging").
        """
        self.database_name = database_name
        self.db = FirestoreClient.get_client(database_name, credentials_path)
        self.collection_name = "job-sources"

    def add_source(
        self,
        name: str,
        source_type: str,
        config: Dict[str, Any],
        enabled: bool = True,
        company_id: Optional[str] = None,
        company_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Add a new job source.

        Args:
            name: Human-readable name (e.g., "Netflix Greenhouse", "We Work Remotely RSS")
            source_type: Type of source - "rss", "greenhouse", "workday", "api", "scraper"
            config: Configuration specific to source type (see below)
            enabled: Whether this source is active
            company_id: Optional reference to company document ID
            company_name: Optional company name (denormalized for display)
            tags: Optional tags for categorization (e.g., ["remote", "tech"])

        Returns:
            Document ID

        Config structure by type:

        RSS:
            {
                "url": "https://example.com/jobs.rss",
                "parse_format": "standard|custom",
                "title_field": "title",
                "description_field": "description",
                "link_field": "link",
                "company_field": "company"  # optional
            }

        Greenhouse:
            {
                "board_token": "company-slug"
            }

        Workday:
            {
                "company_id": "company-slug",
                "base_url": "https://company.wd1.myworkdayjobs.com"
            }

        API:
            {
                "base_url": "https://api.example.com",
                "auth_type": "none|api_key|oauth",
                "api_key_env": "API_KEY_VAR",
                "endpoints": {
                    "search": "/jobs/search",
                    "details": "/jobs/{id}"
                }
            }

        Scraper:
            {
                "url": "https://example.com/jobs",
                "method": "selenium|requests",
                "selectors": {
                    "job_list": ".job-listing",
                    "title": ".job-title",
                    "company": ".company-name"
                }
            }
        """
        if not self.db:
            raise StorageError("Firestore not initialized")

        # Determine initial status based on enabled flag
        initial_status = SourceStatus.ACTIVE if enabled else SourceStatus.DISABLED

        source_doc = {
            "name": name,
            "sourceType": source_type,
            "config": config,
            "enabled": enabled,  # Legacy field, kept for backward compatibility
            "status": initial_status.value,  # New status field
            "tags": tags or [],
            # Company linkage (optional)
            "companyId": company_id,
            "companyName": company_name,
            # Tracking
            "lastScrapedAt": None,
            "lastScrapedStatus": None,  # success, error, skipped
            "lastScrapedError": None,
            "totalJobsFound": 0,
            "totalJobsMatched": 0,
            "consecutiveFailures": 0,  # For health tracking
            # Metadata
            "createdAt": gcloud_firestore.SERVER_TIMESTAMP,
            "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
        }

        try:
            doc_ref = self.db.collection(self.collection_name).add(source_doc)
            doc_id = doc_ref[1].id
            logger.info(
                f"Added job source: {name} ({source_type})"
                + (f" -> {company_name}" if company_name else "")
                + f" - ID: {doc_id}"
            )
            return doc_id

        except (RuntimeError, ValueError, AttributeError) as e:
            logger.error(f"Error adding job source (database/validation): {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error adding job source ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
            raise

    def get_active_sources(
        self, source_type: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all active job sources.

        Args:
            source_type: Filter by source type (rss, greenhouse, workday, api, scraper)
            tags: Filter by tags

        Returns:
            List of active source documents
        """
        if not self.db:
            raise StorageError("Firestore not initialized")

        try:
            query = self.db.collection(self.collection_name).where(
                filter=FieldFilter("enabled", "==", True)
            )

            if source_type:
                query = query.where(filter=FieldFilter("sourceType", "==", source_type))

            if tags:
                # Firestore array-contains only supports single value
                query = query.where(filter=FieldFilter("tags", "array-contains", tags[0]))

            docs = query.stream()

            sources = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id

                # Filter by additional tags if needed
                if tags and len(tags) > 1:
                    if not all(tag in data.get("tags", []) for tag in tags):
                        continue

                sources.append(data)

            logger.info(f"Retrieved {len(sources)} active job sources")
            return sources

        except (RuntimeError, ValueError, AttributeError) as e:
            logger.error(f"Error getting job sources (database): {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error getting job sources ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
            raise

    def get_source_by_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a job source by its document ID.

        Args:
            source_id: Firestore document ID

        Returns:
            Source document or None if not found
        """
        if not self.db:
            raise StorageError("Firestore not initialized")

        try:
            doc = self.db.collection(self.collection_name).document(source_id).get()
            if doc.exists:
                data = doc.to_dict()
                data["id"] = doc.id
                return data
            return None

        except Exception as e:
            logger.error(f"Error getting source {source_id}: {str(e)}")
            return None

    def update_scrape_status(
        self,
        doc_id: str,
        status: str,
        jobs_found: int = 0,
        jobs_matched: int = 0,
        error: Optional[str] = None,
    ) -> None:
        """
        Update the scrape status for a source.

        Args:
            doc_id: Source document ID
            status: Scrape status (success, error, skipped)
            jobs_found: Number of jobs found in this scrape
            jobs_matched: Number of jobs that met match threshold
            error: Error message if status is 'error'
        """
        if not self.db:
            raise StorageError("Firestore not initialized")

        update_data = {
            "lastScrapedAt": gcloud_firestore.SERVER_TIMESTAMP,
            "lastScrapedStatus": status,
            "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
        }

        if error:
            update_data["lastScrapedError"] = error
        else:
            update_data["lastScrapedError"] = None

        if jobs_found > 0:
            update_data["totalJobsFound"] = gcloud_firestore.Increment(jobs_found)

        if jobs_matched > 0:
            update_data["totalJobsMatched"] = gcloud_firestore.Increment(jobs_matched)

        try:
            self.db.collection(self.collection_name).document(doc_id).update(update_data)
            logger.info(f"Updated source {doc_id} - status: {status}")

        except (RuntimeError, ValueError) as e:
            logger.error(f"Error updating source status (database): {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error updating source status ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
            raise

    # ========================================================================
    # Granular Pipeline Support Methods
    # ========================================================================

    def get_source_for_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Find source configuration by URL domain/pattern.

        Checks URL against source configurations to find matching scraping method.

        Args:
            url: Job posting URL

        Returns:
            Source document with config, or None if no match

        Example:
            url = "https://boards.greenhouse.io/netflix/jobs/123"
            source = manager.get_source_for_url(url)
            # Returns source with greenhouse config for Netflix
        """
        if not self.db:
            raise StorageError("Firestore not initialized")

        try:
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()

            # Query all active sources
            sources = self.get_active_sources()

            # Check for domain matches
            for source in sources:
                config = source.get("config", {})
                source_type = source.get("sourceType", "")

                # Greenhouse: Check board_token in URL
                if source_type == "greenhouse":
                    board_token = config.get("board_token", "")
                    if board_token and board_token.lower() in url.lower():
                        logger.debug(f"Matched Greenhouse source: {source.get('name')}")
                        return source

                # RSS: Check URL match
                elif source_type == "rss":
                    rss_url = config.get("url", "")
                    if rss_url and domain in rss_url.lower():
                        logger.debug(f"Matched RSS source: {source.get('name')}")
                        return source

                # Workday: Check base_url
                elif source_type == "workday":
                    base_url = config.get("base_url", "")
                    if base_url and domain in base_url.lower():
                        logger.debug(f"Matched Workday source: {source.get('name')}")
                        return source

                # API: Check base_url
                elif source_type == "api":
                    base_url = config.get("base_url", "")
                    if base_url and domain in base_url.lower():
                        logger.debug(f"Matched API source: {source.get('name')}")
                        return source

                # Scraper: Check URL pattern
                elif source_type == "scraper":
                    scraper_url = config.get("url", "")
                    if scraper_url and domain in scraper_url.lower():
                        logger.debug(f"Matched Scraper source: {source.get('name')}")
                        return source

            logger.debug(f"No source found for URL: {url}")
            return None

        except Exception as e:
            logger.error(f"Error finding source for URL {url}: {e}")
            return None

    def create_from_discovery(
        self,
        name: str,
        source_type: str,
        config: Dict[str, Any],
        discovered_via: str = "user_submission",
        discovered_by: Optional[str] = None,
        discovery_confidence: str = "high",
        discovery_queue_item_id: Optional[str] = None,
        company_id: Optional[str] = None,
        company_name: Optional[str] = None,
        enabled: bool = True,
        validation_required: bool = False,
    ) -> str:
        """
        Create a new source from discovery process.

        This is used by the SOURCE_DISCOVERY queue processor to create sources
        after validation.

        Args:
            name: Human-readable name
            source_type: greenhouse, workday, rss, scraper, etc.
            config: Source-specific configuration
            discovered_via: How it was discovered (user_submission, automated_scan)
            discovered_by: User ID if submitted by user
            discovery_confidence: high, medium, low
            discovery_queue_item_id: Reference to queue item that triggered discovery
            company_id: Optional company reference
            company_name: Optional company name
            enabled: Whether to enable immediately
            validation_required: If true, requires manual validation before enabling

        Returns:
            Document ID of created source
        """
        if not self.db:
            raise StorageError("Firestore not initialized")

        # Determine status based on validation requirement
        if validation_required:
            enabled = False
            status = SourceStatus.PENDING_VALIDATION
        else:
            # Auto-enabled sources are active, others are active if explicitly enabled
            status = SourceStatus.ACTIVE if enabled else SourceStatus.DISABLED

        source_doc = {
            "name": name,
            "sourceType": source_type,
            "config": config,
            "enabled": enabled,  # Legacy field, kept for backward compatibility
            "status": status.value,  # New status field
            "tags": [f"discovered-via-{discovered_via}", f"confidence-{discovery_confidence}"],
            # Company linkage (optional)
            "companyId": company_id,
            "companyName": company_name,
            # Discovery metadata
            "discoveredVia": discovered_via,
            "discoveredBy": discovered_by,
            "discoveredAt": gcloud_firestore.SERVER_TIMESTAMP,
            "discoveryConfidence": discovery_confidence,
            "discoveryQueueItemId": discovery_queue_item_id,
            "validationRequired": validation_required,
            "autoEnabled": enabled and not validation_required,  # Track if auto-enabled
            # Tracking
            "lastScrapedAt": None,
            "lastScrapedStatus": None,
            "lastScrapedError": None,
            "totalJobsFound": 0,
            "totalJobsMatched": 0,
            "consecutiveFailures": 0,
            # Metadata
            "createdAt": gcloud_firestore.SERVER_TIMESTAMP,
            "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
        }

        try:
            doc_ref = self.db.collection(self.collection_name).add(source_doc)
            doc_id = doc_ref[1].id

            status_label = "enabled" if enabled else "pending validation"
            logger.info(
                f"Created source from discovery: {name} ({source_type}) "
                f"[{discovery_confidence} confidence, {status_label}] - ID: {doc_id}"
            )

            return doc_id

        except (RuntimeError, ValueError, AttributeError) as e:
            logger.error(f"Error creating source from discovery (database/validation): {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error creating source from discovery ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
            raise

    def update_source_selectors(
        self,
        source_id: str,
        selectors: Dict[str, Any],
        alternative_selectors: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Update selectors for a source after discovery or validation.

        Args:
            source_id: Source document ID
            selectors: New primary selectors
            alternative_selectors: Optional list of fallback selectors to try
        """
        if not self.db:
            raise StorageError("Firestore not initialized")

        try:
            update_data = {
                "config.selectors": selectors,
                "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
            }

            if alternative_selectors:
                update_data["config.alternative_selectors"] = alternative_selectors

            self.db.collection(self.collection_name).document(source_id).update(update_data)
            logger.info(f"Updated selectors for source {source_id}")

        except Exception as e:
            logger.error(f"Error updating selectors for source {source_id}: {e}")
            raise

    def record_scraping_failure(
        self,
        source_id: str,
        error_message: str,
        selector_failures: Optional[List[str]] = None,
    ) -> None:
        """
        Record scraping failure for health tracking.

        Args:
            source_id: Source document ID
            error_message: Error that occurred
            selector_failures: List of selectors that failed
        """
        if not self.db:
            raise StorageError("Firestore not initialized")

        try:
            # Get current source to check failure count
            source = self.get_source_by_id(source_id)
            if not source:
                logger.warning(f"Cannot record failure: source {source_id} not found")
                return

            # Track consecutive failures
            consecutive_failures = source.get("consecutiveFailures", 0) + 1

            update_data = {
                "lastScrapedAt": gcloud_firestore.SERVER_TIMESTAMP,
                "lastScrapedStatus": "error",
                "lastScrapedError": error_message,
                "consecutiveFailures": consecutive_failures,
                "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
            }

            if selector_failures:
                update_data["failingSelectors"] = selector_failures

            # Auto-disable after 5 consecutive failures
            if consecutive_failures >= 5:
                update_data["enabled"] = False
                logger.warning(
                    f"Auto-disabled source {source_id} after {consecutive_failures} consecutive failures"
                )

            self.db.collection(self.collection_name).document(source_id).update(update_data)
            logger.info(
                f"Recorded failure for source {source_id} (consecutive: {consecutive_failures})"
            )

        except Exception as e:
            logger.error(f"Error recording failure for source {source_id}: {e}")
            raise

    def record_scraping_success(self, source_id: str, jobs_found: int = 0) -> None:
        """
        Record successful scraping to reset failure tracking.

        Args:
            source_id: Source document ID
            jobs_found: Number of jobs found in this scrape
        """
        if not self.db:
            raise StorageError("Firestore not initialized")

        try:
            update_data = {
                "lastScrapedAt": gcloud_firestore.SERVER_TIMESTAMP,
                "lastScrapedStatus": "success",
                "lastScrapedError": None,
                "consecutiveFailures": 0,  # Reset on success
                "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
            }

            if jobs_found > 0:
                update_data["totalJobsFound"] = gcloud_firestore.Increment(jobs_found)

            self.db.collection(self.collection_name).document(source_id).update(update_data)
            logger.debug(f"Recorded success for source {source_id}")

        except Exception as e:
            logger.error(f"Error recording success for source {source_id}: {e}")
            raise

    def update_source_status(
        self,
        source_id: str,
        status: SourceStatus,
        sync_enabled: bool = True,
    ) -> bool:
        """
        Update the status of a job source.

        Used during source discovery and validation to track operational state.

        Args:
            source_id: Firestore document ID
            status: New status (SourceStatus enum)
            sync_enabled: If True, also update legacy 'enabled' field to match status

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            update_data = {
                "status": status.value if isinstance(status, SourceStatus) else status,
                "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
            }

            # Sync legacy enabled field if requested
            if sync_enabled:
                # enabled=True for ACTIVE status, False for all others
                update_data["enabled"] = status == SourceStatus.ACTIVE

            self.db.collection(self.collection_name).document(source_id).update(update_data)
            logger.info(
                f"Updated source {source_id} status to {status.value if isinstance(status, SourceStatus) else status}"
            )
            return True

        except Exception as e:
            logger.error(f"Error updating source status for {source_id}: {e}")
            return False
