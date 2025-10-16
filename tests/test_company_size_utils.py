"""Tests for company size detection and scoring utilities."""

from job_finder.utils.company_size_utils import (
    calculate_company_size_adjustment,
    detect_company_size,
)


class TestDetectCompanySize:
    """Test company size detection."""

    # Known large companies
    def test_detect_google_as_large(self):
        """Test Google is detected as large company."""
        assert detect_company_size("Google") == "large"
        assert detect_company_size("Google LLC") == "large"
        assert detect_company_size("Alphabet Inc.") == "large"

    def test_detect_microsoft_as_large(self):
        """Test Microsoft is detected as large company."""
        assert detect_company_size("Microsoft") == "large"
        assert detect_company_size("Microsoft Corporation") == "large"

    def test_detect_apple_as_large(self):
        """Test Apple is detected as large company."""
        assert detect_company_size("Apple") == "large"
        assert detect_company_size("Apple Inc.") == "large"

    def test_detect_amazon_as_large(self):
        """Test Amazon is detected as large company."""
        assert detect_company_size("Amazon") == "large"
        assert detect_company_size("Amazon.com") == "large"
        assert detect_company_size("AWS") == "large"

    def test_detect_meta_as_large(self):
        """Test Meta/Facebook is detected as large company."""
        assert detect_company_size("Meta") == "large"
        assert detect_company_size("Facebook") == "large"

    def test_detect_financial_companies_as_large(self):
        """Test major financial companies are detected as large."""
        assert detect_company_size("Goldman Sachs") == "large"
        assert detect_company_size("JPMorgan") == "large"
        assert detect_company_size("Morgan Stanley") == "large"

    def test_detect_enterprise_software_as_large(self):
        """Test enterprise software companies are detected as large."""
        assert detect_company_size("Salesforce") == "large"
        assert detect_company_size("Oracle") == "large"
        assert detect_company_size("SAP") == "large"

    # Large company patterns
    def test_detect_fortune_500_pattern(self):
        """Test Fortune 500 pattern detection."""
        result = detect_company_size(
            "Unknown Corp", company_info="Fortune 500 company with global presence"
        )
        assert result == "large"

    def test_detect_employee_count_pattern(self):
        """Test large employee count pattern."""
        result = detect_company_size(
            "BigCorp", company_info="Company with 10,000+ employees worldwide"
        )
        assert result == "large"

    def test_detect_publicly_traded_pattern(self):
        """Test publicly traded pattern."""
        result = detect_company_size("TechCo", company_info="Publicly traded on NYSE")
        assert result == "large"

    def test_detect_multinational_pattern(self):
        """Test multinational pattern."""
        result = detect_company_size(
            "GlobalTech", company_info="Multinational corporation with offices worldwide"
        )
        assert result == "large"

    def test_detect_sp500_pattern(self):
        """Test S&P 500 pattern."""
        result = detect_company_size("FinCo", company_info="S&P 500 listed company")
        assert result == "large"

    # Small company patterns
    def test_detect_startup_pattern(self):
        """Test startup pattern detection."""
        result = detect_company_size("NewCo", company_info="Fast-growing startup in Series A")
        assert result == "small"

    def test_detect_seed_funding_pattern(self):
        """Test seed funding pattern."""
        result = detect_company_size("StartupCo", company_info="Seed stage startup")
        assert result == "small"

    def test_detect_early_stage_pattern(self):
        """Test early-stage pattern."""
        result = detect_company_size("EarlyCo", company_info="Early-stage company looking to grow")
        assert result == "small"

    def test_detect_bootstrapped_pattern(self):
        """Test bootstrapped pattern."""
        result = detect_company_size("IndieComp", company_info="Bootstrapped company, profitable")
        assert result == "small"

    def test_detect_small_team_pattern(self):
        """Test small team pattern."""
        result = detect_company_size("TinyTech", company_info="Small team of 25 employees")
        assert result == "small"

    def test_detect_series_a_funding(self):
        """Test Series A funding pattern."""
        result = detect_company_size("FundedCo", company_info="Recently raised Series A funding")
        assert result == "small"

    def test_detect_series_b_funding(self):
        """Test Series B funding pattern."""
        result = detect_company_size(
            "GrowthCo", company_info="Series B funding round, scaling rapidly"
        )
        assert result == "small"

    # Medium company patterns
    def test_detect_mid_sized_pattern(self):
        """Test mid-sized pattern."""
        result = detect_company_size("MidCo", company_info="Mid-sized company with 500 employees")
        assert result == "medium"

    def test_detect_growing_company_pattern(self):
        """Test growing company pattern."""
        result = detect_company_size(
            "GrowCo", company_info="Growing company expanding into new markets"
        )
        assert result == "medium"

    def test_detect_series_c_funding(self):
        """Test Series C funding pattern."""
        result = detect_company_size(
            "MatureCo", company_info="Series C funding round, 300 employees"
        )
        assert result == "medium"

    def test_detect_hundreds_of_employees(self):
        """Test hundreds of employees pattern."""
        result = detect_company_size("EstablishedCo", company_info="Hundreds of employees globally")
        assert result == "medium"

    # Multiple pattern matches
    def test_multiple_large_patterns(self):
        """Test multiple large company patterns."""
        result = detect_company_size(
            "MegaCorp",
            company_info="Fortune 500 company, publicly traded, thousands of employees",
        )
        assert result == "large"

    def test_multiple_small_patterns(self):
        """Test multiple small company patterns."""
        result = detect_company_size(
            "NewStartup", company_info="Early-stage startup, seed funded, small team of 15"
        )
        assert result == "small"

    # Conflicting patterns (tie-breaking)
    def test_single_large_pattern_wins_over_none(self):
        """Test single large pattern with no small patterns."""
        result = detect_company_size("UnknownCo", company_info="Fortune 500 listed")
        assert result == "large"

    def test_single_small_pattern_wins_over_none(self):
        """Test single small pattern with no large patterns."""
        result = detect_company_size("UnknownStartup", company_info="Bootstrapped company")
        assert result == "small"

    def test_large_patterns_win_in_tie(self):
        """Test large patterns win when more than others."""
        result = detect_company_size(
            "CompanyXYZ",
            company_info="Fortune 500, publicly traded startup",  # 2 large, 1 small
        )
        assert result == "large"

    # Text in job description
    def test_detect_from_job_description(self):
        """Test company size detected from job description."""
        result = detect_company_size(
            "TechCorp",
            company_info="",
            description="Join our Fortune 500 tech company with global offices",
        )
        assert result == "large"

    def test_detect_startup_from_description(self):
        """Test startup detected from job description."""
        result = detect_company_size(
            "NewCo",
            company_info="",
            description="Join our early-stage startup building innovative solutions",
        )
        assert result == "small"

    # Combined text analysis
    def test_detect_from_combined_sources(self):
        """Test detection using all text sources."""
        result = detect_company_size(
            company_name="TechStartup",
            company_info="Seed funded company",
            description="Small team of passionate builders",
        )
        assert result == "small"

    # Edge cases
    def test_empty_inputs_returns_none(self):
        """Test empty inputs return None."""
        assert detect_company_size("") is None
        assert detect_company_size("", "", "") is None

    def test_unknown_company_returns_none(self):
        """Test unknown company without patterns returns None."""
        result = detect_company_size(
            "RandomCo", company_info="We build software", description="Job opportunity"
        )
        assert result is None

    def test_case_insensitive_detection(self):
        """Test detection is case-insensitive."""
        assert detect_company_size("GOOGLE") == "large"
        assert detect_company_size("google") == "large"
        assert detect_company_size("Google") == "large"

    def test_partial_company_name_match(self):
        """Test partial company name matches work."""
        assert detect_company_size("Google LLC") == "large"
        assert detect_company_size("Microsoft Corporation") == "large"
        assert detect_company_size("Amazon.com, Inc.") == "large"

    # Real-world examples
    def test_netflix_detected_as_large(self):
        """Test Netflix is detected as large."""
        assert detect_company_size("Netflix") == "large"

    def test_stripe_detected_as_large(self):
        """Test Stripe is detected as large."""
        assert detect_company_size("Stripe") == "large"

    def test_uber_detected_as_large(self):
        """Test Uber is detected as large."""
        assert detect_company_size("Uber") == "large"

    def test_pre_seed_startup_detected(self):
        """Test pre-seed startup is detected as small."""
        result = detect_company_size("PreSeedCo", company_info="Pre-seed stage, 5 employees")
        assert result == "small"


