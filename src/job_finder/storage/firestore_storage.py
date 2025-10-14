"""Store job matches and analysis in Firestore."""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import os

import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore as gcloud_firestore

from job_finder.ai.matcher import JobMatchResult

logger = logging.getLogger(__name__)


class FirestoreJobStorage:
    """Stores job matches in Firestore with tracking for document generation."""

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        database_name: str = "portfolio-staging"
    ):
        """
        Initialize Firestore job storage.

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

    def save_job_match(
        self,
        job: Dict[str, Any],
        match_result: JobMatchResult,
        user_id: Optional[str] = None
    ) -> str:
        """
        Save a job match to Firestore.

        Args:
            job: Job posting dictionary
            match_result: AI match analysis result
            user_id: Optional user ID for multi-user support

        Returns:
            Document ID of saved job match
        """
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        # Build job match document
        job_match = {
            # Job Information
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "companyWebsite": job.get("company_website", ""),
            "companyInfo": job.get("company_info", ""),
            "location": job.get("location", ""),
            "description": job.get("description", ""),
            "url": job.get("url", ""),
            "postedDate": job.get("posted_date"),
            "salary": job.get("salary"),
            "keywords": job.get("keywords", []),

            # Match Analysis
            "matchScore": match_result.match_score,
            "matchedSkills": match_result.matched_skills,
            "missingSkills": match_result.missing_skills,
            "experienceMatch": match_result.experience_match,
            "keyStrengths": match_result.key_strengths,
            "potentialConcerns": match_result.potential_concerns,
            "applicationPriority": match_result.application_priority,
            "customizationRecommendations": match_result.customization_recommendations,

            # Resume Intake Data
            "resumeIntakeData": match_result.resume_intake_data,

            # Tracking & Metadata
            "documentGenerated": False,
            "documentGeneratedAt": None,
            "documentUrl": None,
            "applied": False,
            "appliedAt": None,
            "status": "new",  # new, reviewed, applied, rejected, interview, offer
            "notes": "",

            # Timestamps
            "createdAt": gcloud_firestore.SERVER_TIMESTAMP,
            "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
        }

        # Add user ID if provided
        if user_id:
            job_match["userId"] = user_id

        # Save to Firestore
        try:
            doc_ref = self.db.collection("job-matches").add(job_match)
            doc_id = doc_ref[1].id
            logger.info(f"Saved job match: {job.get('title')} at {job.get('company')} (ID: {doc_id})")
            return doc_id

        except Exception as e:
            logger.error(f"Error saving job match: {str(e)}")
            raise

    def update_document_generated(
        self,
        doc_id: str,
        document_url: str
    ) -> None:
        """
        Mark a job match as having had a document generated.

        Args:
            doc_id: Firestore document ID
            document_url: URL to generated resume/cover letter
        """
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        try:
            self.db.collection("job-matches").document(doc_id).update({
                "documentGenerated": True,
                "documentGeneratedAt": gcloud_firestore.SERVER_TIMESTAMP,
                "documentUrl": document_url,
                "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
            })
            logger.info(f"Updated job match {doc_id} - document generated")

        except Exception as e:
            logger.error(f"Error updating job match: {str(e)}")
            raise

    def update_status(
        self,
        doc_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> None:
        """
        Update the status of a job match.

        Args:
            doc_id: Firestore document ID
            status: New status (new, reviewed, applied, rejected, interview, offer)
            notes: Optional notes to add
        """
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        update_data = {
            "status": status,
            "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
        }

        if notes:
            update_data["notes"] = notes

        if status == "applied":
            update_data["applied"] = True
            update_data["appliedAt"] = gcloud_firestore.SERVER_TIMESTAMP

        try:
            self.db.collection("job-matches").document(doc_id).update(update_data)
            logger.info(f"Updated job match {doc_id} - status: {status}")

        except Exception as e:
            logger.error(f"Error updating job match status: {str(e)}")
            raise

    def get_job_matches(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        min_score: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query job matches from Firestore.

        Args:
            user_id: Filter by user ID
            status: Filter by status
            min_score: Filter by minimum match score
            limit: Maximum number of results

        Returns:
            List of job match documents
        """
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        try:
            query = self.db.collection("job-matches")

            if user_id:
                query = query.where("userId", "==", user_id)

            if status:
                query = query.where("status", "==", status)

            if min_score:
                query = query.where("matchScore", ">=", min_score)

            # Order by match score descending
            query = query.order_by("matchScore", direction=gcloud_firestore.Query.DESCENDING)
            query = query.limit(limit)

            docs = query.stream()

            matches = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                matches.append(data)

            logger.info(f"Retrieved {len(matches)} job matches")
            return matches

        except Exception as e:
            logger.error(f"Error querying job matches: {str(e)}")
            raise

    def job_exists(self, job_url: str, user_id: Optional[str] = None) -> bool:
        """
        Check if a job already exists in the database.

        Args:
            job_url: Job posting URL
            user_id: Optional user ID for multi-user support

        Returns:
            True if job exists, False otherwise
        """
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        try:
            query = self.db.collection("job-matches").where("url", "==", job_url)

            if user_id:
                query = query.where("userId", "==", user_id)

            query = query.limit(1)
            docs = list(query.stream())

            return len(docs) > 0

        except Exception as e:
            logger.error(f"Error checking job existence: {str(e)}")
            return False

    def batch_check_exists(self, job_urls: List[str], user_id: Optional[str] = None) -> Dict[str, bool]:
        """
        Batch check if multiple jobs already exist in the database.

        Args:
            job_urls: List of job posting URLs
            user_id: Optional user ID for multi-user support

        Returns:
            Dictionary mapping URL to existence status
        """
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        exists_map = {}

        try:
            # Firestore 'in' queries are limited to 10 items, so batch in chunks
            chunk_size = 10
            for i in range(0, len(job_urls), chunk_size):
                chunk = job_urls[i:i + chunk_size]

                query = self.db.collection("job-matches").where("url", "in", chunk)

                if user_id:
                    query = query.where("userId", "==", user_id)

                docs = query.stream()

                # Mark found URLs as existing
                for doc in docs:
                    data = doc.to_dict()
                    url = data.get("url")
                    if url:
                        exists_map[url] = True

            # Mark URLs not found as non-existing
            for url in job_urls:
                if url not in exists_map:
                    exists_map[url] = False

            return exists_map

        except Exception as e:
            logger.error(f"Error batch checking job existence: {str(e)}")
            # Return all as non-existing on error
            return {url: False for url in job_urls}
