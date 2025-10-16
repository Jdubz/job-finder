"""Manage job sources in Firestore - separate from companies."""

import logging
from typing import Any, Dict, List, Optional

from google.cloud import firestore as gcloud_firestore

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
            raise RuntimeError("Firestore not initialized")

        source_doc = {
            "name": name,
            "sourceType": source_type,
            "config": config,
            "enabled": enabled,
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
            raise RuntimeError("Firestore not initialized")

        try:
            query = self.db.collection(self.collection_name).where("enabled", "==", True)

            if source_type:
                query = query.where("sourceType", "==", source_type)

            if tags:
                # Firestore array-contains only supports single value
                query = query.where("tags", "array-contains", tags[0])

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
            raise RuntimeError("Firestore not initialized")

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

    def get_sources_for_company(self, company_id: str) -> List[Dict[str, Any]]:
        """
        Get all sources associated with a specific company.

        Args:
            company_id: Company document ID

        Returns:
            List of source documents for this company
        """
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        try:
            query = self.db.collection(self.collection_name).where("companyId", "==", company_id)

            docs = query.stream()

            sources = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                sources.append(data)

            return sources

        except Exception as e:
            logger.error(f"Error getting sources for company {company_id}: {str(e)}")
            return []

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
            raise RuntimeError("Firestore not initialized")

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

    def disable_source(self, doc_id: str) -> None:
        """Disable a job source."""
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        try:
            self.db.collection(self.collection_name).document(doc_id).update(
                {
                    "enabled": False,
                    "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
                }
            )
            logger.info(f"Disabled source {doc_id}")

        except (RuntimeError, ValueError) as e:
            logger.error(f"Error disabling source (database): {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error disabling source ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
            raise

    def enable_source(self, doc_id: str) -> None:
        """Enable a job source."""
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        try:
            self.db.collection(self.collection_name).document(doc_id).update(
                {
                    "enabled": True,
                    "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
                }
            )
            logger.info(f"Enabled source {doc_id}")

        except (RuntimeError, ValueError) as e:
            logger.error(f"Error enabling source (database): {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error enabling source ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
            raise

    def link_source_to_company(self, source_id: str, company_id: str, company_name: str) -> None:
        """
        Link a source to a company.

        Args:
            source_id: Source document ID
            company_id: Company document ID
            company_name: Company name (denormalized)
        """
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        try:
            self.db.collection(self.collection_name).document(source_id).update(
                {
                    "companyId": company_id,
                    "companyName": company_name,
                    "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
                }
            )
            logger.info(f"Linked source {source_id} to company {company_name} ({company_id})")

        except Exception as e:
            logger.error(f"Error linking source to company: {str(e)}")
            raise

    def unlink_source_from_company(self, source_id: str) -> None:
        """
        Unlink a source from its company.

        Args:
            source_id: Source document ID
        """
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        try:
            self.db.collection(self.collection_name).document(source_id).update(
                {
                    "companyId": None,
                    "companyName": None,
                    "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
                }
            )
            logger.info(f"Unlinked source {source_id} from company")

        except Exception as e:
            logger.error(f"Error unlinking source from company: {str(e)}")
            raise
