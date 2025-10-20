# Logging Documentation

This document describes the logging system for the job-finder-worker, including configuration, best practices, and how to work with company names and other long text fields.

## Overview

The job-finder-worker uses a structured logging approach that:
- Preserves full data in structured logs (no information loss)
- Provides readable truncated output for console/terminal viewing
- Supports Google Cloud Logging integration with environment labels
- Handles unicode and special characters safely

## Configuration

Logging behavior is configured in `config/logging.yaml`:

```yaml
# Console display settings
console:
  max_company_name_length: 80  # Truncate company names longer than this
  max_job_title_length: 60     # Truncate job titles longer than this
  max_url_length: 50           # Truncate URLs longer than this

# Structured logging settings
structured:
  include_display_fields: true  # Include both full and display versions
  preserve_full_values: true    # Never truncate in structured output
```

### Adjusting Display Length

To change the maximum display length for company names, edit `config/logging.yaml`:

```yaml
console:
  max_company_name_length: 120  # Allow longer names in console
```

To disable truncation entirely, set to 0:

```yaml
console:
  max_company_name_length: 0  # No truncation
```

## Company Name Logging

### The Problem

Long company names can clutter console output and make logs difficult to read.

### The Solution

The logging system now provides both full and display-friendly versions using the `format_company_name()` helper.

**Important**: Full company names are still available in structured logs for querying and analysis.

### Using the Helper Function

Use the `format_company_name()` helper when logging company names:

```python
from job_finder.logging_config import format_company_name

company_name = "International Business Machines Corporation"
full_name, display_name = format_company_name(company_name)

# full_name: "International Business Machines Corporation" (unchanged)
# display_name: "International Business Machines Corporat..." (truncated)

# Use in log messages
logger.info(f"Processing company: {display_name}")
```

### Using StructuredLogger

For company-specific logging, use the `company_activity()` method:

```python
from job_finder.logging_config import get_structured_logger

logger = get_structured_logger(__name__)

# Automatically handles truncation
logger.company_activity(
    company_name="Very Long Company Name That Exceeds Display Limit",
    action="FETCH",
    details={"pages": 5, "chars": 1000}
)

# Force full name logging when needed
logger.company_activity(
    company_name="Important Company",
    action="ANALYZE",
    truncate=False  # Show full name
)
```

## Best Practices

### 1. Always Use Helpers for Long Text

When logging company names, use the appropriate helper to avoid cluttering logs.

### 2. Preserve Full Data in Structured Logs

The `format_company_name()` helper returns both full and display versions. Store the full version for structured logging.

### 3. Use StructuredLogger Methods

The `StructuredLogger` class provides specialized methods for common operations.

### 4. Handle Unicode Safely

The `format_company_name()` helper handles unicode characters safely without encoding errors.

### 5. Configure for Your Environment

Different environments may need different settings. Production logs may benefit from shorter display lengths.

## Testing

Run the logging tests to verify behavior:

```bash
# Run all logging tests
pytest tests/logging/test_company_name_logging.py

# Run specific test class
pytest tests/logging/test_company_name_logging.py::TestFormatCompanyName -v

# Run with coverage
pytest tests/logging/ --cov=src/job_finder/logging_config
```

## Related Documentation

- [Cloud Logging Design](../CLOUD_LOGGING_DESIGN.md) - Architecture for Google Cloud Logging integration
- [Monitoring Guide](../monitoring/) - Overall monitoring and observability strategy

## Summary

The logging system now provides:
- ✅ Full company names preserved in structured logs (no data loss)
- ✅ Readable truncated display in console output
- ✅ Safe unicode handling
- ✅ Configurable max lengths per field type
- ✅ Helper functions for consistent logging
- ✅ StructuredLogger methods for common patterns
- ✅ Comprehensive test coverage

For questions or issues, refer to the test suite in `tests/logging/test_company_name_logging.py` for examples of correct usage.
