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

### Project Management

**IMPORTANT**: This repository is part of a multi-repository project managed centrally.

- **Task Tracking**: ALL task tracking is done in [job-finder-app-manager](https://github.com/Jdubz/job-finder-app-manager)
- **Worker Assignment**: Check `CLAUDE_WORKER_A.md` in the manager repo for your assigned tasks
- **Workflow**: Work in dedicated worktree on your worker branch, submit PRs to `staging`
- **Documentation**: Architecture and setup docs live here, project management lives in manager repo

**This Repository's Purpose:**
- Queue worker that processes jobs from Firestore
- Scrapes job boards and analyzes matches with AI
- Stores results in Firestore for frontend consumption
- No UI - frontend lives in `job-finder-FE` repository

**Shared Resources:**
- **Firestore Collections**: `job-queue`, `job-matches`, `companies`, `job-sources`
- **Google Cloud Logging**: Structured logs with environment labels for real-time monitoring (see [CLOUD_LOGGING_DESIGN.md](docs/CLOUD_LOGGING_DESIGN.md))

**Integration:**
- **Frontend**: [job-finder-FE](https://github.com/Jdubz/job-finder-FE) - React UI for job review and management
- **Backend**: [job-finder-BE](https://github.com/Jdubz/job-finder-BE) - Firebase Cloud Functions API
- **Shared Types**: [job-finder-shared-types](https://github.com/Jdubz/job-finder-shared-types) - TypeScript types for Firestore

When considering improvements or new features:
- ❌ **DO NOT** create tasks or roadmaps in this repo - use manager repo
- ❌ **DO NOT** build a web UI, dashboard, or visualization in this project
- ✅ **DO** focus on improving scraping, filtering, matching quality, and data structure
<<<<<<< HEAD
- ✅ **DO** ensure data is properly structured for consumption by the job-finder-FE project
=======
- ✅ **DO** ensure data is properly structured for consumption by the frontend
>>>>>>> 66f46a9 (Clean up documentation: Remove task tracking, update project references)
- ✅ **DO** use structured logging for visibility into worker operations

## Commands

### Local Development (Recommended)

**For local development, use the dev-monitor tool which manages all services including the Python worker via Docker.**

```bash
# Navigate to the dev-monitor directory (in job-finder-app-manager repo)
cd ../dev-monitor

# Start all services including Python worker container
make dev-monitor

# View worker logs
tail -f logs/queue_worker.log

# Restart worker after code changes
make restart-worker

# Access dev-monitor web UI
open http://localhost:5174
```

The dev-monitor manages:
- Firebase Emulators (Firestore on localhost:8080)
- Python Worker (Docker container)
- Frontend dev server
- Backend Firebase Functions

**Worker logs location:** `dev-monitor/logs/queue_worker.log`

### Setup (For Manual Testing Only)

For running tests or scripts outside of dev-monitor:

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Running the Worker

**Primary method - via dev-monitor:**
```bash
cd ../dev-monitor
make dev-monitor  # Starts worker in Docker container
```

**Alternative - manual queue worker (not recommended):**
```bash
# Only use this for testing specific configurations
source venv/bin/activate
GOOGLE_APPLICATION_CREDENTIALS="credentials/serviceAccountKey.json" \
STORAGE_DATABASE_NAME="portfolio-staging" \
python scripts/workers/queue_worker.py
```

**Note**: The legacy monolithic mode (`python -m job_finder.main`) has been removed. All job processing now happens through the queue-based worker system.

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
**Processing**: Worker container (running in Portainer on NAS) polls queue and processes items in FIFO order

**Worker Deployment**:
- **Location**: Portainer stack `job-finder-staging` running on NAS
- **Container**: `job-finder-staging` (image: `ghcr.io/jdubz/job-finder:staging`)
- **Database**: `portfolio-staging` Firestore database
- **Logging**: Google Cloud Logging (log name: `job-finder`)

**Monitoring Worker**:
```bash
# Check staging worker logs (with environment labels)
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" AND labels.environment="staging"' \
  --limit 20 \
  --freshness 1h

# Check production worker logs
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" AND labels.environment="production"' \
  --limit 20 \
  --freshness 1h

# Filter by specific operation types (structured logging)
# Worker status
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" AND labels.environment="staging" AND textPayload:"[WORKER]"' \
  --limit 10

# Queue processing
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" AND labels.environment="staging" AND textPayload:"[QUEUE:"' \
  --limit 10

# Pipeline stages
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" AND labels.environment="staging" AND textPayload:"[PIPELINE:"' \
  --limit 10
```

**Structured Logging Format**:
All logs use a structured format with categories for easy filtering:
- `[WORKER]` - Worker lifecycle events (started, idle, stopped)
- `[QUEUE:type]` - Queue item processing (JOB, COMPANY, SCRAPE)
- `[PIPELINE:stage]` - Pipeline stages (SCRAPE, FILTER, ANALYZE, SAVE)
- `[SCRAPE]` - Web scraping operations
- `[AI:operation]` - AI model operations (MATCH, ANALYZE, EXTRACT)
- `[DB:operation]` - Database operations (CREATE, UPDATE, QUERY)

**Environment Labels**:
All Cloud Logging entries include labels for filtering:
- `environment`: staging, production, or development
- `service`: job-finder
- `version`: 1.0.0

**Worker Configuration** (docker-compose.staging.yml):
- `ENABLE_QUEUE_MODE=true` - Queue worker enabled
- `ENABLE_CRON=false` - No automatic scraping (manual submissions only)
- `ENABLE_CLOUD_LOGGING=true` - Logs sent to Google Cloud with environment labels
- `ENVIRONMENT=staging` - Environment identifier (added to all logs)
- `STORAGE_DATABASE_NAME=portfolio-staging` - Firestore database

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

### Granular Company Pipeline (NEW)

Companies are processed through a **4-step granular pipeline** similar to job processing, optimizing cost and enabling intelligent analysis.

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ COMPANY_FETCH    │───▶│ COMPANY_EXTRACT  │───▶│ COMPANY_ANALYZE  │───▶│  COMPANY_SAVE    │
│                  │    │                  │    │                  │    │                  │
│ Fetch website    │    │ AI extraction    │    │ Tech stack       │    │  Firestore       │
│ HTML content     │    │ about/culture    │    │ Job board detect │    │  +source queue   │
│                  │    │                  │    │ Priority scoring │    │                  │
│ Claude Haiku     │    │ Claude Sonnet    │    │  Rule-based      │    │    No AI         │
│ $0.001/1K        │    │ $0.015-0.075/1K  │    │      $0          │    │     $0           │
│                  │    │                  │    │                  │    │                  │
│ ~100KB memory    │    │   ~150KB         │    │    ~100KB        │    │   ~50KB          │
└──────────────────┘    └──────────────────┘    └──────────────────┘    └──────────────────┘
     │ FAILED                 │ FAILED                │ SKIPPED              │ SUCCESS
     └────────────────────────┴───────────────────────┴──────────────────────┘
                         Pipeline stops at rejection points
```

**Pipeline Steps:**

1. **COMPANY_FETCH** (src/job_finder/queue/processor.py:_process_company_fetch)
   - Scrapes 5 common pages: `/about`, `/about-us`, `/company`, `/careers`, homepage
   - Uses cheap AI (Haiku) for dynamic content if needed
   - Memory: ~100KB (HTML content)
   - Cost: $0.001 per 1K tokens
   - On success: Spawns COMPANY_EXTRACT
   - On failure: Marks item as FAILED

2. **COMPANY_EXTRACT** (src/job_finder/queue/processor.py:_process_company_extract)
   - Extracts company info using AI: about, culture, mission, size, HQ, industry
   - Uses expensive AI (Sonnet) for accurate extraction
   - Fallback to heuristics if AI fails
   - Memory: ~150KB (HTML + extracted data)
   - Cost: $0.015-0.075 per 1K tokens
   - On success: Spawns COMPANY_ANALYZE
   - On failure: Marks item as FAILED

3. **COMPANY_ANALYZE** (src/job_finder/queue/processor.py:_process_company_analyze)
   - **Tech Stack Detection**: Pattern matching from company info + job listings
   - **Job Board Discovery**: Detects Greenhouse, Workday, RSS feeds, custom boards
   - **Priority Scoring**: Calculates tier (S/A/B/C/D) based on:
     - Portland office: +50 points
     - Tech stack alignment: up to +100 points
     - Company attributes: remote-first (+15), AI/ML focus (+10)
   - Memory: ~100KB (extracted data + analysis)
   - Cost: $0 (rule-based)
   - On complete: Spawns COMPANY_SAVE
   - On skip: Marks item as SKIPPED (insufficient data)

4. **COMPANY_SAVE** (src/job_finder/queue/processor.py:_process_company_save)
   - Saves company record to Firestore with tech stack and tier
   - If job board found: Spawns SOURCE_DISCOVERY queue item automatically
   - Updates analysis_status to "complete"
   - Memory: ~50KB (minimal)
   - Cost: $0 (Firestore write)
   - Always: Marks item as SUCCESS

**Company Pipeline Benefits:**
- **70% cost reduction**: Cheap AI for fetch, expensive only for extraction
- **67% memory reduction**: Each step holds only necessary data (~100KB avg)
- **Automatic job board discovery**: Creates SOURCE_DISCOVERY items for found boards
- **Priority-based scheduling**: S/A tier companies scraped more frequently
- **Tech stack insights**: Automatic detection helps with job matching

**Company Pipeline State:**

Each step passes data via `pipeline_state`:
```python
{
    "company_name": "Example Corp",
    "company_website": "https://example.com",
    "html_content": {...},        # From FETCH
    "extracted_info": {...},      # From EXTRACT
    "analysis_result": {          # From ANALYZE
        "tech_stack": ["python", "react"],
        "job_board_url": "https://boards.greenhouse.io/example",
        "priority_score": 105,
        "tier": "A"
    }
}
```

**Submitting Companies for Analysis:**

```python
from job_finder.queue.scraper_intake import ScraperIntake

intake = ScraperIntake(queue_manager)

# Submit company to granular pipeline
doc_id = intake.submit_company(
    company_name="Example Corp",
    company_website="https://example.com",
    source="user_submission"
)
# Returns: Document ID of the created queue item, or None if failed/duplicate
```

**BREAKING CHANGE:** All pipeline processing now uses the granular 4-step system.

**Job items REQUIRE `sub_task`** - all job processing uses the granular pipeline exclusively (JOB_SCRAPE → JOB_FILTER → JOB_ANALYZE → JOB_SAVE).

**Company items REQUIRE `company_sub_task`** - all company processing uses the granular pipeline exclusively (COMPANY_FETCH → COMPANY_EXTRACT → COMPANY_ANALYZE → COMPANY_SAVE).

### Legacy Code Removed

The following legacy components have been **removed** from the codebase:

1. **Monolithic job pipeline** - `_process_job()` method removed from processor.py
2. **JobFilter class** - src/job_finder/filters/job_filter.py removed (use StrikeFilterEngine instead)
3. **Job-level keywords field** - Removed from job dictionaries (ATS keywords now only in resumeIntakeData.atsKeywords)

The `main.py` file is now only used for development/testing purposes. All production job processing happens via the queue system and granular pipeline.

### Scraper Pattern

All scrapers inherit from `BaseScraper` (src/job_finder/scrapers/base.py:5) which defines:
- `scrape()` - Main method that returns list of job dictionaries
- `parse_job()` - Parses individual job elements into standardized format

**Standard job dictionary structure:**
```python
{
    # REQUIRED FIELDS (must be present for all jobs)
    "title": str,              # Job title/role
    "company": str,            # Company name
    "company_website": str,    # Company website URL
    "location": str,           # Job location
    "description": str,        # Full job description
    "url": str,                # Job posting URL (unique identifier)

    # OPTIONAL FIELDS (may be None if not available on job page)
    "posted_date": str,        # Job posting date (None if not found)
    "salary": str,             # Salary range (None if not listed)

    # ADDED DURING PROCESSING (not from scraper)
    "company_info": str,       # Company about/culture (fetched via CompanyInfoFetcher)
    "companyId": str,          # Firestore company document ID (added during analysis)
}
```

**REMOVED FIELD:** `keywords` - This field has been removed from the job-level structure. ATS keywords are now **only** stored in `resumeIntakeData.atsKeywords` (AI-generated during job analysis). Scrapers should NOT populate any keywords field.

When adding a new job site scraper:
1. Create new file in `src/job_finder/scrapers/`
2. Inherit from `BaseScraper`
3. Implement `scrape()` and `parse_job()` methods
4. Return jobs in the standard dictionary format above

### Filtering System

The `StrikeFilterEngine` (src/job_finder/filters/strike_filter_engine.py) uses a **two-tier filtering system**:

1. **Hard Rejections** - Immediate disqualification for deal-breakers:
   - Non-remote jobs (unless Portland, OR hybrid)
   - Excluded companies or keywords
   - Job types that don't match preferences (e.g., management roles for IC preference)

2. **Strike Accumulation** - Points-based system (threshold: 5 strikes):
   - Location mismatches (non-Portland, non-remote): 2-3 strikes
   - Seniority mismatches: 2-3 strikes
   - Tech stack mismatches: 1-3 strikes per missing skill
   - Experience level mismatches: 2-3 strikes

Jobs are rejected if they hit a hard rejection OR accumulate 5+ strikes.

**Legacy JobFilter removed** - Use StrikeFilterEngine instead for all filtering.

Filters are configured in `config/config.yaml` under the `filters` section and `config/job-filters.yaml`.

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

### Source Submission System

**job-finder-FE Integration** (src/job_finder/queue/processor.py:1032):

Users can submit job board URLs through the job-finder-FE UI for automated discovery and configuration. The system supports:

**Supported Source Types:**
- **Greenhouse**: boards.greenhouse.io/* (API validation, high confidence)
- **Workday**: *.myworkdayjobs.com/* (requires manual validation, medium confidence)
- **RSS Feeds**: *.xml, */feed, */rss (feed format validation, high confidence)
- **Generic HTML**: Any career page (AI selector discovery, variable confidence)

**Submission Flow:**

```typescript
// In job-finder-FE project
const queueItem: QueueItem = {
  type: 'source_discovery',
  url: '',  // Not used for source_discovery
  company_name: companyName || '',
  company_id: companyId,
  source: 'user_submission',
  submitted_by: currentUser.uid,
  source_discovery_config: {
    url: 'https://boards.greenhouse.io/stripe',
    type_hint: 'auto',  // or 'greenhouse', 'workday', 'rss', 'generic'
    company_id: companyId,
    company_name: companyName,
    auto_enable: true,
    validation_required: false,
  },
  status: 'pending',
  created_at: new Date(),
}

await db.collection('job-queue').add(queueItem)
```

**Discovery Process:**

1. **Type Detection** (src/job_finder/utils/source_type_detector.py:25):
   - Auto-detects from URL patterns
   - Extracts configuration (board_token, company_id, etc.)
   - Infers company name from URL

2. **Validation**:
   - **Greenhouse**: Fetches API to verify jobs exist
   - **Workday**: Basic validation (full scraping requires manual testing)
   - **RSS**: Parses feed to verify format
   - **Generic**: Uses AI to discover CSS selectors

3. **Source Creation** (src/job_finder/storage/job_sources_manager.py:538):
   - Creates job-source document with discovered config
   - Sets confidence level (high/medium/low)
   - Auto-enables high confidence sources
   - Flags low confidence for manual validation

4. **Result Notification**:
   - Success: Returns source_id in queue item result_message
   - Failure: Returns error details in result_message

**Monitoring Submission:**

```typescript
// Monitor queue item for completion
db.collection('job-queue')
  .doc(queueItemId)
  .onSnapshot(snapshot => {
    const item = snapshot.data()

    if (item.status === 'success') {
      const sourceId = item.result_message  // Contains source ID
      console.log(`Source created: ${sourceId}`)
    } else if (item.status === 'failed') {
      console.error(`Discovery failed: ${item.result_message}`)
    }
  })
```

**Confidence Levels:**
- **High**: Greenhouse (API validated), RSS (valid feed) → Auto-enabled
- **Medium**: Workday (needs testing) → Requires validation
- **Low**: Generic AI discovery → Requires validation

For detailed implementation, see [SOURCE_SUBMISSION_DESIGN.md](docs/SOURCE_SUBMISSION_DESIGN.md).

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
├── main.py              # Legacy entry point (dev/testing only)
├── storage.py           # JobStorage class - JSON/CSV output
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
├── filters/
│   ├── __init__.py
│   ├── strike_filter_engine.py  # Two-tier filtering system
│   ├── filter_engine.py         # Filter rule engine
│   └── models.py                # FilterResult, FilterRejection models
├── queue/
│   ├── __init__.py
│   ├── processor.py     # Granular pipeline processor (JOB_*, COMPANY_*)
│   ├── manager.py       # Queue item management
│   └── models.py        # JobQueueItem, JobSubTask models
├── storage/
│   ├── __init__.py
│   ├── firestore_storage.py     # Job matches storage
│   ├── companies_manager.py     # Company data management
│   └── job_sources_manager.py   # Job source configs
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
