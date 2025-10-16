"""Tests for job type and seniority filtering."""

import pytest

from job_finder.utils.job_type_filter import (
    FilterDecision,
    check_job_type_filter,
    check_seniority_filter,
    filter_job,
    has_engineering_role_keyword,
    is_acceptable_data_role,
    is_acceptable_lead_role,
)


class TestEngineeringRoleDetection:
    """Test detection of engineering role keywords."""

    def test_has_engineering_keywords(self):
        """Test titles with engineering keywords are detected."""
        assert has_engineering_role_keyword("Senior Software Engineer")
        assert has_engineering_role_keyword("Backend Developer")
        assert has_engineering_role_keyword("Python Programmer")
        assert has_engineering_role_keyword("Solutions Architect")
        assert has_engineering_role_keyword("SRE - Site Reliability Engineer")
        assert has_engineering_role_keyword("DevOps Engineer")

    def test_no_engineering_keywords(self):
        """Test titles without engineering keywords are detected."""
        assert not has_engineering_role_keyword("Product Manager")
        # Sales Engineer contains "engineer" so it HAS engineering keywords
        # (it gets rejected for containing "sales" instead)
        assert not has_engineering_role_keyword("Technical Writer")
        assert not has_engineering_role_keyword("Data Analyst")


class TestAcceptableLeadRoles:
    """Test detection of acceptable lead role variants."""

    def test_acceptable_lead_variants(self):
        """Test that acceptable lead variants are detected."""
        assert is_acceptable_lead_role("Tech Lead")
        assert is_acceptable_lead_role("Technical Lead")
        assert is_acceptable_lead_role("Lead Engineer")
        assert is_acceptable_lead_role("Lead Software Engineer")
        assert is_acceptable_lead_role("Engineering Lead")
        assert is_acceptable_lead_role("Development Lead")
        assert is_acceptable_lead_role("Lead Developer")

    def test_unacceptable_lead_roles(self):
        """Test that management lead roles are not accepted."""
        assert not is_acceptable_lead_role("Team Lead")
        assert not is_acceptable_lead_role("Project Lead")
        assert not is_acceptable_lead_role("Product Lead")
        assert not is_acceptable_lead_role("Engineering Manager")


class TestAcceptableDataRoles:
    """Test detection of acceptable data/ML engineering roles."""

    def test_acceptable_data_engineering_roles(self):
        """Test that data engineering roles are accepted."""
        assert is_acceptable_data_role("Data Engineer")
        assert is_acceptable_data_role("ML Engineer")
        assert is_acceptable_data_role("Machine Learning Engineer")
        assert is_acceptable_data_role("AI Engineer")
        assert is_acceptable_data_role("Analytics Engineer")
        assert is_acceptable_data_role("MLOps Engineer")

    def test_unacceptable_data_roles(self):
        """Test that data analytics roles are not accepted."""
        assert not is_acceptable_data_role("Data Analyst")
        assert not is_acceptable_data_role("Data Scientist")
        assert not is_acceptable_data_role("Business Analyst")
        assert not is_acceptable_data_role("Business Intelligence Analyst")


