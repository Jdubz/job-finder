# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Job Finder is a web scraping application that finds online job postings matching user-defined criteria. The system scrapes multiple job boards, filters results based on keywords/location/experience, and outputs data in various formats.

## Commands

### Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Running the Application
```bash
# Run with default config
python -m job_finder.main

# Run with custom config
python -m job_finder.main --config path/to/config.yaml

# Override output file
python -m job_finder.main --output data/custom_output.json
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=src/job_finder --cov-report=html

# Run specific test file
pytest tests/test_filters.py

# Run specific test function
pytest tests/test_filters.py::test_filter_by_keywords -v
```

### Code Quality
```bash
# Format code with black
black src/ tests/

# Check formatting without changes
black --check src/ tests/

# Run linter
flake8 src/ tests/

# Type checking
mypy src/
```

## Architecture

### Core Pipeline

The application follows a three-stage pipeline architecture:

1. **Scrape** - Site-specific scrapers collect job postings
2. **Filter** - Jobs are filtered based on user criteria
3. **Store** - Results are saved in configured format

This pipeline is orchestrated in `src/job_finder/main.py:main()`.

### Scraper Pattern

All scrapers inherit from `BaseScraper` (src/job_finder/scrapers/base.py:5) which defines:
- `scrape()` - Main method that returns list of job dictionaries
- `parse_job()` - Parses individual job elements into standardized format

**Standard job dictionary structure:**
```python
{
    "title": str,
    "company": str,
    "location": str,
    "description": str,
    "url": str,
    "posted_date": str,
    "salary": str (optional)
}
```

When adding a new job site scraper:
1. Create new file in `src/job_finder/scrapers/`
2. Inherit from `BaseScraper`
3. Implement `scrape()` and `parse_job()` methods
4. Return jobs in the standard dictionary format above

### Filtering System

The `JobFilter` class (src/job_finder/filters.py:6) applies multiple filter stages:
1. Keyword matching (inclusive) - Jobs must contain at least one keyword
2. Location filtering - Jobs must be in preferred locations
3. Keyword exclusion - Jobs cannot contain excluded keywords

Filters are configured in `config/config.yaml` under the `profile` section.

### Storage System

The `JobStorage` class (src/job_finder/storage.py:8) supports multiple output formats:
- **JSON** - Default, human-readable format
- **CSV** - Spreadsheet-compatible format
- **Database** - SQLAlchemy-based storage (not yet implemented)

Output format and path are configured in `config/config.yaml` under the `output` section.

### Configuration

All application behavior is controlled through `config/config.yaml`:
- **profile**: User preferences (keywords, experience, locations, exclusions)
- **sites**: Which job boards to scrape and their settings
- **scraping**: Rate limiting and request settings
- **output**: Where and how to save results
- **filters**: Additional filtering criteria (salary, age, etc.)

Use `config/config.example.yaml` as a template when creating new configurations.

### Module Organization

```
src/job_finder/
├── __init__.py          # Package initialization
├── main.py              # Entry point and pipeline orchestration
├── filters.py           # JobFilter class - all filtering logic
├── storage.py           # JobStorage class - output handling
└── scrapers/
    ├── __init__.py
    ├── base.py          # BaseScraper abstract class
    └── [site].py        # Site-specific scraper implementations
```

## Development Notes

### Adding a New Job Site

1. Create scraper: `src/job_finder/scrapers/[sitename].py`
2. Inherit from `BaseScraper`
3. Implement required methods
4. Add site configuration to `config/config.yaml`
5. Register scraper in main.py (when scraper initialization is implemented)
6. Write tests in `tests/test_scrapers_[sitename].py`

### Testing Scrapers

When testing scrapers, use mocked HTTP responses to avoid:
- Rate limiting issues
- Changing website structure breaking tests
- Network dependencies in test suite

### Web Scraping Considerations

- Respect robots.txt for each site
- Implement delays between requests (configured in scraping.delay_between_requests)
- Handle rate limiting gracefully
- Use appropriate User-Agent headers
- Consider using Selenium for JavaScript-heavy sites

### Error Handling

Scrapers should gracefully handle:
- Network failures
- Missing elements
- Changed page structure
- Rate limiting/blocking

Return partial results rather than failing completely.
