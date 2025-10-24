"""Tests for profile data loader."""

import json

import pytest

from job_finder.exceptions import ProfileError
from job_finder.profile.loader import ProfileLoader
from job_finder.profile.schema import Experience, Profile, Skill


class TestLoadFromJson:
    """Test loading profile from JSON file."""

    def test_load_valid_json(self, tmp_path):
        """Test loading valid profile JSON."""
        profile_data = {
            "name": "Test User",
            "email": "test@example.com",
            "phone": None,
            "location": "San Francisco, CA",
            "linkedin_url": None,
            "github_url": None,
            "portfolio_url": None,
            "summary": "Software engineer with 5 years experience",
            "years_of_experience": 5.0,
            "skills": [
                {
                    "name": "Python",
                    "level": "advanced",
                    "years_experience": 5.0,
                    "category": "programming",
                }
            ],
            "experience": [],
            "education": [],
            "projects": [],
            "preferences": None,
            "certifications": [],
            "languages": ["English"],
        }

        # Create temp JSON file
        json_file = tmp_path / "profile.json"
        with open(json_file, "w") as f:
            json.dump(profile_data, f)

        # Load profile
        profile = ProfileLoader.load_from_json(str(json_file))

        assert isinstance(profile, Profile)
        assert profile.name == "Test User"
        assert profile.email == "test@example.com"
        assert profile.years_of_experience == 5.0
        assert len(profile.skills) == 1
        assert profile.skills[0].name == "Python"

    def test_load_file_not_found(self):
        """Test loading from non-existent file raises ProfileError."""
        with pytest.raises(ProfileError) as exc_info:
            ProfileLoader.load_from_json("/nonexistent/path/profile.json")

        assert "Profile file not found" in str(exc_info.value)

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON raises ValueError."""
        json_file = tmp_path / "invalid.json"
        with open(json_file, "w") as f:
            f.write("{ invalid json ")

        with pytest.raises((ValueError, json.JSONDecodeError)):
            ProfileLoader.load_from_json(str(json_file))

    def test_load_invalid_schema(self, tmp_path):
        """Test loading data with invalid field types raises ProfileError."""
        invalid_data = {
            "name": "Test User",
            "skills": "not a list",  # Invalid type - should be list
            "years_of_experience": "not a number",  # Invalid type
        }

        json_file = tmp_path / "invalid_schema.json"
        with open(json_file, "w") as f:
            json.dump(invalid_data, f)

        with pytest.raises(ProfileError) as exc_info:
            ProfileLoader.load_from_json(str(json_file))

        assert "Invalid profile data" in str(exc_info.value)

    def test_load_empty_json(self, tmp_path):
        """Test loading empty JSON raises ProfileError."""
        json_file = tmp_path / "empty.json"
        with open(json_file, "w") as f:
            json.dump({}, f)

        with pytest.raises(ProfileError) as exc_info:
            ProfileLoader.load_from_json(str(json_file))

        assert "Invalid profile data" in str(exc_info.value)


class TestLoadFromDict:
    """Test loading profile from dictionary."""

    def test_load_valid_dict(self):
        """Test loading valid profile dictionary."""
        profile_data = {
            "name": "Test User",
            "email": "test@example.com",
            "phone": None,
            "location": "San Francisco, CA",
            "linkedin_url": None,
            "github_url": None,
            "portfolio_url": None,
            "summary": "Software engineer",
            "years_of_experience": 5.0,
            "skills": [],
            "experience": [],
            "education": [],
            "projects": [],
            "preferences": None,
            "certifications": [],
            "languages": [],
        }

        profile = ProfileLoader.load_from_dict(profile_data)

        assert isinstance(profile, Profile)
        assert profile.name == "Test User"
        assert profile.email == "test@example.com"

    def test_load_dict_with_nested_objects(self):
        """Test loading dictionary with nested objects."""
        profile_data = {
            "name": "Test User",
            "email": "test@example.com",
            "phone": None,
            "location": None,
            "linkedin_url": None,
            "github_url": None,
            "portfolio_url": None,
            "summary": None,
            "years_of_experience": 3.0,
            "skills": [
                {
                    "name": "Python",
                    "level": "advanced",
                    "years_experience": 3.0,
                    "category": "programming",
                }
            ],
            "experience": [
                {
                    "company": "Tech Corp",
                    "title": "Software Engineer",
                    "start_date": "2020-01",
                    "end_date": "2023-06",
                    "location": "SF",
                    "description": "Built things",
                    "responsibilities": [],
                    "achievements": [],
                    "technologies": ["Python"],
                    "is_current": False,
                }
            ],
            "education": [],
            "projects": [],
            "preferences": None,
            "certifications": [],
            "languages": [],
        }

        profile = ProfileLoader.load_from_dict(profile_data)

        assert len(profile.skills) == 1
        assert profile.skills[0].name == "Python"
        assert len(profile.experience) == 1
        assert profile.experience[0].company == "Tech Corp"

    def test_load_invalid_dict(self):
        """Test loading dictionary with invalid field types raises ProfileError."""
        invalid_data = {
            "name": "Test User",
            "skills": "not a list",  # Invalid type
            "experience": "not a list",  # Invalid type
        }

        with pytest.raises(ProfileError) as exc_info:
            ProfileLoader.load_from_dict(invalid_data)

        assert "Invalid profile data" in str(exc_info.value)

    def test_load_empty_dict(self):
        """Test loading empty dictionary raises ProfileError."""
        with pytest.raises(ProfileError) as exc_info:
            ProfileLoader.load_from_dict({})

        assert "Invalid profile data" in str(exc_info.value)


class TestValidateProfile:
    """Test profile validation."""

    def test_validate_profile_with_name_and_skills(self):
        """Test validating profile with name and skills."""
        profile = Profile(
            name="Test User",
            email=None,
            phone=None,
            location=None,
            linkedin_url=None,
            github_url=None,
            portfolio_url=None,
            summary=None,
            years_of_experience=0,
            skills=[
                Skill(name="Python", level="advanced", years_experience=5.0, category="programming")
            ],
            experience=[],
            education=[],
            projects=[],
            preferences=None,
            certifications=[],
            languages=[],
        )

        assert ProfileLoader.validate_profile(profile) is True

    def test_validate_profile_with_name_and_experience(self):
        """Test validating profile with name and experience."""
        profile = Profile(
            name="Test User",
            email=None,
            phone=None,
            location=None,
            linkedin_url=None,
            github_url=None,
            portfolio_url=None,
            summary=None,
            years_of_experience=0,
            skills=[],
            experience=[
                Experience(
                    company="Tech Corp",
                    title="Engineer",
                    start_date="2020-01",
                    end_date="2023-06",
                    location="SF",
                    description="Built things",
                    responsibilities=[],
                    achievements=[],
                    technologies=[],
                    is_current=False,
                )
            ],
            education=[],
            projects=[],
            preferences=None,
            certifications=[],
            languages=[],
        )

        assert ProfileLoader.validate_profile(profile) is True

    def test_validate_profile_with_name_and_summary(self):
        """Test validating profile with name and summary."""
        profile = Profile(
            name="Test User",
            email=None,
            phone=None,
            location=None,
            linkedin_url=None,
            github_url=None,
            portfolio_url=None,
            summary="Software engineer with 5 years experience",
            years_of_experience=5.0,
            skills=[],
            experience=[],
            education=[],
            projects=[],
            preferences=None,
            certifications=[],
            languages=[],
        )

        assert ProfileLoader.validate_profile(profile) is True

    def test_validate_profile_without_name(self):
        """Test validating profile without name fails."""
        profile = Profile(
            name="",  # Empty name
            email=None,
            phone=None,
            location=None,
            linkedin_url=None,
            github_url=None,
            portfolio_url=None,
            summary="Summary",
            years_of_experience=0,
            skills=[],
            experience=[],
            education=[],
            projects=[],
            preferences=None,
            certifications=[],
            languages=[],
        )

        assert ProfileLoader.validate_profile(profile) is False

    def test_validate_profile_without_data(self):
        """Test validating profile without skills/experience/summary fails."""
        profile = Profile(
            name="Test User",
            email=None,
            phone=None,
            location=None,
            linkedin_url=None,
            github_url=None,
            portfolio_url=None,
            summary=None,  # No summary
            years_of_experience=0,
            skills=[],  # No skills
            experience=[],  # No experience
            education=[],
            projects=[],
            preferences=None,
            certifications=[],
            languages=[],
        )

        assert ProfileLoader.validate_profile(profile) is False


class TestSaveToJson:
    """Test saving profile to JSON file."""

    def test_save_valid_profile(self, tmp_path):
        """Test saving valid profile to JSON."""
        profile = Profile(
            name="Test User",
            email="test@example.com",
            phone=None,
            location="SF",
            linkedin_url=None,
            github_url=None,
            portfolio_url=None,
            summary="Engineer",
            years_of_experience=5.0,
            skills=[
                Skill(name="Python", level="advanced", years_experience=5.0, category="programming")
            ],
            experience=[],
            education=[],
            projects=[],
            preferences=None,
            certifications=[],
            languages=["English"],
        )

        json_file = tmp_path / "output.json"
        ProfileLoader.save_to_json(profile, str(json_file))

        # Verify file was created
        assert json_file.exists()

        # Verify content
        with open(json_file, "r") as f:
            data = json.load(f)

        assert data["name"] == "Test User"
        assert data["email"] == "test@example.com"
        assert len(data["skills"]) == 1
        assert data["skills"][0]["name"] == "Python"

    def test_save_creates_parent_directories(self, tmp_path):
        """Test saving creates parent directories if they don't exist."""
        profile = Profile(
            name="Test User",
            email=None,
            phone=None,
            location=None,
            linkedin_url=None,
            github_url=None,
            portfolio_url=None,
            summary=None,
            years_of_experience=0,
            skills=[],
            experience=[],
            education=[],
            projects=[],
            preferences=None,
            certifications=[],
            languages=[],
        )

        json_file = tmp_path / "nested" / "dir" / "profile.json"
        ProfileLoader.save_to_json(profile, str(json_file))

        assert json_file.exists()

    def test_save_with_custom_indent(self, tmp_path):
        """Test saving with custom indentation."""
        profile = Profile(
            name="Test User",
            email=None,
            phone=None,
            location=None,
            linkedin_url=None,
            github_url=None,
            portfolio_url=None,
            summary=None,
            years_of_experience=0,
            skills=[],
            experience=[],
            education=[],
            projects=[],
            preferences=None,
            certifications=[],
            languages=[],
        )

        json_file = tmp_path / "profile.json"
        ProfileLoader.save_to_json(profile, str(json_file), indent=4)

        # Verify file uses 4-space indent
        with open(json_file, "r") as f:
            content = f.read()

        assert "    " in content  # 4 spaces


