"""Prompt templates for AI job matching and analysis."""

from typing import Any, Dict

from job_finder.profile.schema import Profile


class JobMatchPrompts:
    """Prompt templates for job matching tasks."""

    @staticmethod
    def build_profile_summary(profile: Profile) -> str:
        """
        Build a comprehensive profile summary for prompts.

        Args:
            profile: User profile.

        Returns:
            Formatted profile summary string.
        """
        lines = [f"# Candidate Profile: {profile.name}\n"]

        # Location and Languages (if available)
        metadata = []
        if profile.location:
            metadata.append(f"**Location:** {profile.location}")
        if profile.languages:
            metadata.append(f"**Languages:** {', '.join(profile.languages)}")
        if metadata:
            lines.extend(metadata)
            lines.append("")

        # Professional Summary
        if profile.summary:
            lines.append(f"## Professional Summary\n{profile.summary}\n")

        # Experience Overview
        if profile.years_of_experience:
            lines.append(f"## Experience Overview")
            lines.append(f"Total Years: {profile.years_of_experience}")

            # Current role
            current = profile.get_current_role()
            if current:
                lines.append(f"Current Role: {current.title} at {current.company}")
            lines.append("")

        # Skills (with levels and years)
        if profile.skills:
            lines.append("## Technical Skills")

            # Group by level if available
            expert_skills = [s for s in profile.skills if s.level and "expert" in s.level.lower()]
            advanced_skills = [
                s for s in profile.skills if s.level and "advanced" in s.level.lower()
            ]
            intermediate_skills = [
                s for s in profile.skills if s.level and "intermediate" in s.level.lower()
            ]
            other_skills = [
                s
                for s in profile.skills
                if not s.level or s.level.lower() not in ["expert", "advanced", "intermediate"]
            ]

            if expert_skills:
                lines.append("**Expert:**")
                for skill in expert_skills:
                    exp_str = f" ({skill.years_experience} years)" if skill.years_experience else ""
                    lines.append(f"  - {skill.name}{exp_str}")

            if advanced_skills:
                lines.append("**Advanced:**")
                for skill in advanced_skills:
                    exp_str = f" ({skill.years_experience} years)" if skill.years_experience else ""
                    lines.append(f"  - {skill.name}{exp_str}")

            if intermediate_skills:
                lines.append("**Intermediate:**")
                for skill in intermediate_skills:
                    exp_str = f" ({skill.years_experience} years)" if skill.years_experience else ""
                    lines.append(f"  - {skill.name}{exp_str}")

            if other_skills:
                lines.append("**Other Skills:**")
                skill_names = [
                    f"{s.name} ({s.years_experience} years)" if s.years_experience else s.name
                    for s in other_skills
                ]
                lines.append("  " + ", ".join(skill_names))

            lines.append("")

        # Recent work experience with responsibilities and achievements
        if profile.experience:
            lines.append("## Work Experience (Recent)")
            for exp in profile.experience[:3]:  # Top 3 most recent
                duration = f"{exp.start_date} - {exp.end_date or 'Present'}"
                lines.append(f"\n### {exp.title} at {exp.company}")
                lines.append(f"*{duration}*")

                if exp.description:
                    lines.append(f"{exp.description}")

                if exp.responsibilities:
                    lines.append("**Responsibilities:**")
                    for resp in exp.responsibilities[:4]:  # Top 4 responsibilities
                        lines.append(f"  - {resp}")

                if exp.achievements:
                    lines.append("**Key Achievements:**")
                    for achievement in exp.achievements[:3]:  # Top 3
                        lines.append(f"  - {achievement}")

                if exp.technologies:
                    lines.append(f"**Technologies:** {', '.join(exp.technologies)}")
            lines.append("")

        # Notable Projects
        if profile.projects:
            lines.append("## Notable Projects")
            for proj in profile.projects[:2]:  # Top 2
                lines.append(f"\n### {proj.name}")
                lines.append(f"{proj.description}")
                if proj.technologies:
                    lines.append(f"**Technologies:** {', '.join(proj.technologies)}")
                if proj.highlights:
                    lines.append("**Highlights:**")
                    for highlight in proj.highlights[:2]:
                        lines.append(f"  - {highlight}")
            lines.append("")

        # Education
        if profile.education:
            lines.append("## Education")
            for edu in profile.education:
                degree_str = (
                    f"{edu.degree} in {edu.field_of_study}" if edu.field_of_study else edu.degree
                )
                lines.append(f"- {degree_str} from {edu.institution}")
                if edu.honors:
                    lines.append(f"  Honors: {', '.join(edu.honors)}")
            lines.append("")

        # Certifications
        if profile.certifications:
            lines.append("## Certifications")
            lines.append(", ".join(profile.certifications))
            lines.append("")

        # Job Search Preferences
        if profile.preferences:
            prefs = profile.preferences
            lines.append("## Job Search Preferences")

            # Add Portland location preference (always include for visibility)
            lines.append(f"**Location:** Portland, OR (prefers local or remote positions)")

            if prefs.desired_roles:
                lines.append(f"**Desired Roles:** {', '.join(prefs.desired_roles)}")
            if prefs.remote_preference:
                lines.append(f"**Remote Preference:** {prefs.remote_preference}")
            if prefs.min_salary or prefs.max_salary:
                salary_range = ""
                if prefs.min_salary and prefs.max_salary:
                    salary_range = f"${prefs.min_salary:,} - ${prefs.max_salary:,}"
                elif prefs.min_salary:
                    salary_range = f"${prefs.min_salary:,}+"
                elif prefs.max_salary:
                    salary_range = f"Up to ${prefs.max_salary:,}"
                lines.append(f"**Salary Range:** {salary_range}")
            if prefs.employment_types:
                lines.append(f"**Employment Types:** {', '.join(prefs.employment_types)}")
            if prefs.industries:
                lines.append(f"**Preferred Industries:** {', '.join(prefs.industries)}")
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

        prompt = f"""You are an expert career advisor and job matching specialist. Analyze how well this job posting matches the candidate's profile with extreme accuracy and honesty.

{profile_summary}

# Job Posting

**Title:** {job.get('title', 'N/A')}
**Company:** {job.get('company', 'N/A')}
**Location:** {job.get('location', 'N/A')}
**Salary:** {job.get('salary', 'Not specified')}
**Description:**
{job.get('description', 'N/A')}
{f'''
**Company Information:**
{job.get('company_info', '')}
''' if job.get('company_info') else ''}
# Analysis Task

Provide a thorough, accurate analysis of job fit. Be HONEST and REALISTIC - false positives waste the candidate's time.

## CRITICAL PRE-SCREENING CHECKS (Auto-Reject if True):

Before scoring, check for these AUTOMATIC DISQUALIFIERS:

1. **Hidden Non-Engineering Role**
   - Is this actually a management role disguised as IC? (e.g., "Technical Program Manager", "Delivery Manager")
   - Is it primarily sales/customer-facing? (e.g., "Solutions Architect" that's 80% sales, "Customer Success Engineer")
   - Does it require minimal coding? (e.g., "oversee", "coordinate", "manage team" but no "build", "develop", "code")
   - **If YES to any:** Set match_score = 0 and explain why in potential_concerns

2. **Remote Work Red Flags**
   - Does it require frequent travel (25%+ of time)?
   - Does it say "remote for now, relocate later" or "remote during pandemic only"?
   - Does it require specific timezone hours incompatible with Pacific Time? (e.g., "must work UK hours")
   - Is it "remote" but requires regular in-office attendance outside Portland, OR?
   - **If YES to any:** Set match_score = 0 and explain in potential_concerns

3. **Compensation/Employment Structure Issues**
   - Is this a contract/1099 position when candidate wants FTE?
   - Does it emphasize equity over base salary for an unproven startup?
   - Does "competitive salary" seem like code for below-market pay?
   - Is it commission-based or performance-pay heavy?
   - **If YES to any:** Reduce score by 30 points minimum

4. **Unrealistic Expectations**
   - Does it list 10+ required technologies that no one person could master?
   - Does it want senior-level skills but offer mid-level compensation?
   - Is the title inflated for the actual role? (e.g., "Senior" but requires only 2 years experience)
   - **If YES:** Reduce score by 20 points minimum

5. **Quality/Culture Red Flags**
   - Excessive buzzwords with no substance ("rockstar", "ninja", "10x engineer")?
   - "Fast-paced startup environment" + "wear many hats" = chaotic/undefined role?
   - "Unlimited PTO" without clear team boundaries = overwork culture?
   - "Family atmosphere" + "we work hard and play hard" = poor work-life balance?
   - No mention of WLB, benefits, or team structure?
   - **If multiple flags:** Reduce score by 10-15 points

## Step 1: Extract Job Requirements

From the title and description, identify:
1. **Required skills** (MUST-have technologies/tools)
2. **Preferred skills** (nice-to-have)
3. **Experience level** (Junior 0-2 years, Mid 2-5 years, Senior 5+ years, Staff/Principal 8+ years)
4. **Years of experience required**
5. **Seniority indicators** (Junior/Mid/Senior/Lead/Staff/Principal in title or description)
6. **Domain expertise** (e.g., fintech, healthcare, e-commerce)

## Step 2: Match Against Profile

For each requirement, check:
- Does candidate have this skill? At what level?
- How many years of experience with this skill?
- Have they used it in a professional setting (not just side projects)?
- Do they have recent experience (within last 2-3 years)?

## Step 3: Calculate Match Score (0-100) - STRICT GRADING

Use this formula with **EXTREMELY HIGH STANDARDS**:

**Title Skills (50 points max):**
- ALL title skills at Expert/Advanced level (5+ years): 50 points
- ALL title skills at Advanced level (3-5 years): 40 points
- Title skills at Intermediate level (1-3 years): 20-25 points
- Missing ANY title skill OR only beginner level: 0-10 points

**Description Requirements (30 points max):**
- 95%+ of REQUIRED skills present at strong level: 30 points
- 85-95% of required skills present at strong level: 20 points
- 70-85% of required skills present: 10 points
- <70% of required skills present: 0-5 points

**Experience Level Match (20 points max):**
- Seniority EXACTLY matches + domain experience: 20 points
- Seniority matches but different domain: 15 points
- One level off (e.g., Mid for Senior): 5-10 points
- Two+ levels off OR seniority unclear: 0 points

**CRITICAL RULES - STRICT ENFORCEMENT:**

1. **Title Skills are NON-NEGOTIABLE**
   - Missing ANY core technology from title → MAXIMUM score = 30 (fails threshold)
   - Title skill at beginner level → MAXIMUM score = 40

2. **Seniority Strictly Enforced**
   - Job says "Senior" (5+ years) but candidate has <4 years → MAXIMUM score = 45
   - Job says "Staff/Principal" (8+ years) but candidate has <7 years → MAXIMUM score = 40
   - Job says "Lead/Director" but candidate has no leadership experience → MAXIMUM score = 35

3. **Domain Expertise Required**
   - Job requires specific domain (fintech, healthcare, etc.) candidate lacks → Reduce by 15-20 points
   - Job requires specific platform (e.g., AWS) candidate lacks → Reduce by 10-15 points

4. **Recency Matters**
   - Skill mentioned in title but not used in last 3 years → Reduce title score by 20 points
   - Multiple outdated skills → Additional 10 point reduction

5. **Buzzword Detection**
   - If job is a generic "Full Stack Developer" with no specific tech → Can be more lenient
   - If job lists 15+ technologies → Focus on 5-7 most important ones

6. **Be BRUTALLY Honest**
   - When in doubt, score LOWER
   - Better to miss marginal matches than waste time on poor fits
   - Only scores 80+ should pass threshold

## Step 4: Provide Analysis

Return detailed analysis in JSON format with:

1. **match_score** (0-100): Calculated using above formula
2. **matched_skills**: Array of skills candidate HAS that match (with proficiency level)
3. **missing_skills**: Array of required skills candidate LACKS
4. **experience_match**: Detailed explanation of experience level fit
5. **key_strengths**: Top 3-5 specific reasons candidate is strong (be concrete, reference actual experience)
6. **potential_concerns**: Honest assessment of gaps/weaknesses (be specific)
7. **application_priority**: "High" (85-100), "Medium" (70-84), "Low" (0-69)
8. **customization_recommendations**: Specific, actionable advice for tailoring application

## Scoring Examples (STRICT STANDARDS):

**Example 1 - Excellent Match (Score: 92) - HIGH PRIORITY**
- Job: "Senior Python Developer" at fintech company
- Candidate: 7 years Python (expert), 5 years in fintech, all required skills at advanced level
- Title skills (50) + Description (30) + Experience (12) = 92

**Example 2 - Good Match (Score: 85) - HIGH PRIORITY**
- Job: "React Frontend Engineer"
- Candidate: 5 years React (expert), 4 years JavaScript, missing 1 nice-to-have skill
- Title skills (50) + Description (25) + Experience (10) = 85

**Example 3 - Decent Match (Score: 72) - MEDIUM PRIORITY**
- Job: "Senior Full Stack Engineer (Python/React)"
- Candidate: 6 years Python (expert), 2 years React (intermediate), senior title mismatch
- Title skills (35) + Description (25) + Experience (12) = 72

**Example 4 - Borderline (Score: 58) - FAILS THRESHOLD**
- Job: "Full Stack Engineer (Python/React)"
- Candidate: Strong Python (5 years expert), basic React (6 months beginner)
- Title skills (25 - React too weak) + Description (20) + Experience (13) = 58

**Example 5 - Poor Match (Score: 30) - FAILS THRESHOLD**
- Job: ".NET Developer"
- Candidate: Strong Python/JavaScript, NO .NET experience
- Title skills (0 - missing .NET) + Description (20) + Experience (10) = 30 (capped)

**Example 6 - Very Poor Match (Score: 15) - FAILS THRESHOLD**
- Job: "Senior DevOps Engineer (Kubernetes/AWS)"
- Candidate: Junior developer with 2 years, no infrastructure or cloud experience
- Title skills (0) + Description (5) + Experience (0) + Seniority cap = 15

**Example 7 - Auto-Reject (Score: 0) - HIDDEN NON-ENGINEERING**
- Job: "Technical Program Manager" with "coordinate teams", "manage stakeholders", minimal coding
- Candidate: IC engineer seeking hands-on role
- Score: 0 - Not an engineering role despite "technical" in title

**Example 8 - Auto-Reject (Score: 0) - REMOTE RED FLAG**
- Job: "Remote" but requires "50% travel" or "must work EST hours" from Pacific timezone
- Score: 0 - Remote restrictions incompatible with candidate location/preferences

**PORTLAND BONUS:**
- If job explicitly mentions Portland, OR office/presence: +15 bonus points (shows local opportunity)
- If hybrid Portland option mentioned: +10 bonus points
- Apply AFTER calculating base score, can push borderline matches over threshold

**Remember:** Only scores 80+ should realistically pass. Be harsh - candidate's time is valuable.

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

        prompt = f"""You are an expert resume writer and ATS (Applicant Tracking System) optimization specialist. Create a detailed resume customization guide for this specific job application.

