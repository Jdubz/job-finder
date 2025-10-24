"""Load queue configuration from Firestore."""

import logging
from typing import Any, Dict, List, Optional

from job_finder.constants import DEFAULT_STRIKE_THRESHOLD
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
        """Get default job filter configuration (strike-based system)."""
        return {
            # Meta
            "enabled": True,
            "strikeThreshold": DEFAULT_STRIKE_THRESHOLD,
            # Hard Rejections
            "hardRejections": {
                "excludedJobTypes": ["sales", "hr", "recruiter", "support", "customer success"],
                "excludedSeniority": [
                    "associate",
                    "junior",
                    "intern",
                    "entry-level",
                    "entry level",
                    "co-op",
                ],
                "excludedCompanies": [],
                "excludedKeywords": [
                    "clearance required",
                    "security clearance",
                    "relocation required",
                    "must relocate",
                ],
                "minSalaryFloor": 100000,
                "rejectCommissionOnly": True,
            },
            # Remote Policy
            "remotePolicy": {
                "allowRemote": True,
                "allowHybridPortland": True,
                "allowOnsite": False,
            },
            # Strike: Salary
            "salaryStrike": {"enabled": True, "threshold": 150000, "points": 2},
            # Strike: Experience
            "experienceStrike": {"enabled": True, "minPreferred": 6, "points": 1},
            # Strike: Seniority
            "seniorityStrikes": {
                "mid-level": 2,
                "mid level": 2,
                "principal": 1,
                "director": 1,
                "manager": 1,
                "engineering manager": 1,
            },
            # Strike: Quality
            "qualityStrikes": {
                "minDescriptionLength": 200,
                "shortDescriptionPoints": 1,
                "buzzwords": ["rockstar", "ninja", "guru", "10x engineer", "code wizard"],
                "buzzwordPoints": 1,
            },
            # Strike: Age
            "ageStrike": {
                "enabled": True,
                "strikeDays": 1,  # > 1 day = strike
                "rejectDays": 7,  # > 7 days = hard reject
                "points": 1,
            },
        }

    def get_technology_ranks(self) -> Dict[str, Any]:
        """
        Get technology ranking configuration.

        Returns:
            Dictionary with technology ranks for strike-based filtering
        """
        if "technology_ranks" in self._cache:
            return self._cache["technology_ranks"]

        try:
            doc = self.db.collection(self.collection_name).document("technology-ranks").get()

            if doc.exists:
                data = doc.to_dict()
                tech_ranks = {
                    "technologies": data.get("technologies", {}),
                    "strikes": data.get("strikes", {"missingAllRequired": 1, "perBadTech": 2}),
                }
                self._cache["technology_ranks"] = tech_ranks
                logger.info(
                    f"Loaded technology ranks: {len(tech_ranks['technologies'])} technologies"
                )
                return tech_ranks
            else:
                logger.warning("Technology ranks document not found, using defaults")
                return self._get_default_technology_ranks()

        except Exception as e:
            logger.error(f"Error loading technology ranks from Firestore: {e}")
            return self._get_default_technology_ranks()

    def _get_default_technology_ranks(self) -> Dict[str, Any]:
        """Get default technology ranking configuration."""
        return {
            "technologies": {
                # Required (must have at least one)
                "Python": {"rank": "required", "points": 0, "mentions": 0},
                "TypeScript": {"rank": "required", "points": 0, "mentions": 0},
                "JavaScript": {"rank": "required", "points": 0, "mentions": 0},
                "React": {"rank": "required", "points": 0, "mentions": 0},
                "Angular": {"rank": "required", "points": 0, "mentions": 0},
                "Node.js": {"rank": "required", "points": 0, "mentions": 0},
                "GCP": {"rank": "required", "points": 0, "mentions": 0},
                "Google Cloud": {"rank": "required", "points": 0, "mentions": 0},
                "Kubernetes": {"rank": "required", "points": 0, "mentions": 0},
                "Docker": {"rank": "required", "points": 0, "mentions": 0},
                # OK (neutral)
                "C++": {"rank": "ok", "points": 0, "mentions": 0},
                "Go": {"rank": "ok", "points": 0, "mentions": 0},
                "Rust": {"rank": "ok", "points": 0, "mentions": 0},
                "PostgreSQL": {"rank": "ok", "points": 0, "mentions": 0},
                "MySQL": {"rank": "ok", "points": 0, "mentions": 0},
                "MongoDB": {"rank": "ok", "points": 0, "mentions": 0},
                "Redis": {"rank": "ok", "points": 0, "mentions": 0},
                # Strike (prefer to avoid)
                "Java": {"rank": "strike", "points": 2, "mentions": 0},
                "PHP": {"rank": "strike", "points": 2, "mentions": 0},
                "Ruby": {"rank": "strike", "points": 2, "mentions": 0},
                "Rails": {"rank": "strike", "points": 2, "mentions": 0},
                "Ruby on Rails": {"rank": "strike", "points": 2, "mentions": 0},
                "WordPress": {"rank": "strike", "points": 2, "mentions": 0},
                ".NET": {"rank": "strike", "points": 2, "mentions": 0},
                "C#": {"rank": "strike", "points": 2, "mentions": 0},
                "Perl": {"rank": "strike", "points": 2, "mentions": 0},
            },
            "strikes": {"missingAllRequired": 1, "perBadTech": 2},
        }

    def get_scheduler_settings(self) -> Optional[Dict[str, Any]]:
        """
        Get scheduler settings for cron-based scraping.

        Returns:
            Dictionary with enabled, cron_schedule, daytime_hours, target_matches, etc.
            Returns None if settings document doesn't exist (scheduler should not run).
        """
        if "scheduler_settings" in self._cache:
            return self._cache["scheduler_settings"]

        try:
            doc = self.db.collection(self.collection_name).document("scheduler-settings").get()

            if doc.exists:
                data = doc.to_dict()
                settings = {
                    # Enable/disable scheduler
                    "enabled": data.get("enabled", True),
                    # Cron schedule (stored for reference, actual scheduling happens in crontab)
                    "cron_schedule": data.get("cron_schedule", "0 */6 * * *"),
                    # Daytime hours (when to actually run scrapes)
                    "daytime_hours": data.get("daytime_hours", {"start": 6, "end": 22}),
                    # Timezone for daytime hours check
                    "timezone": data.get("timezone", "America/Los_Angeles"),
                    # Scrape settings
                    "target_matches": data.get("target_matches", 5),
                    "max_sources": data.get("max_sources", 10),
                    "min_match_score": data.get("min_match_score", 80),
                    # Metadata
                    "last_updated": data.get("updatedAt"),
                    "updated_by": data.get("updatedBy"),
                }
                self._cache["scheduler_settings"] = settings
                logger.info(
                    f"Loaded scheduler settings: enabled={settings['enabled']}, "
                    f"target_matches={settings['target_matches']}, "
                    f"max_sources={settings['max_sources']}"
                )
                return settings
            else:
                logger.error(
                    "Scheduler settings document not found in Firestore. "
                    "Please run 'python scripts/setup_firestore_config.py' to create it."
                )
                return None

        except Exception as e:
            logger.error(f"Error loading scheduler settings from Firestore: {e}")
            return None

    def refresh_cache(self) -> None:
        """Clear cache to force reload of all settings on next access."""
        self._cache.clear()
        logger.info("Configuration cache cleared")
