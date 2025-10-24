"""Tests for timezone detection and scoring utilities."""

from job_finder.utils.timezone_utils import (
    calculate_timezone_score_adjustment,
    detect_timezone_for_job,
    detect_timezone_from_location,
)


class TestDetectTimezoneFromLocation:
    """Test timezone detection from location strings."""

    # Explicit timezone mentions
    def test_detect_pacific_timezone(self):
        """Test detecting Pacific timezone."""
        assert detect_timezone_from_location("Remote - PST") == -8
        assert detect_timezone_from_location("Remote - Pacific Time") == -8
        assert detect_timezone_from_location("Remote - PT") == -8

    def test_detect_eastern_timezone(self):
        """Test detecting Eastern timezone."""
        assert detect_timezone_from_location("Remote - EST") == -5
        assert detect_timezone_from_location("Remote - Eastern Time") == -5
        assert detect_timezone_from_location("Remote - ET") == -5

    def test_detect_central_timezone(self):
        """Test detecting Central timezone."""
        assert detect_timezone_from_location("Remote - CST") == -6
        assert detect_timezone_from_location("Remote - Central Time") == -6
        assert detect_timezone_from_location("Remote - CT") == -6

    def test_detect_mountain_timezone(self):
        """Test detecting Mountain timezone."""
        assert detect_timezone_from_location("Remote - MST") == -7
        assert detect_timezone_from_location("Remote - Mountain Time") == -7
        assert detect_timezone_from_location("Remote - MT") == -7

    # US West Coast cities
    def test_detect_seattle_timezone(self):
        """Test detecting Seattle timezone."""
        assert detect_timezone_from_location("Seattle, WA") == -8

    def test_detect_portland_timezone(self):
        """Test detecting Portland timezone."""
        assert detect_timezone_from_location("Portland, OR") == -8

    def test_detect_san_francisco_timezone(self):
        """Test detecting San Francisco timezone."""
        assert detect_timezone_from_location("San Francisco, CA") == -8
        assert detect_timezone_from_location("SF Bay Area") == -8

    def test_detect_los_angeles_timezone(self):
        """Test detecting Los Angeles timezone."""
        assert detect_timezone_from_location("Los Angeles, CA") == -8
        assert detect_timezone_from_location("LA, California") == -8

    # US West Coast states
    def test_detect_california_timezone(self):
        """Test detecting California timezone."""
        assert detect_timezone_from_location("California") == -8
        assert detect_timezone_from_location("Remote - California") == -8

    def test_detect_oregon_timezone(self):
        """Test detecting Oregon timezone."""
        assert detect_timezone_from_location("Oregon") == -8

    def test_detect_washington_timezone(self):
        """Test detecting Washington state timezone."""
        assert detect_timezone_from_location("Washington") == -8

    # US Mountain cities
    def test_detect_denver_timezone(self):
        """Test detecting Denver timezone."""
        assert detect_timezone_from_location("Denver, CO") == -7

    def test_detect_phoenix_timezone(self):
        """Test detecting Phoenix timezone."""
        assert detect_timezone_from_location("Phoenix, AZ") == -7

    # US Central cities
    def test_detect_chicago_timezone(self):
        """Test detecting Chicago timezone."""
        assert detect_timezone_from_location("Chicago, IL") == -6

    def test_detect_austin_timezone(self):
        """Test detecting Austin timezone."""
        assert detect_timezone_from_location("Austin, TX") == -6

    def test_detect_houston_timezone(self):
        """Test detecting Houston timezone."""
        assert detect_timezone_from_location("Houston, TX") == -6

    # US Eastern cities
    def test_detect_new_york_timezone(self):
        """Test detecting New York timezone."""
        assert detect_timezone_from_location("New York, NY") == -5
        assert detect_timezone_from_location("NYC") == -5

    def test_detect_boston_timezone(self):
        """Test detecting Boston timezone."""
        assert detect_timezone_from_location("Boston, MA") == -5

    def test_detect_miami_timezone(self):
        """Test detecting Miami timezone."""
        assert detect_timezone_from_location("Miami, FL") == -5

    # International - Europe
    def test_detect_london_timezone(self):
        """Test detecting London timezone."""
        assert detect_timezone_from_location("London, UK") == 0

    def test_detect_berlin_timezone(self):
        """Test detecting Berlin timezone."""
        assert detect_timezone_from_location("Berlin, Germany") == 1

    def test_detect_paris_timezone(self):
        """Test detecting Paris timezone."""
        assert detect_timezone_from_location("Paris, France") == 1

    def test_detect_brussels_timezone(self):
        """Test detecting Brussels timezone."""
        assert detect_timezone_from_location("Brussels, Belgium") == 1

    # International - Asia
    def test_detect_india_timezone(self):
        """Test detecting India timezone."""
        assert detect_timezone_from_location("Bangalore, India") == 5.5
        assert detect_timezone_from_location("Mumbai, India") == 5.5

    def test_detect_tokyo_timezone(self):
        """Test detecting Tokyo timezone."""
        assert detect_timezone_from_location("Tokyo, Japan") == 9

    def test_detect_singapore_timezone(self):
        """Test detecting Singapore timezone."""
        assert detect_timezone_from_location("Singapore") == 8

    # International - Australia
    def test_detect_sydney_timezone(self):
        """Test detecting Sydney timezone."""
        assert detect_timezone_from_location("Sydney, Australia") == 10

    # Canada
    def test_detect_vancouver_timezone(self):
        """Test detecting Vancouver timezone."""
        assert detect_timezone_from_location("Vancouver, BC") == -8

    def test_detect_toronto_timezone(self):
        """Test detecting Toronto timezone."""
        assert detect_timezone_from_location("Toronto, ON") == -5

    # Edge cases
    def test_detect_timezone_none_input(self):
        """Test detecting timezone from None input returns None."""
        assert detect_timezone_from_location(None) is None

    def test_detect_timezone_empty_string(self):
        """Test detecting timezone from empty string returns None."""
        assert detect_timezone_from_location("") is None

    def test_detect_timezone_no_match(self):
        """Test detecting timezone from unknown location returns None."""
        assert detect_timezone_from_location("Unknown City") is None

    def test_detect_timezone_case_insensitive(self):
        """Test timezone detection is case-insensitive."""
        assert detect_timezone_from_location("SEATTLE, WA") == -8
        assert detect_timezone_from_location("seattle, wa") == -8
        assert detect_timezone_from_location("SeAtTlE, Wa") == -8


