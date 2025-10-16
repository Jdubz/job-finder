"""Tests for profile schema utility methods."""

from job_finder.profile.schema import Experience, Profile, Project, Skill


class TestProfileUtilityMethods:
    """Test utility methods on Profile model."""

    def test_get_all_skills(self):
        """Test getting all skills from profile."""
        profile = Profile(
            name="Test User",
            skills=[
                Skill(name="Python", level="expert"),
                Skill(name="JavaScript", level="advanced"),
            ],
            experience=[
                Experience(
                    company="Tech Corp",
                    title="Senior Engineer",
                    start_date="2020-01",
                    technologies=["Django", "React", "Python"],
                )
            ],
            projects=[
                Project(
                    name="Cool Project",
                    description="A cool project",
                    technologies=["TypeScript", "React", "Node.js"],
                )
            ],
        )

        all_skills = profile.get_all_skills()

        # Should include skills from all sources (skills, experience, projects)
        assert "Python" in all_skills
        assert "JavaScript" in all_skills
        assert "Django" in all_skills
        assert "React" in all_skills
        assert "TypeScript" in all_skills
        assert "Node.js" in all_skills

        # Should be sorted
        assert all_skills == sorted(all_skills)

        # Should not have duplicates (React appears in both experience and projects)
        assert all_skills.count("React") == 1

    def test_get_all_skills_empty_profile(self):
        """Test getting skills from empty profile."""
        profile = Profile(name="Test User")
        assert profile.get_all_skills() == []

    def test_get_current_role(self):
        """Test getting current employment."""
        profile = Profile(
            name="Test User",
            experience=[
                Experience(
                    company="Old Corp",
                    title="Junior Engineer",
                    start_date="2018-01",
                    end_date="2020-01",
                    is_current=False,
                ),
                Experience(
                    company="Current Corp",
                    title="Senior Engineer",
                    start_date="2020-01",
                    is_current=True,
                ),
            ],
        )

        current = profile.get_current_role()

        assert current is not None
        assert current.company == "Current Corp"
        assert current.title == "Senior Engineer"
        assert current.is_current is True

    def test_get_current_role_none(self):
        """Test getting current role when no current employment."""
        profile = Profile(
            name="Test User",
            experience=[
                Experience(
                    company="Old Corp",
                    title="Engineer",
                    start_date="2018-01",
                    end_date="2020-01",
                    is_current=False,
                )
            ],
        )

        assert profile.get_current_role() is None

    def test_get_current_role_empty_experience(self):
        """Test getting current role with no experience."""
        profile = Profile(name="Test User")
        assert profile.get_current_role() is None

    def test_get_experience_by_company(self):
        """Test getting experience for specific company."""
        profile = Profile(
            name="Test User",
            experience=[
                Experience(
                    company="Tech Corp",
                    title="Junior Engineer",
                    start_date="2018-01",
                    end_date="2019-01",
                ),
                Experience(
                    company="Tech Corp",
                    title="Senior Engineer",
                    start_date="2019-01",
                    end_date="2021-01",
                ),
                Experience(
                    company="Other Corp",
                    title="Staff Engineer",
                    start_date="2021-01",
                ),
            ],
        )

        tech_corp_exp = profile.get_experience_by_company("Tech Corp")

        assert len(tech_corp_exp) == 2
        assert all(exp.company == "Tech Corp" for exp in tech_corp_exp)
        assert tech_corp_exp[0].title == "Junior Engineer"
        assert tech_corp_exp[1].title == "Senior Engineer"

    def test_get_experience_by_company_case_insensitive(self):
        """Test company name matching is case-insensitive."""
        profile = Profile(
            name="Test User",
            experience=[
                Experience(
                    company="Tech Corp",
                    title="Engineer",
                    start_date="2020-01",
                )
            ],
        )

        # Should match regardless of case
        assert len(profile.get_experience_by_company("tech corp")) == 1
        assert len(profile.get_experience_by_company("TECH CORP")) == 1
        assert len(profile.get_experience_by_company("Tech Corp")) == 1

    def test_get_experience_by_company_not_found(self):
        """Test getting experience for non-existent company."""
        profile = Profile(
            name="Test User",
            experience=[
                Experience(
                    company="Tech Corp",
                    title="Engineer",
                    start_date="2020-01",
                )
            ],
        )

        assert profile.get_experience_by_company("Other Corp") == []
