"""Job filtering system."""

from job_finder.filters.filter_engine import JobFilterEngine
from job_finder.filters.models import FilterRejection, FilterResult
from job_finder.filters.strike_filter_engine import StrikeFilterEngine

# REMOVED: JobFilter (legacy filter class) - use StrikeFilterEngine instead

__all__ = [
    "JobFilterEngine",
    "StrikeFilterEngine",
    "FilterResult",
    "FilterRejection",
]
