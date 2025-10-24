"""AI-powered job matching and intake data generation."""

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from job_finder.ai.prompts import JobMatchPrompts
from job_finder.ai.providers import AIProvider
from job_finder.constants import (
    MAX_INTAKE_DESCRIPTION_LENGTH,
    MAX_INTAKE_FIELD_LENGTH,
    MAX_INTAKE_TEXT_LENGTH,
    MAX_TEXT_OPTIMIZATION_LENGTH,
)
from job_finder.profile.schema import Profile
from job_finder.utils.company_size_utils import (
    calculate_company_size_adjustment,
    detect_company_size,
)
from job_finder.utils.date_utils import calculate_freshness_adjustment, parse_job_date
from job_finder.utils.role_preference_utils import calculate_role_preference_adjustment
from job_finder.utils.timezone_utils import (
    calculate_timezone_score_adjustment,
    detect_timezone_for_job,
)

logger = logging.getLogger(__name__)


class JobMatchResult(BaseModel):
    """Result of AI job matching analysis."""

    # Job Info
    job_title: str
    job_company: str
    job_url: str

    # Match Analysis
    match_score: int = Field(..., ge=0, le=100, description="Overall match score (0-100)")
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    experience_match: str = ""
    key_strengths: List[str] = Field(default_factory=list)
    potential_concerns: List[str] = Field(default_factory=list)
    application_priority: str = "Medium"  # High/Medium/Low

    # Customization Guidance
    customization_recommendations: Dict[str, Any] = Field(default_factory=dict)

    # Resume Intake Data (for resume generator)
    resume_intake_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump()


