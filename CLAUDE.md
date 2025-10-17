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

### Integration with Portfolio Project

**IMPORTANT**: This tool is a **data pipeline** that feeds job matching data to the [Portfolio project](https://github.com/Jdubz/portfolio/).

- **No UI needed here**: All job review, analysis, and management happens in the Portfolio project's web interface
- **This tool's purpose**: Scrape jobs, analyze matches, store results in Firestore
- **Portfolio's purpose**: Display matched jobs, manage applications, generate tailored resumes
- **Data flow**: job-finder (scraping + AI analysis) → Firestore → portfolio (UI + user interaction)

When considering improvements or new features:
- ❌ **DO NOT** build a web UI, dashboard, or visualization in this project
- ✅ **DO** focus on improving scraping, filtering, matching quality, and data structure
- ✅ **DO** ensure data is properly structured for consumption by the Portfolio project

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

### Queue-Based Processing

The application uses a **Firestore-backed queue system** for asynchronous job processing. This allows the portfolio project to submit jobs for analysis, and this tool processes them in the background.

**Queue Collection**: `job-queue` in Firestore
**Processing**: Cloud Run worker polls queue and processes items in FIFO order

### Granular Pipeline Architecture (NEW)

Jobs are processed through a **4-step granular pipeline** that optimizes cost, memory, and reliability. Each step is an independent queue item that spawns the next step upon completion.

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ JOB_SCRAPE   │───▶│ JOB_FILTER   │───▶│ JOB_ANALYZE  │───▶│  JOB_SAVE    │
│              │    │              │    │              │    │              │
│ Claude Haiku │    │  Rule-based  │    │ Claude Sonnet│    │  Firestore   │
│ $0.001/1K    │    │   No AI ($0) │    │ $0.02-0.075/1K│    │    No AI     │
│              │    │              │    │              │    │              │
│ ~50KB memory │    │   ~50KB      │    │   ~200KB     │    │   ~50KB      │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
     │ FAILED             │ FILTERED          │ SKIPPED           │ SUCCESS
     └────────────────────┴───────────────────┴───────────────────┘
                    Pipeline stops at rejection points
```

**Pipeline Steps:**

1. **JOB_SCRAPE** (src/job_finder/queue/processor.py:_process_job_scrape)
   - Fetches HTML and extracts job data using source-specific selectors
   - Uses cheap AI model (Claude Haiku) for complex extraction when needed
   - Memory: ~50KB (job data only)
   - Cost: $0.001 per 1K tokens
   - On success: Spawns JOB_FILTER
   - On failure: Marks item as FAILED

2. **JOB_FILTER** (src/job_finder/queue/processor.py:_process_job_filter)
   - Applies strike-based filtering using rule engine
   - No AI involved - completely free
   - Memory: ~50KB + filter results
   - Cost: $0 (rule-based)
   - On pass: Spawns JOB_ANALYZE
   - On fail: Marks item as FILTERED

3. **JOB_ANALYZE** (src/job_finder/queue/processor.py:_process_job_analyze)
   - Runs AI matching with expensive model (Claude Sonnet)
   - Generates resume intake data and match score
   - Memory: ~200KB (job + company + analysis)
   - Cost: $0.015-0.075 per 1K tokens (only for filtered jobs!)
   - On score ≥ threshold: Spawns JOB_SAVE
   - On score < threshold: Marks item as SKIPPED

4. **JOB_SAVE** (src/job_finder/queue/processor.py:_process_job_save)
   - Saves job match to Firestore (job-matches collection)
   - Final step - no further spawning
   - Memory: ~50KB (minimal)
   - Cost: $0 (Firestore write)
   - Always: Marks item as SUCCESS

**Benefits:**
- **70% cost reduction**: Cheap models for scraping, expensive only for analysis
- **67% memory reduction**: Each step holds only necessary data (~100KB avg vs 585KB)
- **Better recovery**: Restart individual failed steps, not entire pipeline
- **Pay-as-you-go**: Only pay for AI on jobs that pass filtering
- **Clear observability**: Each step has distinct success/failure states

**Pipeline State Management:**

Each step passes data to the next via `pipeline_state` field:
```python
{
    "job_data": {...},           # From SCRAPE
    "scrape_method": "source",   # From SCRAPE
    "filter_result": {...},      # From FILTER
    "match_result": {...},       # From ANALYZE
}
```

**Backwards Compatibility:**

Legacy items (no `sub_task` field) still process monolithically through the original `_process_job()` method. Both approaches coexist seamlessly.

### Legacy Pipeline (Still Supported)

The application also supports a traditional five-stage pipeline for backwards compatibility:

1. **Profile Loading** - Load user profile data from JSON (src/job_finder/profile/loader.py:32)
2. **Scrape** - Site-specific scrapers collect job postings
3. **Basic Filter** - Traditional keyword/location filtering (src/job_finder/filters.py:12)
4. **AI Matching** - AI-powered job analysis and scoring (src/job_finder/ai/matcher.py:71)
5. **Store** - Results with AI analysis saved in configured format

This pipeline is orchestrated in `src/job_finder/main.py:main()` and `src/job_finder/queue/processor.py:_process_job()`.

### Scraper Pattern

All scrapers inherit from `BaseScraper` (src/job_finder/scrapers/base.py:5) which defines:
- `scrape()` - Main method that returns list of job dictionaries
- `parse_job()` - Parses individual job elements into standardized format

**Standard job dictionary structure:**
```python
{
    "title": str,              # Job title/role
    "company": str,            # Company name
    "company_website": str,    # Company website URL
    "company_info": str,       # Company culture/mission statements (optional)
    "location": str,           # Job location
    "description": str,        # Full job description
    "url": str,                # Job posting URL
    "posted_date": str,        # When the job was posted (optional)
    "salary": str,             # Salary range (optional)
    "keywords": List[str],     # Keywords for emphasis (populated by AI analysis)
}
```

**Note:** The `keywords` field is automatically populated by the AI analysis from the `keywords_to_include` field in the resume intake data. These keywords are extracted from the job description and profile analysis to help with ATS optimization and resume tailoring.

When adding a new job site scraper:
1. Create new file in `src/job_finder/scrapers/`
2. Inherit from `BaseScraper`
3. Implement `scrape()` and `parse_job()` methods
4. Return jobs in the standard dictionary format above

### Filtering System

The `JobFilter` class (src/job_finder/filters.py:6) applies multiple filter stages:
1. **Work location filtering** - Only remote jobs or Portland, OR hybrid jobs are allowed (always applied)
2. **Keyword matching** (inclusive) - Jobs must contain at least one keyword
3. **Location filtering** - Jobs must be in preferred locations
4. **Keyword exclusion** - Jobs cannot contain excluded keywords

The work location filter (src/job_finder/filters.py:42) ensures:
- Remote jobs are always included
- Portland, OR hybrid jobs are included
- All other in-office or hybrid jobs are filtered out

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
- **ClaudeProvider** (src/job_finder/ai/providers.py:30) - Anthropic Claude (recommended)
- **OpenAIProvider** (src/job_finder/ai/providers.py:64) - OpenAI GPT-4

Configure provider in `config/config.yaml` under the `ai` section.

**AI Model Selection & Cost Optimization:**

The system uses **task-based model selection** to optimize costs (src/job_finder/ai/providers.py:147):

```python
# Automatic model selection
from job_finder.ai import AITask, create_provider

# Use cheap model for scraping
scrape_provider = create_provider("claude", task=AITask.SCRAPE)
# → Uses Claude Haiku ($0.001/1K tokens)

# Use expensive model for analysis
analyze_provider = create_provider("claude", task=AITask.ANALYZE)
# → Uses Claude Sonnet ($0.015-0.075/1K tokens)
```

**Model Tiers:**
- **FAST** (cheap, fast): Claude Haiku, GPT-4o-mini
  - Used for: SCRAPE, SELECTOR_DISCOVERY
  - Cost: ~$0.001 per 1K tokens

- **SMART** (expensive, capable): Claude Sonnet, GPT-4
  - Used for: ANALYZE (job matching)
  - Cost: ~$0.02-0.075 per 1K tokens

**Cost Savings:**
By using cheap models for scraping and expensive models only for analysis of filtered jobs, the system achieves approximately **70% cost reduction** compared to using expensive models for all operations.

**Scoring Configuration:**
The system uses strict matching criteria with a minimum score threshold of 80 points (0-100 scale). Jobs at companies with Portland offices receive a +15 bonus, effectively lowering the threshold to 65 for local opportunities. Priority tiers are: High (85-100), Medium (70-84), Low (0-69). Scoring heavily weights exact title skill matches at Expert/Advanced levels and requires 95%+ of required skills for full points.

**Timezone Scoring:**
The system applies timezone-based score adjustments (src/job_finder/utils/timezone_utils.py) to prioritize jobs with teams in compatible timezones:
- Same timezone (Pacific): +5 bonus points
- 1-2 hour difference: -2 penalty
- 3-4 hour difference: -5 penalty
- 5-8 hour difference: -10 penalty
- 9+ hour difference: -15 penalty
- Unknown timezone: no adjustment

**Smart Timezone Detection** (src/job_finder/utils/timezone_utils.py:225):
The system uses intelligent prioritization when detecting timezones:
1. **Team location** mentioned in job description (e.g., "reporting to our Seattle team")
2. **Job location** specified in the listing
3. **Company headquarters** (only for small/medium companies)
4. **Large companies**: Assumed to be global, no HQ-based timezone penalty unless specific team location is mentioned

This prevents penalizing remote jobs at large global companies (Google, Microsoft, etc.) when the actual team timezone is unknown, while still applying timezone scoring for small/medium companies where HQ location is more relevant.

The timezone detection system recognizes US cities/states, major international cities, and explicit timezone mentions (PT, ET, GMT, etc.). Configure your timezone offset in `config.yaml` under `ai.user_timezone` (default: -8 for Pacific Time).

**Company Size Scoring:**
The system applies company size-based score adjustments (src/job_finder/utils/company_size_utils.py) based on your preference:
- Large companies (when prefer_large_companies=true): +10 bonus points
- Medium companies: no adjustment (neutral)
- Small companies/startups (when prefer_large_companies=true): -5 penalty

Large companies are detected through:
- Known major companies (Fortune 500, tech giants like Google, Microsoft, Amazon, etc.)
- Keywords: "Fortune 500", "10,000+ employees", "publicly traded", "enterprise", "multinational"
- Patterns indicating size in company info and job descriptions

Small companies/startups are detected through:
- Keywords: "startup", "small team", "Series A/B funding", "seed stage", "bootstrapped"
- Employee count mentions under 100

Configure your preference in `config.yaml` under `ai.prefer_large_companies` (default: true).

**Company Information Fetching:**
The `CompanyInfoFetcher` (src/job_finder/company_info_fetcher.py) automatically scrapes company websites for about/culture/mission information and caches it in Firestore via `CompaniesManager` (src/job_finder/storage/companies_manager.py). This information is included in AI job analysis prompts to provide better context for cultural fit assessment. The system uses AI extraction with heuristics fallback and smart caching (only re-fetches if cached data is sparse).

**Company Data Storage:**
Company records in Firestore (src/job_finder/storage/companies_manager.py:64) include:
- Basic info: name, website, about, culture, mission, industry, founded
- **company_size_category**: Detected size ("large", "medium", "small") - used for scoring and timezone logic
- **headquarters_location**: Company HQ location - used as timezone fallback for small/medium companies
- Size and HQ data are automatically detected and stored for use in match scoring

**Company Scraping Prioritization:**
Job listing sources are scored to prioritize scraping: Portland office (+50 points), tech stack alignment (up to 100 points based on user expertise), and company attributes like remote-first (+15) or AI/ML focus (+10). Companies are grouped into tiers: S (150+), A (100-149), B (70-99), C (50-69), D (0-49), with higher-tier companies scraped more frequently in rotation.

### Source Configuration & Health Tracking

The `JobSourcesManager` (src/job_finder/storage/job_sources_manager.py) manages job source configurations stored in Firestore (`job-sources` collection).

**Source Configuration:**
Each source includes:
- **sourceType**: greenhouse, rss, workday, api, scraper
- **config**: Source-specific configuration (selectors, API keys, etc.)
- **enabled**: Whether source is active
- **health**: Success/failure tracking

**Smart URL Matching:**

The system can automatically match URLs to configured sources (src/job_finder/storage/job_sources_manager.py:417):

```python
# Find source config by URL
source = sources_manager.get_source_for_url("https://boards.greenhouse.io/netflix/jobs/123")
# Returns: Netflix Greenhouse config with selectors
```

**AI-Powered Selector Discovery:**

When encountering a new job board, the system can use AI to discover CSS selectors (src/job_finder/ai/selector_discovery.py):

```python
from job_finder.ai import SelectorDiscovery

discovery = SelectorDiscovery(provider_type="claude")
selectors = discovery.discover_selectors(html, url)
# Returns: {"title": ".job-title", "company": ".company-name", ...}

# Save discovered selectors
sources_manager.save_discovered_source(
    url=url,
    name="NewSite Jobs",
    source_type="scraper",
    selectors=selectors,
    confidence="high"
)
```

**Health Tracking & Auto-Disable:**

Sources are monitored for reliability (src/job_finder/storage/job_sources_manager.py:571):

```python
# Record scraping failure
sources_manager.record_scraping_failure(
    source_id="source-123",
    error_message="Selector not found",
    selector_failures=["title"]
)
# After 5 consecutive failures → auto-disabled

# Record success (resets failure counter)
sources_manager.record_scraping_success(
    source_id="source-123",
    jobs_found=10
)
```

**Selector Fallback Chains:**

Sources can have alternative selectors for resilience (src/job_finder/storage/job_sources_manager.py:538):

```python
sources_manager.update_source_selectors(
    source_id="source-123",
    selectors={"title": ".job-title"},
    alternative_selectors=[
        {"title": ".alt-title"},
        {"title": "h1.position"}
    ]
)
```

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
