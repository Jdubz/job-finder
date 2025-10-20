# Architecture Overview

This document provides a comprehensive overview of the Job Finder system architecture, data flow, and component interactions.

## Table of Contents

- [System Overview](#system-overview)
- [Core Pipeline](#core-pipeline)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Design Patterns](#design-patterns)
- [Scalability Considerations](#scalability-considerations)

---

## System Overview

Job Finder is an AI-powered job search automation tool that scrapes job boards, analyzes job fit using LLMs, and stores matched jobs in Firestore. The system is designed for scheduled execution in Docker containers with automatic updates.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Scheduler                              │
│                   (Cron in Docker)                          │
└─────────────────┬───────────────────────────────────────────┘
                  │ Runs every 6 hours
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  Search Orchestrator                         │
│        (Coordinates entire job search pipeline)             │
└───┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬───────┘
    │      │      │      │      │      │      │      │
    ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
┌────────┐┌────────┐┌────────┐┌────────┐  External Services
│Profile ││Listings││Scrapers││Company │  ┌──────────────┐
│Loader  ││Manager ││        ││Info    │  │ Anthropic    │
└────────┘└────────┘└────────┘└────────┘  │ Claude API   │
    │         │         │         │        └──────────────┘
    ▼         ▼         ▼         ▼        ┌──────────────┐
┌─────────────────────────────────────┐    │ OpenAI       │
│           AI Matcher                 │◄───│ GPT-4 API    │
│    (Job Analysis & Scoring)          │    └──────────────┘
└─────────────────┬───────────────────┘    ┌──────────────┐
                  │                         │ Firestore    │
                  ▼                         │ Database     │
┌─────────────────────────────────────┐    └──────────────┘
│        Firestore Storage             │           ▲
│   (Job Matches, Companies, etc.)     │───────────┘
└─────────────────────────────────────┘
```

---

## Core Pipeline

The job search pipeline operates in two modes:

1. **Legacy Direct Processing** - Sequential 5-stage pipeline (deprecated)
2. **Queue-Based Processing** - Asynchronous queue architecture (current production)

### Queue-Based Pipeline (Current Architecture)

The queue-based system separates job discovery from job analysis for better scalability and reliability:

**Discovery Phase (Scrapers → Queue):**
1. Cron triggers scrapers every 6 hours
2. Scrapers collect jobs from sources
3. Basic filtering applied (remote/hybrid only)
4. Jobs added to Firestore `job-queue` collection
5. Scraper exits (lightweight, fast)

**Processing Phase (Queue Worker → Storage):**
1. Queue worker daemon polls for pending jobs (60s intervals)
2. Processes jobs in batches (10 items per cycle)
3. Applies stop list filters (company/keyword/domain exclusions)
4. Fetches company information (with caching)
5. Runs AI matching and scoring
6. Stores matched jobs (score >= 80) to Firestore

See **[Queue System Guide](queue-system.md)** for complete architectural details and configuration.

### Legacy Direct Processing Pipeline

The original pipeline executes in five sequential stages:

### Stage 1: Profile Loading

**Component:** `FirestoreProfileLoader` (src/job_finder/profile/firestore_loader.py:16)

**Purpose:** Load user profile data from Firestore database

**Process:**
1. Connect to Firestore database (`portfolio` or `portfolio-staging`)
2. Load experience entries from `experience-entries` collection
3. Load experience blurbs from `experience-blurbs` collection
4. Extract skills from experiences
5. Generate professional summary
6. Build complete Profile object

**Output:** `Profile` object containing:
- Personal information
- Work experience with technologies and responsibilities
- Skills with proficiency levels
- Job search preferences

### Stage 2: Listing Selection & Scraping

**Components:**
- `JobListingsManager` (src/job_finder/storage/listings_manager.py:16)
- Scrapers in `src/job_finder/scrapers/`

**Purpose:** Get active job listings and scrape jobs from each source

**Process:**
1. Query Firestore for enabled job listings
2. Apply company scoring to prioritize listings
3. For each active listing:
   - Get scraper configuration
   - Initialize appropriate scraper (GreenhouseScraper, etc.)
   - Scrape jobs from the source
   - Update listing statistics (last scraped, jobs found)

**Company Scoring System:**
- Portland office: +50 points
- Tech stack alignment: up to 100 points (MongoDB +15, Redis +15, Kubernetes +10, etc.)
- Company attributes: up to 35 points (remote-first +15, AI/ML +10, etc.)
- Tiers: S (150+), A (100-149), B (70-99), C (50-69), D (0-49)

**Output:** List of raw job dictionaries

### Stage 3: Basic Filtering

**Component:** `JobFilter` (src/job_finder/filters.py:6)

**Purpose:** Apply traditional keyword and location filtering

**Process:**
1. Filter by remote status (must be remote or hybrid)
2. Filter by exclusion keywords (reject jobs with specific terms)
3. Deduplicate jobs (by URL)

**Output:** Filtered list of job dictionaries

### Stage 4: AI Matching & Analysis

**Components:**
- `CompanyInfoFetcher` (src/job_finder/company_info_fetcher.py)
- `CompaniesManager` (src/job_finder/storage/companies_manager.py)
- `AIJobMatcher` (src/job_finder/ai/matcher.py:41)

**Purpose:** Analyze job fit using AI and generate tailored application data

**Process:**

**4a. Company Information Fetching:**
1. Extract company name and website from job
2. Check Firestore cache in `companies` collection
3. If not cached or sparse:
   - Fetch company website (try /about, /about-us, /company, /careers, homepage)
   - Parse HTML with BeautifulSoup
   - Extract info using AI (about, culture, mission, size, industry, founded)
   - Cache in Firestore
4. Combine about/culture/mission fields into company_info string
5. Update all jobs with company_info

**4b. AI Job Analysis:**
1. For each job:
   - Construct prompt with job details, profile, and company info
   - Call AI provider (Claude Opus 4 or GPT-4)
   - Parse structured response:
     - Match score (0-100)
     - Matched skills
     - Skill gaps
     - Experience level match
     - Application priority (High/Medium/Low)
     - Reasoning
     - Resume intake data (summary, skills to highlight, projects, achievements)
2. Apply Portland office bonus (+15 points if applicable)
3. Recalculate priority based on adjusted score
4. Filter by minimum match score threshold (default: 80)

**Scoring System:**
- Title skills (50 points max): Must have Expert/Advanced level for full points
- Description requirements (30 points max): Must have 95%+ of required skills
- Experience level match (20 points max): Seniority + domain experience
- Portland bonus: +15 points if company has Portland office
- Minimum threshold: 80 points (effectively 65 for Portland companies)
- Priority tiers: High (85-100), Medium (70-84), Low (0-69)

**Output:** List of jobs with AI analysis data

### Stage 5: Storage

**Component:** `FirestoreJobStorage` (src/job_finder/storage/firestore_storage.py:16)

**Purpose:** Save matched jobs to Firestore database

**Process:**
1. For each matched job:
   - Generate document ID from job URL hash
   - Check if job already exists
   - If new or updated:
     - Store in `job-matches` collection
     - Update tracking fields (firstSeenAt, lastSeenAt, status)
2. Log statistics (jobs analyzed, jobs matched, match rate)

**Output:** Jobs persisted in Firestore

---

## Component Architecture

### Profile System

**Location:** `src/job_finder/profile/`

**Components:**
- `schema.py` - Pydantic models (Profile, Experience, Skill, Project, Preferences)
- `loader.py` - Abstract base class for profile loading
- `firestore_loader.py` - Firestore-based profile loader

**Design Pattern:** Repository pattern with adapter

**Key Features:**
- Pydantic validation ensures data integrity
- Firestore integration keeps profile in sync with portfolio
- Automatic skill extraction from experience data
- Professional summary generation

### Scraper System

**Location:** `src/job_finder/scrapers/`

**Components:**
- `base.py` - Abstract BaseScraper class
- `greenhouse_scraper.py` - Greenhouse job board scraper

**Design Pattern:** Template method pattern

**Standard Job Schema:**
```python
{
    "title": str,              # Job title
    "company": str,            # Company name
    "company_website": str,    # Company website URL
    "company_info": str,       # About/culture/mission (populated later)
    "location": str,           # Job location
    "description": str,        # Full job description
    "url": str,                # Job posting URL (unique identifier)
    "posted_date": str,        # When posted (optional)
    "salary": str,             # Salary range (optional)
    "keywords": List[str],     # ATS keywords (populated by AI)
}
```

**Key Features:**
- Pluggable architecture - easy to add new scrapers
- Standardized output format
- Error handling and graceful degradation
- Rate limiting and robots.txt respect

### AI System

**Location:** `src/job_finder/ai/`

**Components:**
- `providers.py` - AI provider abstraction (ClaudeProvider, OpenAIProvider)
- `prompts.py` - Prompt templates for job analysis
- `matcher.py` - Job matching orchestration

**Design Pattern:** Strategy pattern with adapter

**Key Features:**
- Provider abstraction allows switching between Claude/GPT-4
- Structured prompts with company context
- JSON response parsing with fallback
- Token counting and cost estimation
- Comprehensive match analysis with reasoning

### Storage System

**Location:** `src/job_finder/storage/`

**Components:**
- `firestore_storage.py` - Job match storage
- `listings_manager.py` - Job source listings management
- `companies_manager.py` - Company data caching
- `firestore_client.py` - Centralized Firestore connection management (singleton pattern)

**Design Pattern:** Repository pattern

**Collections:**
- `job-matches` - Matched jobs with AI analysis
- `job-listings` - Active job sources (boards, feeds, companies)
- `companies` - Cached company information
- `job-queue` - Queue items for asynchronous processing
- `job-finder-config` - Stop lists and configuration

**Key Features:**
- Automatic deduplication by URL hash
- Tracking fields (status, appliedAt, firstSeen, lastSeen)
- Efficient querying with indexes
- Update tracking and statistics

### Queue System

**Location:** `src/job_finder/queue/`

**Components:**
- `manager.py` - Queue CRUD operations and statistics
- `processor.py` - Item processing logic with retry mechanism
- `models.py` - Pydantic models for queue items
- `config_loader.py` - Firestore configuration loading
- `scraper_intake.py` - Helper for submitting jobs to queue

**Design Pattern:** Producer-Consumer pattern

**Key Features:**
- FIFO queue processing
- Duplicate detection before submission
- Stop list filtering (companies, keywords, domains)
- Retry logic with exponential backoff (max 3 retries)
- Status tracking (pending → processing → success/failed/skipped)
- Batch processing (10 items per cycle)

**Integration:**
- Scrapers produce jobs to queue
- Queue worker consumes and processes jobs
- job-finder-FE project can submit jobs via API
- Real-time status updates in Firestore

---

## Data Flow

### Complete Job Search Flow

```
1. INITIALIZATION
   ┌────────────────┐
   │ Scheduler      │ Runs every 6 hours
   └───────┬────────┘
           ▼
   ┌────────────────┐
   │ Orchestrator   │ Initialize managers
   └───────┬────────┘
           │
           ├──► Profile Loader ──► Firestore (portfolio DB)
           ├──► Listings Manager ──► Firestore (job-listings)
           ├──► Companies Manager ──► Firestore (companies)
           └──► AI Matcher ──► Anthropic/OpenAI API


2. SCRAPING
   ┌────────────────────────────────────────────┐
   │ For each active listing (scored & sorted): │
   └───────┬────────────────────────────────────┘
           ▼
   ┌────────────────┐
   │ Get Listing    │ Query job-listings WHERE enabled = true
   └───────┬────────┘ ORDER BY score DESC
           ▼
   ┌────────────────┐
   │ Initialize     │ Create scraper for source type
   │ Scraper        │ (Greenhouse, RSS, API, etc.)
   └───────┬────────┘
           ▼
   ┌────────────────┐
   │ Scrape Jobs    │ Fetch job postings from source
   └───────┬────────┘ Returns: List[Job Dict]
           ▼
   ┌────────────────┐
   │ Update Stats   │ lastScrapedAt, totalJobsFound
   └────────────────┘


3. COMPANY INFO ENRICHMENT
   ┌─────────────────────────────────┐
   │ For each company in scraped jobs:│
   └───────┬─────────────────────────┘
           ▼
   ┌────────────────┐      ┌──────────────┐
   │ Check Cache    │─YES─►│ Use Cached   │
   └───────┬────────┘      │ Company Info │
           │NO             └──────────────┘
           ▼
   ┌────────────────┐
   │ Fetch Website  │ Try /about, /about-us, /company, etc.
   └───────┬────────┘
           ▼
   ┌────────────────┐
   │ Parse HTML     │ BeautifulSoup extraction
   └───────┬────────┘
           ▼
   ┌────────────────┐      ┌──────────────┐
   │ AI Extraction  │─────►│ Structured   │
   └───────┬────────┘      │ Company Data │
           │               └──────────────┘
           ▼
   ┌────────────────┐
   │ Cache in       │ Save to companies collection
   │ Firestore      │ (about, culture, mission, etc.)
   └────────────────┘


4. BASIC FILTERING
   ┌────────────────┐
   │ Remote Filter  │ Keep remote/hybrid jobs only
   └───────┬────────┘
           ▼
   ┌────────────────┐
   │ Exclusion      │ Remove jobs with excluded keywords
   │ Filter         │ (e.g., "senior manager", "director")
   └───────┬────────┘
           ▼
   ┌────────────────┐
   │ Deduplication  │ Remove duplicate URLs
   └────────────────┘


5. AI MATCHING
   ┌─────────────────────────────┐
   │ For each filtered job:       │
   └───────┬─────────────────────┘
           ▼
   ┌────────────────┐
   │ Build Prompt   │ Job + Profile + Company Info
   └───────┬────────┘
           ▼
   ┌────────────────┐      ┌──────────────┐
   │ Call AI API    │─────►│ Anthropic    │
   └───────┬────────┘      │ Claude Opus 4│
           │               └──────────────┘
           ▼
   ┌────────────────┐
   │ Parse Response │ Extract match score, skills, gaps, etc.
   └───────┬────────┘
           ▼
   ┌────────────────┐
   │ Apply Portland │ +15 bonus if company has PDX office
   │ Bonus          │
   └───────┬────────┘
           ▼
   ┌────────────────┐
   │ Threshold      │ Keep if score >= 80 (or 65 with bonus)
   │ Check          │
   └───────┬────────┘
           │PASS
           ▼
   ┌────────────────┐
   │ Generate       │ Resume intake data:
   │ Resume Intake  │ - Summary
   └────────────────┘ - Skills to highlight
                      - Projects to include
                      - Achievement angles
                      - ATS keywords


6. STORAGE
   ┌─────────────────────────────┐
   │ For each matched job:        │
   └───────┬─────────────────────┘
           ▼
   ┌────────────────┐
   │ Generate ID    │ Hash of job URL
   └───────┬────────┘
           ▼
   ┌────────────────┐      ┌──────────────┐
   │ Check Existing │─YES─►│ Update       │
   └───────┬────────┘      │ lastSeenAt   │
           │NO             └──────────────┘
           ▼
   ┌────────────────┐
   │ Save to        │ job-matches collection
   │ Firestore      │ All job data + AI analysis
   └────────────────┘


7. COMPLETION
   ┌────────────────┐
   │ Log Statistics │ Jobs analyzed: X
   └────────────────┘ Jobs matched: Y
                      Match rate: Z%
                      Duration: T seconds
```

---

## Technology Stack

### Core Technologies

**Language:**
- Python 3.12

**Frameworks & Libraries:**
- **Pydantic 2.10+** - Data validation and serialization
- **BeautifulSoup4** - HTML parsing for web scraping
- **Requests** - HTTP client for scraping
- **PyYAML** - Configuration file parsing

**AI/LLM:**
- **Anthropic SDK (0.40+)** - Claude API client (primary)
- **OpenAI SDK (1.54+)** - GPT-4 API client (secondary)
- **tiktoken (0.8+)** - Token counting for cost estimation

**Database:**
- **Google Cloud Firestore** - NoSQL document database
- **Firebase Admin SDK** - Firestore connection management

**Infrastructure:**
- **Docker** - Containerization
- **Cron** - Scheduled job execution
- **Watchtower** - Automatic container updates

**Development:**
- **pytest** - Testing framework
- **black** - Code formatting
- **flake8** - Linting
- **isort** - Import sorting
- **bandit** - Security analysis
- **mypy** - Static type checking
- **pre-commit** - Git hooks for quality checks

### External Services

**AI Providers:**
- Anthropic Claude Opus 4 (primary) - Best reasoning for job matching
- OpenAI GPT-4 (fallback) - Alternative provider

**Cloud Services:**
- Google Cloud Firestore - Data persistence
- Google Cloud Logging (optional) - Centralized logging
- GitHub Container Registry - Docker image hosting
- GitHub Actions - CI/CD pipeline

---

## Design Patterns

### 1. Pipeline Pattern

The core job search flow is implemented as a pipeline with sequential stages. Each stage transforms data and passes it to the next stage.

**Benefits:**
- Clear separation of concerns
- Easy to understand and debug
- Easy to add new stages or modify existing ones

### 2. Repository Pattern

Storage components (`FirestoreJobStorage`, `JobListingsManager`, `CompaniesManager`) abstract database operations.

**Benefits:**
- Database implementation can be swapped without changing business logic
- Easy to mock for testing
- Centralized data access logic

### 3. Strategy Pattern

AI providers implement a common interface, allowing runtime selection of Claude vs GPT-4.

**Benefits:**
- Flexibility to switch providers
- Easy to add new AI providers
- Cost optimization (use cheaper models when appropriate)

### 4. Template Method Pattern

`BaseScraper` defines the scraping algorithm structure, with subclasses implementing specific details.

**Benefits:**
- Consistent scraper interface
- Code reuse for common functionality
- Easy to add new scrapers

### 5. Adapter Pattern

`FirestoreProfileLoader` adapts Firestore data to the `Profile` Pydantic model.

**Benefits:**
- Decouples external data format from internal representation
- Easy to support multiple profile sources (JSON, API, etc.)

---

## Scalability Considerations

### Current Design (Single Instance)

The system is designed to run as a single containerized instance with scheduled execution. This is appropriate for:
- Personal job searches (1 user)
- Low to moderate job volume (10-50 jobs per search)
- Scheduled execution (every 6 hours)

### Bottlenecks

1. **AI API Rate Limits**
   - Claude Opus 4: 5,000 RPM (requests per minute)
   - Solution: Batch processing, rate limiting, exponential backoff

2. **Scraping Rate Limits**
   - Job boards may block or throttle requests
   - Solution: Respect robots.txt, implement delays, rotate user agents

3. **Sequential Processing**
   - Jobs analyzed one at a time
   - Solution: Batch AI analysis (analyze multiple jobs in single request)

4. **Firestore Quota**
   - 50,000 reads/day (free tier)
   - Solution: Caching, batch operations, upgrade to Blaze plan

### Scaling Strategies

**Vertical Scaling (Current):**
- Increase container resources (CPU/memory)
- Run more frequent searches
- Process more jobs per search

**Horizontal Scaling (Future):**
- Multiple containers processing different listings
- Message queue for job processing (Pub/Sub, BullMQ)
- Distributed caching (Redis)
- API layer for multi-user support

### Multi-User Architecture (Future)

```
┌─────────────────────────────────────────────────────────────┐
│                       Load Balancer                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌──────────────┐    ┌──────────────┐
│ API Server 1 │    │ API Server 2 │
└───────┬──────┘    └───────┬──────┘
        │                   │
        └─────────┬─────────┘
                  ▼
┌─────────────────────────────────────┐
│         Redis Cache                  │
│  (Profile data, companies, etc.)    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│         Message Queue                │
│  (Job scraping & analysis tasks)    │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  Worker 1    │    │  Worker 2    │
│  (Scrapers)  │    │  (AI Match)  │
└───────┬──────┘    └───────┬──────┘
        │                   │
        └─────────┬─────────┘
                  ▼
┌─────────────────────────────────────┐
│           Firestore                  │
│  (Users, profiles, job-matches)     │
└─────────────────────────────────────┘
```

---

## Security & Privacy

### Secrets Management

**Sensitive Data:**
- Anthropic API key (AI access)
- OpenAI API key (fallback AI)
- Firebase service account JSON (database access)

**Storage:**
- Environment variables in Docker/Portainer
- Never committed to Git (in .gitignore)
- Credentials mounted as read-only volumes

### Data Privacy

**User Data:**
- Profile data stored in Firestore with access controls
- No PII in logs
- Credentials encrypted at rest (Google Cloud default)

**Job Data:**
- Only stores publicly available job postings
- No user tracking or analytics
- Respects website Terms of Service

### Web Scraping Ethics

**Compliance:**
- Respects robots.txt
- Implements rate limiting and delays
- Uses appropriate User-Agent headers
- Only scrapes public data
- For personal use only (not commercial)

---

## Testing Strategy

### Unit Tests

**Coverage:**
- Profile loading and validation
- Job filtering logic
- AI response parsing
- Storage operations

**Tools:**
- pytest with coverage reporting
- Mocked external services (Firestore, AI APIs)

### Integration Tests

**Coverage:**
- Full pipeline execution
- Firestore read/write operations
- AI provider integration

### Manual Testing

**Process:**
1. Run on staging database
2. Review matched jobs for quality
3. Check Firestore data integrity
4. Monitor logs for errors

---

## Deployment Architecture

### Docker Container

**Base Image:** `python:3.12-slim`

**Services:**
- Cron daemon (scheduled execution)
- Python application

**Volumes:**
- `/app/credentials` - Firebase service account (read-only)
- `/app/config` - Configuration files (read-only)
- `/app/logs` - Application logs (read-write)
- `/app/data` - Local data exports (read-write)

### CI/CD Pipeline

**GitHub Actions Workflow:**
1. Code pushed to `main` branch
2. Run tests (pytest)
3. Check code quality (black, flake8, mypy)
4. Build Docker image
5. Push to GitHub Container Registry (ghcr.io)
6. Tag with commit SHA and `latest`

**Auto-Deployment:**
- Watchtower polls registry every 5 minutes
- Pulls new images with tag `latest`
- Restarts container automatically
- Removes old images

### Environment Separation

**Staging:**
- Container: `job-finder-staging`
- Database: `portfolio-staging`
- Purpose: Testing and development

**Production:**
- Container: `job-finder-production`
- Database: `portfolio`
- Purpose: Live job searches

---

## Monitoring & Observability

### Logging

**Levels:**
- INFO - Normal operation (jobs found, matched, stored)
- WARNING - Recoverable errors (scraping failed, rate limited)
- ERROR - Unrecoverable errors (AI API down, Firestore error)

**Destinations:**
- Container logs (Docker)
- File logs (`/app/logs/scheduler.log`)
- Google Cloud Logging (optional)

### Metrics

**Key Metrics:**
- Jobs scraped per run
- Jobs matched per run
- Match rate (matched/scraped)
- Average match score
- AI API cost per run
- Execution duration

### Alerting

**Current:** Manual monitoring via logs

**Future:**
- Email/Slack notifications on errors
- Daily summary reports
- Budget alerts for AI API costs

---

## Future Enhancements

### Phase 1: Quality Improvements
- Comprehensive test coverage (>80%)
- Refactor Firestore initialization (eliminate duplication)
- Improve error handling (reduce broad exception catching)
- Add type hints throughout codebase

### Phase 2: Feature Additions
- Application tracking (applied, interview, offer, rejected)
- Cover letter generation from resume intake data
- Job recommendation email digest
- Web UI for reviewing matches

### Phase 3: Scale & Performance
- Batch AI analysis (analyze multiple jobs in one request)
- Parallel scraping (process multiple listings concurrently)
- Redis caching layer
- Rate limiting with exponential backoff

### Phase 4: Multi-User Support
- API layer for multi-user access
- User authentication and authorization
- Per-user profiles and preferences
- Subscription management

---

**Last Updated:** 2025-10-16
**Version:** 2.0 (Queue-based architecture)
