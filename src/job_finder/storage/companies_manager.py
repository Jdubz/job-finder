"""Firestore companies collection manager."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from job_finder.utils.company_name_utils import normalize_company_name

from .firestore_client import FirestoreClient

logger = logging.getLogger(__name__)


class CompaniesManager:
    """Manages company information in Firestore."""

    def __init__(self, credentials_path: Optional[str] = None, database_name: str = "portfolio"):
        """
        Initialize companies manager.

        Args:
            credentials_path: Path to Firebase service account JSON (optional).
            database_name: Firestore database name
        """
        self.db = FirestoreClient.get_client(database_name, credentials_path)
        self.collection_name = "companies"

    def get_company(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        Get company information by name (using normalized matching).

        Args:
            company_name: Company name

        Returns:
            Company data dictionary or None if not found
        """
        try:
            # Query by normalized name for better deduplication
            # This matches "Cloudflare" and "Cloudflare Careers" as the same company
            normalized_name = normalize_company_name(company_name)
            docs = (
                self.db.collection(self.collection_name)
                .where("name_normalized", "==", normalized_name)
                .limit(1)
                .stream()
            )

            for doc in docs:
                company_data = doc.to_dict()
                company_data["id"] = doc.id
                return company_data

            return None

        except (RuntimeError, ValueError, AttributeError) as e:
            # Firestore query errors or data access issues
            logger.error(f"Error getting company {company_name} (database): {e}")
            return None
        except Exception as e:
            # Unexpected errors - log with traceback and return None
            logger.error(
                f"Unexpected error getting company {company_name} ({type(e).__name__}): {e}",
                exc_info=True,
            )
            return None

    def get_company_by_id(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        Get company information by document ID.

        Args:
            company_id: Firestore document ID

        Returns:
            Company data dictionary or None if not found
        """
        try:
            doc = self.db.collection(self.collection_name).document(company_id).get()
            if doc.exists:
                company_data = doc.to_dict()
                company_data["id"] = doc.id
                return company_data
            return None

        except (RuntimeError, ValueError, AttributeError) as e:
            # Firestore query errors or data access issues
            logger.error(f"Error getting company by ID {company_id} (database): {e}")
            return None
        except Exception as e:
            # Unexpected errors - log with traceback and return None
            logger.error(
                f"Unexpected error getting company by ID {company_id} ({type(e).__name__}): {e}",
                exc_info=True,
            )
            return None

    def save_company(self, company_data: Dict[str, Any]) -> str:
        """
        Save or update company information.

        Args:
            company_data: Company information dictionary with keys:
                - name: Company name (required)
                - website: Company website
                - about: Company description
                - culture: Culture/values info
                - mission: Mission statement
                - size: Company size (employee count or description)
                - company_size_category: Detected size category ("large", "medium", "small")
                - headquarters_location: Company headquarters location
                - industry: Industry/sector
                - founded: Year founded
                - hasPortlandOffice: Whether company has Portland office (boolean)
                - techStack: List of technologies/skills (list)
                - tier: Priority tier S/A/B/C/D (computed from scoring)
                - priorityScore: Numeric priority score (computed)

        Returns:
            Document ID of saved company
        """
        try:
            company_name = company_data.get("name")
            if not company_name:
                raise ValueError("Company name is required")

            # Check if company already exists
            existing = self.get_company(company_name)

            # Prepare data
            save_data = {
                "name": company_name,
                "name_lower": company_name.lower(),  # For case-insensitive search (legacy)
                "name_normalized": normalize_company_name(company_name),  # For deduplication
                "website": company_data.get("website", ""),
                "about": company_data.get("about", ""),
                "culture": company_data.get("culture", ""),
                "mission": company_data.get("mission", ""),
                "size": company_data.get("size", ""),
                "company_size_category": company_data.get("company_size_category", ""),
                "headquarters_location": company_data.get("headquarters_location", ""),
                "industry": company_data.get("industry", ""),
                "founded": company_data.get("founded", ""),
                # New fields for source separation
                "hasPortlandOffice": company_data.get("hasPortlandOffice", False),
                "techStack": company_data.get("techStack", []),
                "tier": company_data.get("tier", ""),
                "priorityScore": company_data.get("priorityScore", 0),
                "updatedAt": datetime.now(),
            }

            if existing:
                # Update existing company
                doc_id = existing["id"]

                # Only update if we have new/better information
                should_update = False
                for field in [
                    "about",
                    "culture",
                    "mission",
                    "size",
                    "company_size_category",
                    "headquarters_location",
                    "industry",
                    "founded",
                    "hasPortlandOffice",
                    "techStack",
                    "tier",
                    "priorityScore",
                ]:
                    new_value = save_data.get(field, "")
                    existing_value = existing.get(field, "")

                    # Update if new value is longer/better
                    if new_value and len(str(new_value)) > len(str(existing_value)):
                        should_update = True
                        break

                if should_update:
                    self.db.collection(self.collection_name).document(doc_id).update(save_data)
                    logger.info(f"Updated company: {company_name} (ID: {doc_id})")
                else:
                    logger.info(f"Company {company_name} already has good info, skipping update")

                return doc_id

            else:
                # Create new company
                save_data["createdAt"] = datetime.now()
                doc_ref = self.db.collection(self.collection_name).add(save_data)
                doc_id = doc_ref[1].id

                logger.info(f"Created new company: {company_name} (ID: {doc_id})")
                return doc_id

        except (RuntimeError, ValueError, AttributeError) as e:
            # Firestore errors, validation errors, or missing data
            company_name = company_data.get("name")
            logger.error(f"Error saving company {company_name} (database/validation): {e}")
            raise
        except Exception as e:
            # Unexpected errors - log with traceback and re-raise
            company_name = company_data.get("name")
            logger.error(
                f"Unexpected error saving company {company_name} " f"({type(e).__name__}): {e}",
                exc_info=True,
            )
            raise

    def get_or_create_company(
        self, company_name: str, company_website: str = "", fetch_info_func=None
    ) -> Dict[str, Any]:
        """
        Get company from database or fetch and create if not exists.

        Args:
            company_name: Company name
            company_website: Company website
            fetch_info_func: Function to fetch company info if not in database
                           Should accept (company_name, company_website) and return dict

        Returns:
            Company data dictionary
        """
        # Try to get from database first
        company = self.get_company(company_name)

        if company:
            # Check if info is complete enough
            has_about = len(company.get("about", "")) > 100
            has_culture = len(company.get("culture", "")) > 50

            if has_about or has_culture:
                logger.info(f"Using cached company info for {company_name}")
                return company

            logger.info(f"Existing company info for {company_name} is sparse, fetching fresh")

        # Fetch new information
        if fetch_info_func and company_website:
            try:
                logger.info(f"Fetching company info for {company_name}")
                fetched_info = fetch_info_func(company_name, company_website)

                # Save to database
                self.save_company(fetched_info)

                # Return the fetched info
                return fetched_info

            except (RuntimeError, ValueError, AttributeError) as e:
                # Database, validation, or fetcher errors - return fallback data
                logger.error(
                    f"Error fetching company info for {company_name} " f"(fetch/database): {e}"
                )

                # Return existing data or minimal data
                if company:
                    return company
                else:
                    return {
                        "name": company_name,
                        "website": company_website,
                        "about": "",
                        "culture": "",
                        "mission": "",
                    }
            except Exception as e:
                # Unexpected errors - log with traceback and return fallback
                logger.error(
                    f"Unexpected error fetching company info for {company_name} "
                    f"({type(e).__name__}): {e}",
                    exc_info=True,
                )

                # Return existing data or minimal data
                if company:
                    return company
                else:
                    return {
                        "name": company_name,
                        "website": company_website,
                        "about": "",
                        "culture": "",
                        "mission": "",
                    }
        else:
            # Return existing or minimal data
            if company:
                return company
            else:
                return {
                    "name": company_name,
                    "website": company_website,
                    "about": "",
                    "culture": "",
                    "mission": "",
                }

    def get_all_companies(self, limit: int = 100) -> list[Dict[str, Any]]:
        """
        Get all companies from database.

        Args:
            limit: Maximum number of companies to return

        Returns:
            List of company data dictionaries
        """
        try:
            docs = self.db.collection(self.collection_name).limit(limit).stream()

            companies = []
            for doc in docs:
                company = doc.to_dict()
                company["id"] = doc.id
                companies.append(company)

            return companies

        except (RuntimeError, ValueError, AttributeError) as e:
            # Firestore query errors or data access issues
            logger.error(f"Error getting all companies (database): {e}")
            return []
        except Exception as e:
            # Unexpected errors - log with traceback and return empty list
            logger.error(
                f"Unexpected error getting all companies ({type(e).__name__}): {e}",
                exc_info=True,
            )
            return []