class TestJobTypeFiltering:
    """Test job type filtering logic."""

    def test_accept_engineering_roles(self):
        """Test that engineering roles are accepted."""
        decision, _ = check_job_type_filter("Senior Software Engineer")
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_job_type_filter("Backend Developer")
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_job_type_filter("Full Stack Engineer")
        assert decision == FilterDecision.ACCEPT

    def test_reject_management_roles(self):
        """Test that management roles are rejected."""
        decision, reason = check_job_type_filter("Engineering Manager")
        assert decision == FilterDecision.REJECT
        assert "manager" in reason.lower()

        decision, reason = check_job_type_filter("Director of Engineering")
        assert decision == FilterDecision.REJECT
        assert "director" in reason.lower()

        decision, reason = check_job_type_filter("VP of Engineering")
        assert decision == FilterDecision.REJECT

    def test_reject_sales_roles(self):
        """Test that sales roles are rejected."""
        decision, reason = check_job_type_filter("Sales Engineer")
        assert decision == FilterDecision.REJECT
        assert "sales" in reason.lower()

        decision, reason = check_job_type_filter("Account Executive")
        assert decision == FilterDecision.REJECT

        decision, reason = check_job_type_filter("Business Development Representative")
        assert decision == FilterDecision.REJECT

    def test_reject_product_management(self):
        """Test that product management roles are rejected."""
        decision, reason = check_job_type_filter("Product Manager")
        assert decision == FilterDecision.REJECT
        # Could be rejected for "manager" or "product manager" - both are valid
        assert "manager" in reason.lower()

        decision, reason = check_job_type_filter("Technical Product Manager")
        assert decision == FilterDecision.REJECT

        decision, reason = check_job_type_filter("Program Manager")
        assert decision == FilterDecision.REJECT

    def test_reject_product_owner(self):
        """Test that Product Owner (no 'manager' in title) is rejected."""
        decision, reason = check_job_type_filter("Product Owner")
        assert decision == FilterDecision.REJECT
        assert "product" in reason.lower() or "management" in reason.lower()

    def test_reject_scrum_master(self):
        """Test that Scrum Master is rejected for product management."""
        decision, reason = check_job_type_filter("Scrum Master")
        assert decision == FilterDecision.REJECT
        # Should be rejected for product management keywords
        assert (
            "product" in reason.lower()
            or "program" in reason.lower()
            or "management" in reason.lower()
        )

    def test_reject_recruiting_roles(self):
        """Test that recruiting roles are rejected."""
        decision, reason = check_job_type_filter("Technical Recruiter")
        assert decision == FilterDecision.REJECT
        assert "recruit" in reason.lower()

        decision, reason = check_job_type_filter("Talent Acquisition Specialist")
        assert decision == FilterDecision.REJECT

    def test_reject_data_analytics(self):
        """Test that data analytics roles are rejected."""
        decision, reason = check_job_type_filter("Data Analyst")
        assert decision == FilterDecision.REJECT
        assert "data analyst" in reason.lower()

        decision, reason = check_job_type_filter("Business Analyst")
        assert decision == FilterDecision.REJECT

        decision, reason = check_job_type_filter("Business Intelligence Analyst")
        assert decision == FilterDecision.REJECT

    def test_accept_data_engineering(self):
        """Test that data engineering roles are accepted."""
        decision, _ = check_job_type_filter("Data Engineer")
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_job_type_filter("ML Engineer")
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_job_type_filter("Machine Learning Engineer")
        assert decision == FilterDecision.ACCEPT

    def test_accept_technical_lead_variants(self):
        """Test that acceptable lead variants are accepted."""
        decision, _ = check_job_type_filter("Tech Lead")
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_job_type_filter("Lead Software Engineer")
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_job_type_filter("Engineering Lead")
        assert decision == FilterDecision.ACCEPT

    def test_reject_other_non_engineering(self):
        """Test that other non-engineering roles are rejected."""
        decision, reason = check_job_type_filter("UX Designer")
        assert decision == FilterDecision.REJECT

        decision, reason = check_job_type_filter("Technical Writer")
        assert decision == FilterDecision.REJECT

        decision, reason = check_job_type_filter("DevOps Consultant")
        assert decision == FilterDecision.REJECT

    def test_strict_mode_requires_engineering_keywords(self):
        """Test that strict mode requires engineering keywords."""
        # Strict mode ON (default) - "Systems Analyst" gets rejected for "analyst" first
        decision, reason = check_job_type_filter("Systems Analyst", strict=True)
        assert decision == FilterDecision.REJECT
        # Rejected for analyst keyword, not for missing engineering keywords
        assert "analyst" in reason.lower()

        # Strict mode OFF - should still reject for "analyst"
        decision, _ = check_job_type_filter("Systems Analyst", strict=False)
        assert decision == FilterDecision.REJECT

        # Test a role with no engineering keywords and no blocked keywords
        decision, reason = check_job_type_filter("QA Tester", strict=True)
        assert decision == FilterDecision.REJECT
        assert "no engineering" in reason.lower()

        # Strict mode OFF - should allow QA Tester
        decision, _ = check_job_type_filter("QA Tester", strict=False)
        assert decision == FilterDecision.ACCEPT


