# Issue Context - job-finder-worker

> **Purpose**: This document provides standard context referenced by all issues in this repository. It eliminates redundant information and keeps issues focused on specific tasks.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Repository Structure](#repository-structure)
3. [Technology Stack](#technology-stack)
4. [Development Environment](#development-environment)
5. [Testing](#testing)
6. [Code Standards](#code-standards)
7. [Common Patterns](#common-patterns)
8. [Related Documentation](#related-documentation)

---

## Project Overview

**job-finder-worker** is a Python-based queue worker that processes job scraping and analysis tasks from Firestore. It is part of a multi-repository Job Finder application.

### What This Repository Does
- Scrapes job boards (Greenhouse, Workday, RSS, custom HTML)
- Processes jobs through granular AI pipeline
- Analyzes job fit using Claude AI
- Stores matched jobs in Firestore
- Manages company information and job sources

### What This Repository Does NOT Do
- ❌ Provide user interface (handled by `job-finder-FE`)
- ❌ Serve HTTP API endpoints (handled by `job-finder-BE`)
- ❌ Manage user authentication (handled by Firebase Auth)

### Multi-Repository Architecture

This repository is one of four:

1. **job-finder-worker** (THIS REPO) - Queue worker, scraping, AI matching
2. **job-finder-FE** - React frontend UI
3. **job-finder-BE** - Firebase Cloud Functions API
4. **job-finder-shared-types** - TypeScript type definitions

**Project Manager Repository**: `job-finder-app-manager` contains:
- Cross-repository coordination
- Task tracking and prioritization
- Workflow documentation
- Issue templates

### Integration Points

**Firestore Collections** (shared with other repos):
- `job-queue` - Asynchronous task queue
- `job-matches` - Analyzed job matches
- `companies` - Company information cache
- `job-sources` - Job board configurations

**APIs Consumed**:
- Anthropic Claude API (AI matching)
- OpenAI GPT-4 API (alternative AI provider)
- Various job board APIs (Greenhouse, Workday)

**APIs Provided**:
- None (this is a worker, not an API server)
- Data is written to Firestore for consumption by frontend

---

## Repository Structure

```
job-finder-worker/
├── src/job_finder/              # Main application code
│   ├── ai/                      # AI providers and matching logic
│   │   ├── providers.py         # Claude, OpenAI providers
│   │   ├── matcher.py           # Job matching engine
│   │   ├── prompts.py           # AI prompt templates
│   │   └── selector_discovery.py # AI-powered selector discovery
│   ├── filters/                 # Filtering system
│   │   ├── strike_filter_engine.py # Two-tier filter system
│   │   ├── filter_engine.py     # Rule engine
│   │   └── models.py            # Filter data models
│   ├── queue/                   # Queue processing
│   │   ├── processor.py         # Granular pipeline processor
│   │   ├── manager.py           # Queue management
│   │   ├── scraper_intake.py   # Job/company submission
│   │   └── models.py            # Queue data models
│   ├── scrapers/                # Web scrapers
│   │   ├── base.py              # BaseScraper abstract class
│   │   ├── greenhouse_scraper.py
│   │   ├── workday_scraper.py
│   │   └── rss_scraper.py
│   ├── storage/                 # Data persistence
│   │   ├── firestore_storage.py # Job matches storage
│   │   ├── companies_manager.py # Company data management
│   │   └── job_sources_manager.py # Job source configs
│   ├── utils/                   # Utility modules
│   │   ├── url_utils.py         # URL manipulation
│   │   ├── timezone_utils.py    # Timezone detection
│   │   ├── company_size_utils.py # Company size detection
│   │   ├── source_type_detector.py # Job board type detection
│   │   └── logger.py            # Structured logging
│   ├── profile/                 # User profile management
│   │   ├── schema.py            # Pydantic models
│   │   ├── loader.py            # JSON profile loader
│   │   └── firestore_loader.py  # Firestore profile loader
│   └── main.py                  # Legacy entry point (dev only)
├── tests/                       # Test suite
│   ├── queue/                   # Queue tests
│   ├── filters/                 # Filter tests
│   ├── scrapers/                # Scraper tests
│   ├── utils/                   # Utility tests
│   └── e2e/                     # End-to-end tests
├── scripts/                     # Utility scripts
│   ├── database/                # Database management
│   ├── workers/                 # Worker scripts
│   └── testing/                 # Test helpers
├── docs/                        # Documentation
│   ├── architecture.md          # System architecture
│   ├── queue-system.md          # Queue system guide
│   ├── development.md           # Development guide
│   ├── deployment.md            # Deployment guide
│   └── issues/                  # Issue tracking
└── config/                      # Configuration files
    └── config.yaml              # Main configuration
```

---

## Technology Stack

### Core Technologies
- **Language**: Python 3.11+
- **Package Management**: pip, virtualenv
- **Configuration**: YAML (config/config.yaml)
- **Data Validation**: Pydantic

### External Services
- **Database**: Google Cloud Firestore
- **Logging**: Google Cloud Logging
- **AI Provider**: Anthropic Claude API (primary), OpenAI GPT-4 (alternative)
- **Deployment**: Docker (Portainer on NAS)

### Key Libraries
- **Web Scraping**: requests, beautifulsoup4, lxml
- **AI/LLM**: anthropic, openai
- **Cloud**: google-cloud-firestore, google-cloud-logging
- **Testing**: pytest, pytest-cov
- **Code Quality**: black (formatting), flake8 (linting), mypy (type checking)

### Python Version
- **Minimum**: 3.11
- **Recommended**: 3.12

---

## Development Environment

### Prerequisites

```bash
# Required
Python 3.11+
pip 23+
virtualenv

# Optional but recommended
make (for Makefile commands)
docker (for local Firestore emulator)
```

### Initial Setup

```bash
# 1. Navigate to repository
cd /path/to/job-finder-worker

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 4. Install dependencies
pip install -r requirements.txt

# 5. Install in development mode
pip install -e ".[dev]"

# 6. Set up environment variables
cp .env.example .env
# Edit .env with your credentials
```

### Environment Variables

Required environment variables (in `.env`):

```bash
# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=path/to/serviceAccountKey.json

# AI APIs
ANTHROPIC_API_KEY=your-claude-api-key
OPENAI_API_KEY=your-openai-api-key  # Optional

# Firestore
STORAGE_DATABASE_NAME=portfolio-staging  # or portfolio

# Logging
ENABLE_CLOUD_LOGGING=true
ENVIRONMENT=development  # or staging, production

# Queue
ENABLE_QUEUE_MODE=true
ENABLE_CRON=false
```

### Running Locally

```bash
# Run queue worker (processes items from Firestore)
python scripts/workers/queue_worker.py

# Run with specific config
python -m job_finder.main --config config/config.yaml

# Run specific scraper (testing)
python -m job_finder.scrapers.greenhouse_scraper
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src/job_finder --cov-report=html

# Run specific test file
pytest tests/queue/test_scraper_intake.py

# Run specific test function
pytest tests/queue/test_scraper_intake.py::test_submit_job -v

# Run tests matching pattern
pytest -k "test_url"

# Run with verbose output
pytest -v

# Run with print statements visible
pytest -s
```

### Test Structure

```
tests/
├── conftest.py                  # Pytest fixtures
├── queue/
│   ├── test_processor.py        # Queue processing tests
│   ├── test_scraper_intake.py   # Job/company submission tests
│   └── test_queue_manager.py    # Queue management tests
├── filters/
│   └── test_strike_filter_engine.py
├── utils/
│   ├── test_url_utils.py
│   ├── test_timezone_utils.py
│   └── test_company_size_utils.py
└── e2e/
    └── test_end_to_end_pipeline.py
```

### Writing Tests

**Good Test Pattern**:
```python
import pytest
from job_finder.queue.scraper_intake import ScraperIntake

def test_submit_job_success(mock_queue_manager):
    """Test successful job submission to queue"""
    intake = ScraperIntake(mock_queue_manager)

    job_data = {
        "title": "Senior Python Developer",
        "company": "Example Corp",
        "url": "https://example.com/jobs/123",
        "location": "Remote",
        "description": "We are looking for...",
    }

    doc_id = intake.submit_job(job_data, source="test")

    assert doc_id is not None
    assert isinstance(doc_id, str)
```

### Test Coverage Requirements
- **Target**: 80%+ code coverage
- **Priority**: Critical paths (queue processing, filtering, AI matching)
- **Focus**: Unit tests for utilities, integration tests for pipelines

---

## Code Standards

### Python Style Guide

**Follow PEP 8** with these specifics:
- **Line Length**: 100 characters (not 79)
- **Indentation**: 4 spaces (no tabs)
- **Imports**: Organize as stdlib, third-party, local
- **Docstrings**: Google style
- **Type Hints**: Required for function signatures

### Code Formatting

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

### Naming Conventions

**Files/Modules**: `snake_case.py`
```python
# Good
url_utils.py
scraper_intake.py

# Bad
UrlUtils.py
scraperIntake.py
```

**Classes**: `PascalCase`
```python
# Good
class ScraperIntake:
class JobQueueManager:

# Bad
class scraper_intake:
class jobQueueManager:
```

**Functions/Variables**: `snake_case`
```python
# Good
def normalize_url(url: str) -> str:
job_data = {"title": "..."}

# Bad
def normalizeUrl(url: str) -> str:
jobData = {"title": "..."}
```

**Constants**: `UPPER_SNAKE_CASE`
```python
# Good
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Bad
maxRetries = 3
default_timeout = 30
```

### Documentation

**Module Docstrings** (at top of file):
```python
"""Module for job queue processing.

This module provides classes and functions for managing
the Firestore-backed job queue system.
"""
```

**Function Docstrings**:
```python
def normalize_job_url(url: str) -> str:
    """Normalize a job URL for duplicate detection.

    Args:
        url: Raw job URL from scraper

    Returns:
        Normalized URL with tracking params removed

    Raises:
        ValueError: If URL is invalid or empty
    """
```

**Class Docstrings**:
```python
class ScraperIntake:
    """Handles submission of jobs and companies to the queue.

    This class provides methods for adding items to the Firestore
    queue with duplicate detection and validation.

    Attributes:
        queue_manager: QueueManager instance for queue operations
        logger: Logger instance for structured logging
    """
```

### Logging Standards

**Use Structured Logging**:
```python
from job_finder.utils.logger import get_logger

logger = get_logger(__name__)

# Good - structured with context
logger.info(
    "[QUEUE:JOB] Processing job submission",
    extra={
        "job_url": job_url,
        "company": company_name,
        "source": source,
    }
)

# Bad - unstructured
logger.info(f"Processing job from {company_name}")
```

**Logging Categories** (use in square brackets):
- `[WORKER]` - Worker lifecycle events
- `[QUEUE:type]` - Queue processing (JOB, COMPANY, SCRAPE)
- `[PIPELINE:stage]` - Pipeline stages
- `[SCRAPE]` - Web scraping operations
- `[AI:operation]` - AI operations
- `[DB:operation]` - Database operations

### Error Handling

```python
# Good - specific exceptions with context
try:
    result = process_job(job_data)
except ValidationError as e:
    logger.error(
        "[QUEUE:JOB] Validation failed",
        extra={"error": str(e), "job_url": job_data.get("url")}
    )
    raise
except Exception as e:
    logger.exception(
        "[QUEUE:JOB] Unexpected error",
        extra={"job_url": job_data.get("url")}
    )
    raise

# Bad - catch all with no context
try:
    result = process_job(job_data)
except:
    logger.error("Error")
    raise
```

---

## Common Patterns

### Submitting Jobs to Queue

```python
from job_finder.queue.scraper_intake import ScraperIntake
from job_finder.queue.manager import QueueManager

# Initialize
queue_manager = QueueManager()
intake = ScraperIntake(queue_manager)

# Submit job (uses granular pipeline)
job_data = {
    "title": "Senior Python Developer",
    "company": "Example Corp",
    "company_website": "https://example.com",
    "url": "https://example.com/jobs/123",
    "location": "Remote",
    "description": "Full job description...",
    "posted_date": "2025-10-19",
    "salary": "$150k-$200k",
}

doc_id = intake.submit_job(
    job_data=job_data,
    source="greenhouse",  # or "user_submission", "rss", etc.
)

# Returns: Document ID or None if duplicate/failed
```

### Submitting Companies to Queue

```python
# Submit company for analysis
doc_id = intake.submit_company(
    company_name="Example Corp",
    company_website="https://example.com",
    source="user_submission"
)

# Company goes through granular pipeline:
# COMPANY_FETCH → COMPANY_EXTRACT → COMPANY_ANALYZE → COMPANY_SAVE
```

### Accessing Firestore

```python
from job_finder.storage.firestore_storage import FirestoreStorage

# Get Firestore client
db = FirestoreStorage.get_client(database_name="portfolio-staging")

# Query collection
jobs = db.collection("job-queue").where("status", "==", "pending").limit(10).stream()

for job in jobs:
    job_data = job.to_dict()
    print(f"Job: {job_data['company']}")
```

### Using AI Providers

```python
from job_finder.ai import create_provider, AITask

# Create provider for specific task
# (automatically selects appropriate model)
provider = create_provider("claude", task=AITask.ANALYZE)

# Use for job matching
result = provider.analyze_job(job_data, profile, company_info)

# Result contains:
# - match_score (0-100)
# - matched_skills
# - skill_gaps
# - resume_intake_data
```

### URL Normalization

```python
from job_finder.utils.url_utils import normalize_url

# Normalize for duplicate detection
raw_url = "https://example.com/jobs/123?utm_source=linkedin&ref=social"
normalized = normalize_url(raw_url)
# Returns: "https://example.com/jobs/123"

# Handles:
# - Lowercase
# - Remove tracking params (utm_*, ref, source, etc.)
# - Strip trailing slashes
# - Normalize www subdomain
```

### Timezone Detection

```python
from job_finder.utils.timezone_utils import detect_timezone, get_timezone_offset

# Detect from location string
tz_offset = detect_timezone(
    location="Seattle, WA",
    company_hq="San Francisco",
    company_size="large"
)

# Returns: -8 (Pacific Time)
```

---

## Related Documentation

### Core Documentation (in this repo)
- **[CLAUDE.md](../../CLAUDE.md)** - AI assistant context and overview
- **[README.md](../../README.md)** - Getting started guide
- **[docs/architecture.md](../architecture.md)** - System architecture
- **[docs/queue-system.md](../queue-system.md)** - Queue system guide
- **[docs/development.md](../development.md)** - Development practices
- **[docs/deployment.md](../deployment.md)** - Deployment procedures

### Architecture Documentation
- **[docs/STATE_DRIVEN_PIPELINE_DESIGN.md](../STATE_DRIVEN_PIPELINE_DESIGN.md)** - Granular pipeline architecture
- **[docs/GRANULAR_PIPELINE_DEPLOYMENT.md](../GRANULAR_PIPELINE_DEPLOYMENT.md)** - Pipeline deployment guide
- **[docs/CLOUD_LOGGING_DESIGN.md](../CLOUD_LOGGING_DESIGN.md)** - Structured logging design

### API Documentation
- **[docs/SOURCE_SUBMISSION_API.md](../SOURCE_SUBMISSION_API.md)** - Job board submission API
- **[docs/SOURCE_SUBMISSION_DESIGN.md](../SOURCE_SUBMISSION_DESIGN.md)** - Submission system design

### Integration Documentation
- **[docs/FRONTEND_CONFIG.md](../FRONTEND_CONFIG.md)** - Frontend integration
- **[docs/shared-types.md](../shared-types.md)** - Shared TypeScript types

### Operational Documentation
- **[docs/STAGING_VS_PRODUCTION.md](../STAGING_VS_PRODUCTION.md)** - Environment differences
- **[docs/PRODUCTION_QUEUE_TROUBLESHOOTING.md](../PRODUCTION_QUEUE_TROUBLESHOOTING.md)** - Troubleshooting guide
- **[docs/PORTAINER_QUICK_START.md](../PORTAINER_QUICK_START.md)** - Portainer deployment

### Manager Repository Documentation
- **[job-finder-app-manager](https://github.com/Jdubz/job-finder-app-manager)** - Project management hub
- **CLAUDE_WORKER_A.md** (in manager) - Worker A context and tasks
- **PROJECT_TASK_LIST.md** (in manager) - Cross-repo task tracking

---

## Quick Reference

### Common Commands

```bash
# Development
source venv/bin/activate
python scripts/workers/queue_worker.py
pytest

# Code Quality
black src/ tests/
flake8 src/ tests/
mypy src/

# Testing
pytest -v
pytest --cov=src/job_finder --cov-report=html
pytest tests/queue/

# Database
python scripts/database/cleanup_job_matches.py
```

### Key File Paths

```
Configuration:     config/config.yaml
Credentials:       credentials/serviceAccountKey.json
Environment:       .env
Tests:             tests/
Documentation:     docs/
Issues:            docs/issues/
```

### Issue References

When creating or updating issues, **always reference this document** to avoid redundancy:

```markdown
> **Context**: See [ISSUE_CONTEXT.md](./ISSUE_CONTEXT.md) for project overview,
> repository structure, development environment, and common patterns.
```

---

**Last Updated**: 2025-10-19
**Maintainer**: Project Manager
**Purpose**: Centralized context for all job-finder-worker issues
