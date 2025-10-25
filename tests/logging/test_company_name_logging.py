"""Tests for company name logging functionality.

This test suite validates that:
1. Full company names are always preserved (no data loss)
2. Display truncation works correctly with ellipsis
3. Unicode characters are handled safely
4. Configuration settings are respected
5. Edge cases (empty strings, very short limits) are handled
"""

import logging
from unittest.mock import patch

from job_finder.logging_config import (
    format_company_name,
    get_structured_logger,
    StructuredLogger,
)


class TestFormatCompanyName:
    """Test the format_company_name helper function."""

    def test_short_name_unchanged(self):
        """Short company names should not be truncated."""
        full, display = format_company_name("Acme Inc")
        assert full == "Acme Inc"
        assert display == "Acme Inc"
        assert full == display

    def test_empty_name(self):
        """Empty strings should be handled gracefully."""
        full, display = format_company_name("")
        assert full == ""
        assert display == ""

    def test_whitespace_trimmed(self):
        """Leading/trailing whitespace should be removed."""
        full, display = format_company_name("  Acme Inc  ")
        assert full == "Acme Inc"
        assert display == "Acme Inc"

    def test_long_name_truncated(self):
        """Long company names should be truncated with ellipsis."""
        long_name = "A" * 100
        full, display = format_company_name(long_name, max_length=50)

        assert len(full) == 100
        assert len(display) == 50
        assert display.endswith("...")
        assert display == long_name[:47] + "..."

    def test_exact_length_not_truncated(self):
        """Names exactly at max length should not be truncated."""
        name = "A" * 80
        full, display = format_company_name(name, max_length=80)

        assert full == name
        assert display == name
        assert not display.endswith("...")

    def test_one_over_length_truncated(self):
        """Names one character over max should be truncated."""
        name = "A" * 81
        full, display = format_company_name(name, max_length=80)

        assert len(full) == 81
        assert len(display) == 80
        assert display.endswith("...")

    def test_unicode_characters(self):
        """Unicode characters should be handled safely."""
        unicode_name = "Société Générale ™ 株式会社"
        full, display = format_company_name(unicode_name, max_length=20)

        assert full == unicode_name
        assert len(display) <= 20
        assert display.endswith("...")

    def test_emoji_in_name(self):
        """Emoji characters should be handled (some companies use them!)."""
        emoji_name = "🚀 Rocket Corp 🌟"
        full, display = format_company_name(emoji_name, max_length=10)

        assert full == emoji_name
        assert len(display) <= 10

    def test_zero_max_length_no_truncation(self):
        """max_length=0 should disable truncation."""
        long_name = "A" * 200
        full, display = format_company_name(long_name, max_length=0)

        assert full == long_name
        assert display == long_name

    def test_negative_max_length_no_truncation(self):
        """Negative max_length should disable truncation."""
        long_name = "A" * 200
        full, display = format_company_name(long_name, max_length=-1)

        assert full == long_name
        assert display == long_name

    def test_very_short_max_length(self):
        """Very short max_length should still work (edge case)."""
        name = "Acme Corporation"
        full, display = format_company_name(name, max_length=5)

        assert full == name
        assert len(display) == 5
        assert display == "Ac..."

    def test_max_length_three(self):
        """max_length=3 should show only ellipsis."""
        name = "Acme Corporation"
        full, display = format_company_name(name, max_length=3)

        assert full == name
        assert len(display) == 3

    def test_uses_config_default(self):
        """When max_length is None, should use config default (80)."""
        long_name = "A" * 100
        full, display = format_company_name(long_name)

        assert len(full) == 100
        # Default max_length from config is 80
        assert len(display) == 80
        assert display.endswith("...")

    def test_preserves_spaces(self):
        """Internal spaces should be preserved in truncation."""
        name = "Very Long Company Name With Many Words That Exceeds The Limit"
        full, display = format_company_name(name, max_length=30)

        assert full == name
        assert len(display) == 30
        assert display.endswith("...")
        # Should preserve the partial words/spaces
        assert display == name[:27] + "..."

    def test_real_world_examples(self):
        """Test with actual long company names."""
        examples = [
            "International Business Machines Corporation",
            "Bath & Body Works, LLC",
            "The Walt Disney Company",
            "Sony Interactive Entertainment America LLC",
        ]

        for name in examples:
            full, display = format_company_name(name, max_length=40)
            assert full == name
            assert len(display) <= 40
            if len(name) > 40:
                assert display.endswith("...")


