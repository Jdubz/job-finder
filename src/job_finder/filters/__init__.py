"""Job filtering system."""

from job_finder.filters.models import FilterRejection, FilterResult
from job_finder.filters.strike_filter_engine import StrikeFilterEngine

# REMOVED: JobFilter (legacy filter class) - use StrikeFilterEngine instead
# REMOVED: JobFilterEngine (legacy, replaced by StrikeFilterEngine) - Session 6 cleanup

__all__ = [
    "StrikeFilterEngine",
    "FilterResult",
    "FilterRejection",
]
