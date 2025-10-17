"""
Filter models for job intake filtering.

These models define the results of the filter engine.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class FilterRejection:
    """
    Detailed rejection reason from filter engine.

    Attributes:
        filter_category: High-level category (e.g., "location", "experience", "tech_stack")
        filter_name: Specific filter that rejected (e.g., "remote_policy", "min_years_experience")
        reason: Human-readable short reason
        detail: Specific detail about why rejected
    """

    filter_category: str
    filter_name: str
    reason: str
    detail: str

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "filter_category": self.filter_category,
            "filter_name": self.filter_name,
            "reason": self.reason,
            "detail": self.detail,
        }


@dataclass
class FilterResult:
    """
    Result of running filter engine on a job.

    Attributes:
        passed: True if job passed all filters
        rejections: List of rejection reasons (empty if passed)
    """

    passed: bool
    rejections: List[FilterRejection] = field(default_factory=list)

    def add_rejection(
        self, filter_category: str, filter_name: str, reason: str, detail: str
    ) -> None:
        """
        Add a rejection reason.

        Args:
            filter_category: Category of filter
            filter_name: Name of filter
            reason: Human-readable reason
            detail: Specific detail
        """
        self.passed = False
        self.rejections.append(
            FilterRejection(
                filter_category=filter_category,
                filter_name=filter_name,
                reason=reason,
                detail=detail,
            )
        )

    def get_rejection_summary(self) -> str:
        """
        Get comma-separated list of rejection reasons.

        Returns:
            Summary string like "Missing required technologies, Requires too much experience"
        """
        if not self.rejections:
            return "No rejections"
        return ", ".join([r.reason for r in self.rejections])

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "passed": self.passed,
            "rejections": [r.to_dict() for r in self.rejections],
            "rejection_summary": self.get_rejection_summary(),
        }