class TestCreateTemplate:
    """Test creating template profile JSON."""

    def test_create_template(self, tmp_path):
        """Test creating template file."""
        template_file = tmp_path / "template.json"
        ProfileLoader.create_template(str(template_file))

        # Verify file was created
        assert template_file.exists()

        # Verify content structure
        with open(template_file, "r") as f:
            data = json.load(f)

        # Check for key fields
        assert "name" in data
        assert "email" in data
        assert "skills" in data
        assert "experience" in data
        assert "education" in data
        assert "projects" in data
        assert "preferences" in data

        # Check template has example data
        assert data["name"] == "Your Name"
        assert len(data["skills"]) > 0
        assert len(data["experience"]) > 0

    def test_create_template_creates_parent_directories(self, tmp_path):
        """Test template creation creates parent directories."""
        template_file = tmp_path / "nested" / "dir" / "template.json"
        ProfileLoader.create_template(str(template_file))

        assert template_file.exists()

    def test_create_template_can_be_loaded(self, tmp_path):
        """Test that created template can be loaded as a valid profile."""
        template_file = tmp_path / "template.json"
        ProfileLoader.create_template(str(template_file))

        # Should be able to load the template as a valid profile
        profile = ProfileLoader.load_from_json(str(template_file))

        assert isinstance(profile, Profile)
        assert profile.name == "Your Name"
        assert len(profile.skills) > 0
