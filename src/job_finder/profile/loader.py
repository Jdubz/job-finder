"""Profile data loader from various sources."""

import json
from pathlib import Path
from typing import Any, Dict

from job_finder.exceptions import ProfileError
from job_finder.profile.schema import Profile


class ProfileLoader:
    """Loads user profile data from files."""

    @staticmethod
    def load_from_json(file_path: str) -> Profile:
        """
        Load profile from a JSON file.

        Args:
            file_path: Path to JSON file containing profile data.

        Returns:
            Profile instance.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the JSON is invalid or doesn't match the schema.
        """
        path = Path(file_path)

        if not path.exists():
            raise ProfileError(f"Profile file not found: {file_path}")

        with open(path, "r") as f:
            data = json.load(f)

        try:
            return Profile(**data)
        except Exception as e:
            raise ProfileError(f"Invalid profile data: {str(e)}") from e

    @staticmethod
    def load_from_dict(data: Dict[str, Any]) -> Profile:
        """
        Load profile from a dictionary.

        Args:
            data: Dictionary containing profile data.

        Returns:
            Profile instance.

        Raises:
            ValueError: If the data doesn't match the schema.
        """
        try:
            return Profile(**data)
        except Exception as e:
            raise ProfileError(f"Invalid profile data: {str(e)}") from e

    @staticmethod
    def validate_profile(profile: Profile) -> bool:
        """
        Validate that a profile has minimum required data.

        Args:
            profile: Profile instance to validate.

        Returns:
            True if profile is valid, False otherwise.
        """
        # Check for required fields
        if not profile.name:
            return False

        # Check that profile has some useful data
        has_data = (
            len(profile.skills) > 0 or len(profile.experience) > 0 or profile.summary is not None
        )

        return has_data

    @staticmethod
    def save_to_json(profile: Profile, file_path: str, indent: int = 2) -> None:
        """
        Save profile to a JSON file.

        Args:
            profile: Profile instance to save.
            file_path: Path where JSON file should be saved.
            indent: JSON indentation level (default: 2).
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(profile.model_dump(mode="json"), f, indent=indent)

    @staticmethod
    def create_template(file_path: str) -> None:
        """
        Create a template profile JSON file.

        Args:
            file_path: Path where template should be created.
        """
        template = {
            "name": "Your Name",
            "email": "your.email@example.com",
            "location": "City, State/Country",
            "summary": "Brief professional summary highlighting your expertise and career goals.",
            "years_of_experience": 5.0,
            "skills": [
                {
                    "name": "Python",
                    "level": "advanced",
                    "years_experience": 5.0,
                    "category": "programming",
                },
                {
                    "name": "JavaScript",
                    "level": "intermediate",
                    "years_experience": 3.0,
                    "category": "programming",
                },
            ],
            "experience": [
                {
                    "company": "Company Name",
                    "title": "Software Engineer",
                    "start_date": "2020-01",
                    "end_date": "2023-06",
                    "location": "City, State",
                    "description": "Brief description of the role",
                    "responsibilities": ["Key responsibility 1", "Key responsibility 2"],
                    "achievements": ["Notable achievement 1", "Notable achievement 2"],
                    "technologies": ["Python", "Django", "PostgreSQL"],
                    "is_current": False,
                }
            ],
            "education": [
                {
                    "institution": "University Name",
                    "degree": "Bachelor of Science",
                    "field_of_study": "Computer Science",
                    "start_date": "2015",
                    "end_date": "2019",
                    "honors": ["Dean's List", "Cum Laude"],
                }
            ],
            "projects": [
                {
                    "name": "Project Name",
                    "description": "Description of the project",
                    "technologies": ["Python", "React", "Docker"],
                    "highlights": ["Key achievement 1", "Key achievement 2"],
                }
            ],
            "preferences": {
                "desired_roles": ["Software Engineer", "Backend Developer"],
                "preferred_locations": ["Remote", "San Francisco", "New York"],
                "remote_preference": "remote",
                "min_salary": 100000,
                "employment_types": ["full-time"],
                "company_sizes": ["startup", "medium", "large"],
                "industries": ["technology", "fintech", "healthcare"],
            },
            "certifications": ["AWS Certified Developer"],
            "languages": ["English", "Spanish"],
        }

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(template, f, indent=2)