{profile_summary}

# Job Posting

**Title:** {job.get('title', 'N/A')}
**Company:** {job.get('company', 'N/A')}
**Description:**
{job.get('description', 'N/A')}
{f'''
**Company Information:**
{job.get('company_info', '')}
''' if job.get('company_info') else ''}
# Match Analysis

**Match Score:** {match_analysis.get('match_score', 'N/A')}/100
**Matched Skills:** {', '.join(match_analysis.get('matched_skills', []))}
**Missing Skills:** {', '.join(match_analysis.get('missing_skills', []))}
**Key Strengths:** {', '.join(match_analysis.get('key_strengths', []))}
**Potential Concerns:** {', '.join(match_analysis.get('potential_concerns', []))}

# Resume Customization Task

Generate specific, actionable guidance for tailoring the resume to THIS job. Focus on ATS optimization and relevance.

## Requirements:

1. **Target Summary** (2-3 sentences)
   - Emphasize skills and experience MOST relevant to this role
   - Include key technologies from the job title
   - Mention years of experience if it matches seniority level
   - Use power words and quantifiable achievements

2. **Skills Priority** (Ordered list)
   - List ALL matched skills in priority order
   - Put title-mentioned skills FIRST
   - Group related technologies together
   - Exclude skills not relevant to this role