class TestCalculateCompanySizeAdjustment:
    """Test company size score adjustments."""

    # Prefer large companies (default)
    def test_large_company_with_prefer_large(self):
        """Test large company gets bonus when preferring large."""
        adjustment, description = calculate_company_size_adjustment("large", prefer_large=True)
        assert adjustment == 10
        assert "Large company" in description
        assert "+10" in description

    def test_medium_company_with_prefer_large(self):
        """Test medium company is neutral when preferring large."""
        adjustment, description = calculate_company_size_adjustment("medium", prefer_large=True)
        assert adjustment == 0
        assert "Medium company" in description
        assert "neutral" in description

    def test_small_company_with_prefer_large(self):
        """Test small company gets penalty when preferring large."""
        adjustment, description = calculate_company_size_adjustment("small", prefer_large=True)
        assert adjustment == -5
        assert "Small company" in description or "startup" in description
        assert "-5" in description

    # Prefer small companies (inverse)
    def test_small_company_with_prefer_small(self):
        """Test small company gets bonus when preferring small."""
        adjustment, description = calculate_company_size_adjustment("small", prefer_large=False)
        assert adjustment == 10
        assert "Small company" in description or "startup" in description
        assert "+10" in description

    def test_medium_company_with_prefer_small(self):
        """Test medium company is neutral when preferring small."""
        adjustment, description = calculate_company_size_adjustment("medium", prefer_large=False)
        assert adjustment == 0
        assert "Medium company" in description
        assert "neutral" in description

    def test_large_company_with_prefer_small(self):
        """Test large company gets penalty when preferring small."""
        adjustment, description = calculate_company_size_adjustment("large", prefer_large=False)
        assert adjustment == -5
        assert "Large company" in description
        assert "-5" in description

    # Unknown size (None)
    def test_none_size_with_prefer_large(self):
        """Test None size returns no adjustment (prefer large)."""
        adjustment, description = calculate_company_size_adjustment(None, prefer_large=True)
        assert adjustment == 0
        assert "Unknown" in description
        assert "no adjustment" in description

    def test_none_size_with_prefer_small(self):
        """Test None size returns no adjustment (prefer small)."""
        adjustment, description = calculate_company_size_adjustment(None, prefer_large=False)
        assert adjustment == 0
        assert "Unknown" in description
        assert "no adjustment" in description

    # Edge cases
    def test_default_prefer_large_parameter(self):
        """Test prefer_large defaults to True."""
        adjustment, _ = calculate_company_size_adjustment("large")
        assert adjustment == 10  # Default behavior prefers large

    def test_invalid_size_returns_neutral(self):
        """Test invalid size string returns neutral adjustment."""
        adjustment, description = calculate_company_size_adjustment("invalid", prefer_large=True)
        assert adjustment == 0
        assert "Unknown" in description


class TestEdgeCaseTieBreakers:
    """Test edge cases that might trigger tie-breaker logic."""

    def test_single_medium_pattern_only(self):
        """Test single medium pattern returns medium."""
        result = detect_company_size("MedCo", company_info="Mid-sized organization")
        assert result == "medium"

    def test_conflicting_single_patterns_returns_none(self):
        """Test conflicting single patterns (1 large, 1 small) returns None."""
        result = detect_company_size(
            "ConflictCo",
            company_info="Fortune 500 startup",  # 1 large, 1 small - conflict
        )
        # With 1 large and 1 small, neither condition on lines 181-186 is met
        # Tie-breaker can't decide since large == small == 1
        # Should return None
        assert result is None
