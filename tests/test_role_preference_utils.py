"""Tests for role preference detection and scoring utilities."""

from job_finder.utils.role_preference_utils import (
    calculate_role_preference_adjustment,
    detect_role_type,
)


class TestDetectRoleType:
    """Test role type detection from job titles."""

    # Preferred engineering/development roles
    def test_detect_software_engineer(self):
        """Test software engineer is detected as preferred."""
        assert detect_role_type("Software Engineer") == "preferred"
        assert detect_role_type("Senior Software Engineer") == "preferred"

    def test_detect_backend_engineer(self):
        """Test backend engineer is detected as preferred."""
        assert detect_role_type("Backend Engineer") == "preferred"
        assert detect_role_type("Senior Backend Engineer") == "preferred"

    def test_detect_frontend_developer(self):
        """Test frontend developer is detected as preferred."""
        assert detect_role_type("Frontend Developer") == "preferred"
        assert detect_role_type("Senior Frontend Developer") == "preferred"

    def test_detect_full_stack_engineer(self):
        """Test full stack engineer is detected as preferred."""
        assert detect_role_type("Full Stack Engineer") == "preferred"
        assert detect_role_type("Full-Stack Developer") == "preferred"

    def test_detect_devops_engineer(self):
        """Test DevOps engineer is detected as preferred."""
        assert detect_role_type("DevOps Engineer") == "preferred"
        assert detect_role_type("Site Reliability Engineer (SRE)") == "preferred"

    def test_detect_cloud_engineer(self):
        """Test cloud engineer is detected as preferred."""
        assert detect_role_type("Cloud Engineer") == "preferred"
        assert detect_role_type("AWS Cloud Engineer") == "preferred"

    def test_detect_data_engineer(self):
        """Test data engineer is detected as preferred."""
        assert detect_role_type("Data Engineer") == "preferred"
        assert detect_role_type("Senior Data Engineer") == "preferred"

    def test_detect_ml_engineer(self):
        """Test ML engineer is detected as preferred."""
        assert detect_role_type("Machine Learning Engineer") == "preferred"
        assert detect_role_type("ML Engineer") == "preferred"

    def test_detect_platform_engineer(self):
        """Test platform engineer is detected as preferred."""
        assert detect_role_type("Platform Engineer") == "preferred"
        assert detect_role_type("Infrastructure Engineer") == "preferred"

    def test_detect_software_architect(self):
        """Test software architect is detected as preferred."""
        assert detect_role_type("Software Architect") == "preferred"
        assert detect_role_type("Solutions Architect") == "preferred"

    # Acceptable lead variants (technical leadership)
    def test_detect_tech_lead(self):
        """Test tech lead is detected as preferred."""
        assert detect_role_type("Tech Lead") == "preferred"
        assert detect_role_type("Technical Lead") == "preferred"

    def test_detect_lead_engineer(self):
        """Test lead engineer is detected as preferred."""
        assert detect_role_type("Lead Engineer") == "preferred"
        assert detect_role_type("Lead Software Engineer") == "preferred"

    def test_detect_engineering_lead(self):
        """Test engineering lead is detected as preferred."""
        assert detect_role_type("Engineering Lead") == "preferred"
        assert detect_role_type("Development Lead") == "preferred"

    def test_detect_lead_developer(self):
        """Test lead developer is detected as preferred."""
        assert detect_role_type("Lead Developer") == "preferred"

    # Less desirable management roles
    def test_detect_engineering_manager(self):
        """Test engineering manager is detected as less desirable."""
        assert detect_role_type("Engineering Manager") == "less_desirable"
        assert detect_role_type("Software Engineering Manager") == "less_desirable"

    def test_detect_director(self):
        """Test director is detected as less desirable."""
        assert detect_role_type("Director of Engineering") == "less_desirable"
        assert detect_role_type("Engineering Director") == "less_desirable"

    def test_detect_vp(self):
        """Test VP is detected as less desirable."""
        assert detect_role_type("VP of Engineering") == "less_desirable"
        assert detect_role_type("Vice President, Technology") == "less_desirable"

    def test_detect_head_of(self):
        """Test head of is detected as less desirable."""
        assert detect_role_type("Head of Engineering") == "less_desirable"
        assert detect_role_type("Head of Product") == "less_desirable"

    def test_detect_cto(self):
        """Test CTO is detected as less desirable."""
        assert detect_role_type("CTO") == "less_desirable"
        assert detect_role_type("Chief Technology Officer") == "less_desirable"

    # Product management roles
    def test_detect_product_manager(self):
        """Test product manager is detected as less desirable."""
        assert detect_role_type("Product Manager") == "less_desirable"
        assert detect_role_type("Senior Product Manager") == "less_desirable"

    def test_detect_program_manager(self):
        """Test program manager is detected as less desirable."""
        assert detect_role_type("Program Manager") == "less_desirable"
        assert detect_role_type("Technical Program Manager") == "less_desirable"

    def test_detect_project_manager(self):
        """Test project manager is detected as less desirable."""
        assert detect_role_type("Project Manager") == "less_desirable"

    # Sales/business development roles
    def test_detect_sales(self):
        """Test sales roles are detected as less desirable."""
        assert detect_role_type("Sales Engineer") == "less_desirable"
        assert detect_role_type("Account Executive") == "less_desirable"

    def test_detect_business_development(self):
        """Test business development is detected as less desirable."""
        assert detect_role_type("Business Development Manager") == "less_desirable"
        assert detect_role_type("BD Representative") == "less_desirable"

    def test_detect_account_manager(self):
        """Test account manager is detected as less desirable."""
        assert detect_role_type("Account Manager") == "less_desirable"
        assert detect_role_type("Strategic Account Manager") == "less_desirable"

    # Recruiting roles
    def test_detect_recruiter(self):
        """Test recruiter is detected as less desirable."""
        assert detect_role_type("Technical Recruiter") == "less_desirable"
        assert detect_role_type("Talent Acquisition Specialist") == "less_desirable"

    # Analyst roles (non-engineering)
    def test_detect_business_analyst(self):
        """Test business analyst is detected as less desirable."""
        assert detect_role_type("Business Analyst") == "less_desirable"
        assert detect_role_type("Data Analyst") == "less_desirable"

    # Support roles
    def test_detect_support_engineer(self):
        """Test support engineer is ambiguous but success engineer is less desirable."""
        # "Support Engineer" has both "support engineer" (less desirable) and "engineer" (preferred)
        # Equal matches result in None
        assert detect_role_type("Support Engineer") is None
        # "Customer Success Engineer" has "customer success" AND "success engineer"
        # (2 less desirable matches) vs "engineer" (1 preferred), so less_desirable wins
        assert detect_role_type("Customer Success Engineer") == "less_desirable"

    # Consultant roles
    def test_detect_consultant(self):
        """Test consultant is detected as less desirable."""
        assert detect_role_type("Technical Consultant") == "less_desirable"
        assert detect_role_type("Solutions Consultant") == "less_desirable"

    # Designer roles
    def test_detect_designer(self):
        """Test designer is detected as less desirable."""
        assert detect_role_type("UX Designer") == "less_desirable"
        assert detect_role_type("Product Designer") == "less_desirable"

    # Marketing roles
    def test_detect_marketing(self):
        """Test marketing roles are detected as less desirable."""
        assert detect_role_type("Marketing Manager") == "less_desirable"
        assert detect_role_type("Technical Marketing Engineer") == "less_desirable"

    # Edge cases - role-defining keywords take precedence
    def test_manager_overrides_engineer(self):
        """Test manager keyword overrides engineer."""
        # "Engineering Manager" has both "engineering" and "manager"
        # but "manager" is role-defining so it's less_desirable
        assert detect_role_type("Engineering Manager") == "less_desirable"

    def test_director_overrides_technical(self):
        """Test director keyword overrides technical."""
        assert detect_role_type("Director of Engineering") == "less_desirable"

    def test_sales_overrides_engineer(self):
        """Test sales keyword overrides engineer."""
        assert detect_role_type("Sales Engineer") == "less_desirable"

    # Acceptable lead variants override generic "lead"
    def test_tech_lead_overrides_lead_penalty(self):
        """Test tech lead is preferred despite having 'lead'."""
        # "lead" alone is in LESS_DESIRABLE_KEYWORDS
        # but "tech lead" is in ACCEPTABLE_LEAD_VARIANTS
        assert detect_role_type("Tech Lead") == "preferred"

    def test_lead_engineer_overrides_lead_penalty(self):
        """Test lead engineer is preferred."""
        assert detect_role_type("Lead Engineer") == "preferred"

    # Neutral/unknown roles
    def test_unknown_role_returns_none(self):
        """Test unknown role returns None."""
        assert detect_role_type("Unicorn Wrangler") is None
        assert detect_role_type("Happiness Specialist") is None
        assert detect_role_type("Growth Hacker") is None

    def test_empty_title_returns_none(self):
        """Test empty title returns None."""
        assert detect_role_type("") is None

    # Case insensitivity
    def test_case_insensitive_detection(self):
        """Test role detection is case-insensitive."""
        assert detect_role_type("SOFTWARE ENGINEER") == "preferred"
        assert detect_role_type("software engineer") == "preferred"
        assert detect_role_type("Software Engineer") == "preferred"

    # Multiple preferred keywords
    def test_multiple_preferred_keywords(self):
        """Test multiple preferred keywords."""
        assert detect_role_type("Senior Backend Software Engineer") == "preferred"
        assert detect_role_type("Full Stack DevOps Engineer") == "preferred"

    # Ambiguous roles (should return None or less_desirable based on matches)
    def test_ambiguous_role_with_equal_matches(self):
        """Test ambiguous role with mixed keywords."""
        # This is tricky - depends on how keywords match
        # Just verify it doesn't crash and returns something
        result = detect_role_type("Technical Lead Manager")
        assert result in ["preferred", "less_desirable", None]


