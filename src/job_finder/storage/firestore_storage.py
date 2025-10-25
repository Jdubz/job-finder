"""Store job matches and analysis in Firestore."""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from google.cloud import firestore as gcloud_firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from job_finder.exceptions import StorageError
from job_finder.storage.firestore_client import FirestoreClient
from job_finder.utils.url_utils import normalize_url

if TYPE_CHECKING:
    from job_finder.ai.matcher import JobMatchResult

logger = logging.getLogger(__name__)


# Standard field name mappings: Python snake_case → Firestore camelCase
# This mapping ensures consistent field name transformations across the codebase
FIELD_MAPPING = {
    # Job basic fields
    "company_website": "companyWebsite",
    "company_info": "companyInfo",
    "company_id": "companyId",
    "posted_date": "postedDate",
    # Analysis fields
    "match_score": "matchScore",
    "matched_skills": "matchedSkills",
    "missing_skills": "missingSkills",
    "experience_match": "experienceMatch",
    "key_strengths": "keyStrengths",
    "potential_concerns": "potentialConcerns",
    "application_priority": "applicationPriority",
    "customization_recommendations": "customizationRecommendations",
    "resume_intake_data": "resumeIntakeData",
    # Status tracking fields
    "document_generated": "documentGenerated",
    "document_generated_at": "documentGeneratedAt",
    "document_url": "documentUrl",
    "applied_at": "appliedAt",
    "user_id": "userId",
    "created_at": "createdAt",
    "updated_at": "updatedAt",
}


