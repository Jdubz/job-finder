"""Timezone detection and scoring utilities."""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Timezone offset from UTC
TIMEZONES = {
    # US Timezones
    "pacific": -8,
    "pt": -8,
    "pst": -8,
    "pdt": -7,
    "mountain": -7,
    "mt": -7,
    "mst": -7,
    "mdt": -6,
    "central": -6,
    "ct": -6,
    "cst": -6,
    "cdt": -5,
    "eastern": -5,
    "et": -5,
    "est": -5,
    "edt": -4,
    # Other common timezones
    "utc": 0,
    "gmt": 0,
    "bst": 1,  # British Summer Time
    "cet": 1,  # Central European Time
    "ist": 5.5,  # India Standard Time
    "jst": 9,  # Japan Standard Time
    "aest": 10,  # Australian Eastern Standard Time
}

# City/State to timezone mapping
LOCATION_TO_TIMEZONE = {
    # US West Coast - Pacific Time
    "seattle": -8,
    "portland": -8,
    "san francisco": -8,
    "sf": -8,
    "san jose": -8,
    "los angeles": -8,
    "la": -8,
    "san diego": -8,
    "sacramento": -8,
    "oakland": -8,
    "berkeley": -8,
    "palo alto": -8,
    "mountain view": -8,
    "sunnyvale": -8,
    "santa clara": -8,
    "fremont": -8,
    "irvine": -8,
    # States - Pacific
    "california": -8,
    "oregon": -8,
    "washington": -8,
    "nevada": -8,
    # US Mountain Time
    "denver": -7,
    "phoenix": -7,
    "salt lake city": -7,
    "albuquerque": -7,
    "boulder": -7,
    "colorado": -7,
    "utah": -7,
    "arizona": -7,
    "montana": -7,
    "wyoming": -7,
    "new mexico": -7,
    "idaho": -7,
    # US Central Time
    "chicago": -6,
    "dallas": -6,
    "houston": -6,
    "austin": -6,
    "san antonio": -6,
    "minneapolis": -6,
    "kansas city": -6,
    "oklahoma city": -6,
    "milwaukee": -6,
    "nashville": -6,
    "memphis": -6,
    "new orleans": -6,
    "texas": -6,
    "illinois": -6,
    "wisconsin": -6,
    "minnesota": -6,
    "iowa": -6,
    "missouri": -6,
    "arkansas": -6,
    "louisiana": -6,
    "tennessee": -6,
    "mississippi": -6,
    "alabama": -6,
    "oklahoma": -6,
    "kansas": -6,
    # US Eastern Time
    "new york": -5,
    "nyc": -5,
    "boston": -5,
    "philadelphia": -5,
    "washington dc": -5,
    "dc": -5,
    "atlanta": -5,
    "miami": -5,
    "detroit": -5,
    "pittsburgh": -5,
    "baltimore": -5,
    "raleigh": -5,
    "charlotte": -5,
    "tampa": -5,
    "orlando": -5,
    "massachusetts": -5,
    "pennsylvania": -5,
    "virginia": -5,
    "north carolina": -5,
    "south carolina": -5,
    "georgia": -5,
    "florida": -5,
    "michigan": -5,
    "ohio": -5,
    "kentucky": -5,
    "indiana": -5,
    # Canada
    "vancouver": -8,
    "toronto": -5,
    "montreal": -5,
    "ottawa": -5,
    "calgary": -7,
    "edmonton": -7,
    "winnipeg": -6,
    # UK
    "london": 0,
    "manchester": 0,
    "edinburgh": 0,
    "glasgow": 0,
    "birmingham": 0,
    "united kingdom": 0,
    "uk": 0,
    "england": 0,
    "scotland": 0,
    # Europe
    "berlin": 1,
    "paris": 1,
    "amsterdam": 1,
    "brussels": 1,
    "madrid": 1,
    "rome": 1,
    "vienna": 1,
    "zurich": 1,
    "stockholm": 1,
    "copenhagen": 1,
    "oslo": 1,
    "helsinki": 1,
    "dublin": 0,
    "germany": 1,
    "france": 1,
    "netherlands": 1,
    "belgium": 1,
    "spain": 1,
    "italy": 1,
    "switzerland": 1,
    "austria": 1,
    "sweden": 1,
    "denmark": 1,
    "norway": 1,
    "finland": 1,
    "ireland": 0,
    # Asia
    "bangalore": 5.5,
    "mumbai": 5.5,
    "delhi": 5.5,
    "hyderabad": 5.5,
    "chennai": 5.5,
    "india": 5.5,
    "singapore": 8,
    "tokyo": 9,
    "japan": 9,
    "beijing": 8,
    "shanghai": 8,
    "china": 8,
    "hong kong": 8,
    "seoul": 9,
    "south korea": 9,
    # Australia
    "sydney": 10,
    "melbourne": 10,
    "brisbane": 10,
    "perth": 8,
    "australia": 10,
}


