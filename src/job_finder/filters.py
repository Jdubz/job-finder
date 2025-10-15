"""Job filtering logic based on user requirements."""

from typing import Any, Dict, List


class JobFilter:
    """Filter jobs based on user-defined criteria."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize filter with configuration."""
        self.config = config

    def filter_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter jobs based on configured criteria.

        Args:
            jobs: List of job postings to filter.

        Returns:
            Filtered list of job postings.
        """
        filtered = jobs

        # Apply keyword matching
        if keywords := self.config.get("profile", {}).get("keywords", []):
            filtered = self._filter_by_keywords(filtered, keywords)

        # Apply location filtering
        if locations := self.config.get("profile", {}).get("preferred_locations", []):
            filtered = self._filter_by_location(filtered, locations)

        # Exclude based on keywords
        if excluded := self.config.get("profile", {}).get("excluded_keywords", []):
            filtered = self._exclude_by_keywords(filtered, excluded)

        return filtered

    def _filter_by_keywords(
        self, jobs: List[Dict[str, Any]], keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """Filter jobs containing any of the specified keywords."""
        return [
            job
            for job in jobs
            if any(
                keyword.lower() in job.get("title", "").lower()
                or keyword.lower() in job.get("description", "").lower()
                for keyword in keywords
            )
        ]

    def _filter_by_location(
        self, jobs: List[Dict[str, Any]], locations: List[str]
    ) -> List[Dict[str, Any]]:
        """Filter jobs in preferred locations."""
        return [
            job
            for job in jobs
            if any(location.lower() in job.get("location", "").lower() for location in locations)
        ]

    def _exclude_by_keywords(
        self, jobs: List[Dict[str, Any]], keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """Exclude jobs containing any of the specified keywords."""
        return [
            job
            for job in jobs
            if not any(
                keyword.lower() in job.get("title", "").lower()
                or keyword.lower() in job.get("description", "").lower()
                for keyword in keywords
            )
        ]