def to_firestore_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Python snake_case field names to Firestore camelCase.

    Args:
        data: Dictionary with Python snake_case field names

    Returns:
        Dictionary with Firestore camelCase field names
    """
    return {FIELD_MAPPING.get(k, k): v for k, v in data.items() if v is not None}


class FirestoreJobStorage:
    """Stores job matches in Firestore with tracking for document generation."""

    def __init__(
        self, credentials_path: Optional[str] = None, database_name: str = "portfolio-staging"
    ):
        """
        Initialize Firestore job storage.

        Args:
            credentials_path: Path to Firebase service account JSON.
            database_name: Firestore database name (default: "portfolio-staging").
        """
        self.database_name = database_name
        self.db = FirestoreClient.get_client(database_name, credentials_path)

    def _extract_role_from_title(self, title: str) -> str:
        """
        Extract role from job title, removing common prefixes/suffixes.

        Examples:
            "Senior Software Engineer" -> "Software Engineer"
            "Lead Frontend Developer" -> "Frontend Developer"
            "Full Stack Engineer (L5)" -> "Full Stack Engineer"
        """
        import re

        # Remove level indicators in parentheses or brackets
        role = re.sub(r"\s*[\(\[].*?[\)\]]", "", title)

        # Remove common seniority prefixes (but keep the core role)
        seniority_pattern = (
            r"^(Senior|Sr\.|Junior|Jr\.|Lead|Principal|Staff|Entry[ -]?Level|Mid[ -]?Level)\s+"
        )
        role = re.sub(seniority_pattern, "", role, flags=re.IGNORECASE).strip()

        # If the removal made it too short, use original title
        if len(role) < 5:
            role = title

        return role.strip()

    def _get_existing_job_id(
        self, normalized_url: str, user_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Check if a job with the normalized URL already exists.

        Args:
            normalized_url: Normalized job URL
            user_id: Optional user ID for multi-user support

        Returns:
            Document ID if job exists, None otherwise
        """
        if not self.db or not normalized_url:
            return None

        try:
            query = self.db.collection("job-matches").where(
                filter=FieldFilter("url", "==", normalized_url)
            )

            if user_id:
                query = query.where(filter=FieldFilter("userId", "==", user_id))

            query = query.limit(1)
            docs = list(query.stream())

            if docs:
                return docs[0].id

            return None

        except Exception as e:
            logger.warning(f"Error checking for existing job: {e}")
            return None

    def save_job_match(
        self, job: Dict[str, Any], match_result: "JobMatchResult", user_id: Optional[str] = None
    ) -> str:
        """
        Save a job match to Firestore.

        Checks for duplicates before saving. If a job with the same normalized URL
        already exists, logs and skips the save operation, returning the existing
        document ID.

        Args:
            job: Job posting dictionary
            match_result: AI match analysis result
            user_id: Optional user ID for multi-user support

        Returns:
            Document ID of saved job match (new or existing)
        """
        if not self.db:
            raise StorageError("Firestore not initialized")

        # Extract role from title
        title = job.get("title", "")
        role = self._extract_role_from_title(title)

        # Normalize URL for consistent storage and deduplication
        job_url = job.get("url", "")
        normalized_url = normalize_url(job_url) if job_url else ""

        # Check for duplicate before saving
        if normalized_url:
            existing_doc_id = self._get_existing_job_id(normalized_url, user_id)
            if existing_doc_id:
                logger.info(
                    f"[DB:DUPLICATE] Job already exists: {title} at {job.get('company')} "
                    f"(URL: {normalized_url[:60]}..., existing ID: {existing_doc_id})"
                )
                return existing_doc_id

        # Build job match document
        # Note: Field names use camelCase for Firestore storage
        # Optional fields (postedDate, salary, companyId) are only included if present
        job_match = {
            # Job Information
            "title": title,
            "role": role,  # Extracted role without seniority level
            "company": job.get("company", ""),
            "companyWebsite": job.get("company_website", ""),
            "companyInfo": job.get("company_info", ""),
            "location": job.get("location", ""),
            "description": job.get("description", ""),
            "url": normalized_url,  # Store normalized URL
            # Match Analysis
            "matchScore": match_result.match_score,
            "matchedSkills": match_result.matched_skills,
            "missingSkills": match_result.missing_skills,
            "experienceMatch": match_result.experience_match,
            "keyStrengths": match_result.key_strengths,
            "potentialConcerns": match_result.potential_concerns,
            "applicationPriority": match_result.application_priority,
            "customizationRecommendations": match_result.customization_recommendations,
            # Resume Intake Data (contains atsKeywords)
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

        # Add optional fields only if present
        if job.get("companyId"):
            job_match["companyId"] = job["companyId"]
        if job.get("posted_date"):
            job_match["postedDate"] = job["posted_date"]
        if job.get("salary"):
            job_match["salary"] = job["salary"]

        # Add user ID if provided
        if user_id:
            job_match["userId"] = user_id

        # Save to Firestore
        try:
            doc_ref = self.db.collection("job-matches").add(job_match)
            doc_id = doc_ref[1].id
            logger.info(
                f"[DB:CREATE] Saved job match: {job.get('title')} at {job.get('company')} "
                f"(ID: {doc_id}, Score: {match_result.match_score})"
            )
            return doc_id

        except (RuntimeError, ValueError, AttributeError) as e:
            # Firestore errors, validation errors, or missing data
            logger.error(f"Error saving job match (database/validation): {str(e)}")
            raise
        except Exception as e:
            # Unexpected errors - log with traceback and re-raise
            logger.error(
                f"Unexpected error saving job match ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
            raise

    def update_document_generated(self, doc_id: str, document_url: str) -> None:
        """
        Mark a job match as having had a document generated.

        Args:
            doc_id: Firestore document ID
            document_url: URL to generated resume/cover letter
        """
        if not self.db:
            raise StorageError("Firestore not initialized")

        try:
            self.db.collection("job-matches").document(doc_id).update(
                {
                    "documentGenerated": True,
                    "documentGeneratedAt": gcloud_firestore.SERVER_TIMESTAMP,
                    "documentUrl": document_url,
                    "updatedAt": gcloud_firestore.SERVER_TIMESTAMP,
                }
            )
            logger.info(f"Updated job match {doc_id} - document generated")

        except (RuntimeError, ValueError) as e:
            # Firestore errors or invalid document ID
            logger.error(f"Error updating job match (database): {str(e)}")
            raise
        except Exception as e:
            # Unexpected errors - log with traceback and re-raise
            logger.error(
                f"Unexpected error updating job match ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
            raise

    def update_status(self, doc_id: str, status: str, notes: Optional[str] = None) -> None:
        """
        Update the status of a job match.

        Args:
            doc_id: Firestore document ID
            status: New status (new, reviewed, applied, rejected, interview, offer)
            notes: Optional notes to add
        """
        if not self.db:
            raise StorageError("Firestore not initialized")

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

        except (RuntimeError, ValueError) as e:
            # Firestore errors or invalid status/document ID
            logger.error(f"Error updating job match status (database): {str(e)}")
            raise
        except Exception as e:
            # Unexpected errors - log with traceback and re-raise
            logger.error(
                f"Unexpected error updating job match status ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
            raise

    def get_job_matches(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        min_score: Optional[int] = None,
        limit: int = 100,
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
            raise StorageError("Firestore not initialized")

        try:
            query = self.db.collection("job-matches")

            if user_id:
                query = query.where(filter=FieldFilter("userId", "==", user_id))

            if status:
                query = query.where(filter=FieldFilter("status", "==", status))

            if min_score:
                query = query.where(filter=FieldFilter("matchScore", ">=", min_score))

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

        except (RuntimeError, ValueError) as e:
            # Firestore query errors or invalid parameters
            logger.error(f"Error querying job matches (database): {str(e)}")
            raise
        except Exception as e:
            # Unexpected errors - log with traceback and re-raise
            logger.error(
                f"Unexpected error querying job matches ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
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
            raise StorageError("Firestore not initialized")

        try:
            # Normalize URL for consistent comparison
            normalized_url = normalize_url(job_url)

            query = self.db.collection("job-matches").where(
                filter=FieldFilter("url", "==", normalized_url)
            )

            if user_id:
                query = query.where(filter=FieldFilter("userId", "==", user_id))

            query = query.limit(1)
            docs = list(query.stream())

            return len(docs) > 0

        except (RuntimeError, ValueError) as e:
            # Firestore query errors - return False (job doesn't exist)
            logger.error(f"Error checking job existence (database): {str(e)}")
            return False
        except Exception as e:
            # Unexpected errors - log with warning and return False
            logger.warning(
                f"Unexpected error checking job existence ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
            return False

    def batch_check_exists(
        self, job_urls: List[str], user_id: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Batch check if multiple jobs already exist in the database.

        Normalizes URLs before checking and returns mapping of normalized URLs.

        Args:
            job_urls: List of job posting URLs
            user_id: Optional user ID for multi-user support

        Returns:
            Dictionary mapping normalized URL to existence status
        """
        if not self.db:
            raise StorageError("Firestore not initialized")

        # Normalize all input URLs first
        normalized_urls = [normalize_url(url) for url in job_urls]
        exists_map = {}

        try:
            # Firestore 'in' queries are limited to 10 items, so batch in chunks
            chunk_size = 10
            for i in range(0, len(normalized_urls), chunk_size):
                chunk = normalized_urls[i : i + chunk_size]

                query = self.db.collection("job-matches").where(
                    filter=FieldFilter("url", "in", chunk)
                )

                if user_id:
                    query = query.where(filter=FieldFilter("userId", "==", user_id))

                docs = query.stream()

                # Mark found URLs as existing
                for doc in docs:
                    data = doc.to_dict()
                    url = data.get("url")
                    if url:
                        exists_map[url] = True

            # Mark URLs not found as non-existing
            for url in normalized_urls:
                if url not in exists_map:
                    exists_map[url] = False

            return exists_map

        except (RuntimeError, ValueError) as e:
            # Firestore query errors - return all as non-existing
            logger.error(f"Error batch checking job existence (database): {str(e)}")
            return {url: False for url in normalized_urls}
        except Exception as e:
            # Unexpected errors - log with warning and return all as non-existing
            logger.warning(
                f"Unexpected error batch checking job existence ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
            return {url: False for url in normalized_urls}
