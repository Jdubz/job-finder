"""
Strike-based job filter engine.

Two-tier filtering system:
1. Hard Rejections - Immediate fail (sales jobs, too junior, etc.)
2. Strike System - Accumulate points, fail if >= threshold
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from job_finder.constants import DEFAULT_STRIKE_THRESHOLD
from job_finder.filters.models import FilterResult
from job_finder.utils.date_utils import parse_job_date

logger = logging.getLogger(__name__)


class StrikeFilterEngine:
    """
    Strike-based filter engine with two-tier system.

    Tier 1: Hard rejections (immediate fail)
    Tier 2: Strike accumulation (fail if >= threshold)
    """

    def __init__(self, config: dict, tech_ranks: dict):
        """
        Initialize strike-based filter engine.

        Args:
            config: Main filter configuration (job-finder-config/job-filters)
            tech_ranks: Technology ranking config (job-finder-config/technology-ranks)
        """
        self.config = config
        self.tech_ranks = tech_ranks
        self.enabled = config.get("enabled", True)
        self.strike_threshold = config.get("strikeThreshold", DEFAULT_STRIKE_THRESHOLD)

        # Hard Rejections
        hard_rej = config.get("hardRejections", {})
        self.excluded_job_types = [t.lower() for t in hard_rej.get("excludedJobTypes", [])]
        self.excluded_seniority = [s.lower() for s in hard_rej.get("excludedSeniority", [])]
        self.excluded_companies = [c.lower() for c in hard_rej.get("excludedCompanies", [])]
        self.excluded_keywords = [k.lower() for k in hard_rej.get("excludedKeywords", [])]
        self.min_salary_floor = hard_rej.get("minSalaryFloor", 100000)
        self.reject_commission_only = hard_rej.get("rejectCommissionOnly", True)

        # Remote Policy
        remote = config.get("remotePolicy", {})
        self.allow_remote = remote.get("allowRemote", True)
        self.allow_hybrid_portland = remote.get("allowHybridPortland", True)
        self.allow_onsite = remote.get("allowOnsite", False)

        # Strike: Salary
        salary_strike = config.get("salaryStrike", {})
        self.salary_strike_enabled = salary_strike.get("enabled", True)
        self.salary_strike_threshold = salary_strike.get("threshold", 150000)
        self.salary_strike_points = salary_strike.get("points", 2)

        # Strike: Experience
        exp_strike = config.get("experienceStrike", {})
        self.experience_strike_enabled = exp_strike.get("enabled", True)
        self.min_experience_preferred = exp_strike.get("minPreferred", 6)
        self.experience_strike_points = exp_strike.get("points", 1)

        # Strike: Seniority
        self.seniority_strikes = config.get("seniorityStrikes", {})

        # Strike: Quality
        quality = config.get("qualityStrikes", {})
        self.min_description_length = quality.get("minDescriptionLength", 200)
        self.short_description_points = quality.get("shortDescriptionPoints", 1)
        self.buzzwords = [b.lower() for b in quality.get("buzzwords", [])]
        self.buzzword_points = quality.get("buzzwordPoints", 1)

        # Strike: Age
        age_strike = config.get("ageStrike", {})
        self.age_strike_enabled = age_strike.get("enabled", True)
        self.age_strike_days = age_strike.get("strikeDays", 1)  # > 1 day = strike
        self.age_reject_days = age_strike.get("rejectDays", 7)  # > 7 days = reject
        self.age_strike_points = age_strike.get("points", 1)

        # Technology ranks
        self.technologies = tech_ranks.get("technologies", {})
        self.missing_required_tech_points = tech_ranks.get("strikes", {}).get(
            "missingAllRequired", 1
        )

    def evaluate_job(self, job_data: dict) -> FilterResult:
        """
        Evaluate job with strike-based system.

        Args:
            job_data: Job data with title, description, salary, posted_date, etc.

        Returns:
            FilterResult with strikes and hard rejections
        """
        if not self.enabled:
            return FilterResult(passed=True, strike_threshold=self.strike_threshold)

        result = FilterResult(passed=True, strike_threshold=self.strike_threshold)

        # Extract fields
        title = job_data.get("title", "")
        company = job_data.get("company", "")
        description = job_data.get("description", "")
        location = job_data.get("location", "")
        salary = job_data.get("salary", "")
        posted_date_str = job_data.get("posted_date", "")

        # === PHASE 1: Hard Rejections (immediate fail) ===

        # Check job type
        if self._is_excluded_job_type(title, description, result):
            return result

        # Check seniority
        if self._is_excluded_seniority(title, result):
            return result

        # Check company
        if self._is_excluded_company(company, result):
            return result

        # Check keywords
        if self._has_excluded_keywords(description, result):
            return result

        # Check salary floor
        if self._below_salary_floor(salary, result):
            return result

        # Check commission only
        if self._is_commission_only(description, result):
            return result

        # Check remote policy
        if self._violates_remote_policy(description, location, result):
            return result

        # Check age (hard reject if too old)
        if self._is_too_old(posted_date_str, result):
            return result

        # === PHASE 2: Strike Accumulation ===

        # Salary strike (< $150k)
        if self.salary_strike_enabled:
            self._check_salary_strike(salary, result)

        # Experience strike (< 6 years preferred)
        if self.experience_strike_enabled:
            self._check_experience_strike(description, result)

        # Seniority strikes (mid-level, principal, director)
        self._check_seniority_strikes(title, result)

        # Technology strikes
        self._check_technology_strikes(title, description, result)

        # Quality strikes
        self._check_quality_strikes(description, result)

        # Age strike (> 1 day old)
        if self.age_strike_enabled:
            self._check_age_strike(posted_date_str, result)

        # Log result
        if result.passed:
            logger.info(
                f"Job PASSED filters: {title} ({result.total_strikes}/{self.strike_threshold} strikes)"
            )
        else:
            hard_rejects = [r for r in result.rejections if r.severity == "hard_reject"]
            if hard_rejects:
                logger.info(f"Job HARD REJECTED: {title} - {hard_rejects[0].reason}")
            else:
                logger.info(
                    f"Job STRIKE FILTERED: {title} - {result.total_strikes}/{self.strike_threshold} strikes"
                )

        return result

    # === Hard Rejection Checks ===

    def _is_excluded_job_type(self, title: str, description: str, result: FilterResult) -> bool:
        """Check if job is excluded type (sales, HR, etc.)."""
        title_lower = title.lower()
        description_lower = description.lower()

        for job_type in self.excluded_job_types:
            # Use word boundary regex to match whole words only
            pattern = r"\b" + re.escape(job_type) + r"\b"

            # Check title first (strong signal of job type)
            if re.search(pattern, title_lower):
                result.add_rejection(
                    filter_category="hard_reject",
                    filter_name="excluded_job_type",
                    reason=f"Excluded job type: {job_type}",
                    detail=f"Title contains '{job_type}'",
                    severity="hard_reject",
                    points=0,
                )
                return True

            # For very short job types (2-3 chars), ONLY match in title to avoid false positives
            # Examples: "hr" matches in "hr@company.com" or "finance, hr, legal" lists
            if len(job_type) <= 3:
                continue  # Skip description check for short keywords

            # For longer job types, use stricter context matching to avoid false positives
            # Look for job type near role-indicating keywords
            role_indicators = [
                r"(^|\s)(looking for|seeking|hiring|role|position|job)",  # Job context
                r"(responsibilities|duties|will be|you will)",  # Responsibilities
                r"(team|department|division)",  # Organizational
            ]

            # Check if job_type appears near role indicators (within ~50 chars)
            for indicator_pattern in role_indicators:
                # Build combined pattern: indicator followed by job_type within 50 chars
                combined_pattern = (
                    indicator_pattern + r".{0,50}?" + r"\b" + re.escape(job_type) + r"\b"
                )
                if re.search(combined_pattern, description_lower, re.IGNORECASE):
                    result.add_rejection(
                        filter_category="hard_reject",
                        filter_name="excluded_job_type",
                        reason=f"Excluded job type: {job_type}",
                        detail=f"Job appears to be a {job_type} role based on description context",
                        severity="hard_reject",
                        points=0,
                    )
                    return True

                # Also check reverse: job_type followed by indicator
                reverse_pattern = (
                    r"\b" + re.escape(job_type) + r"\b" + r".{0,50}?" + indicator_pattern
                )
                if re.search(reverse_pattern, description_lower, re.IGNORECASE):
                    result.add_rejection(
                        filter_category="hard_reject",
                        filter_name="excluded_job_type",
                        reason=f"Excluded job type: {job_type}",
                        detail=f"Job appears to be a {job_type} role based on description context",
                        severity="hard_reject",
                        points=0,
                    )
                    return True

        return False

    def _is_excluded_seniority(self, title: str, result: FilterResult) -> bool:
        """Check if seniority is too junior."""
        title_lower = title.lower()

        for seniority in self.excluded_seniority:
            # Use word boundary regex to match whole words only
            pattern = r"\b" + re.escape(seniority) + r"\b"
            if re.search(pattern, title_lower):
                result.add_rejection(
                    filter_category="hard_reject",
                    filter_name="excluded_seniority",
                    reason=f"Too junior: {seniority}",
                    detail=f"Title contains '{seniority}' which is below required level",
                    severity="hard_reject",
                    points=0,
                )
                return True
        return False

    def _is_excluded_company(self, company: str, result: FilterResult) -> bool:
        """Check if company is in exclusion list."""
        company_lower = company.lower()

        for excluded in self.excluded_companies:
            if excluded in company_lower:
                result.add_rejection(
                    filter_category="hard_reject",
                    filter_name="excluded_company",
                    reason=f"Excluded company: {excluded}",
                    detail=f"Company '{company}' is in exclusion list",
                    severity="hard_reject",
                    points=0,
                )
                return True
        return False

    def _has_excluded_keywords(self, description: str, result: FilterResult) -> bool:
        """Check for deal-breaker keywords."""
        description_lower = description.lower()

        for keyword in self.excluded_keywords:
            # For multi-word phrases, use phrase matching
            # For single words, use word boundary matching
            if " " in keyword:
                # Multi-word phrase - simple substring match is appropriate
                if keyword in description_lower:
                    result.add_rejection(
                        filter_category="hard_reject",
                        filter_name="excluded_keyword",
                        reason=f"Deal-breaker keyword: {keyword}",
                        detail=f"Description contains '{keyword}'",
                        severity="hard_reject",
                        points=0,
                    )
                    return True
            else:
                # Single word - use word boundary to avoid false positives
                pattern = r"\b" + re.escape(keyword) + r"\b"
                if re.search(pattern, description_lower):
                    result.add_rejection(
                        filter_category="hard_reject",
                        filter_name="excluded_keyword",
                        reason=f"Deal-breaker keyword: {keyword}",
                        detail=f"Description contains '{keyword}'",
                        severity="hard_reject",
                        points=0,
                    )
                    return True
        return False

    def _below_salary_floor(self, salary: str, result: FilterResult) -> bool:
        """Check if salary is below hard floor ($100k)."""
        if not salary:
            return False  # No salary info = allow

        max_salary = self._parse_salary(salary)
        if max_salary and max_salary < self.min_salary_floor:
            result.add_rejection(
                filter_category="hard_reject",
                filter_name="salary_floor",
                reason=f"Salary below ${self.min_salary_floor // 1000}k floor",
                detail=f"Max salary ${max_salary:,} is below minimum ${self.min_salary_floor:,}",
                severity="hard_reject",
                points=0,
            )
            return True
        return False

    def _is_commission_only(self, description: str, result: FilterResult) -> bool:
        """Check for commission-only/MLM indicators."""
        if not self.reject_commission_only:
            return False

        description_lower = description.lower()
        indicators = [
            "commission only",
            "commission-only",
            "unlimited earning potential",
            "mlm",
            "multi-level marketing",
            "be your own boss",
        ]

        for indicator in indicators:
            if indicator in description_lower:
                result.add_rejection(
                    filter_category="hard_reject",
                    filter_name="commission_only",
                    reason="Commission-only or MLM position",
                    detail=f"Description contains '{indicator}'",
                    severity="hard_reject",
                    points=0,
                )
                return True
        return False

    def _violates_remote_policy(
        self, description: str, location: str, result: FilterResult
    ) -> bool:
        """Check if job violates remote work policy."""
        description_lower = description.lower()
        location_lower = location.lower()
        combined = f"{description_lower} {location_lower}"

        # Detect work arrangement
        is_remote = any(
            ind in combined
            for ind in [
                "fully remote",
                "100% remote",
                "remote position",
                "work from home",
                "wfh",
                "remote-first",
            ]
        )

        is_hybrid = any(
            ind in combined for ind in ["hybrid", "flexible work", "days in office", "days remote"]
        )

        is_portland = "portland" in combined and ("or" in combined or "oregon" in combined)

        is_onsite = any(
            ind in combined for ind in ["on-site", "onsite", "in-office", "office-based"]
        )

        # If we can't detect work arrangement, pass it through (don't reject on missing data)
        if not is_remote and not is_hybrid and not is_onsite:
            return False  # Unclear = allow (let AI analysis handle it)

        # Apply policy to detected arrangements
        if is_remote and self.allow_remote:
            return False  # Remote OK

        if is_hybrid and is_portland and self.allow_hybrid_portland:
            return False  # Hybrid Portland OK

        if is_onsite and self.allow_onsite:
            return False  # Onsite OK (if allowed)

        # Only reject if we detected an arrangement that violates policy
        if is_remote:
            policy_reason = "Remote jobs not allowed"
        elif is_hybrid and is_portland:
            policy_reason = "Hybrid Portland jobs not allowed"
        elif is_hybrid:
            policy_reason = "Hybrid jobs outside Portland not allowed"
        else:  # is_onsite
            policy_reason = "On-site jobs not allowed"

        result.add_rejection(
            filter_category="hard_reject",
            filter_name="remote_policy",
            reason=policy_reason,
            detail=f"Remote: {is_remote}, Hybrid: {is_hybrid}, Portland: {is_portland}, Onsite: {is_onsite}",
            severity="hard_reject",
            points=0,
        )
        return True

    def _is_too_old(self, posted_date_str: str, result: FilterResult) -> bool:
        """Check if job is older than hard reject threshold (7 days)."""
        if not posted_date_str:
            return False  # No date = allow

        posted_date = parse_job_date(posted_date_str)
        if not posted_date:
            return False  # Can't parse = allow

        # Ensure timezone-aware
        if posted_date.tzinfo is None:
            posted_date = posted_date.replace(tzinfo=timezone.utc)

        age_days = (datetime.now(timezone.utc) - posted_date).days

        if age_days > self.age_reject_days:
            result.add_rejection(
                filter_category="hard_reject",
                filter_name="job_age",
                reason=f"Job too old (>{self.age_reject_days} days)",
                detail=f"Job posted {age_days} days ago",
                severity="hard_reject",
                points=0,
            )
            return True
        return False

    # === Strike Checks ===

    def _check_salary_strike(self, salary: str, result: FilterResult) -> None:
        """Add strike if salary < $150k."""
        if not salary:
            return  # No salary = no strike

        max_salary = self._parse_salary(salary)
        if max_salary and max_salary < self.salary_strike_threshold:
            result.add_strike(
                filter_category="salary",
                filter_name="low_salary",
                reason=f"Salary below ${self.salary_strike_threshold // 1000}k",
                detail=f"Max salary ${max_salary:,} is below preferred ${self.salary_strike_threshold:,}",
                points=self.salary_strike_points,
            )

    def _check_experience_strike(self, description: str, result: FilterResult) -> None:
        """Add strike if < 6 years experience required."""
        # Parse experience patterns
        patterns = [
            r"(\d+)\+?\s*years?",
            r"(\d+)\s*-\s*(\d+)\s*years?",
            r"minimum\s+(\d+)\s*years?",
            r"at least\s+(\d+)\s*years?",
        ]

        years_required = []
        for pattern in patterns:
            matches = re.finditer(pattern, description.lower())
            for match in matches:
                nums = [int(g) for g in match.groups() if g]
                if nums:
                    years_required.append(max(nums))

        if not years_required:
            return  # No experience mentioned = no strike

        max_required = max(years_required)
        if max_required < self.min_experience_preferred:
            result.add_strike(
                filter_category="experience",
                filter_name="low_experience",
                reason=f"Requires <{self.min_experience_preferred} years",
                detail=f"Job requires {max_required} years, prefer {self.min_experience_preferred}+",
                points=self.experience_strike_points,
            )

    def _check_seniority_strikes(self, title: str, result: FilterResult) -> None:
        """Add strikes for non-ideal seniority levels."""
        title_lower = title.lower()

        for seniority_pattern, points in self.seniority_strikes.items():
            if seniority_pattern.lower() in title_lower:
                result.add_strike(
                    filter_category="seniority",
                    filter_name=f"seniority_{seniority_pattern.replace(' ', '_')}",
                    reason=f"Seniority: {seniority_pattern}",
                    detail=f"Title contains '{seniority_pattern}' which is not ideal",
                    points=points,
                )
                return  # Only count first match

    def _check_technology_strikes(self, title: str, description: str, result: FilterResult) -> None:
        """Check technology stack and add strikes."""
        combined = f"{title} {description}".lower()

        # Track tech found
        required_found = []
        strikes_found = []
        fails_found = []

        for tech_name, tech_data in self.technologies.items():
            rank = tech_data.get("rank", "ok")
            points = tech_data.get("points", 0)

            # Word boundary search to avoid Java/JavaScript confusion
            pattern = r"\b" + re.escape(tech_name.lower()) + r"\b"
            if re.search(pattern, combined):
                if rank == "required":
                    required_found.append(tech_name)
                elif rank == "strike":
                    strikes_found.append((tech_name, points))
                elif rank == "fail":
                    fails_found.append(tech_name)

        # Check for "fail" technologies (immediate rejection, but shouldn't happen with current config)
        for tech in fails_found:
            result.add_rejection(
                filter_category="hard_reject",
                filter_name="failed_tech",
                reason=f"Forbidden technology: {tech}",
                detail=f"Job requires {tech} which is not acceptable",
                severity="hard_reject",
                points=0,
            )

        # Add strikes for bad tech
        for tech_name, points in strikes_found:
            result.add_strike(
                filter_category="tech_stack",
                filter_name="bad_tech",
                reason=f"Undesired tech: {tech_name}",
                detail=f"Job requires {tech_name}",
                points=points,
            )

        # Add strike if NO required tech found
        if not required_found and self.missing_required_tech_points > 0:
            required_list = [
                name for name, data in self.technologies.items() if data.get("rank") == "required"
            ]
            result.add_strike(
                filter_category="tech_stack",
                filter_name="missing_required_tech",
                reason="Missing all required technologies",
                detail=f"None of required tech found: {', '.join(required_list[:5])}...",
                points=self.missing_required_tech_points,
            )

    def _check_quality_strikes(self, description: str, result: FilterResult) -> None:
        """Check description quality and add strikes."""
        # Short description (only if we have a description)
        if description and len(description) < self.min_description_length:
            result.add_strike(
                filter_category="quality",
                filter_name="short_description",
                reason="Description too short",
                detail=f"Description is {len(description)} chars, prefer {self.min_description_length}+",
                points=self.short_description_points,
            )

        # Buzzwords
        description_lower = description.lower()
        for buzzword in self.buzzwords:
            if buzzword in description_lower:
                result.add_strike(
                    filter_category="quality",
                    filter_name="buzzword",
                    reason=f"Contains buzzword: {buzzword}",
                    detail=f"Description contains '{buzzword}'",
                    points=self.buzzword_points,
                )
                return  # Only count first buzzword

    def _check_age_strike(self, posted_date_str: str, result: FilterResult) -> None:
        """Add strike if job is > 1 day old."""
        if not posted_date_str:
            return

        posted_date = parse_job_date(posted_date_str)
        if not posted_date:
            return

        # Ensure timezone-aware
        if posted_date.tzinfo is None:
            posted_date = posted_date.replace(tzinfo=timezone.utc)

        age_days = (datetime.now(timezone.utc) - posted_date).days

        if age_days > self.age_strike_days:
            result.add_strike(
                filter_category="age",
                filter_name="job_age",
                reason=f"Job >{self.age_strike_days} day(s) old",
                detail=f"Job posted {age_days} days ago",
                points=self.age_strike_points,
            )

    # === Helpers ===

    def _parse_salary(self, salary: str) -> Optional[int]:
        """Parse salary string and return max value."""
        if not salary:
            return None

        # Remove common formatting
        salary_clean = salary.replace("$", "").replace(",", "").lower()

        # Find all numbers
        pattern = r"(\d+\.?\d*)\s*k?"
        matches = re.findall(pattern, salary_clean)

        if not matches:
            return None

        # Convert to actual numbers
        salaries = []
        for match in matches:
            num = float(match)
            # If it's in thousands notation (k), multiply by 1000
            if "k" in salary_clean:
                num *= 1000
            salaries.append(int(num))

        return max(salaries) if salaries else None
