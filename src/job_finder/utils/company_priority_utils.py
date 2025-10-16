"""Company priority scoring utilities for job source prioritization."""

import logging
from typing import Dict, List, Optional, Tuple

from job_finder.profile.schema import Profile

logger = logging.getLogger(__name__)


def calculate_company_priority(
    company_data: Dict,
    profile: Optional[Profile] = None,
    has_portland_office: bool = False,
    tech_stack: Optional[List[str]] = None,
) -> Tuple[int, str]:
    """
    Calculate priority score and tier for a company.

    Priority scoring:
    - Portland office: +50 points
    - Tech stack alignment: up to +100 points (based on user expertise match)
    - Company size preference: uses existing company_size_utils logic

    Tiers:
    - S (150+): Perfect match - Portland office + strong tech alignment
    - A (100-149): Excellent match - Strong tech alignment
    - B (70-99): Good match - Moderate tech alignment
    - C (50-69): Moderate match - Portland office or some tech match
    - D (0-49): Basic match - Minimal alignment

    Args:
        company_data: Company information dictionary
        profile: User profile for tech stack matching
        has_portland_office: Whether company has Portland office
        tech_stack: List of company technologies/skills

    Returns:
        Tuple of (priority_score, tier)
    """
    score = 0

    # Portland office bonus
    if has_portland_office or company_data.get("hasPortlandOffice", False):
        score += 50
        logger.debug("Portland office bonus: +50 points")

    # Tech stack alignment bonus
    if tech_stack and profile:
        tech_score = _calculate_tech_stack_score(tech_stack, profile)
        score += tech_score
        logger.debug(f"Tech stack alignment: +{tech_score} points")
    elif company_data.get("techStack") and profile:
        tech_score = _calculate_tech_stack_score(company_data["techStack"], profile)
        score += tech_score
        logger.debug(f"Tech stack alignment: +{tech_score} points")

    # Company size preference (if available)
    # This would use existing company_size_utils.calculate_company_size_adjustment
    # but we'll keep it simple for now since that's already handled elsewhere

    # Determine tier
    if score >= 150:
        tier = "S"
    elif score >= 100:
        tier = "A"
    elif score >= 70:
        tier = "B"
    elif score >= 50:
        tier = "C"
    else:
        tier = "D"

    return score, tier


def _calculate_tech_stack_score(tech_stack: List[str], profile: Profile) -> int:
    """
    Calculate score based on tech stack alignment with user profile.

    Scoring logic:
    - Expert level match: +15 points per skill
    - Advanced level match: +10 points per skill
    - Intermediate level match: +5 points per skill
    - Beginner level match: +2 points per skill
    - Experience but no level: +7 points per skill
    - Max total: 100 points

    Args:
        tech_stack: Company's technology stack
        profile: User profile

    Returns:
        Tech stack alignment score (0-100)
    """
    if not tech_stack or not profile:
        return 0

    # Get user's skills with proficiency levels
    user_skills = {skill.name.lower(): skill.level for skill in profile.skills}

    # Also check technologies from experience
    user_tech_from_exp = set()
    for exp in profile.experience:
        user_tech_from_exp.update([tech.lower() for tech in exp.technologies])

    score = 0
    matches = 0

    for tech in tech_stack:
        tech_lower = tech.lower()

        # Check if user has this skill with a level
        if tech_lower in user_skills:
            level = user_skills[tech_lower]
            if level:
                level_lower = level.lower()
                if "expert" in level_lower:
                    score += 15
                    matches += 1
                elif "advanced" in level_lower:
                    score += 10
                    matches += 1
                elif "intermediate" in level_lower:
                    score += 5
                    matches += 1
                elif "beginner" in level_lower:
                    score += 2
                    matches += 1
            else:
                # Has skill but no level specified
                score += 7
                matches += 1
        # Check if tech appears in experience
        elif tech_lower in user_tech_from_exp:
            score += 7
            matches += 1

    # Cap at 100
    score = min(score, 100)

    if matches > 0:
        logger.debug(f"  Matched {matches} technologies from stack of {len(tech_stack)}")

    return score


def compute_company_priority_fields(
    company_data: Dict,
    profile: Optional[Profile] = None,
) -> Dict:
    """
    Compute and add priority fields to company data.

    This function calculates priorityScore and tier fields and adds them
    to the company data dictionary.

    Args:
        company_data: Company information dictionary
        profile: Optional user profile for tech stack matching

    Returns:
        Updated company data dictionary with priorityScore and tier fields
    """
    has_portland_office = company_data.get("hasPortlandOffice", False)
    tech_stack = company_data.get("techStack", [])

    score, tier = calculate_company_priority(
        company_data=company_data,
        profile=profile,
        has_portland_office=has_portland_office,
        tech_stack=tech_stack,
    )

    company_data["priorityScore"] = score
    company_data["tier"] = tier

    return company_data


def get_tier_display_name(tier: str) -> str:
    """
    Get human-readable name for tier.

    Args:
        tier: Tier letter (S, A, B, C, D)

    Returns:
        Display name for the tier
    """
    tier_names = {
        "S": "Perfect Match",
        "A": "Excellent Match",
        "B": "Good Match",
        "C": "Moderate Match",
        "D": "Basic Match",
    }
    return tier_names.get(tier, "Unknown")