class TestSeniorityFiltering:
    """Test seniority filtering logic."""

    def test_block_junior_roles(self):
        """Test that junior/entry-level roles are always blocked."""
        decision, reason = check_seniority_filter("Junior Software Engineer")
        assert decision == FilterDecision.REJECT
        assert "junior" in reason.lower()

        decision, reason = check_seniority_filter("Software Engineer Intern")
        assert decision == FilterDecision.REJECT
        assert "intern" in reason.lower()

        decision, reason = check_seniority_filter("Associate Software Engineer")
        assert decision == FilterDecision.REJECT
        assert "associate" in reason.lower()

        decision, reason = check_seniority_filter("Entry Level Developer")
        assert decision == FilterDecision.REJECT

        decision, reason = check_seniority_filter("Software Engineer I")
        assert decision == FilterDecision.REJECT

    def test_accept_senior_roles_with_no_min_requirement(self):
        """Test that senior roles are accepted when no minimum is set."""
        decision, _ = check_seniority_filter("Senior Software Engineer", min_seniority=None)
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_seniority_filter("Staff Engineer", min_seniority=None)
        assert decision == FilterDecision.ACCEPT

    def test_accept_mid_level_with_no_min_requirement(self):
        """Test that mid-level roles (no seniority indicator) are accepted."""
        decision, _ = check_seniority_filter("Software Engineer", min_seniority=None)
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_seniority_filter("Backend Developer", min_seniority=None)
        assert decision == FilterDecision.ACCEPT

    def test_require_senior_level(self):
        """Test that requiring senior level filters out mid-level roles."""
        # Should reject mid-level (no senior indicator)
        decision, reason = check_seniority_filter("Software Engineer", min_seniority="senior")
        assert decision == FilterDecision.REJECT
        assert "minimum seniority" in reason.lower()

        # Should accept senior+
        decision, _ = check_seniority_filter("Senior Software Engineer", min_seniority="senior")
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_seniority_filter("Staff Engineer", min_seniority="senior")
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_seniority_filter("Principal Engineer", min_seniority="senior")
        assert decision == FilterDecision.ACCEPT

    def test_require_staff_level(self):
        """Test that requiring staff level filters out senior roles."""
        # Should reject senior (not staff+)
        decision, reason = check_seniority_filter("Senior Software Engineer", min_seniority="staff")
        assert decision == FilterDecision.REJECT

        # Should accept staff+
        decision, _ = check_seniority_filter("Staff Engineer", min_seniority="staff")
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_seniority_filter("Principal Engineer", min_seniority="staff")
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_seniority_filter("Distinguished Engineer", min_seniority="staff")
        assert decision == FilterDecision.ACCEPT

    def test_require_principal_level(self):
        """Test that requiring principal level filters out staff roles."""
        # Should reject staff
        decision, reason = check_seniority_filter("Staff Engineer", min_seniority="principal")
        assert decision == FilterDecision.REJECT

        # Should accept principal+
        decision, _ = check_seniority_filter("Principal Engineer", min_seniority="principal")
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_seniority_filter("Distinguished Engineer", min_seniority="principal")
        assert decision == FilterDecision.ACCEPT

    def test_require_distinguished_level(self):
        """Test that requiring distinguished level filters out principal roles."""
        # Should reject principal (doesn't meet distinguished requirement)
        decision, reason = check_seniority_filter(
            "Principal Engineer", min_seniority="distinguished"
        )
        assert decision == FilterDecision.REJECT
        assert "minimum seniority" in reason.lower()

        # Should accept distinguished/fellow
        decision, _ = check_seniority_filter(
            "Distinguished Engineer", min_seniority="distinguished"
        )
        assert decision == FilterDecision.ACCEPT

        decision, _ = check_seniority_filter("Fellow", min_seniority="distinguished")
        assert decision == FilterDecision.ACCEPT