class TestDetectTimezoneForJob:
    """Test smart timezone detection for jobs with company size prioritization."""

    # Large company tests
    def test_large_company_with_team_location_in_description(self):
        """Test large company prioritizes team location in description."""
        job_location = "Remote - United States"
        job_description = "Join our Seattle-based engineering team..."
        result = detect_timezone_for_job(
            job_location=job_location,
            job_description=job_description,
            company_size="large",
            headquarters_location="New York, NY",
        )
        assert result == -8  # Seattle timezone, not HQ

    def test_large_company_with_job_location_only(self):
        """Test large company uses job location if no team location."""
        job_location = "San Francisco, CA"
        job_description = "We are hiring for this role..."
        result = detect_timezone_for_job(
            job_location=job_location,
            job_description=job_description,
            company_size="large",
            headquarters_location="New York, NY",
        )
        assert result == -8  # San Francisco timezone

    def test_large_company_without_specific_location_returns_none(self):
        """Test large company returns None if no specific location detected."""
        job_location = "Remote - Worldwide"
        job_description = "Join our global team..."
        result = detect_timezone_for_job(
            job_location=job_location,
            job_description=job_description,
            company_size="large",
            headquarters_location="New York, NY",
        )
        assert result is None  # Large global company, don't assume HQ timezone

    def test_large_company_remote_with_region(self):
        """Test large company remote job with specified region."""
        job_location = "Remote - Pacific Time Zone"
        job_description = "Remote position for US candidates..."
        result = detect_timezone_for_job(
            job_location=job_location,
            job_description=job_description,
            company_size="large",
        )
        assert result == -8  # Pacific timezone from location

    # Small/Medium company tests
    def test_small_company_with_team_location_in_description(self):
        """Test small company prioritizes team location in description."""
        job_location = "Remote"
        job_description = "Our Boston office is looking for..."
        result = detect_timezone_for_job(
            job_location=job_location,
            job_description=job_description,
            company_size="small",
            headquarters_location="New York, NY",
        )
        assert result == -5  # Boston timezone from description

    def test_medium_company_with_job_location(self):
        """Test medium company uses job location."""
        job_location = "Portland, OR"
        job_description = "We are hiring..."
        result = detect_timezone_for_job(
            job_location=job_location,
            job_description=job_description,
            company_size="medium",
            headquarters_location="Seattle, WA",
        )
        assert result == -8  # Portland timezone from job location

    def test_small_company_falls_back_to_hq(self):
        """Test small company falls back to HQ location."""
        job_location = "Remote"
        job_description = "Join our remote team..."
        result = detect_timezone_for_job(
            job_location=job_location,
            job_description=job_description,
            company_size="small",
            headquarters_location="Austin, TX",
        )
        assert result == -6  # Austin HQ timezone

    def test_medium_company_falls_back_to_hq(self):
        """Test medium company falls back to HQ location."""
        job_location = "Remote - US"
        job_description = "Remote position available..."
        result = detect_timezone_for_job(
            job_location=job_location,
            job_description=job_description,
            company_size="medium",
            headquarters_location="San Francisco, CA",
        )
        assert result == -8  # San Francisco HQ timezone

    def test_small_company_no_location_info_returns_none(self):
        """Test small company returns None with no location info."""
        job_location = "Remote"
        job_description = "We are hiring..."
        result = detect_timezone_for_job(
            job_location=job_location,
            job_description=job_description,
            company_size="small",
            headquarters_location="",
        )
        assert result is None

    # No company size (default handling)
    def test_no_company_size_uses_small_medium_logic(self):
        """Test no company size uses small/medium logic."""
        job_location = "Remote"
        job_description = "Join our team..."
        result = detect_timezone_for_job(
            job_location=job_location,
            job_description=job_description,
            company_size=None,
            headquarters_location="Chicago, IL",
        )
        assert result == -6  # Falls back to HQ like small/medium

    # Edge cases
    def test_all_empty_inputs_returns_none(self):
        """Test all empty inputs returns None."""
        result = detect_timezone_for_job(
            job_location="", job_description="", company_size=None, headquarters_location=""
        )
        assert result is None

    def test_priority_order_team_over_job_location(self):
        """Test team location in description takes priority over job location."""
        job_location = "New York, NY"  # Eastern
        job_description = "Work with our San Francisco team..."  # Pacific
        result = detect_timezone_for_job(
            job_location=job_location,
            job_description=job_description,
            company_size="medium",
            headquarters_location="Boston, MA",
        )
        assert result == -8  # San Francisco from description, not NYC from job location