class TestStructuredLoggerCompanyActivity:
    """Test the StructuredLogger.company_activity method."""

    def test_company_activity_logs_truncated_by_default(self, caplog):
        """company_activity should use truncated display name by default."""
        logger = logging.getLogger("test_logger")
        structured_logger = StructuredLogger(logger)

        long_name = "A" * 100

        with caplog.at_level(logging.INFO):
            structured_logger.company_activity(long_name, "FETCH")

        # Should contain truncated version in log message
        assert len(caplog.records) == 1
        message = caplog.records[0].message
        assert "Company fetch:" in message
        # Display version should be truncated (default 80 chars)
        assert "..." in message
        assert len(message) < 150  # Much shorter than full 100-char name

    def test_company_activity_logs_full_when_requested(self, caplog):
        """company_activity should include full name in structured fields."""
        logger = logging.getLogger("test_logger")
        structured_logger = StructuredLogger(logger)

        long_name = "A" * 100

        with caplog.at_level(logging.INFO):
            structured_logger.company_activity(long_name, "FETCH", truncate=False)

        # In structured JSON mode, full name is in details, message may be truncated
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert "Company fetch:" in record.message
        # Full name should be in structured fields
        assert hasattr(record, "structured_fields")
        assert record.structured_fields["details"]["company_name"] == long_name

    def test_company_activity_with_details(self, caplog):
        """company_activity should include details dict."""
        logger = logging.getLogger("test_logger")
        structured_logger = StructuredLogger(logger)

        with caplog.at_level(logging.INFO):
            structured_logger.company_activity(
                "Acme Corp", "EXTRACT", details={"pages": 5, "chars": 1000}
            )

        assert len(caplog.records) == 1
        message = caplog.records[0].message
        assert "Company extract:" in message
        assert "Acme Corp" in message

    def test_company_activity_handles_unicode(self, caplog):
        """company_activity should handle unicode company names."""
        logger = logging.getLogger("test_logger")
        structured_logger = StructuredLogger(logger)

        unicode_name = "Société Générale 株式会社"

        with caplog.at_level(logging.INFO):
            structured_logger.company_activity(unicode_name, "ANALYZE")

        # Should not raise any encoding errors
        assert len(caplog.records) == 1
        message = caplog.records[0].message
        assert "Company analyze:" in message


class TestGetStructuredLogger:
    """Test the get_structured_logger factory function."""

    def test_returns_structured_logger(self):
        """get_structured_logger should return StructuredLogger instance."""
        structured_logger = get_structured_logger("test")
        assert isinstance(structured_logger, StructuredLogger)

    def test_creates_logger_with_name(self):
        """get_structured_logger should create logger with given name."""
        structured_logger = get_structured_logger("my_module")
        assert structured_logger.logger.name == "my_module"


class TestLoggingConfigIntegration:
    """Integration tests for logging configuration."""

    @patch("job_finder.logging_config._load_logging_config")
    def test_respects_custom_max_length(self, mock_load_config):
        """format_company_name should respect custom max_length from config."""
        # Mock config with custom max length
        mock_load_config.return_value = {
            "console": {"max_company_name_length": 50},
            "structured": {"include_display_fields": True, "preserve_full_values": True},
        }

        # Clear the cached config
        import job_finder.logging_config as log_config

        log_config._logging_config = None

        long_name = "A" * 100
        full, display = format_company_name(long_name)

        assert len(full) == 100
        assert len(display) == 50
        assert display.endswith("...")

    def test_no_exception_on_missing_config(self):
        """Should not crash if logging.yaml is missing."""
        # This test ensures the default config works
        long_name = "A" * 100
        full, display = format_company_name(long_name)

        # Should use default max_length (80)
        assert len(full) == 100
        assert len(display) <= 100  # Some truncation should occur
        assert full != display  # Display should be truncated


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_none_company_name(self):
        """None company name should be handled gracefully."""
        # This should not crash - though we expect empty strings in practice
        try:
            full, display = format_company_name(None)
            # If it doesn't crash, should return empty strings
            assert full == ""
            assert display == ""
        except (TypeError, AttributeError):
            # It's acceptable to raise TypeError for None
            pass

    def test_numeric_company_name(self):
        """Numeric company names should work (e.g., '1-800-FLOWERS')."""
        name = "1-800-FLOWERS.COM, Inc."
        full, display = format_company_name(name, max_length=20)

        assert full == name
        assert len(display) <= 20

    def test_special_characters(self):
        """Company names with special characters should work."""
        name = "AT&T Inc. [Formerly SBC Communications]"
        full, display = format_company_name(name, max_length=25)

        assert full == name
        assert len(display) <= 25
        if len(name) > 25:
            assert display.endswith("...")

    def test_newlines_in_name(self):
        """Newlines in company name should be preserved (though unusual)."""
        name = "Acme\nCorporation"
        full, display = format_company_name(name, max_length=10)

        assert full == name
        assert len(display) <= 10
