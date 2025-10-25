"""Common filtering functions shared across orchestrators."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from job_finder.utils.date_utils import parse_job_date
from job_finder.utils.job_type_filter import FilterDecision, filter_job

logger = logging.getLogger(__name__)


def filter_remote_only(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter jobs to only include remote positions or Portland, OR on-site/hybrid.

    Args:
        jobs: List of jobs to filter

    Returns:
        List of jobs that are either remote or Portland-based
    """
    remote_keywords = ["remote", "work from home", "wfh", "anywhere", "distributed"]

    filtered_jobs = []
    for job in jobs:
        location = job.get("location", "").lower()
        title = job.get("title", "").lower()
        description = job.get("description", "").lower()

        # Check if remote
        is_remote = (
            any(keyword in location for keyword in remote_keywords)
            or any(keyword in title for keyword in remote_keywords)
            or any(keyword in description[:500] for keyword in remote_keywords)
        )

        # Check if Portland, OR location
        is_portland = "portland" in location and ("or" in location or "oregon" in location)

        # Include if remote OR Portland location (on-site/hybrid in Portland is OK)
        if is_remote or is_portland:
            filtered_jobs.append(job)

    return filtered_jobs


def filter_by_age(
    jobs: List[Dict[str, Any]], max_days: int = 7, verbose: bool = False
) -> List[Dict[str, Any]]:
    """
    Filter jobs to only include those posted within the last N days.

    Args:
        jobs: List of jobs to filter
        max_days: Maximum age in days (default: 7)
        verbose: Whether to log debug messages for skipped jobs

    Returns:
        List of jobs posted within max_days
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_days)
    fresh_jobs = []

    for job in jobs:
        posted_date_str = job.get("posted_date", "")

        # If no date, skip (can't verify age)
        if not posted_date_str:
            if verbose:
                logger.debug(f"Skipping job with no posted_date: {job.get('title')}")
            continue

        # Parse the date
        posted_date = parse_job_date(posted_date_str)

        # If we couldn't parse it, skip (can't verify age)
        if not posted_date:
            if verbose:
                logger.debug(f"Could not parse posted_date for: {job.get('title')}")
            continue

        # Check if within age limit
        if posted_date >= cutoff_date:
            fresh_jobs.append(job)
        else:
            if verbose:
                days_old = (datetime.now(timezone.utc) - posted_date).days
                logger.debug(
                    f"Skipping old job ({days_old} days): "
                    f"{job.get('title')} at {job.get('company')}"
                )

    return fresh_jobs


def filter_by_job_type(
    jobs: List[Dict[str, Any]],
    filters_config: Dict[str, Any],
    verbose: bool = False,
) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Filter jobs by role type and seniority before AI analysis to save costs.

    Args:
        jobs: List of jobs to filter
        filters_config: Filter configuration dict
        verbose: Whether to log debug messages for filtered jobs

    Returns:
        Tuple of (filtered_jobs, filter_stats) where filter_stats contains
        counts of jobs filtered by each reason
    """
    strict_role_filter = filters_config.get("strict_role_filtering", True)
    min_seniority = filters_config.get("min_seniority_level", None)

    filtered_jobs = []
    filter_stats: Dict[str, int] = {}

    for job in jobs:
        title = job.get("title", "")
        description = job.get("description", "")

        # Apply all filters
        decision, reason = filter_job(
            title=title,
            description=description,
            strict_role_filter=strict_role_filter,
            min_seniority=min_seniority,
        )

        if decision == FilterDecision.ACCEPT:
            filtered_jobs.append(job)
        else:
            # Track rejection reasons
            filter_stats[reason] = filter_stats.get(reason, 0) + 1
            if verbose:
                logger.debug(f"  ❌ Filtered: {title} - {reason}")

    # Log summary of filtered jobs
    if verbose and filter_stats:
        total_filtered = sum(filter_stats.values())
        logger.info(f"  Filtered out {total_filtered} jobs by role/seniority:")
        for reason, count in sorted(filter_stats.items(), key=lambda x: -x[1]):
            logger.info(f"    - {count}: {reason}")

    return filtered_jobs, filter_stats
