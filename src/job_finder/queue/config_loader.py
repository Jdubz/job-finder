"""Load queue configuration from Firestore."""

import logging
from typing import Any, Dict, List, Optional

from job_finder.storage.firestore_client import FirestoreClient

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Loads configuration from Firestore for queue processing.

    Configuration is stored in the 'job-finder-config' collection.
    This allows dynamic updates without code deployment.
    """

    def __init__(
        self, credentials_path: Optional[str] = None, database_name: str = "portfolio-staging"
    ):
        """
        Initialize config loader.

        Args:
            credentials_path: Path to Firebase service account JSON
            database_name: Firestore database name
        """
        self.db = FirestoreClient.get_client(database_name, credentials_path)
        self.collection_name = "job-finder-config"
        self._cache: Dict[str, Any] = {}

    def get_stop_list(self) -> Dict[str, List[str]]:
        """
        Get stop list (excluded companies, keywords, domains).

        Returns:
            Dictionary with excludedCompanies, excludedKeywords, excludedDomains
        """
        if "stop_list" in self._cache:
            return self._cache["stop_list"]

        try:
            doc = self.db.collection(self.collection_name).document("stop-list").get()

            if doc.exists:
                data = doc.to_dict()
                stop_list = {
                    "excludedCompanies": data.get("excludedCompanies", []),
                    "excludedKeywords": data.get("excludedKeywords", []),
                    "excludedDomains": data.get("excludedDomains", []),
                }
                self._cache["stop_list"] = stop_list
                logger.info(
                    f"Loaded stop list: {len(stop_list['excludedCompanies'])} companies, "
                    f"{len(stop_list['excludedKeywords'])} keywords, "
                    f"{len(stop_list['excludedDomains'])} domains"
                )
                return stop_list
            else:
                logger.warning("Stop list document not found, using empty lists")
                return {"excludedCompanies": [], "excludedKeywords": [], "excludedDomains": []}

        except Exception as e:
            logger.error(f"Error loading stop list from Firestore: {e}")
            return {"excludedCompanies": [], "excludedKeywords": [], "excludedDomains": []}

    def get_queue_settings(self) -> Dict[str, int]:
        """
        Get queue processing settings.

        Returns:
            Dictionary with maxRetries, retryDelaySeconds, processingTimeout
        """
        if "queue_settings" in self._cache:
            return self._cache["queue_settings"]

        try:
            doc = self.db.collection(self.collection_name).document("queue-settings").get()

            if doc.exists:
                data = doc.to_dict()
                settings = {
                    "maxRetries": data.get("maxRetries", 3),
                    "retryDelaySeconds": data.get("retryDelaySeconds", 60),
                    "processingTimeout": data.get("processingTimeout", 300),
                }
                self._cache["queue_settings"] = settings
                logger.info(f"Loaded queue settings: {settings}")
                return settings
            else:
                logger.warning("Queue settings document not found, using defaults")
                return {"maxRetries": 3, "retryDelaySeconds": 60, "processingTimeout": 300}

        except Exception as e:
            logger.error(f"Error loading queue settings from Firestore: {e}")
            return {"maxRetries": 3, "retryDelaySeconds": 60, "processingTimeout": 300}

    def get_ai_settings(self) -> Dict[str, Any]:
        """
        Get AI processing settings.

        Returns:
            Dictionary with provider, model, minMatchScore, costBudgetDaily
        """
        if "ai_settings" in self._cache:
            return self._cache["ai_settings"]

        try:
            doc = self.db.collection(self.collection_name).document("ai-settings").get()

            if doc.exists:
                data = doc.to_dict()
                settings = {
                    "provider": data.get("provider", "claude"),
                    "model": data.get("model", "claude-3-haiku-20240307"),
                    "minMatchScore": data.get("minMatchScore", 70),
                    "costBudgetDaily": data.get("costBudgetDaily", 50.0),
                }
                self._cache["ai_settings"] = settings
                logger.info(f"Loaded AI settings: {settings}")
                return settings
            else:
                logger.warning("AI settings document not found, using defaults")
                return {
                    "provider": "claude",
                    "model": "claude-3-haiku-20240307",
                    "minMatchScore": 70,
                    "costBudgetDaily": 50.0,
                }

        except Exception as e:
            logger.error(f"Error loading AI settings from Firestore: {e}")
            return {
                "provider": "claude",
                "model": "claude-3-haiku-20240307",
                "minMatchScore": 70,
                "costBudgetDaily": 50.0,
            }

    def get_job_filters(self) -> Dict[str, Any]:
        """
        Get job filter configuration.

        Returns:
            Dictionary with filter settings for pre-AI job filtering
        """
        if "job_filters" in self._cache:
            return self._cache["job_filters"]

        try:
            doc = self.db.collection(self.collection_name).document("job-filters").get()

            if doc.exists:
                data = doc.to_dict()
                filters = {
                    # Exclusions
                    "excludedCompanies": data.get("excludedCompanies", []),
                    "excludedDomains": data.get("excludedDomains", []),
                    "excludedKeywordsUrl": data.get("excludedKeywordsUrl", []),
                    "excludedKeywordsTitle": data.get("excludedKeywordsTitle", []),
                    "excludedKeywordsDescription": data.get("excludedKeywordsDescription", []),
                    # Location & Remote
                    "remotePolicy": data.get("remotePolicy", "remote_only"),
                    "allowedLocations": data.get("allowedLocations", []),
                    # Job Type
                    "employmentType": data.get("employmentType", "full_time"),
                    # Experience
                    "minYearsExperience": data.get("minYearsExperience"),
                    "maxYearsExperience": data.get("maxYearsExperience"),
                    "allowedSeniority": data.get("allowedSeniority", []),
                    # Salary
                    "minSalary": data.get("minSalary"),
                    # Tech Stack
                    "requiredTech": data.get("requiredTech", []),
                    "excludedTech": data.get("excludedTech", []),
                    # Quality
                    "minDescriptionLength": data.get("minDescriptionLength", 200),
                    "rejectCommissionOnly": data.get("rejectCommissionOnly", True),
                    # Meta
                    "enabled": data.get("enabled", True),
                }
                self._cache["job_filters"] = filters
                logger.info(
                    f"Loaded job filters: enabled={filters['enabled']}, "
                    f"remotePolicy={filters['remotePolicy']}, "
                    f"requiredTech={len(filters['requiredTech'])} items"
                )
                return filters
            else:
                logger.warning("Job filters document not found, using defaults")
                return self._get_default_job_filters()

        except Exception as e:
            logger.error(f"Error loading job filters from Firestore: {e}")
            return self._get_default_job_filters()

    def _get_default_job_filters(self) -> Dict[str, Any]:
        """Get default job filter configuration."""
        return {
            # Exclusions
            "excludedCompanies": [],
            "excludedDomains": [],
            "excludedKeywordsUrl": [],
            "excludedKeywordsTitle": ["senior", "lead", "principal", "intern", "junior"],
            "excludedKeywordsDescription": ["clearance required", "relocation required"],
            # Location & Remote
            "remotePolicy": "remote_only",
            "allowedLocations": ["Portland, OR", "Remote"],
            # Job Type
            "employmentType": "full_time",
            # Experience
            "minYearsExperience": 3,
            "maxYearsExperience": 10,
            "allowedSeniority": ["mid", "senior"],
            # Salary
            "minSalary": 100000,
            # Tech Stack
            "requiredTech": ["Python", "TypeScript", "React", "Node.js", "AWS"],
            "excludedTech": ["PHP", "WordPress", "Java"],
            # Quality
            "minDescriptionLength": 200,
            "rejectCommissionOnly": True,
            # Meta
            "enabled": True,
        }

    def refresh_cache(self) -> None:
        """Clear cache to force reload of all settings on next access."""
        self._cache.clear()
        logger.info("Configuration cache cleared")
