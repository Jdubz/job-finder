"""Firestore companies collection manager."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from google.cloud import firestore

logger = logging.getLogger(__name__)


class CompaniesManager:
    """Manages company information in Firestore."""

    def __init__(self, database_name: str = "portfolio"):
        """
        Initialize companies manager.

        Args:
            database_name: Firestore database name
        """
        self.db = firestore.Client(database=database_name)
        self.collection_name = "companies"

    def get_company(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        Get company information by name.

        Args:
            company_name: Company name

        Returns:
            Company data dictionary or None if not found
        """
        try:
            # Query by name (case-insensitive)
            docs = self.db.collection(self.collection_name).where(
                'name_lower', '==', company_name.lower()
            ).limit(1).stream()

            for doc in docs:
                company_data = doc.to_dict()
                company_data['id'] = doc.id
                return company_data

            return None

        except Exception as e:
            logger.error(f"Error getting company {company_name}: {e}")
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
                - size: Company size
                - industry: Industry/sector
                - founded: Year founded

        Returns:
            Document ID of saved company
        """
        try:
            company_name = company_data.get('name')
            if not company_name:
                raise ValueError("Company name is required")

            # Check if company already exists
            existing = self.get_company(company_name)

            # Prepare data
            save_data = {
                'name': company_name,
                'name_lower': company_name.lower(),  # For case-insensitive search
                'website': company_data.get('website', ''),
                'about': company_data.get('about', ''),
                'culture': company_data.get('culture', ''),
                'mission': company_data.get('mission', ''),
                'size': company_data.get('size', ''),
                'industry': company_data.get('industry', ''),
                'founded': company_data.get('founded', ''),
                'updatedAt': datetime.now(),
            }

            if existing:
                # Update existing company
                doc_id = existing['id']

                # Only update if we have new/better information
                should_update = False
                for field in ['about', 'culture', 'mission', 'size', 'industry', 'founded']:
                    new_value = save_data.get(field, '')
                    existing_value = existing.get(field, '')

                    # Update if new value is longer/better
                    if new_value and len(new_value) > len(existing_value):
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
                save_data['createdAt'] = datetime.now()
                doc_ref = self.db.collection(self.collection_name).add(save_data)
                doc_id = doc_ref[1].id

                logger.info(f"Created new company: {company_name} (ID: {doc_id})")
                return doc_id

        except Exception as e:
            logger.error(f"Error saving company {company_data.get('name')}: {e}")
            raise

    def get_or_create_company(
        self,
        company_name: str,
        company_website: str = '',
        fetch_info_func=None
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
            has_about = len(company.get('about', '')) > 100
            has_culture = len(company.get('culture', '')) > 50

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

            except Exception as e:
                logger.error(f"Error fetching company info for {company_name}: {e}")

                # Return existing data or minimal data
                if company:
                    return company
                else:
                    return {
                        'name': company_name,
                        'website': company_website,
                        'about': '',
                        'culture': '',
                        'mission': ''
                    }
        else:
            # Return existing or minimal data
            if company:
                return company
            else:
                return {
                    'name': company_name,
                    'website': company_website,
                    'about': '',
                    'culture': '',
                    'mission': ''
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
                company['id'] = doc.id
                companies.append(company)

            return companies

        except Exception as e:
            logger.error(f"Error getting all companies: {e}")
            return []
