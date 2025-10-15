"""Job type and seniority filtering for pre-AI filtering.

This module provides hard-blocking filters to eliminate unwanted job types
(sales, management, recruiting, etc.) and junior-level positions BEFORE
running expensive AI analysis.
"""

from enum import Enum
from typing import Optional, Tuple


class FilterDecision(Enum):
    """Decision from job type filter."""

    ACCEPT = "accept"
    REJECT = "reject"


# === JOB TYPE FILTERS ===

# Management/Executive roles (BLOCK)
MANAGEMENT_KEYWORDS = [
    "manager",
    "director",
    "vp",
    "vice president",
    "head of",
    "chief",
    "cto",
    "cio",
    "ceo",
    "coo",
    "executive",
    "supervisor",
    "coordinator",
]

# Sales/Business Development roles (BLOCK)
SALES_KEYWORDS = [
    "sales",
    "account executive",
    "account manager",
    "business development",
    " bd ",  # Space-padded to avoid matching "embedded"
    "partnerships",
    "customer success",
    "sales engineer",  # Different from solutions engineer
    "pre-sales",
    "presales",
]

# Recruiting/HR roles (BLOCK)
RECRUITING_KEYWORDS = [
    "recruiter",
    "recruitment",
    "talent acquisition",
    " hr ",
    "human resources",
    "people operations",
    "talent partner",
    "staffing",
]

# Product/Program Management roles (BLOCK)
PRODUCT_MANAGEMENT_KEYWORDS = [
    "product manager",
    " pm ",  # Space-padded to avoid matching "rpm", "npm"
    "program manager",
    "product owner",
    "scrum master",
    "agile coach",
    "project manager",
    "delivery manager",
]

# Data/Analytics (Non-Engineering) roles (BLOCK)
DATA_ANALYTICS_KEYWORDS = [
    "data analyst",
    "business analyst",
    " analyst",  # Generic analyst
    "analytics",
    " bi ",  # Business Intelligence
    "business intelligence",
]

# Other non-engineering roles (BLOCK)
OTHER_NON_ENGINEERING_KEYWORDS = [
    "designer",
    " ux ",
    " ui ",
    "user experience",
    "user interface",
    "marketing",
    "content",
    "writer",
    "technical writer",
    "consultant",
    "support",
    "success engineer",  # Customer success engineer
    "admin",
    "administrator",
]

# Acceptable "lead" variants (ALLOW even with "lead" in title)
ACCEPTABLE_LEAD_VARIANTS = [
    "tech lead",
    "technical lead",
    "lead engineer",
    "lead developer",
    "lead software",
    "engineering lead",
    "development lead",
    "lead programmer",
    "lead architect",
]

# Engineering role indicators (REQUIRED - at least one must match)
ENGINEERING_ROLE_KEYWORDS = [
    "engineer",
    "developer",
    "programmer",
    "architect",
    "sre",
    "devops",
    "software",
]

# Acceptable data roles (ALLOW - these are engineering, not analytics)
ACCEPTABLE_DATA_ROLES = [
    "data engineer",
    "ml engineer",
    "machine learning engineer",
    "ai engineer",
    "analytics engineer",
    "mlops",
]

# === SENIORITY FILTERS ===

# Block junior/entry-level roles (BLOCK)
JUNIOR_KEYWORDS = [
    "intern",
    "internship",
    "junior",
    "associate",
    "entry level",
    "entry-level",
    " i$",  # Engineer I, Software Engineer I (end of string)
    " ii$",  # Engineer II (end of string)
    "engineer i",  # Also catch variations
    "engineer ii",
    "graduate",
    "new grad",
    "early career",
]

# Preferred senior-level indicators (PREFER but don't require)
SENIOR_KEYWORDS = [
    "senior",
    "staff",
    "principal",
    "distinguished",
    "fellow",
    "architect",
    "lead",  # If combined with engineering role
]


def is_acceptable_lead_role(title: str) -> bool:
    """
    Check if title contains an acceptable lead variant.

    Args:
        title: Job title

    Returns:
        True if title contains acceptable lead variant (e.g., "tech lead", "lead engineer")
    """
    title_lower = title.lower()
    return any(variant in title_lower for variant in ACCEPTABLE_LEAD_VARIANTS)


def is_acceptable_data_role(title: str) -> bool:
    """
    Check if title is an acceptable data/ML engineering role.

    Args:
        title: Job title

    Returns:
        True if title is data/ML engineering (not analytics)
    """
    title_lower = title.lower()
    return any(variant in title_lower for variant in ACCEPTABLE_DATA_ROLES)


def has_engineering_role_keyword(title: str) -> bool:
    """
    Check if title contains at least one engineering role keyword.

    Args:
        title: Job title

    Returns:
        True if title contains engineer, developer, programmer, etc.
    """
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in ENGINEERING_ROLE_KEYWORDS)


