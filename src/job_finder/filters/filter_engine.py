"""
Job filter engine for pre-AI filtering.

Evaluates jobs against configured filters before AI analysis to reduce costs
and improve match quality by only analyzing jobs that meet basic requirements.
"""

import logging
import re
from typing import List, Optional

from job_finder.filters.models import FilterResult, FilterRejection

logger = logging.getLogger(__name__)


class JobFilterEngine:
    """
    Filter engine that evaluates jobs against configured criteria.

    Applies multiple filter stages:
    1. Exclusion filters (companies, domains, keywords)
    2. Requirement filters (remote, location, experience, tech stack)
    3. Quality filters (description length, spam detection)

    Returns FilterResult with detailed rejection reasons for transparency.
    """

    def __init__(self, config: dict):
        """
        Initialize filter engine with configuration.

        Args:
            config: Filter configuration from Firestore (job-finder-config/job-filters)
        """
        self.config = config
        self.enabled = config.get("enabled", True)

        # Exclusions
        self.excluded_companies = [c.lower() for c in config.get("excludedCompanies", [])]
        self.excluded_domains = [d.lower() for d in config.get("excludedDomains", [])]
        self.excluded_keywords_url = [
            k.lower() for k in config.get("excludedKeywordsUrl", [])
        ]
        self.excluded_keywords_title = [
            k.lower() for k in config.get("excludedKeywordsTitle", [])
        ]
        self.excluded_keywords_description = [
            k.lower() for k in config.get("excludedKeywordsDescription", [])
        ]

        # Location & Remote
        self.remote_policy = config.get("remotePolicy", "remote_only")
        self.allowed_locations = config.get("allowedLocations", [])

        # Job Type
        self.employment_type = config.get("employmentType", "full_time")

        # Experience
        self.min_years_experience = config.get("minYearsExperience")
        self.max_years_experience = config.get("maxYearsExperience")
        self.allowed_seniority = [
            s.lower() for s in config.get("allowedSeniority", [])
        ]

        # Salary
        self.min_salary = config.get("minSalary")

        # Tech Stack
        self.required_tech = [t.lower() for t in config.get("requiredTech", [])]
        self.excluded_tech = [t.lower() for t in config.get("excludedTech", [])]

        # Quality
        self.min_description_length = config.get("minDescriptionLength", 200)
        self.reject_commission_only = config.get("rejectCommissionOnly", True)

    def evaluate_job(self, job_data: dict) -> FilterResult:
        """
        Evaluate job against all filters.

        Args:
            job_data: Job data from scraper with keys:
                - title: Job title
                - company: Company name
                - url: Job posting URL
                - description: Job description
                - location: Job location (optional)
                - salary: Salary info (optional)

        Returns:
            FilterResult with pass/fail and detailed rejection reasons
        """
        if not self.enabled:
            return FilterResult(passed=True)

        result = FilterResult(passed=True)

        # Extract job fields
        title = job_data.get("title", "")
        company = job_data.get("company", "")
        url = job_data.get("url", "")
        description = job_data.get("description", "")
        location = job_data.get("location", "")
        salary = job_data.get("salary", "")

        # Run all filter stages
        self._check_excluded_companies(company, result)
        self._check_excluded_domains(url, result)
        self._check_excluded_keywords_url(url, result)
        self._check_excluded_keywords_title(title, result)
        self._check_excluded_keywords_description(description, result)
        self._check_remote_policy(description, location, result)
        self._check_tech_stack(title, description, result)
        self._check_experience_level(title, description, result)
        self._check_seniority_level(title, result)
        self._check_salary(salary, result)
        self._check_employment_type(title, description, result)
        self._check_description_quality(description, result)
        self._check_commission_only(description, result)

        # Log result
        if result.passed:
            logger.debug(f"Job passed all filters: {title} at {company}")
        else:
            logger.info(
                f"Job filtered: {title} at {company} - {result.get_rejection_summary()}"
            )

        return result

    def _check_excluded_companies(self, company: str, result: FilterResult) -> None:
        """Check if company is in exclusion list."""
        company_lower = company.lower()
        for excluded in self.excluded_companies:
            if excluded in company_lower:
                result.add_rejection(
                    filter_category="exclusions",
                    filter_name="excluded_company",
                    reason="Excluded company",
                    detail=f"Company '{company}' matches excluded pattern '{excluded}'",
                )
                return

    def _check_excluded_domains(self, url: str, result: FilterResult) -> None:
        """Check if URL domain is in exclusion list."""
        url_lower = url.lower()
        for excluded in self.excluded_domains:
            if excluded in url_lower:
                result.add_rejection(
                    filter_category="exclusions",
                    filter_name="excluded_domain",
                    reason="Excluded domain",
                    detail=f"URL contains excluded domain '{excluded}'",
                )
                return

    def _check_excluded_keywords_url(self, url: str, result: FilterResult) -> None:
        """Check if URL contains excluded keywords."""
        url_lower = url.lower()
        for keyword in self.excluded_keywords_url:
            if keyword in url_lower:
                result.add_rejection(
                    filter_category="exclusions",
                    filter_name="excluded_keyword_url",
                    reason="URL contains excluded keyword",
                    detail=f"URL contains '{keyword}'",
                )
                return

    def _check_excluded_keywords_title(self, title: str, result: FilterResult) -> None:
        """Check if title contains excluded keywords."""
        title_lower = title.lower()
        for keyword in self.excluded_keywords_title:
            if keyword in title_lower:
                result.add_rejection(
                    filter_category="exclusions",
                    filter_name="excluded_keyword_title",
                    reason="Title contains excluded keyword",
                    detail=f"Title contains '{keyword}'",
                )
                return

    def _check_excluded_keywords_description(
        self, description: str, result: FilterResult
    ) -> None:
        """Check if description contains excluded keywords."""
        description_lower = description.lower()
        for keyword in self.excluded_keywords_description:
            if keyword in description_lower:
                result.add_rejection(
                    filter_category="exclusions",
                    filter_name="excluded_keyword_description",
                    reason="Description contains excluded keyword",
                    detail=f"Description contains '{keyword}'",
                )
                return

    def _check_remote_policy(
        self, description: str, location: str, result: FilterResult
    ) -> None:
        """
        Check if job matches remote work policy.

        Policies:
        - remote_only: Only fully remote jobs
        - hybrid_ok: Remote or hybrid
        - on_site_ok: Any (remote, hybrid, on-site)
        - any: No filtering
        """
        if self.remote_policy == "any":
            return

        description_lower = description.lower()
        location_lower = location.lower()
        combined_text = f"{description_lower} {location_lower}"

        # Detect remote indicators
        remote_indicators = [
            "fully remote",
            "100% remote",
            "remote position",
            "work from home",
            "wfh",
            "remote-first",
        ]
        is_remote = any(indicator in combined_text for indicator in remote_indicators)

        # Detect hybrid indicators
        hybrid_indicators = [
            "hybrid",
            "flexible work",
            "remote with occasional",
            "days in office",
        ]
        is_hybrid = any(indicator in combined_text for indicator in hybrid_indicators)

        # Detect on-site indicators
        onsite_indicators = [
            "on-site",
            "onsite",
            "in-office",
            "in office",
            "office-based",
        ]
        is_onsite = any(indicator in combined_text for indicator in onsite_indicators)

        # Apply policy
        if self.remote_policy == "remote_only":
            if not is_remote or is_hybrid or is_onsite:
                result.add_rejection(
                    filter_category="location",
                    filter_name="remote_policy",
                    reason="Not a fully remote position",
                    detail="Job requires on-site or hybrid work",
                )

        elif self.remote_policy == "hybrid_ok":
            if not (is_remote or is_hybrid):
                result.add_rejection(
                    filter_category="location",
                    filter_name="remote_policy",
                    reason="Requires on-site work",
                    detail="Job does not offer remote or hybrid options",
                )

    def _check_tech_stack(
        self, title: str, description: str, result: FilterResult
    ) -> None:
        """
        Check required and excluded technologies.

        Required: At least one must be present
        Excluded: None can be present
        """
        title_lower = title.lower()
        description_lower = description.lower()
        combined_text = f"{title_lower} {description_lower}"

        # Check excluded tech first (hard block)
        for tech in self.excluded_tech:
            # Use word boundaries to avoid false matches (e.g., "Java" in "JavaScript")
            pattern = r"\b" + re.escape(tech) + r"\b"
            if re.search(pattern, combined_text, re.IGNORECASE):
                result.add_rejection(
                    filter_category="tech_stack",
                    filter_name="excluded_tech",
                    reason="Contains excluded technology",
                    detail=f"Job requires '{tech}' which is in exclusion list",
                )
                return

        # Check required tech (at least one must be present)
        if self.required_tech:
            found_tech = []
            for tech in self.required_tech:
                pattern = r"\b" + re.escape(tech) + r"\b"
                if re.search(pattern, combined_text, re.IGNORECASE):
                    found_tech.append(tech)

            if not found_tech:
                result.add_rejection(
                    filter_category="tech_stack",
                    filter_name="required_tech",
                    reason="Missing required technologies",
                    detail=f"None of required tech found: {', '.join(self.required_tech)}",
                )

    def _check_experience_level(
        self, title: str, description: str, result: FilterResult
    ) -> None:
        """
        Check years of experience requirements.

        Parses patterns like:
        - "5+ years"
        - "3-5 years experience"
        - "minimum 7 years"
        """
        if self.min_years_experience is None and self.max_years_experience is None:
            return

        description_lower = description.lower()

        # Regex patterns for experience
        patterns = [
            r"(\d+)\+?\s*years?",  # "5+ years" or "5 years"
            r"(\d+)\s*-\s*(\d+)\s*years?",  # "3-5 years"
            r"minimum\s+(\d+)\s*years?",  # "minimum 5 years"
            r"at least\s+(\d+)\s*years?",  # "at least 5 years"
        ]

        years_required = []
        for pattern in patterns:
            matches = re.finditer(pattern, description_lower)
            for match in matches:
                # Get the highest number from the match (for ranges)
                nums = [int(g) for g in match.groups() if g]
                if nums:
                    years_required.append(max(nums))

        if not years_required:
            # No experience mentioned, allow it
            return

        max_required = max(years_required)

        # Check against min/max bounds
        if self.min_years_experience and max_required < self.min_years_experience:
            result.add_rejection(
                filter_category="experience",
                filter_name="years_experience",
                reason="Requires too little experience",
                detail=f"Job requires {max_required} years, your minimum is {self.min_years_experience}",
            )

        if self.max_years_experience and max_required > self.max_years_experience:
            result.add_rejection(
                filter_category="experience",
                filter_name="years_experience",
                reason="Requires too much experience",
                detail=f"Job requires {max_required}+ years, your maximum is {self.max_years_experience}",
            )

    def _check_seniority_level(self, title: str, result: FilterResult) -> None:
        """
        Check if job seniority level matches allowed levels.

        Detects: junior, mid/mid-level, senior, staff, principal, lead
        """
        if not self.allowed_seniority:
            return

        title_lower = title.lower()

        # Seniority patterns
        seniority_map = {
            "junior": ["junior", "jr.", "entry level", "entry-level"],
            "mid": ["mid-level", "mid level", "intermediate"],
            "senior": ["senior", "sr.", "sr "],
            "staff": ["staff"],
            "principal": ["principal"],
            "lead": ["lead", "team lead"],
        }

        detected_level = None
        for level, patterns in seniority_map.items():
            for pattern in patterns:
                if pattern in title_lower:
                    detected_level = level
                    break
            if detected_level:
                break

        # If no level detected, assume mid-level (most common)
        if not detected_level:
            detected_level = "mid"

        # Check if detected level is allowed
        if detected_level not in self.allowed_seniority:
            result.add_rejection(
                filter_category="experience",
                filter_name="seniority_level",
                reason="Seniority level mismatch",
                detail=f"Job is '{detected_level}' level, allowed: {', '.join(self.allowed_seniority)}",
            )

    def _check_salary(self, salary: str, result: FilterResult) -> None:
        """
        Check if salary meets minimum requirement.

        Parses patterns like:
        - "$120k-$150k"
        - "$100,000+"
        - "100-120K"

        If salary not listed, skip (don't reject).
        """
        if self.min_salary is None or not salary:
            return

        # Extract numbers from salary string
        # Remove common formatting: $, k, K, commas
        salary_clean = salary.replace("$", "").replace(",", "").lower()

        # Find all numbers, including k notation
        pattern = r"(\d+\.?\d*)\s*k?"
        matches = re.findall(pattern, salary_clean)

        if not matches:
            # No salary info found, don't reject
            return

        # Convert to actual numbers
        salaries = []
        for match in matches:
            num = float(match)
            # If it's in thousands notation (k), multiply by 1000
            if "k" in salary_clean:
                num *= 1000
            salaries.append(int(num))

        if not salaries:
            return

        # Use the maximum salary in the range
        max_salary = max(salaries)

        if max_salary < self.min_salary:
            result.add_rejection(
                filter_category="requirements",
                filter_name="min_salary",
                reason="Salary below minimum",
                detail=f"Max salary ${max_salary:,} is below minimum ${self.min_salary:,}",
            )

    def _check_employment_type(
        self, title: str, description: str, result: FilterResult
    ) -> None:
        """
        Check if employment type matches requirements.

        Types: full_time, contract, part_time, any
        """
        if self.employment_type == "any":
            return

        combined_text = f"{title} {description}".lower()

        # Detect employment type
        contract_indicators = [
            "contract",
            "contractor",
            "c2c",
            "corp to corp",
            "1099",
            "freelance",
            "temporary",
        ]
        is_contract = any(indicator in combined_text for indicator in contract_indicators)

        part_time_indicators = ["part-time", "part time", "part time"]
        is_part_time = any(indicator in combined_text for indicator in part_time_indicators)

        # Apply filter
        if self.employment_type == "full_time":
            if is_contract:
                result.add_rejection(
                    filter_category="requirements",
                    filter_name="employment_type",
                    reason="Contract position",
                    detail="Job is a contract position, not full-time",
                )
            elif is_part_time:
                result.add_rejection(
                    filter_category="requirements",
                    filter_name="employment_type",
                    reason="Part-time position",
                    detail="Job is part-time, not full-time",
                )

        elif self.employment_type == "contract":
            if not is_contract:
                result.add_rejection(
                    filter_category="requirements",
                    filter_name="employment_type",
                    reason="Not a contract position",
                    detail="Job is full-time, not contract",
                )

        elif self.employment_type == "part_time":
            if not is_part_time:
                result.add_rejection(
                    filter_category="requirements",
                    filter_name="employment_type",
                    reason="Not a part-time position",
                    detail="Job is full-time, not part-time",
                )

    def _check_description_quality(self, description: str, result: FilterResult) -> None:
        """Check if job description meets minimum quality standards."""
        if len(description) < self.min_description_length:
            result.add_rejection(
                filter_category="quality",
                filter_name="min_description_length",
                reason="Job description too short",
                detail=f"Description is {len(description)} chars, minimum is {self.min_description_length}",
            )

    def _check_commission_only(self, description: str, result: FilterResult) -> None:
        """Check for commission-only or MLM-style jobs."""
        if not self.reject_commission_only:
            return

        description_lower = description.lower()

        commission_indicators = [
            "commission only",
            "commission-only",
            "performance-based pay",
            "earn up to",
            "unlimited earning potential",
            "be your own boss",
            "mlm",
            "multi-level marketing",
        ]

        for indicator in commission_indicators:
            if indicator in description_lower:
                result.add_rejection(
                    filter_category="quality",
                    filter_name="commission_only",
                    reason="Commission-only or MLM position",
                    detail=f"Description contains '{indicator}'",
                )
                return
