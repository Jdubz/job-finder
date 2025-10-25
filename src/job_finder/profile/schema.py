"""Data models for user profile and experience."""

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class Skill(BaseModel):
    """Represents a skill or technology."""

    name: str = Field(..., description="Skill or technology name")
    level: Optional[str] = Field(
        None, description="Proficiency level (beginner, intermediate, advanced, expert)"
    )
    years_experience: Optional[float] = Field(
        None, description="Years of experience with this skill"
    )
    category: Optional[str] = Field(
        None, description="Category (e.g., programming, framework, tool)"
    )


class Experience(BaseModel):
    """Represents work experience."""

    company: str = Field(..., description="Company name")
    title: str = Field(..., description="Job title/role")
    start_date: str = Field(..., description="Start date (YYYY-MM or YYYY-MM-DD)")
    end_date: Optional[str] = Field(
        None, description="End date (YYYY-MM or YYYY-MM-DD), null if current"
    )
    location: Optional[str] = Field(None, description="Job location")
    description: Optional[str] = Field(None, description="Role description")
    responsibilities: List[str] = Field(default_factory=list, description="Key responsibilities")
    achievements: List[str] = Field(default_factory=list, description="Notable achievements")
    technologies: List[str] = Field(default_factory=list, description="Technologies used")
    is_current: bool = Field(False, description="Whether this is current employment")


class Education(BaseModel):
    """Represents educational background."""

    institution: str = Field(..., description="School/university name")
    degree: str = Field(..., description="Degree type (e.g., BS, MS, PhD)")
    field_of_study: Optional[str] = Field(None, description="Major/field of study")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM or YYYY)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM or YYYY)")
    gpa: Optional[float] = Field(None, description="GPA (optional)")
    honors: List[str] = Field(default_factory=list, description="Honors and awards")


class Project(BaseModel):
    """Represents a project (personal or professional)."""

    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    technologies: List[str] = Field(default_factory=list, description="Technologies used")
    url: Optional[HttpUrl] = Field(None, description="Project URL")
    github_url: Optional[HttpUrl] = Field(None, description="GitHub repository URL")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date")
    highlights: List[str] = Field(
        default_factory=list, description="Key highlights or achievements"
    )


class Preferences(BaseModel):
    """Job search preferences."""

    desired_roles: List[str] = Field(default_factory=list, description="Desired job titles/roles")
    preferred_locations: List[str] = Field(
        default_factory=list, description="Preferred work locations"
    )
    remote_preference: Optional[str] = Field(
        None, description="Remote work preference (remote, hybrid, onsite, flexible)"
    )
    min_salary: Optional[int] = Field(None, description="Minimum desired salary")
    max_salary: Optional[int] = Field(None, description="Maximum expected salary")
    employment_types: List[str] = Field(
        default_factory=list,
        description="Preferred employment types (full-time, part-time, contract)",
    )
    company_sizes: List[str] = Field(
        default_factory=list,
        description="Preferred company sizes (startup, small, medium, large, enterprise)",
    )
    industries: List[str] = Field(default_factory=list, description="Preferred industries")


class Profile(BaseModel):
    """Complete user profile for job matching."""

    # Personal Information
    name: str = Field(..., description="Full name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="Current location")
    linkedin_url: Optional[HttpUrl] = Field(None, description="LinkedIn profile URL")
    github_url: Optional[HttpUrl] = Field(None, description="GitHub profile URL")
    portfolio_url: Optional[HttpUrl] = Field(None, description="job-finder-FE website URL")

    # Professional Summary
    summary: Optional[str] = Field(None, description="Professional summary/bio")
    years_of_experience: Optional[float] = Field(
        None, description="Total years of professional experience"
    )

    # Experience and Skills
    skills: List[Skill] = Field(default_factory=list, description="Skills and technologies")
    experience: List[Experience] = Field(default_factory=list, description="Work experience")
    education: List[Education] = Field(default_factory=list, description="Educational background")
    projects: List[Project] = Field(default_factory=list, description="Projects")

    # Preferences
    preferences: Optional[Preferences] = Field(None, description="Job search preferences")

    # Certifications and Additional Info
    certifications: List[str] = Field(
        default_factory=list, description="Professional certifications"
    )
    languages: List[str] = Field(default_factory=list, description="Spoken languages")

    def get_all_skills(self) -> List[str]:
        """Get a flat list of all skill names."""
        skills_set = {skill.name for skill in self.skills}

        # Add technologies from experience
        for exp in self.experience:
            skills_set.update(exp.technologies)

        # Add technologies from projects
        for project in self.projects:
            skills_set.update(project.technologies)

        return sorted(list(skills_set))

    def get_current_role(self) -> Optional[Experience]:
        """Get current employment if any."""
        current = [exp for exp in self.experience if exp.is_current]
        return current[0] if current else None

    def get_experience_by_company(self, company: str) -> List[Experience]:
        """Get all experience entries for a specific company."""
        return [exp for exp in self.experience if exp.company.lower() == company.lower()]
