"""Manage job source listings in Firestore."""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import os

import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore as gcloud_firestore

logger = logging.getLogger(__name__)


class JobListingsManager:
    """Manages job board listings, RSS feeds, and company pages in Firestore."""

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        database_name: str = "portfolio-staging"
    ):
        """
        Initialize Firestore listings manager.

        Args:
            credentials_path: Path to Firebase service account JSON.
            database_name: Firestore database name (default: "portfolio-staging").
        """
        self.database_name = database_name
        self.db: Optional[gcloud_firestore.Client] = None

        # Get credentials path
        creds_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not creds_path:
            raise ValueError(
                "Firebase credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS "
                "environment variable or pass credentials_path parameter."
            )

        if not Path(creds_path).exists():
            raise FileNotFoundError(f"Credentials file not found: {creds_path}")

        # Initialize Firebase Admin if not already initialized
        try:
            try:
                firebase_admin.get_app()
                logger.info("Using existing Firebase app")
            except ValueError:
                cred = credentials.Certificate(creds_path)
                firebase_admin.initialize_app(cred)
                logger.info("Initialized new Firebase app")

            # Get credentials for project ID
            cred = credentials.Certificate(creds_path)
            project_id = cred.project_id

            # Connect to named database
            if database_name == "(default)":
                self.db = gcloud_firestore.Client(project=project_id)
            else:
                self.db = gcloud_firestore.Client(project=project_id, database=database_name)

            logger.info(f"Connected to Firestore database: {database_name} in project {project_id}")

        except Exception as e:
            raise RuntimeError(f"Failed to initialize Firestore: {str(e)}") from e

    def add_listing(
        self,
        name: str,
        source_type: str,
        config: Dict[str, Any],
        enabled: bool = True,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Add a new job source listing.

        Args:
            name: Human-readable name (e.g., "We Work Remotely", "Netflix Careers")
            source_type: Type of source - "rss", "api", "scraper", "company-page"
            config: Configuration specific to source type
            enabled: Whether this source is active
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

        API:
            {
                "base_url": "https://api.example.com",
                "auth_type": "none|api_key|oauth",
                "api_key_env": "API_KEY_VAR",  # if auth_type is api_key
                "endpoints": {
                    "search": "/jobs/search",
                    "details": "/jobs/{id}"
                },
                "params": {
                    "remote": "true",
                    "type": "full-time"
                }
            }

        Scraper:
            {
                "url": "https://example.com/jobs",
                "method": "selenium|requests",
                "selectors": {
                    "job_list": ".job-listing",
                    "title": ".job-title",
                    "company": ".company-name",
                    "description": ".job-description",
                    "link": "a.apply-link"
                },
                "pagination": {
                    "enabled": true,
                    "selector": ".next-page",
                    "max_pages": 5
                }
            }

        Company Page:
            {
                "company_name": "Netflix",
                "careers_url": "https://jobs.netflix.com/search",
                "company_website": "https://www.netflix.com",
                "company_info": "Culture and mission statement...",
                "method": "api|scraper|rss",
                "api_endpoint": "https://jobs.netflix.com/api/search",  # if method=api
                "rss_url": "https://jobs.netflix.com/feed",  # if method=rss
                "selectors": {...}  # if method=scraper
            }
        """
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        listing = {
            "name": name,
            "sourceType": source_type,
            "config": config,
            "enabled": enabled,
            "tags": tags or [],

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
            doc_ref = self.db.collection("job-listings").add(listing)
            doc_id = doc_ref[1].id
            logger.info(f"Added job listing: {name} ({source_type}) - ID: {doc_id}")
            return doc_id

        except Exception as e:
            logger.error(f"Error adding job listing: {str(e)}")
            raise

    def get_active_listings(
        self,
        source_type: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all active job source listings.

        Args:
            source_type: Filter by source type (rss, api, scraper, company-page)
            tags: Filter by tags

        Returns:
            List of active listing documents
        """
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        try:
            query = self.db.collection("job-listings").where("enabled", "==", True)

            if source_type:
                query = query.where("sourceType", "==", source_type)

            if tags:
                # Note: Firestore array-contains only supports single value
                # For multiple tags, filter in Python
                query = query.where("tags", "array-contains", tags[0])

            docs = query.stream()

            listings = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id

                # Filter by additional tags if needed
                if tags and len(tags) > 1:
                    if not all(tag in data.get("tags", []) for tag in tags):
                        continue

                listings.append(data)

            logger.info(f"Retrieved {len(listings)} active job listings")
            return listings

        except Exception as e:
            logger.error(f"Error getting job listings: {str(e)}")
            raise

    def update_scrape_status(
        self,
        doc_id: str,
        status: str,
        jobs_found: int = 0,
        jobs_matched: int = 0,
        error: Optional[str] = None
    ) -> None:
        """
        Update the scrape status for a listing.

        Args:
            doc_id: Listing document ID
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
            # Increment total counters
            update_data["totalJobsFound"] = gcloud_firestore.Increment(jobs_found)

        if jobs_matched > 0:
            update_data["totalJobsMatched"] = gcloud_firestore.Increment(jobs_matched)

        try:
            self.db.collection("job-listings").document(doc_id).update(update_data)
            logger.info(f"Updated listing {doc_id} - status: {status}")

        except Exception as e:
            logger.error(f"Error updating listing status: {str(e)}")
            raise

    def disable_listing(self, doc_id: str) -> None:
        """Disable a job listing."""
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        try:
            self.db.collection("job-listings").document(doc_id).update({
                "enabled": False,
                "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
            })
            logger.info(f"Disabled listing {doc_id}")

        except Exception as e:
            logger.error(f"Error disabling listing: {str(e)}")
            raise

    def enable_listing(self, doc_id: str) -> None:
        """Enable a job listing."""
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        try:
            self.db.collection("job-listings").document(doc_id).update({
                "enabled": True,
                "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
            })
            logger.info(f"Enabled listing {doc_id}")

        except Exception as e:
            logger.error(f"Error enabling listing: {str(e)}")
            raise
