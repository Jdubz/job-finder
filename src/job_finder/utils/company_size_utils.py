"""Company size detection and scoring utilities."""

import re
from typing import Optional, Tuple

# Known large companies (Fortune 500, major tech companies, etc.)
KNOWN_LARGE_COMPANIES = {
    # Tech Giants
    "google",
    "alphabet",
    "microsoft",
    "apple",
    "amazon",
    "meta",
    "facebook",
    "netflix",
    "nvidia",
    "tesla",
    "oracle",
    "salesforce",
    "adobe",
    "ibm",
    "intel",
    "cisco",
    "dell",
    "hp",
    "hewlett packard",
    "sap",
    "vmware",
    # Cloud/SaaS
    "aws",
    "amazon web services",
    "azure",
    "google cloud",
    "servicenow",
    "workday",
    "atlassian",
    "slack",
    "zoom",
    "dropbox",
    "box",
    "docusign",
    # Enterprise Software
    "sap",
    "oracle",
    "servicenow",
    "palantir",
    "snowflake",
    "databricks",
    # Financial Services
    "jpmorgan",
    "goldman sachs",
    "morgan stanley",
    "wells fargo",
    "bank of america",
    "citigroup",
    "visa",
    "mastercard",
    "paypal",
    "square",
    "stripe",
    # E-commerce/Retail
    "walmart",
    "target",
    "costco",
    "ebay",
    "shopify",
    "wayfair",
    # Healthcare
    "unitedhealth",
    "cvs health",
    "anthem",
    "cigna",
    "humana",
    # Transportation/Logistics
    "fedex",
    "ups",
    "uber",
    "lyft",
    "doordash",
    "instacart",
    # Telecom
    "at&t",
    "verizon",
    "t-mobile",
    "comcast",
    "charter communications",
    # Entertainment/Media
    "disney",
    "comcast",
    "netflix",
    "spotify",
    "hulu",
    "warner bros",
    # Other Major Companies
    "boeing",
    "lockheed martin",
    "general electric",
    "ge",
    "3m",
}

# Patterns indicating large companies
LARGE_COMPANY_PATTERNS = [
    r"fortune\s*\d+",  # Fortune 500/1000
    r"\d{2,},?\d{3}\+?\s*employees",  # 10,000+ employees
    r"thousands?\s+of\s+employees",
    r"global\s+(leader|company|enterprise|organization)",
    r"world['s]?\s*(leading|largest|biggest)",
    r"publicly\s+traded",
    r"nyse|nasdaq",
    r"s&p\s*500",
    r"multinational",
    r"enterprise\s+(software|solutions|company)",
    r"industry\s+(leader|giant)",
]

# Patterns indicating small companies/startups
SMALL_COMPANY_PATTERNS = [
    r"startup",
    r"start-up",
    r"small\s+(team|company|business)",
    r"series\s+[ab]\s+funding",
    r"seed\s+(stage|funded|funding)",
    r"early[\s-]stage",
    r"pre[\s-]seed",
    r"bootstrapped",
    r"10-50\s+employees",
    r"under\s+\d{2,3}\s+employees",
    r"fewer\s+than\s+\d{2,3}",
]

# Patterns indicating medium companies
MEDIUM_COMPANY_PATTERNS = [
    r"mid[\s-]sized",
    r"growing\s+company",
    r"100-1000\s+employees",
    r"hundreds?\s+of\s+employees",
    r"series\s+[cd]\s+funding",
    r"established\s+company",
]


def detect_company_size(
    company_name: str,
    company_info: str = "",
    description: str = "",
) -> Optional[str]:
    """
    Detect company size from company name, info, and job description.

    Args:
        company_name: Company name
        company_info: Company information/about text
        description: Job description text

    Returns:
        "large", "medium", "small", or None if cannot determine
    """
    # Combine all text for analysis
    combined_text = f"{company_name} {company_info} {description}".lower()

    # Check if it's a known large company
    company_name_lower = company_name.lower()
    for known_large in KNOWN_LARGE_COMPANIES:
        if known_large in company_name_lower:
            return "large"

    # Count pattern matches
    large_matches = sum(
        1 for pattern in LARGE_COMPANY_PATTERNS if re.search(pattern, combined_text, re.IGNORECASE)
    )
    small_matches = sum(
        1 for pattern in SMALL_COMPANY_PATTERNS if re.search(pattern, combined_text, re.IGNORECASE)
    )
    medium_matches = sum(
        1 for pattern in MEDIUM_COMPANY_PATTERNS if re.search(pattern, combined_text, re.IGNORECASE)
    )

    # Determine size based on matches
    if large_matches >= 2 or (large_matches == 1 and small_matches == 0):
        return "large"
    elif small_matches >= 2 or (small_matches == 1 and large_matches == 0):
        return "small"
    elif medium_matches >= 1:
        return "medium"

    # Single match tie-breaker
    if large_matches > small_matches and large_matches > medium_matches:
        return "large"
    elif small_matches > large_matches and small_matches > medium_matches:
        return "small"
    elif medium_matches > 0:
        return "medium"

    return None


def calculate_company_size_adjustment(
    company_size: Optional[str], prefer_large: bool = True
) -> Tuple[int, str]:
    """
    Calculate score adjustment based on company size preference.

    Args:
        company_size: Detected company size ("large", "medium", "small", or None)
        prefer_large: Whether to prefer large companies (default: True)

    Returns:
        Tuple of (score_adjustment, description)
    """
    if company_size is None:
        return (0, "Unknown company size - no adjustment")

    if prefer_large:
        # Prefer large companies
        if company_size == "large":
            return (10, "Large company +10")
        elif company_size == "medium":
            return (0, "Medium company (neutral)")
        elif company_size == "small":
            return (-5, "Small company/startup -5")
    else:
        # Prefer small companies (inverse scoring)
        if company_size == "small":
            return (10, "Small company/startup +10")
        elif company_size == "medium":
            return (0, "Medium company (neutral)")
        elif company_size == "large":
            return (-5, "Large company -5")

    return (0, "Unknown company size - no adjustment")