class AIJobMatcher:
    """AI-powered job matcher that analyzes jobs and generates resume intake data."""

    def __init__(
        self,
        provider: AIProvider,
        profile: Profile,
        min_match_score: int = 50,
        generate_intake: bool = True,
        portland_office_bonus: int = 15,
        user_timezone: float = -8,
        prefer_large_companies: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize AI job matcher.

        Args:
            provider: AI provider instance.
            profile: User profile for matching.
            min_match_score: Minimum score threshold for a job to be considered a match.
            generate_intake: Whether to generate resume intake data for matched jobs.
            portland_office_bonus: Bonus points to add for Portland, OR offices.
            user_timezone: User's timezone offset from UTC (default: -8).
            prefer_large_companies: Prefer large companies (default: True).
            config: Optional AI configuration dictionary (for model-specific settings).
        """
        self.provider = provider
        self.profile = profile
        self.min_match_score = min_match_score
        self.generate_intake = generate_intake
        self.portland_office_bonus = portland_office_bonus
        self.user_timezone = user_timezone
        self.prefer_large_companies = prefer_large_companies
        self.config = config or {}
        self.prompts = JobMatchPrompts()

    def analyze_job(
        self, job: Dict[str, Any], has_portland_office: bool = False
    ) -> Optional[JobMatchResult]:
        """
        Analyze a single job posting against the profile.

        Args:
            job: Job posting dictionary with keys: title, company, location, description, url.
            has_portland_office: Whether the company has a Portland, OR office.

        Returns:
            JobMatchResult if successful, None if analysis fails.
        """
        try:
            # Step 1: Analyze job match
            logger.info(f"Analyzing job: {job.get('title')} at {job.get('company')}")
            match_analysis = self._analyze_match(job)

            if not match_analysis:
                logger.warning(f"Failed to analyze job: {job.get('title')}")
                return None

            # Step 2: Apply score adjustments (Portland office bonus, freshness multiplier, etc.)
            match_score = self._calculate_adjusted_score(match_analysis, has_portland_office, job)

            # Step 3: Check if adjusted score meets minimum threshold
            if match_score < self.min_match_score:
                logger.info(
                    f"Job {job.get('title')} scored {match_score}, "
                    f"below threshold {self.min_match_score}"
                )
                return None

            # Step 4: Generate resume intake data if enabled
            intake_data = None
            if self.generate_intake:
                intake_data = self._generate_intake_data(job, match_analysis)

            # Step 5: Build and return result
            result = self._build_match_result(job, match_analysis, match_score, intake_data)

            logger.info(
                f"Successfully analyzed {job.get('title')} - "
                f"Score: {match_score}, Priority: {result.application_priority}"
            )
            return result

        except Exception as e:
            logger.error(f"Error analyzing job {job.get('title', 'unknown')}: {str(e)}")
            return None

    def _calculate_adjusted_score(
        self, match_analysis: Dict[str, Any], has_portland_office: bool, job: Dict[str, Any]
    ) -> int:
        """
        Calculate adjusted match score with bonuses and adjustments applied.

        Args:
            match_analysis: Raw match analysis from AI
            has_portland_office: Whether company has Portland, OR office
            job: Job dictionary with posted_date and other fields

        Returns:
            Adjusted match score (clamped to 0-100)
        """
        base_score = match_analysis.get("match_score", 0)
        match_score = base_score
        adjustments = []

        # Apply Portland office bonus
        if has_portland_office and self.portland_office_bonus > 0:
            match_score += self.portland_office_bonus
            adjustments.append(f"🏙️ Portland office: +{self.portland_office_bonus}")

        # Apply freshness adjustment
        posted_date_str = job.get("posted_date", "")
        if posted_date_str:
            posted_date = parse_job_date(posted_date_str)
            freshness_adj = calculate_freshness_adjustment(posted_date)
            match_score += freshness_adj
            if freshness_adj > 0:
                adjustments.append(f"🆕 Fresh job: +{freshness_adj}")
            elif freshness_adj < 0:
                adjustments.append(f"📅 Job age: {freshness_adj}")
        else:
            # No date info penalty
            freshness_adj = calculate_freshness_adjustment(None)
            match_score += freshness_adj
            adjustments.append(f"❓ No date info: {freshness_adj}")

        # Detect company size
        company_name = job.get("company", "")
        company_info = job.get("company_info", "")
        job_description = job.get("description", "")
        company_size = detect_company_size(company_name, company_info, job_description)

        # Apply timezone adjustment with smart detection
        job_location = job.get("location", "")
        headquarters_location = ""  # Would come from company data if available
        job_timezone = detect_timezone_for_job(
            job_location=job_location,
            job_description=job_description,
            company_size=company_size,
            headquarters_location=headquarters_location,
            company_name=company_name,
            company_info=company_info,
        )
        timezone_adj, timezone_desc = calculate_timezone_score_adjustment(
            job_timezone, self.user_timezone
        )
        if timezone_adj != 0:
            match_score += timezone_adj
            if timezone_adj > 0:
                adjustments.append(f"🌎 {timezone_desc}")
            else:
                adjustments.append(f"⏰ {timezone_desc}")

        # Apply company size adjustment
        size_adj, size_desc = calculate_company_size_adjustment(
            company_size, self.prefer_large_companies
        )
        if size_adj != 0:
            match_score += size_adj
            if size_adj > 0:
                adjustments.append(f"🏢 {size_desc}")
            else:
                adjustments.append(f"🏪 {size_desc}")

        # Apply role preference adjustment
        role_adj, role_desc = calculate_role_preference_adjustment(job.get("title", ""))
        if role_adj != 0:
            match_score += role_adj
            if role_adj > 0:
                adjustments.append(f"💻 {role_desc}")
            else:
                adjustments.append(f"👔 {role_desc}")

        # Clamp score to valid range (0-100)
        match_score = max(0, min(100, match_score))

        # Log adjustments if any were made
        if adjustments:
            logger.info(
                f"  Score adjustments: {', '.join(adjustments)} "
                f"(Base: {base_score} → Final: {match_score})"
            )

        # Recalculate priority tier based on adjusted score
        if match_score >= 75:
            priority = "High"
        elif match_score >= 50:
            priority = "Medium"
        else:
            priority = "Low"

        # Override AI's priority with our calculated one (if score changed)
        if base_score != match_score:
            match_analysis["application_priority"] = priority

        return match_score

    def _build_match_result(
        self,
        job: Dict[str, Any],
        match_analysis: Dict[str, Any],
        match_score: int,
        intake_data: Optional[Dict[str, Any]],
    ) -> JobMatchResult:
        """
        Build JobMatchResult from job data and analysis.

        Args:
            job: Job posting dictionary
            match_analysis: Match analysis from AI
            match_score: Adjusted match score
            intake_data: Resume intake data (optional)

        Returns:
            JobMatchResult object
        """
        return JobMatchResult(
            job_title=job.get("title", ""),
            job_company=job.get("company", ""),
            job_url=job.get("url", ""),
            match_score=match_score,
            matched_skills=match_analysis.get("matched_skills", []),
            missing_skills=match_analysis.get("missing_skills", []),
            experience_match=match_analysis.get("experience_match", ""),
            key_strengths=match_analysis.get("key_strengths", []),
            potential_concerns=match_analysis.get("potential_concerns", []),
            application_priority=match_analysis.get("application_priority", "Medium"),
            customization_recommendations=match_analysis.get("customization_recommendations", {}),
            resume_intake_data=intake_data,
        )

    def analyze_jobs(self, jobs: List[Dict[str, Any]]) -> List[JobMatchResult]:
        """
        Analyze multiple job postings.

        Args:
            jobs: List of job posting dictionaries.

        Returns:
            List of JobMatchResult objects for jobs that meet the threshold.
        """
        results = []

        for job in jobs:
            result = self.analyze_job(job)
            if result:
                results.append(result)

        logger.info(
            f"Analyzed {len(jobs)} jobs, {len(results)} met threshold of {self.min_match_score}"
        )
        return results

    def _analyze_match(self, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Internal method to analyze job match using AI.

        Args:
            job: Job posting dictionary.

        Returns:
            Dictionary with match analysis, or None if failed.
        """
        try:
            prompt = self.prompts.analyze_job_match(self.profile, job)

            # Get model-specific settings or use fallback
            model_name = self.config.get("model", "")
            models_config = self.config.get("models", {})
            model_settings = models_config.get(model_name, {})

            # Use model-specific settings or fallback to top-level config
            max_tokens = model_settings.get("max_tokens", self.config.get("max_tokens", 4096))
            temperature = model_settings.get("temperature", self.config.get("temperature", 0.3))

            response = self.provider.generate(
                prompt, max_tokens=max_tokens, temperature=temperature
            )

            # Parse JSON response
            # Try to extract JSON from response (in case there's extra text)
            response_clean = response.strip()
            if "```json" in response_clean:
                # Extract JSON from markdown code block
                start = response_clean.find("```json") + 7
                end = response_clean.find("```", start)
                response_clean = response_clean[start:end].strip()
            elif "```" in response_clean:
                start = response_clean.find("```") + 3
                end = response_clean.find("```", start)
                response_clean = response_clean[start:end].strip()

            analysis = json.loads(response_clean)

            # Validate required fields
            required_fields = [
                "match_score",
                "matched_skills",
                "missing_skills",
                "application_priority",
            ]
            missing_fields = [field for field in required_fields if field not in analysis]
            if missing_fields:
                logger.error(f"AI response missing required fields: {missing_fields}")
                logger.debug(f"Response was: {response[:500]}...")
                return None

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {str(e)}")
            logger.error(
                f"Raw response (first 500 chars): {response[:500] if response else 'None'}..."
            )
            return None
        except Exception as e:
            logger.error(f"Error during match analysis: {str(e)}", exc_info=True)
            return None

    def _generate_intake_data(
        self, job: Dict[str, Any], match_analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Internal method to generate resume intake data using AI.

        Args:
            job: Job posting dictionary.
            match_analysis: Previous match analysis results.

        Returns:
            Dictionary with resume intake data, or None if failed.
        """
        try:
            prompt = self.prompts.generate_resume_intake_data(self.profile, job, match_analysis)

            # Get model-specific settings or use fallback
            model_name = self.config.get("model", "")
            models_config = self.config.get("models", {})
            model_settings = models_config.get(model_name, {})

            # Use model-specific settings or fallback to top-level config
            max_tokens = model_settings.get("max_tokens", self.config.get("max_tokens", 4096))
            # Use slightly higher temperature for creative intake data generation
            temperature = (
                model_settings.get("temperature", self.config.get("temperature", 0.3)) + 0.1
            )

            response = self.provider.generate(
                prompt, max_tokens=max_tokens, temperature=temperature
            )

            # Parse JSON response
            response_clean = response.strip()
            if "```json" in response_clean:
                start = response_clean.find("```json") + 7
                end = response_clean.find("```", start)
                response_clean = response_clean[start:end].strip()
            elif "```" in response_clean:
                start = response_clean.find("```") + 3
                end = response_clean.find("```", start)
                response_clean = response_clean[start:end].strip()

            intake_data = json.loads(response_clean)

            # Validate required fields
            required_fields = [
                "job_id",
                "job_title",
                "target_summary",
                "skills_priority",
                "ats_keywords",
            ]
            missing_fields = [field for field in required_fields if field not in intake_data]
            if missing_fields:
                logger.warning(f"Intake data missing optional fields: {missing_fields}")

            # Intelligently reduce field sizes if they're too large
            intake_data = self._optimize_intake_data_size(intake_data)

            logger.info(f"Generated intake data for {job.get('title')}")
            return intake_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse intake data response as JSON: {str(e)}")
            logger.error(
                f"Raw response (first 500 chars): {response[:500] if response else 'None'}..."
            )
            return None
        except Exception as e:
            logger.error(f"Error generating intake data: {str(e)}", exc_info=True)
            return None

    def _optimize_intake_data_size(self, intake_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intelligently reduce the size of intake data fields by removing unnecessary
        information and consolidating content. Applies to ALL large fields generically.

        Args:
            intake_data: Resume intake data dictionary

        Returns:
            Optimized intake data with reduced field sizes
        """
        import re

        def clean_text(text: str, max_length: int = MAX_INTAKE_TEXT_LENGTH) -> str:
            """Clean and truncate text intelligently."""
            if not text or len(text) <= max_length:
                return text

            # Remove excessive whitespace
            text = re.sub(r"\s+", " ", text).strip()

            # Remove redundant phrases
            redundant_phrases = [
                r"\b(please|kindly|simply|just|really|very|quite|rather)\b",
                r"\b(note that|it is important to|make sure to)\b",
            ]
            for phrase in redundant_phrases:
                text = re.sub(phrase, "", text, flags=re.IGNORECASE)

            # Clean up extra spaces after removal
            text = re.sub(r"\s+", " ", text).strip()

            # If still too long, truncate at sentence boundary
            if len(text) > max_length:
                # Try to cut at last complete sentence
                truncated = text[:max_length]
                last_period = truncated.rfind(".")
                last_semicolon = truncated.rfind(";")
                cut_point = max(last_period, last_semicolon)

                if cut_point > max_length * 0.7:  # At least 70% of target length
                    text = text[: cut_point + 1].strip()
                else:
                    text = truncated.strip() + "..."

            return text

        def trim_list(
            items: List[str], max_items: int = 20, max_item_length: int = 100
        ) -> List[str]:
            """Trim list to reasonable size and clean each item."""
            if not items:
                return items

            # Take only first max_items
            trimmed = items[:max_items]

            # Clean each item
            cleaned = []
            for item in trimmed:
                if isinstance(item, str):
                    # Remove excess whitespace
                    item = re.sub(r"\s+", " ", item).strip()
                    # Truncate very long items
                    if len(item) > max_item_length:
                        item = item[:max_item_length].strip() + "..."
                    cleaned.append(item)
                else:
                    cleaned.append(item)

            return cleaned

        def optimize_value(value: Any, key: str) -> Any:
            """Recursively optimize any value based on its type and size."""
            if isinstance(value, str):
                # Apply different limits based on field purpose
                if (
                    len(value) > MAX_TEXT_OPTIMIZATION_LENGTH
                ):  # Only optimize strings that are actually large
                    if "description" in key.lower():
                        return clean_text(
                            value, max_length=MAX_INTAKE_DESCRIPTION_LENGTH
                        )  # Descriptions can be longer
                    elif "summary" in key.lower():
                        return clean_text(value, max_length=MAX_INTAKE_FIELD_LENGTH)
                    else:
                        return clean_text(value, max_length=MAX_INTAKE_TEXT_LENGTH)
                return value

            elif isinstance(value, list):
                # Determine limits based on field name
                if "keyword" in key.lower() or "skill" in key.lower():
                    return trim_list(value, max_items=25, max_item_length=100)
                elif "highlight" in key.lower() or "achievement" in key.lower():
                    return trim_list(value, max_items=10, max_item_length=200)
                elif "project" in key.lower():
                    return trim_list(value, max_items=5, max_item_length=150)
                else:
                    return trim_list(value, max_items=15, max_item_length=100)

            elif isinstance(value, dict):
                # Recursively optimize nested dictionaries
                return {k: optimize_value(v, k) for k, v in value.items()}

            else:
                # Return non-text types as-is (numbers, booleans, None, etc.)
                return value

        # Recursively optimize all fields in the intake data
        optimized_data = {}
        for key, value in intake_data.items():
            optimized_data[key] = optimize_value(value, key)

        return optimized_data
