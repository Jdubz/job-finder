"""Tests for date parsing and scoring utilities."""

from datetime import datetime, timedelta, timezone

from job_finder.utils.date_utils import (
    calculate_freshness_adjustment,
    format_job_age,
    parse_job_date,
)


class TestParseJobDate:
    """Test job date parsing."""

    def test_parse_iso8601_with_timezone(self):
        """Test parsing ISO 8601 date with timezone."""
        date_str = "2024-01-15T10:30:00Z"
        result = parse_job_date(date_str)

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.tzinfo is not None

    def test_parse_iso8601_without_timezone(self):
        """Test parsing ISO 8601 date without timezone assumes UTC."""
        date_str = "2024-01-15T10:30:00"
        result = parse_job_date(date_str)

        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_parse_rfc2822_date(self):
        """Test parsing RFC 2822 date format."""
        date_str = "Mon, 15 Jan 2024 10:30:00 GMT"
        result = parse_job_date(date_str)

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_human_readable_date(self):
        """Test parsing human-readable date."""
        date_str = "January 15, 2024"
        result = parse_job_date(date_str)

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_none_returns_none(self):
        """Test parsing None returns None."""
        result = parse_job_date(None)
        assert result is None

    def test_parse_empty_string_returns_none(self):
        """Test parsing empty string returns None."""
        result = parse_job_date("")
        assert result is None

    def test_parse_invalid_date_returns_none(self):
        """Test parsing invalid date string returns None."""
        result = parse_job_date("not a valid date")
        assert result is None


class TestCalculateFreshnessAdjustment:
    """Test freshness score adjustments."""

    def test_none_date_returns_penalty(self):
        """Test None date gets -10 penalty."""
        adjustment = calculate_freshness_adjustment(None)
        assert adjustment == -10

    def test_very_fresh_job_under_24_hours(self):
        """Test job posted under 24 hours gets +15 bonus."""
        posted_date = datetime.now(timezone.utc) - timedelta(hours=12)
        adjustment = calculate_freshness_adjustment(posted_date)
        assert adjustment == 15

    def test_fresh_job_1_to_2_days(self):
        """Test job posted 1-2 days ago gets +5 bonus."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=1.5)
        adjustment = calculate_freshness_adjustment(posted_date)
        assert adjustment == 5

    def test_recent_job_2_to_3_days(self):
        """Test job posted 2-3 days ago gets 0 adjustment."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=2.5)
        adjustment = calculate_freshness_adjustment(posted_date)
        assert adjustment == 0

    def test_week_old_job_3_to_7_days(self):
        """Test job posted 3-7 days ago gets -35 penalty."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=5)
        adjustment = calculate_freshness_adjustment(posted_date)
        assert adjustment == -35

    def test_two_weeks_old_job_7_to_14_days(self):
        """Test job posted 7-14 days ago gets -40 penalty."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=10)
        adjustment = calculate_freshness_adjustment(posted_date)
        assert adjustment == -40

    def test_month_old_job_14_to_30_days(self):
        """Test job posted 14-30 days ago gets -45 penalty."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=20)
        adjustment = calculate_freshness_adjustment(posted_date)
        assert adjustment == -45

    def test_stale_job_over_30_days(self):
        """Test job posted over 30 days ago gets -50 penalty."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=45)
        adjustment = calculate_freshness_adjustment(posted_date)
        assert adjustment == -50

    def test_future_date_returns_zero(self):
        """Test future date (bad data) returns 0."""
        posted_date = datetime.now(timezone.utc) + timedelta(days=1)
        adjustment = calculate_freshness_adjustment(posted_date)
        assert adjustment == 0

    def test_naive_datetime_made_timezone_aware(self):
        """Test naive datetime is made timezone-aware."""
        # Create naive datetime (no timezone)
        posted_date = datetime.now() - timedelta(hours=12)
        adjustment = calculate_freshness_adjustment(posted_date)

        # Should still process correctly and give +15 bonus
        assert adjustment == 15


class TestFormatJobAge:
    """Test human-readable job age formatting."""

    def test_none_date_returns_unknown(self):
        """Test None date returns 'Unknown'."""
        result = format_job_age(None)
        assert result == "Unknown"

    def test_under_1_hour(self):
        """Test job under 1 hour shows hours."""
        posted_date = datetime.now(timezone.utc) - timedelta(minutes=30)
        result = format_job_age(posted_date)
        assert "0 hours ago" in result

    def test_several_hours_ago(self):
        """Test job several hours ago."""
        posted_date = datetime.now(timezone.utc) - timedelta(hours=5)
        result = format_job_age(posted_date)
        assert "5 hours ago" in result

    def test_1_hour_singular(self):
        """Test 1 hour uses singular form."""
        posted_date = datetime.now(timezone.utc) - timedelta(hours=1)
        result = format_job_age(posted_date)
        assert "1 hour ago" in result

    def test_1_day_singular(self):
        """Test 1 day uses singular form."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=1)
        result = format_job_age(posted_date)
        assert "1 day ago" in result

    def test_several_days_ago(self):
        """Test job several days ago."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=3)
        result = format_job_age(posted_date)
        assert "3 days ago" in result

    def test_1_week_singular(self):
        """Test 1 week uses singular form."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=7)
        result = format_job_age(posted_date)
        assert "1 week ago" in result

    def test_several_weeks_ago(self):
        """Test job several weeks ago."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=14)
        result = format_job_age(posted_date)
        assert "2 weeks ago" in result

    def test_1_month_singular(self):
        """Test 1 month uses singular form."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=30)
        result = format_job_age(posted_date)
        assert "1 month ago" in result

    def test_several_months_ago(self):
        """Test job several months ago."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=90)
        result = format_job_age(posted_date)
        assert "3 months ago" in result

    def test_1_year_singular(self):
        """Test 1 year uses singular form."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=365)
        result = format_job_age(posted_date)
        assert "1 year ago" in result

    def test_several_years_ago(self):
        """Test job several years ago."""
        posted_date = datetime.now(timezone.utc) - timedelta(days=730)
        result = format_job_age(posted_date)
        assert "2 years ago" in result

    def test_future_date_returns_just_posted(self):
        """Test future date returns 'Just posted'."""
        posted_date = datetime.now(timezone.utc) + timedelta(hours=1)
        result = format_job_age(posted_date)
        assert result == "Just posted"

    def test_naive_datetime_handled(self):
        """Test naive datetime is handled correctly."""
        posted_date = datetime.now() - timedelta(hours=5)
        result = format_job_age(posted_date)
        assert "hours ago" in result
