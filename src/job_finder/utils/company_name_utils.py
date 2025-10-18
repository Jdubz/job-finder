"""Company name normalization utilities."""

import re


def normalize_company_name(name: str) -> str:
    """
    Normalize company name for deduplication.

    Removes common suffixes and standardizes formatting to match companies
    that are essentially the same (e.g., "Cloudflare" and "Cloudflare Careers").

    Args:
        name: Company name

    Returns:
        Normalized company name

    Examples:
        >>> normalize_company_name("Cloudflare Careers")
        'cloudflare'
        >>> normalize_company_name("Google Jobs")
        'google'
        >>> normalize_company_name("Microsoft Corporation")
        'microsoft'
    """
    if not name:
        return ""

    # Convert to lowercase
    normalized = name.lower().strip()

    # Remove common job board suffixes
    # NOTE: Check dash/pipe separators BEFORE plain suffixes to match " - Careers" before "Careers"
    suffixes_to_remove = [
        r"\s+-\s+careers?$",  # " - Careers" (check before plain "careers")
        r"\s+\|\s+careers?$",  # " | Careers"
        r"\s+careers?$",  # "Careers" or "Career"
        r"\s+jobs?$",  # "Jobs" or "Job"
        r"\s+hiring$",  # "Hiring"
        r"\s+opportunities$",  # "Opportunities"
        r"\s+employment$",  # "Employment"
        r"\s+work$",  # "Work"
        r"\s+positions?$",  # "Positions" or "Position"
        r"\s+openings?$",  # "Openings" or "Opening"
    ]

    for suffix_pattern in suffixes_to_remove:
        normalized = re.sub(suffix_pattern, "", normalized, flags=re.IGNORECASE)

    # Remove common legal entity suffixes
    legal_suffixes = [
        r"\s+inc\.?$",
        r"\s+incorporated$",
        r"\s+corp\.?$",
        r"\s+corporation$",
        r"\s+llc\.?$",
        r"\s+ltd\.?$",
        r"\s+limited$",
        r"\s+co\.?$",
        r"\s+company$",
        r",?\s+inc\.?$",
        r",?\s+llc\.?$",
    ]

    for suffix_pattern in legal_suffixes:
        normalized = re.sub(suffix_pattern, "", normalized, flags=re.IGNORECASE)

    # Remove extra whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Remove punctuation at the end
    normalized = normalized.rstrip(".,;:")

    return normalized
