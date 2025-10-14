"""Prompt templates for AI job matching and analysis."""
from typing import Dict, Any, List
from job_finder.profile.schema import Profile


class JobMatchPrompts:
    """Prompt templates for job matching tasks."""

    @staticmethod
    def build_profile_summary(profile: Profile) -> str:
        """
        Build a concise profile summary for prompts.

        Args:
            profile: User profile.

        Returns:
            Formatted profile summary string.
        """
        lines = [f"# Candidate Profile: {profile.name}\n"]

        if profile.summary:
            lines.append(f"## Summary\n{profile.summary}\n")

        if profile.years_of_experience:
            lines.append(f"## Experience\nTotal Years: {profile.years_of_experience}\n")

        # Skills
        if profile.skills:
            lines.append("## Skills")
            skill_names = [s.name for s in profile.skills]
            lines.append(", ".join(skill_names) + "\n")

        # Recent work experience
        if profile.experience:
            lines.append("## Recent Work Experience")
            for exp in profile.experience[:3]:  # Top 3 most recent
                lines.append(f"- {exp.title} at {exp.company} ({exp.start_date} - {exp.end_date or 'Present'})")
                if exp.technologies:
                    lines.append(f"  Technologies: {', '.join(exp.technologies)}")
            lines.append("")

        # Education
        if profile.education:
            lines.append("## Education")
            for edu in profile.education:
                lines.append(f"- {edu.degree} in {edu.field_of_study} from {edu.institution}")
            lines.append("")

        # Preferences
        if profile.preferences:
            prefs = profile.preferences
            lines.append("## Job Preferences")
            if prefs.desired_roles:
                lines.append(f"Desired Roles: {', '.join(prefs.desired_roles)}")
            if prefs.remote_preference:
                lines.append(f"Remote Preference: {prefs.remote_preference}")
            if prefs.min_salary:
                lines.append(f"Min Salary: ${prefs.min_salary:,}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def analyze_job_match(profile: Profile, job: Dict[str, Any]) -> str:
        """
        Create prompt to analyze job match against profile.

        Args:
            profile: User profile.
            job: Job posting dictionary.

        Returns:
            Formatted prompt string.
        """
        profile_summary = JobMatchPrompts.build_profile_summary(profile)

        prompt = f"""You are an expert career advisor and job matching specialist. Analyze how well this job posting matches the candidate's profile.

{profile_summary}

# Job Posting

**Title:** {job.get('title', 'N/A')}
**Company:** {job.get('company', 'N/A')}
**Location:** {job.get('location', 'N/A')}
**Description:**
{job.get('description', 'N/A')}

# Task

Analyze this job posting and provide:

1. **Match Score (0-100)**: Overall fit score
2. **Matched Skills**: List specific skills from the candidate's profile that match job requirements
3. **Missing Skills**: Skills required by the job that the candidate doesn't have
4. **Experience Match**: How well the candidate's experience aligns with job requirements
5. **Key Strengths**: Top 3-5 reasons this candidate would be strong for this role
6. **Potential Concerns**: Any gaps or mismatches (be honest but constructive)
7. **Application Priority**: High/Medium/Low priority for this candidate to apply
8. **Customization Recommendations**: Specific ways to tailor resume/cover letter for this job

Provide your analysis in the following JSON format:

{{
  "match_score": 85,
  "matched_skills": ["Python", "Django", "PostgreSQL"],
  "missing_skills": ["Kubernetes", "GraphQL"],
  "experience_match": "Strong match - candidate has 5 years in similar roles",
  "key_strengths": [
    "Deep Python and Django expertise",
    "Experience building scalable APIs",
    "Track record of leading projects"
  ],
  "potential_concerns": [
    "Limited Kubernetes experience",
    "No GraphQL background"
  ],
  "application_priority": "High",
  "customization_recommendations": {{
    "resume_focus": [
      "Highlight API development experience",
      "Emphasize Python/Django projects",
      "Include any containerization work (Docker)"
    ],
    "cover_letter_points": [
      "Mention enthusiasm for learning Kubernetes",
      "Highlight similar tech stack experience",
      "Discuss scalability achievements"
    ],
    "skills_to_emphasize": ["Python", "Django", "REST APIs", "PostgreSQL"]
  }}
}}

Respond ONLY with valid JSON, no additional text.
"""
        return prompt

    @staticmethod
    def generate_resume_intake_data(
        profile: Profile, job: Dict[str, Any], match_analysis: Dict[str, Any]
    ) -> str:
        """
        Create prompt to generate resume intake data for this specific job.

        Args:
            profile: User profile.
            job: Job posting dictionary.
            match_analysis: Previous match analysis results.

        Returns:
            Formatted prompt string.
        """
        profile_summary = JobMatchPrompts.build_profile_summary(profile)

        prompt = f"""You are an expert resume writer. Based on the candidate's profile and job posting analysis, generate structured intake data that can be used to create a tailored resume.

{profile_summary}

# Job Posting

**Title:** {job.get('title', 'N/A')}
**Company:** {job.get('company', 'N/A')}
**Description:**
{job.get('description', 'N/A')}

# Match Analysis

Match Score: {match_analysis.get('match_score', 'N/A')}
Matched Skills: {', '.join(match_analysis.get('matched_skills', []))}
Key Strengths: {', '.join(match_analysis.get('key_strengths', []))}

# Task

Generate resume intake data that specifies exactly how to tailor the candidate's resume for this job. Include:

1. **Target Summary**: A tailored professional summary for this specific job
2. **Skills Priority**: Ordered list of which skills to emphasize (most relevant first)
3. **Experience Highlights**: Which work experiences to feature and what to emphasize
4. **Projects to Include**: Which projects are most relevant
5. **Achievement Angles**: How to frame achievements to match job requirements
6. **Keywords to Include**: Important keywords from job description to incorporate

Provide your intake data in the following JSON format:

{{
  "job_id": "{job.get('url', 'unknown')}",
  "job_title": "{job.get('title', '')}",
  "company": "{job.get('company', '')}",
  "target_summary": "Results-driven software engineer with 5+ years...",
  "skills_priority": [
    "Python",
    "Django",
    "REST APIs",
    "PostgreSQL",
    "Docker"
  ],
  "experience_highlights": [
    {{
      "company": "Company Name",
      "title": "Software Engineer",
      "points_to_emphasize": [
        "Led development of microservices architecture",
        "Built RESTful APIs serving 1M+ requests/day"
      ]
    }}
  ],
  "projects_to_include": [
    {{
      "name": "Project Name",
      "why_relevant": "Demonstrates API development skills",
      "points_to_highlight": [
        "Built with Python and Django",
        "Scaled to handle 10k concurrent users"
      ]
    }}
  ],
  "achievement_angles": [
    "Emphasize scalability and performance",
    "Highlight team leadership",
    "Focus on API development expertise"
  ],
  "keywords_to_include": [
    "microservices",
    "scalable",
    "RESTful APIs",
    "agile",
    "CI/CD"
  ]
}}

Respond ONLY with valid JSON, no additional text.
"""
        return prompt