3. **Experience Highlights**
   - For EACH relevant work experience, specify:
     * Which bullet points to emphasize/modify
     * Specific metrics or achievements to highlight
     * Technologies to mention prominently
     * How to reframe responsibilities to match job requirements

4. **Projects to Include**
   - List 2-3 most relevant projects
   - For each: explain WHY it's relevant
   - Suggest specific points to emphasize

5. **Achievement Angles**
   - How to frame/reword achievements to align with job needs
   - Specific metrics to emphasize (scale, performance, impact)
   - Leadership/collaboration angles if relevant

6. **ATS Keywords**
   - Extract 10-15 critical keywords from job description
   - Include exact technology names (case-sensitive)
   - Include role-specific terminology
   - Include domain-specific terms

7. **Gap Mitigation** (If missing skills exist)
   - For each missing skill: suggest how to address or downplay the gap
   - Identify transferable skills to emphasize
   - Recommend cover letter talking points

## Quality Guidelines:

- Be SPECIFIC - reference actual experiences from profile
- Focus on RELEVANCE over quantity
- Use candidate's actual achievements and metrics
- Match the language/terminology used in job description
- Consider ATS keyword matching
- Ensure all recommendations are truthful (no fabrication)

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
  "ats_keywords": [
    "Python",
    "Django",
    "RESTful APIs",
    "microservices",
    "PostgreSQL",
    "Docker",
    "Kubernetes",
    "CI/CD",
    "Agile",
    "Scrum"
  ],
  "gap_mitigation": [
    {{
      "missing_skill": "Kubernetes",
      "mitigation_strategy": "Emphasize Docker and container experience as transferable",
      "cover_letter_point": "Express enthusiasm for expanding Kubernetes expertise"
    }}
  ]
}}

Respond ONLY with valid JSON, no additional text.
"""
        return prompt