class TestCombinedFiltering:
    """Test combined job type and seniority filtering."""

    def test_accept_senior_engineering_role(self):
        """Test that senior engineering roles pass all filters."""
        decision, _ = filter_job(
            "Senior Software Engineer", strict_role_filter=True, min_seniority="senior"
        )
        assert decision == FilterDecision.ACCEPT

    def test_reject_junior_engineering_role(self):
        """Test that junior engineering roles are rejected."""
        decision, reason = filter_job(
            "Junior Software Engineer", strict_role_filter=True, min_seniority=None
        )
        assert decision == FilterDecision.REJECT
        assert "junior" in reason.lower()

    def test_reject_senior_non_engineering_role(self):
        """Test that senior non-engineering roles are rejected."""
        decision, reason = filter_job(
            "Senior Product Manager", strict_role_filter=True, min_seniority="senior"
        )
        assert decision == FilterDecision.REJECT
        # Could be rejected for "manager" or "product manager"
        assert "manager" in reason.lower()

    def test_reject_mid_level_when_senior_required(self):
        """Test that mid-level engineering roles are rejected when senior is required."""
        decision, reason = filter_job(
            "Software Engineer", strict_role_filter=True, min_seniority="senior"
        )
        assert decision == FilterDecision.REJECT
        assert "minimum seniority" in reason.lower()

    def test_accept_staff_data_engineer(self):
        """Test that staff-level data engineering roles are accepted."""
        decision, _ = filter_job(
            "Staff Data Engineer", strict_role_filter=True, min_seniority="staff"
        )
        assert decision == FilterDecision.ACCEPT

    def test_reject_role_without_engineering_keywords_strict(self):
        """Test that roles without engineering keywords are rejected in strict mode."""
        decision, reason = filter_job(
            "Senior Consultant", strict_role_filter=True, min_seniority=None
        )
        assert decision == FilterDecision.REJECT
        # Could be rejected for either consultant keyword or no engineering keywords
        assert "consultant" in reason.lower() or "no engineering" in reason.lower()


class TestRealWorldExamples:
    """Test with real-world job title examples."""

    @pytest.mark.parametrize(
        "title,should_accept",
        [
            # Should ACCEPT
            ("Senior Software Engineer", True),
            ("Staff Backend Engineer", True),
            ("Principal Engineer", True),
            ("Lead Software Engineer", True),
            ("Tech Lead", True),
            ("Senior Data Engineer", True),  # Changed: requires "Senior" prefix
            ("Senior ML Engineer", True),  # Changed: requires "Senior" prefix
            ("Senior DevOps Engineer", True),
            ("Staff Site Reliability Engineer (SRE)", True),
            ("Senior Full Stack Developer", True),
            # Should REJECT
            ("Junior Software Engineer", False),
            ("Software Engineer Intern", False),
            ("Engineering Manager", False),
            ("Senior Engineering Manager", False),
            ("Director of Engineering", False),
            ("VP of Engineering", False),
            ("Product Manager", False),
            ("Technical Product Manager", False),
            ("Program Manager", False),
            ("Data Analyst", False),
            ("Senior Data Analyst", False),
            ("Business Analyst", False),
            ("Sales Engineer", False),
            ("Solutions Engineer", False),  # Sales-oriented
            ("Technical Recruiter", False),
            ("UX Designer", False),
            ("Technical Writer", False),
            ("DevOps Consultant", False),
            ("Customer Success Engineer", False),
        ],
    )
    def test_real_world_titles(self, title, should_accept):
        """Test filtering with real-world job titles."""
        decision, reason = filter_job(title, strict_role_filter=True, min_seniority="senior")

        if should_accept:
            assert (
                decision == FilterDecision.ACCEPT
            ), f"Expected to accept '{title}' but got rejection: {reason}"
        else:
            assert (
                decision == FilterDecision.REJECT
            ), f"Expected to reject '{title}' but it was accepted"