def check_job_type_filter(title: str, strict: bool = True) -> Tuple[FilterDecision, str]:
    """
    Check if job title passes job type filter.

    Args:
        title: Job title string
        strict: If True, require engineering keywords. If False, only block bad keywords.

    Returns:
        Tuple of (FilterDecision, reason)
        - FilterDecision.ACCEPT if job passes filter
        - FilterDecision.REJECT if job should be blocked, with reason string
    """
    title_lower = title.lower()

    # Exception 1: Acceptable lead variants are always OK
    if is_acceptable_lead_role(title):
        return (FilterDecision.ACCEPT, "Acceptable technical lead role")

    # Exception 2: Acceptable data/ML engineering roles are OK
    if is_acceptable_data_role(title):
        return (FilterDecision.ACCEPT, "Data/ML engineering role")

    # Block: Management/Executive
    for keyword in MANAGEMENT_KEYWORDS:
        if keyword in title_lower:
            return (FilterDecision.REJECT, f"Management/Executive role: '{keyword}'")

    # Block: Sales/Business Development
    for keyword in SALES_KEYWORDS:
        if keyword in title_lower:
            return (FilterDecision.REJECT, f"Sales/BD role: '{keyword}'")

    # Block: Recruiting/HR
    for keyword in RECRUITING_KEYWORDS:
        if keyword in title_lower:
            return (FilterDecision.REJECT, f"Recruiting/HR role: '{keyword}'")

    # Block: Product/Program Management
    for keyword in PRODUCT_MANAGEMENT_KEYWORDS:
        if keyword in title_lower:
            return (FilterDecision.REJECT, f"Product/Program Management: '{keyword}'")

    # Block: Data/Analytics (non-engineering)
    for keyword in DATA_ANALYTICS_KEYWORDS:
        if keyword in title_lower:
            return (FilterDecision.REJECT, f"Data Analytics (non-engineering): '{keyword}'")

    # Block: Other non-engineering
    for keyword in OTHER_NON_ENGINEERING_KEYWORDS:
        if keyword in title_lower:
            return (FilterDecision.REJECT, f"Non-engineering role: '{keyword}'")

    # Strict mode: REQUIRE engineering keywords
    if strict and not has_engineering_role_keyword(title):
        return (
            FilterDecision.REJECT,
            "No engineering role keywords (engineer, developer, programmer, etc.)",
        )

    return (FilterDecision.ACCEPT, "Passed job type filter")


def check_seniority_filter(
    title: str, min_seniority: Optional[str] = None
) -> Tuple[FilterDecision, str]:
    """
    Check if job title passes seniority filter.

    Args:
        title: Job title string
        min_seniority: Minimum seniority level ("senior", "staff", "principal", or None)

    Returns:
        Tuple of (FilterDecision, reason)
        - FilterDecision.ACCEPT if job passes filter
        - FilterDecision.REJECT if job should be blocked, with reason string
    """
    title_lower = title.lower()

    # Always block junior/entry-level
    for keyword in JUNIOR_KEYWORDS:
        # Use regex for patterns ending with $
        if keyword.endswith("$"):
            import re

            if re.search(keyword, title_lower):
                return (FilterDecision.REJECT, f"Junior/Entry-level role: '{keyword.rstrip('$')}'")
        elif keyword in title_lower:
            return (FilterDecision.REJECT, f"Junior/Entry-level role: '{keyword}'")

    # If min_seniority is set, check for senior-level indicators
    if min_seniority:
        min_level_lower = min_seniority.lower()

        # Check if title has any senior-level indicators
        has_senior_indicator = any(keyword in title_lower for keyword in SENIOR_KEYWORDS)

        if not has_senior_indicator:
            return (
                FilterDecision.REJECT,
                f"Does not meet minimum seniority level: {min_seniority}",
            )

        # Additional check: if requiring "staff" or above, check for exact level match
        if min_level_lower == "staff":
            # Require staff, principal, distinguished, or fellow
            if not any(
                level in title_lower for level in ["staff", "principal", "distinguished", "fellow"]
            ):
                return (
                    FilterDecision.REJECT,
                    f"Does not meet minimum seniority level: {min_seniority}",
                )
        elif min_level_lower == "principal":
            # Require principal, distinguished, or fellow (not staff)
            if not any(level in title_lower for level in ["principal", "distinguished", "fellow"]):
                return (
                    FilterDecision.REJECT,
                    f"Does not meet minimum seniority level: {min_seniority}",
                )
        elif min_level_lower == "distinguished":
            # Require distinguished or fellow (not staff or principal)
            if not any(level in title_lower for level in ["distinguished", "fellow"]):
                return (
                    FilterDecision.REJECT,
                    f"Does not meet minimum seniority level: {min_seniority}",
                )

    return (FilterDecision.ACCEPT, "Passed seniority filter")


def filter_job(
    title: str,
    description: str = "",
    strict_role_filter: bool = True,
    min_seniority: Optional[str] = None,
) -> Tuple[FilterDecision, str]:
    """
    Apply all job filters (type and seniority).

    Args:
        title: Job title
        description: Job description (optional, for additional context)
        strict_role_filter: If True, require engineering keywords in title
        min_seniority: Minimum seniority level ("senior", "staff", "principal", or None)

    Returns:
        Tuple of (FilterDecision, reason)
        - FilterDecision.ACCEPT if job passes all filters
        - FilterDecision.REJECT if job should be blocked, with reason string
    """
    # Check job type filter first
    type_decision, type_reason = check_job_type_filter(title, strict=strict_role_filter)
    if type_decision == FilterDecision.REJECT:
        return (type_decision, type_reason)

    # Check seniority filter
    seniority_decision, seniority_reason = check_seniority_filter(title, min_seniority)
    if seniority_decision == FilterDecision.REJECT:
        return (seniority_decision, seniority_reason)

    return (FilterDecision.ACCEPT, "Passed all filters")
