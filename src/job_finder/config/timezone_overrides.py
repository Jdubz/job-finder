"""
Timezone override configuration loader.

Loads and caches company timezone overrides from config/company/timezone_overrides.json
to prevent timezone penalties for globally distributed companies.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from job_finder.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Global cache for loaded overrides
_OVERRIDE_CACHE: Optional["TimezoneOverrideConfig"] = None


class TimezoneOverrideConfig:
    """Loads and manages timezone override configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize timezone override configuration.

        Args:
            config_path: Path to timezone_overrides.json (defaults to config/company/timezone_overrides.json)
        """
        if config_path is None:
            # Default to config/company/timezone_overrides.json relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "company" / "timezone_overrides.json"

        self.config_path = config_path
        self.overrides: Dict[str, str] = {}  # company_name -> timezone
        self.patterns: List[Dict] = []  # regex patterns for matching
        self.metadata: Dict = {}

        self._load_config()

    def _load_config(self) -> None:
        """Load and validate timezone override configuration."""
        if not self.config_path.exists():
            logger.warning(
                f"Timezone override config not found at {self.config_path}, "
                f"proceeding without overrides"
            )
            return

        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)

            # Validate required fields
            if "overrides" not in config:
                raise ConfigurationError("Missing 'overrides' field in timezone_overrides.json")

            # Store metadata
            self.metadata = {
                "version": config.get("version", "unknown"),
                "last_updated": config.get("last_updated", "unknown"),
                "description": config.get("description", ""),
            }

            # Load company-specific overrides
            for override in config["overrides"]:
                if "company_name" not in override or "timezone" not in override:
                    logger.warning(f"Skipping invalid override: {override}")
                    continue

                company_name = override["company_name"].lower()  # Case-insensitive
                timezone = override["timezone"]

                if timezone not in ["unknown", "pacific", "eastern", "central", "mountain"]:
                    logger.warning(f"Invalid timezone '{timezone}' for {company_name}, skipping")
                    continue

                self.overrides[company_name] = timezone

            # Load pattern-based overrides
            if "patterns" in config:
                for pattern in config["patterns"]:
                    if "regex" not in pattern or "timezone" not in pattern:
                        logger.warning(f"Skipping invalid pattern: {pattern}")
                        continue

                    try:
                        # Validate regex by compiling it
                        re.compile(pattern["regex"])
                        self.patterns.append(pattern)
                    except re.error as e:
                        logger.warning(f"Invalid regex pattern '{pattern['regex']}': {e}, skipping")
                        continue

            logger.info(
                f"Loaded {len(self.overrides)} company overrides "
                f"and {len(self.patterns)} patterns from {self.config_path}"
            )

        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in {self.config_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load timezone overrides: {e}")

    def get_override(self, company_name: str, company_info: str = "") -> Optional[str]:
        """
        Get timezone override for a company.

        Args:
            company_name: Company name to check
            company_info: Optional company info/description for pattern matching

        Returns:
            Timezone override ('unknown', 'pacific', etc.) or None if no override
        """
        # Check exact company name match (case-insensitive)
        company_lower = company_name.lower()
        if company_lower in self.overrides:
            logger.debug(f"Timezone override for {company_name}: {self.overrides[company_lower]}")
            return self.overrides[company_lower]

        # Check pattern-based matches
        combined_text = f"{company_name} {company_info}".lower()
        for pattern in self.patterns:
            if re.search(pattern["regex"], combined_text, re.IGNORECASE):
                timezone = pattern["timezone"]
                logger.debug(
                    f"Timezone override for {company_name} via pattern "
                    f"'{pattern['regex']}': {timezone}"
                )
                return timezone

        return None

    def is_global_company(self, company_name: str, company_info: str = "") -> bool:
        """
        Check if company is marked as global (timezone='unknown').

        Args:
            company_name: Company name to check
            company_info: Optional company info for pattern matching

        Returns:
            True if company has 'unknown' timezone override
        """
        override = self.get_override(company_name, company_info)
        return override == "unknown"


def get_timezone_overrides() -> TimezoneOverrideConfig:
    """
    Get cached timezone override configuration.

    Returns:
        TimezoneOverrideConfig instance (singleton)
    """
    global _OVERRIDE_CACHE

    if _OVERRIDE_CACHE is None:
        _OVERRIDE_CACHE = TimezoneOverrideConfig()

    return _OVERRIDE_CACHE


def reload_timezone_overrides() -> TimezoneOverrideConfig:
    """
    Reload timezone override configuration (for testing or config updates).

    Returns:
        Newly loaded TimezoneOverrideConfig instance
    """
    global _OVERRIDE_CACHE
    _OVERRIDE_CACHE = TimezoneOverrideConfig()
    return _OVERRIDE_CACHE
