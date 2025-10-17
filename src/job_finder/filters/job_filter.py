"""
Legacy job filtering logic based on user requirements.

NOTE: This is the old filtering system used by main.py (legacy batch processing).
For queue-based processing, use JobFilterEngine instead.
"""

from typing import Any, Dict, List


class JobFilter:
    """Filter jobs based on user-defined criteria (legacy system)."""

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

        # Apply remote/Portland hybrid filter (always applied)
        filtered = self._filter_by_work_location(filtered)

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

    def _filter_by_work_location(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter jobs to only include remote jobs or Portland, OR hybrid jobs.

        Args:
            jobs: List of job postings to filter.

        Returns:
            Filtered list of job postings.
        """
        filtered_jobs = []

        for job in jobs:
            location = job.get("location", "").lower()
            description = job.get("description", "").lower()
            title = job.get("title", "").lower()

            # Check if job is remote
            is_remote = (
                "remote" in location
                or "remote" in description
                or "remote" in title
                or "work from home" in description
                or "wfh" in description
            )

            # Check if job is in Portland, OR
            is_portland = "portland" in location and ("or" in location or "oregon" in location)

            # Check if job is hybrid
            is_hybrid = "hybrid" in location or "hybrid" in description or "hybrid" in title

            # Include if remote OR (Portland AND hybrid)
            if is_remote or (is_portland and is_hybrid):
                filtered_jobs.append(job)

        return filtered_jobs

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
