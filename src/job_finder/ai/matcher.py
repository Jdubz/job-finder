"""AI-powered job matching and intake data generation."""

import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from job_finder.profile.schema import Profile
from job_finder.ai.providers import AIProvider
from job_finder.ai.prompts import JobMatchPrompts


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


class AIJobMatcher:
    """AI-powered job matcher that analyzes jobs and generates resume intake data."""

    def __init__(
        self,
        provider: AIProvider,
        profile: Profile,
        min_match_score: int = 50,
        generate_intake: bool = True,
        portland_office_bonus: int = 15,
    ):
        """
        Initialize AI job matcher.

        Args:
            provider: AI provider instance.
            profile: User profile for matching.
            min_match_score: Minimum score threshold for a job to be considered a match.
            generate_intake: Whether to generate resume intake data for matched jobs.
            portland_office_bonus: Bonus points to add for companies with Portland, OR offices.
        """
        self.provider = provider
        self.profile = profile
        self.min_match_score = min_match_score
        self.generate_intake = generate_intake
        self.portland_office_bonus = portland_office_bonus
        self.prompts = JobMatchPrompts()

    def analyze_job(self, job: Dict[str, Any], has_portland_office: bool = False) -> Optional[JobMatchResult]:
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

            # Get base score from AI analysis
            base_score = match_analysis.get("match_score", 0)
            match_score = base_score

            # Apply Portland office bonus
            if has_portland_office and self.portland_office_bonus > 0:
                match_score = min(100, base_score + self.portland_office_bonus)
                logger.info(
                    f"  🏙️ Portland office bonus: +{self.portland_office_bonus} points "
                    f"(Base: {base_score} → Adjusted: {match_score})"
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

            # Check if adjusted score meets minimum threshold
            if match_score < self.min_match_score:
                logger.info(
                    f"Job {job.get('title')} scored {match_score} (base: {base_score}), "
                    f"below threshold {self.min_match_score}"
                )
                return None

            # Step 2: Generate resume intake data if enabled and score is high enough
            intake_data = None
            if self.generate_intake and match_score >= self.min_match_score:
                intake_data = self._generate_intake_data(job, match_analysis)

            # Build result
            result = JobMatchResult(
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
                customization_recommendations=match_analysis.get(
                    "customization_recommendations", {}
                ),
                resume_intake_data=intake_data,
            )

            logger.info(
                f"Successfully analyzed {job.get('title')} - Score: {match_score}, Priority: {result.application_priority}"
            )
            return result

        except Exception as e:
            logger.error(f"Error analyzing job {job.get('title', 'unknown')}: {str(e)}")
            return None

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
            # Increased max_tokens to 4000 for detailed analysis with comprehensive prompts
            response = self.provider.generate(prompt, max_tokens=4000, temperature=0.3)

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
            # Increased max_tokens to 5000 for comprehensive resume intake data
            response = self.provider.generate(prompt, max_tokens=5000, temperature=0.4)

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
