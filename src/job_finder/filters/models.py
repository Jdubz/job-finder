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
        severity: "hard_reject" or "strike"
        points: Strike points (0 for hard rejects)
    """

    filter_category: str
    filter_name: str
    reason: str
    detail: str
    severity: str = "hard_reject"  # "hard_reject" or "strike"
    points: int = 0  # Strike points (0 for hard rejects)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "filter_category": self.filter_category,
            "filter_name": self.filter_name,
            "reason": self.reason,
            "detail": self.detail,
            "severity": self.severity,
            "points": self.points,
        }


@dataclass
class FilterResult:
    """
    Result of running filter engine on a job.

    Attributes:
        passed: True if job passed all filters
        rejections: List of rejection reasons (empty if passed)
        total_strikes: Total strike points accumulated
        strike_threshold: Threshold for filtering (default 5)
    """

    passed: bool
    rejections: List[FilterRejection] = field(default_factory=list)
    total_strikes: int = 0
    strike_threshold: int = 5

    def add_rejection(
        self,
        filter_category: str,
        filter_name: str,
        reason: str,
        detail: str,
        severity: str = "hard_reject",
        points: int = 0,
    ) -> None:
        """
        Add a rejection reason.

        Args:
            filter_category: Category of filter
            filter_name: Name of filter
            reason: Human-readable reason
            detail: Specific detail
            severity: "hard_reject" or "strike"
            points: Strike points (0 for hard rejects)
        """
        if severity == "hard_reject":
            self.passed = False

        self.rejections.append(
            FilterRejection(
                filter_category=filter_category,
                filter_name=filter_name,
                reason=reason,
                detail=detail,
                severity=severity,
                points=points,
            )
        )

    def add_strike(
        self, filter_category: str, filter_name: str, reason: str, detail: str, points: int
    ) -> None:
        """
        Add a strike (does not immediately fail).

        Args:
            filter_category: Category of filter
            filter_name: Name of filter
            reason: Human-readable reason
            detail: Specific detail
            points: Strike points to add
        """
        self.total_strikes += points
        self.add_rejection(
            filter_category=filter_category,
            filter_name=filter_name,
            reason=reason,
            detail=detail,
            severity="strike",
            points=points,
        )

        # Check if strikes exceeded threshold
        if self.total_strikes >= self.strike_threshold:
            self.passed = False

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
            "total_strikes": self.total_strikes,
            "strike_threshold": self.strike_threshold,
            "hard_rejections": [
                r.to_dict() for r in self.rejections if r.severity == "hard_reject"
            ],
            "strikes": [r.to_dict() for r in self.rejections if r.severity == "strike"],
        }