class TestCalculateTimezoneScoreAdjustment:
    """Test timezone score adjustments."""

    # Pacific timezone (user_timezone = -8)
    def test_same_timezone_bonus(self):
        """Test same timezone (Pacific) gets bonus points."""
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=-8, user_timezone=-8
        )
        assert adjustment == 5
        assert "Same timezone" in description
        assert "+5" in description

    def test_1_hour_difference_minor_penalty(self):
        """Test 1 hour difference gets minor penalty."""
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=-7, user_timezone=-8  # Mountain time
        )
        assert adjustment == -2
        assert "1.0h timezone difference" in description or "1h timezone difference" in description
        assert "-2" in description

    def test_2_hour_difference_minor_penalty(self):
        """Test 2 hour difference gets minor penalty."""
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=-6, user_timezone=-8  # Central time
        )
        assert adjustment == -2
        assert "2" in description
        assert "-2" in description

    def test_3_hour_difference_moderate_penalty(self):
        """Test 3 hour difference gets moderate penalty."""
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=-5, user_timezone=-8  # Eastern time
        )
        assert adjustment == -5
        assert "3" in description
        assert "-5" in description

    def test_4_hour_difference_moderate_penalty(self):
        """Test 4 hour difference gets moderate penalty."""
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=-4, user_timezone=-8  # Atlantic time
        )
        assert adjustment == -5
        assert "4" in description
        assert "-5" in description

    def test_8_hour_difference_significant_penalty(self):
        """Test 8 hour difference gets significant penalty."""
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=0, user_timezone=-8  # London/UTC
        )
        assert adjustment == -10
        assert "8" in description
        assert "-10" in description

    def test_9_hour_difference_major_penalty(self):
        """Test 9 hour difference gets major penalty."""
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=1, user_timezone=-8  # Central Europe
        )
        assert adjustment == -15
        assert "9" in description
        assert "-15" in description

    def test_large_timezone_difference_major_penalty(self):
        """Test very large timezone difference gets major penalty."""
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=10, user_timezone=-8  # Australia
        )
        assert adjustment == -15
        assert "18" in description
        assert "-15" in description

    def test_none_timezone_no_adjustment(self):
        """Test None timezone returns no adjustment."""
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=None, user_timezone=-8
        )
        assert adjustment == 0
        assert "Unknown timezone" in description
        assert "no adjustment" in description

    # Different user timezones
    def test_eastern_user_timezone(self):
        """Test adjustments with Eastern user timezone."""
        # Same timezone (Eastern)
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=-5, user_timezone=-5
        )
        assert adjustment == 5

        # 3 hours to Pacific
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=-8, user_timezone=-5
        )
        assert adjustment == -5

    def test_central_user_timezone(self):
        """Test adjustments with Central user timezone."""
        # Same timezone (Central)
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=-6, user_timezone=-6
        )
        assert adjustment == 5

        # 1 hour to Mountain
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=-7, user_timezone=-6
        )
        assert adjustment == -2

    def test_international_user_timezone(self):
        """Test adjustments with international user timezone."""
        # User in London (UTC)
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=0, user_timezone=0  # London job, London user
        )
        assert adjustment == 5

        # Pacific job for London user (8 hour difference)
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=-8, user_timezone=0
        )
        assert adjustment == -10

    # Edge cases with half-hour timezones
    def test_half_hour_timezone_india(self):
        """Test half-hour timezone (India) adjustment."""
        # India (5.5) vs Pacific (-8) = 13.5 hour difference
        adjustment, description = calculate_timezone_score_adjustment(
            job_timezone=5.5, user_timezone=-8
        )
        assert adjustment == -15  # 13.5 hours = major penalty
        assert "13.5h" in description

    def test_absolute_difference_calculation(self):
        """Test timezone difference is calculated as absolute value."""
        # Pacific job (-8) for Eastern user (-5)
        adjustment1, _ = calculate_timezone_score_adjustment(job_timezone=-8, user_timezone=-5)

        # Eastern job (-5) for Pacific user (-8)
        adjustment2, _ = calculate_timezone_score_adjustment(job_timezone=-5, user_timezone=-8)

        # Both should have same adjustment (3 hour difference)
        assert adjustment1 == adjustment2 == -5


