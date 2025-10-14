# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Job Finder is an AI-powered web scraping application that finds online job postings matching user-defined criteria. The system scrapes multiple job boards, uses AI to analyze job fit, generates resume intake data for tailored applications, and outputs comprehensive results in various formats.

### Key Features
- **AI-Powered Job Matching**: Uses LLMs (Claude/GPT-4) to analyze job fit based on your complete profile
- **Resume Intake Generation**: Automatically generates structured data for tailoring resumes to specific jobs
- **Match Scoring**: Assigns 0-100 match scores based on skills, experience, and preferences
- **Application Prioritization**: Categorizes jobs as High/Medium/Low priority
- **Customization Recommendations**: Provides specific guidance for tailoring applications

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

### Profile Setup
```bash
# Create a profile template
python -m job_finder.main --create-profile data/profile.json

# Edit the profile.json with your information
# Then update config/config.yaml to point to your profile
```

### Running the Application
```bash
# Run with default config (includes AI matching if configured)
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

The application follows a five-stage pipeline architecture:

1. **Profile Loading** - Load user profile data from JSON (src/job_finder/profile/loader.py:32)
2. **Scrape** - Site-specific scrapers collect job postings
3. **Basic Filter** - Traditional keyword/location filtering (src/job_finder/filters.py:12)
4. **AI Matching** - AI-powered job analysis and scoring (src/job_finder/ai/matcher.py:71)
5. **Store** - Results with AI analysis saved in configured format

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

### AI Matching System

The `AIJobMatcher` class (src/job_finder/ai/matcher.py:41) uses LLMs to analyze jobs against user profiles:

**Analysis Process:**
1. Analyzes job description against profile using AI prompts
2. Generates match score (0-100) based on skills, experience, fit
3. Identifies matched skills and skill gaps
4. Assigns application priority (High/Medium/Low)
5. Generates resume intake data with tailoring recommendations

**Resume Intake Data Structure:**
The AI generates structured data for each matched job including:
- Target professional summary tailored to the job
- Priority-ordered skills list (most relevant first)
- Experience highlights to emphasize
- Projects to include
- Achievement angles to emphasize
- Keywords to incorporate

This intake data can be fed into resume generation systems to create tailored resumes.

**AI Providers:**
- **ClaudeProvider** (src/job_finder/ai/providers.py:16) - Anthropic Claude (recommended)
- **OpenAIProvider** (src/job_finder/ai/providers.py:39) - OpenAI GPT-4

Configure provider in `config/config.yaml` under the `ai` section.

### Profile System

User profiles are managed through Pydantic models in `src/job_finder/profile/schema.py`:

- **Profile**: Complete user profile with experience, skills, preferences
- **Experience**: Work history with responsibilities, achievements, technologies
- **Education**: Educational background
- **Skill**: Individual skills with proficiency levels
- **Project**: Personal/professional projects
- **Preferences**: Job search preferences (roles, locations, salary, etc.)

**Profile Loading:**
- **JSON**: Load from JSON files using `ProfileLoader` (src/job_finder/profile/loader.py:7)
- **Firestore**: Load directly from Firestore database using `FirestoreProfileLoader` (src/job_finder/profile/firestore_loader.py:16)

**Firestore Integration:**
The tool can read profile data directly from the portfolio project's Firestore database:
- Connects to `portfolio` database
- Reads from `experience-entries` and `experience-blurbs` collections
- Automatically extracts skills, experience, and generates summary
- Keeps profile data in sync with portfolio without manual export/import

Configure in `config.yaml`:
```yaml
profile:
  source: "firestore"  # or "json"
  firestore:
    database_name: "portfolio"
    name: "Your Name"
```

### Module Organization

```
src/job_finder/
├── __init__.py          # Package initialization
├── main.py              # Entry point and pipeline orchestration
├── filters.py           # JobFilter class - traditional filtering logic
├── storage.py           # JobStorage class - output handling
├── profile/
│   ├── __init__.py
│   ├── schema.py            # Pydantic models for profile data
│   ├── loader.py            # Profile loading from JSON/dict
│   └── firestore_loader.py  # Profile loading from Firestore
├── ai/
│   ├── __init__.py
│   ├── providers.py     # AI provider abstraction (Claude, OpenAI)
│   ├── prompts.py       # Prompt templates for job analysis
│   └── matcher.py       # AI job matching and intake generation
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