class TestCalculateRolePreferenceAdjustment:
    """Test role preference score adjustments."""

    # Preferred roles (+5)
    def test_software_engineer_bonus(self):
        """Test software engineer gets bonus."""
        adjustment, description = calculate_role_preference_adjustment("Software Engineer")
        assert adjustment == 5
        assert "Engineering" in description or "Developer" in description
        assert "+5" in description

    def test_backend_developer_bonus(self):
        """Test backend developer gets bonus."""
        adjustment, description = calculate_role_preference_adjustment("Backend Developer")
        assert adjustment == 5
        assert "+5" in description

    def test_tech_lead_bonus(self):
        """Test tech lead gets bonus."""
        adjustment, description = calculate_role_preference_adjustment("Tech Lead")
        assert adjustment == 5
        assert "+5" in description

    def test_data_engineer_bonus(self):
        """Test data engineer gets bonus."""
        adjustment, description = calculate_role_preference_adjustment("Data Engineer")
        assert adjustment == 5
        assert "+5" in description

    # Less desirable roles (-25)
    def test_engineering_manager_penalty(self):
        """Test engineering manager gets penalty."""
        adjustment, description = calculate_role_preference_adjustment("Engineering Manager")
        assert adjustment == -25
        assert "Management" in description or "Sales" in description
        assert "-25" in description

    def test_product_manager_penalty(self):
        """Test product manager gets penalty."""
        adjustment, description = calculate_role_preference_adjustment("Product Manager")
        assert adjustment == -25
        assert "-25" in description

    def test_director_penalty(self):
        """Test director gets penalty."""
        adjustment, description = calculate_role_preference_adjustment("Director of Engineering")
        assert adjustment == -25
        assert "-25" in description

    def test_sales_engineer_penalty(self):
        """Test sales engineer gets penalty."""
        adjustment, description = calculate_role_preference_adjustment("Sales Engineer")
        assert adjustment == -25
        assert "-25" in description

    def test_recruiter_penalty(self):
        """Test recruiter gets penalty."""
        adjustment, description = calculate_role_preference_adjustment("Technical Recruiter")
        assert adjustment == -25
        assert "-25" in description

    # Neutral roles (0)
    def test_unknown_role_neutral(self):
        """Test unknown role is neutral."""
        adjustment, description = calculate_role_preference_adjustment("Unknown Role")
        assert adjustment == 0
        assert "Neutral" in description

    def test_empty_title_neutral(self):
        """Test empty title is neutral."""
        adjustment, description = calculate_role_preference_adjustment("")
        assert adjustment == 0
        assert "Neutral" in description

    # Real-world examples
    def test_senior_staff_engineer(self):
        """Test senior/staff engineer gets bonus."""
        adjustment, _ = calculate_role_preference_adjustment("Senior Staff Software Engineer")
        assert adjustment == 5

    def test_vp_engineering(self):
        """Test VP Engineering gets penalty."""
        adjustment, _ = calculate_role_preference_adjustment("VP of Engineering")
        assert adjustment == -25

    def test_lead_software_engineer(self):
        """Test lead software engineer gets bonus."""
        adjustment, _ = calculate_role_preference_adjustment("Lead Software Engineer")
        assert adjustment == 5

    def test_technical_program_manager(self):
        """Test technical program manager gets penalty."""
        adjustment, _ = calculate_role_preference_adjustment("Technical Program Manager")
        assert adjustment == -25