def detect_timezone_from_location(location: str) -> Optional[float]:
    """
    Detect timezone offset from location string.

    Args:
        location: Location string (e.g., "San Francisco, CA", "Remote - US", "London, UK")

    Returns:
        Timezone offset from UTC in hours, or None if not detected.
    """
    if not location:
        return None

    location_lower = location.lower()

    # Check for explicit timezone mentions
    for tz_name, offset in TIMEZONES.items():
        if tz_name in location_lower:
            return offset

    # Check for city/state mentions
    for place, offset in LOCATION_TO_TIMEZONE.items():
        if place in location_lower:
            return offset

    return None


def detect_timezone_for_job(
    job_location: str,
    job_description: str,
    company_size: Optional[str] = None,
    headquarters_location: str = "",
    company_name: str = "",
    company_info: str = "",
) -> Optional[float]:
    """
    Detect timezone for a job with smart prioritization and company overrides.

    Priority:
    0. Check timezone overrides for globally distributed companies (NEW)
    1. Team location mentioned in job description
    2. Job location
    3. Company headquarters (only for small/medium companies)
    4. None for large global companies without specific team location

    Args:
        job_location: Job location string
        job_description: Job description (may contain team location info)
        company_size: Company size category ("large", "medium", "small")
        headquarters_location: Company headquarters location
        company_name: Company name (for override lookup)
        company_info: Company info/description (for pattern matching)

    Returns:
        Timezone offset from UTC, or None if not detected or globally distributed company
    """
    # Check for timezone overrides first (globally distributed companies)
    if company_name:
        try:
            from job_finder.config.timezone_overrides import get_timezone_overrides

            overrides = get_timezone_overrides()
            override = overrides.get_override(company_name, company_info)

            if override == "unknown":
                logger.debug(
                    f"Timezone override for {company_name}: returning None (globally distributed)"
                )
                return None
            elif override:
                # If override specifies a specific timezone, use it
                timezone_offset = TIMEZONES.get(override.lower())
                if timezone_offset is not None:
                    logger.debug(
                        f"Timezone override for {company_name}: {override} ({timezone_offset})"
                    )
                    return timezone_offset

        except Exception as e:
            # Don't fail job processing if override loading fails
            logger.warning(f"Failed to check timezone overrides for {company_name}: {e}")

    # For large companies, skip HQ timezone unless specific team location is mentioned
    if company_size == "large":
        # Check job description for team-specific location mentions
        team_tz = detect_timezone_from_location(job_description)
        if team_tz is not None:
            return team_tz

        # Check job location (remote jobs may specify region)
        job_tz = detect_timezone_from_location(job_location)
        if job_tz is not None:
            return job_tz

        # Large companies are global - don't assume HQ timezone
        return None

    # For small/medium companies, use standard priority
    # 1. Check job description for team location
    team_tz = detect_timezone_from_location(job_description)
    if team_tz is not None:
        return team_tz

    # 2. Check job location
    job_tz = detect_timezone_from_location(job_location)
    if job_tz is not None:
        return job_tz

    # 3. Fall back to headquarters for small/medium companies
    if headquarters_location:
        hq_tz = detect_timezone_from_location(headquarters_location)
        if hq_tz is not None:
            return hq_tz

    return None


def calculate_timezone_score_adjustment(
    job_timezone: Optional[float], user_timezone: float = -8
) -> Tuple[int, str]:
    """
    Calculate score adjustment based on timezone difference from user's timezone.

    Args:
        job_timezone: Job's timezone offset from UTC (e.g., -8 for Pacific)
        user_timezone: User's timezone offset from UTC (default: -8 for Pacific)

    Returns:
        Tuple of (score_adjustment, description)
        - Bonus points for Pacific Time (+5)
        - Penalty increases with distance from Pacific Time
        - No adjustment if timezone cannot be determined
    """
    if job_timezone is None:
        return (0, "Unknown timezone - no adjustment")

    # Calculate absolute hour difference
    hour_diff = abs(job_timezone - user_timezone)

    # Same timezone - bonus points!
    if hour_diff == 0:
        return (5, "Same timezone (Pacific) +5")

    # 1-2 hours difference - minor penalty
    if hour_diff <= 2:
        return (-2, f"{hour_diff}h timezone difference -2")

    # 3-4 hours difference - moderate penalty
    if hour_diff <= 4:
        return (-5, f"{hour_diff}h timezone difference -5")

    # 5-8 hours difference - significant penalty
    if hour_diff <= 8:
        return (-10, f"{hour_diff}h timezone difference -10")

    # 9+ hours difference - major penalty
    return (-15, f"{hour_diff}h timezone difference -15")