class TestTimezoneOverrides:
    """Test timezone override functionality for globally distributed companies."""

    def test_override_for_gitlab_returns_none(self):
        """Test GitLab (globally distributed) returns None."""
        result = detect_timezone_for_job(
            job_location="Remote - Worldwide",
            job_description="Join our all-remote team...",
            company_name="GitLab",
            company_info="All-remote company",
        )
        assert result is None

    def test_override_for_zapier_returns_none(self):
        """Test Zapier (globally distributed) returns None."""
        result = detect_timezone_for_job(
            job_location="Remote",
            job_description="Remote position",
            company_name="Zapier",
            company_info="Remote company",
        )
        assert result is None

    def test_override_for_stripe_returns_none(self):
        """Test Stripe (global company) returns None for remote roles."""
        result = detect_timezone_for_job(
            job_location="Remote - Global",
            job_description="Join our distributed team...",
            company_name="Stripe",
            company_info="Global payment platform",
        )
        assert result is None

    def test_override_case_insensitive(self):
        """Test override matching is case-insensitive."""
        result = detect_timezone_for_job(
            job_location="Remote",
            job_description="Remote role",
            company_name="gitlab",  # lowercase
            company_info="",
        )
        assert result is None

        result = detect_timezone_for_job(
            job_location="Remote",
            job_description="Remote role",
            company_name="ZAPIER",  # uppercase
            company_info="",
        )
        assert result is None

    def test_no_override_for_unknown_company(self):
        """Test companies not in override list use normal detection."""
        result = detect_timezone_for_job(
            job_location="Seattle, WA",
            job_description="Local position",
            company_name="Unknown Company",
            company_info="Local startup",
        )
        assert result == -8  # Seattle timezone

    def test_override_without_company_name_uses_normal_logic(self):
        """Test override check is skipped if no company_name provided."""
        result = detect_timezone_for_job(
            job_location="Portland, OR",
            job_description="Local role",
            company_name="",  # No company name
            company_info="",
        )
        assert result == -8  # Portland timezone

    def test_override_with_explicit_team_location_still_uses_override(self):
        """Test override persists even with team location mentioned."""
        # GitLab is globally distributed, so even if a team location is mentioned,
        # we return None to avoid timezone penalties
        result = detect_timezone_for_job(
            job_location="Remote",
            job_description="Our Seattle team is hiring...",
            company_name="GitLab",
            company_info="All-remote company",
        )
        # Override takes precedence - globally distributed companies don't get penalties
        assert result is None

    def test_pattern_based_override_remote_first(self):
        """Test pattern-based override for companies with 'Remote-First' in description."""
        result = detect_timezone_for_job(
            job_location="Remote",
            job_description="We are a Remote-First company...",
            company_name="New Remote Company",
            company_info="We are a Remote-First organization with global teams",
        )
        # Pattern match should trigger unknown timezone
        assert result is None

    def test_missing_config_file_gracefully_continues(self):
        """Test missing config file doesn't break timezone detection."""
        # This tests the fallback behavior when config file doesn't exist
        # Normal detection should still work
        result = detect_timezone_for_job(
            job_location="San Francisco, CA",
            job_description="Office position",
            company_name="Some Company",
            company_info="Tech company",
        )
        assert result == -8  # San Francisco timezone
