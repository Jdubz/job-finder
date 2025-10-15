"""Role preference detection and scoring utilities."""

from typing import Optional, Tuple

# Preferred role keywords (engineering, development)
PREFERRED_ROLE_KEYWORDS = [
    "engineer",
    "developer",
    "programmer",
    "coder",
    "architect",
    "backend",
    "frontend",
    "full stack",
    "software",
    "devops",
    "sre",
    "platform",
    "infrastructure",
    "data engineer",
    "ml engineer",
    "ai engineer",
    "cloud engineer",
    "systems engineer",
    "technical",
]

# Less desirable role keywords (management, sales, etc.)
LESS_DESIRABLE_KEYWORDS = [
    "manager",
    "director",
    "vp",
    "vice president",
    "head of",
    "chief",
    "cto",
    "cio",
    "executive",
    "supervisor",
    "coordinator",
    "sales",
    "account executive",
    "account manager",
    "account",
    "business development",
    "bd",
    "partnerships",
    "marketing",
    "product manager",
    "pm",
    "program manager",
    "project manager",
    "delivery manager",
    "recruiter",
    "talent acquisition",
    "customer success",
    "support engineer",
    "success engineer",
    "consultant",
    "analyst",
    "data analyst",
    "business analyst",
    "designer",
    "lead",  # "lead" without "tech lead" or "technical lead"
]

# Role-defining keywords that take precedence (these define the nature of the role)
ROLE_DEFINING_KEYWORDS = [
    "manager",
    "director",
    "vp",
    "vice president",
    "head of",
    "chief",
    "cto",
    "cio",
    "executive",
    "sales",
    "account executive",
    "account manager",
    "account",
    "business development",
    "bd",
    "partnerships",
    "marketing",
    "product manager",
    "pm",
    "program manager",
    "project manager",
    "delivery manager",
    "recruiter",
    "consultant",
    "analyst",
]

# Acceptable "lead" variants (technical leadership is OK)
ACCEPTABLE_LEAD_VARIANTS = [
    "tech lead",
    "technical lead",
    "lead engineer",
    "lead developer",
    "engineering lead",
    "development lead",
]


def detect_role_type(job_title: str) -> Optional[str]:
    """
    Detect the type of role from job title.

    Args:
        job_title: Job title string

    Returns:
        "preferred" for engineering/development roles
        "less_desirable" for management/sales roles
        None if unclear
    """
    title_lower = job_title.lower()

    # Check for acceptable lead variants first
    for variant in ACCEPTABLE_LEAD_VARIANTS:
        if variant in title_lower:
            return "preferred"

    # Check for role-defining keywords (management, sales) - these take precedence
    for keyword in ROLE_DEFINING_KEYWORDS:
        if keyword in title_lower:
            return "less_desirable"

    # Check for preferred keywords
    preferred_matches = sum(1 for keyword in PREFERRED_ROLE_KEYWORDS if keyword in title_lower)

    # Check for other less desirable keywords
    less_desirable_matches = sum(1 for keyword in LESS_DESIRABLE_KEYWORDS if keyword in title_lower)

    # Determine role type based on matches
    if preferred_matches > less_desirable_matches and preferred_matches > 0:
        return "preferred"
    elif less_desirable_matches > preferred_matches and less_desirable_matches > 0:
        return "less_desirable"

    return None


def calculate_role_preference_adjustment(job_title: str) -> Tuple[int, str]:
    """
    Calculate score adjustment based on role preference.

    Args:
        job_title: Job title string

    Returns:
        Tuple of (score_adjustment, description)
    """
    role_type = detect_role_type(job_title)

    if role_type == "preferred":
        return (5, "Engineering/Developer role +5")
    elif role_type == "less_desirable":
        # Increased penalty from -10 to -25 to more aggressively filter out unwanted roles
        return (-25, "Management/Sales role -25")
    else:
        return (0, "Neutral role type")
