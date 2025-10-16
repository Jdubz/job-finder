# Next Session Context

**Last Updated:** 2025-10-16
**Current Branch:** `feature/separate-companies-from-sources`
**Project Status:** Planning queue-based pipeline refactor

---

## TOP PRIORITY: Queue-Based Pipeline Refactor

### Overview
Transform the current synchronous pipeline into an asynchronous queue-based system with separate intake, scraping, and AI analysis stages. This enables webhook-based job intake, guaranteed company analysis before job analysis, and better separation of concerns.

### Architecture Vision

**Current (Synchronous):**
```
Scraper → Filter → AI Analysis → Storage
```

**New (Queue-Based):**
```
[Webhook/Scraper/Manual] → [Intake Queue]
                                ↓
                          [Validation & Stop List]
                                ↓
                    ┌───────────┴───────────┐
                    ↓                       ↓
            [Company Exists?]        [Job Already in DB?]
                    ↓                       ↓
              [No] [Yes]              [No] [Yes]
                ↓     ↓                 ↓     ↓
    [Company Scrape] [Skip]      [Job Scrape] [Skip]
                ↓                       ↓
    [Company AI Analysis]    [Wait for Company Analysis]
                ↓                       ↓
    [Update Companies DB]     [Job AI Analysis]
                                        ↓
                              [Create Job-Application Entry]
                                        ↓
                                [Portfolio Review]
```

### Key Benefits
- **Guaranteed Order**: Companies analyzed before their jobs
- **Webhook Support**: Accept jobs from external sources (email, manual, APIs)
- **Scalability**: Process jobs asynchronously with multiple workers
- **Resilience**: Retry logic, dead letter queue, state tracking
- **Cost Control**: Rate limiting, budgeting for AI calls

---

## Implementation Phases

### Phase 1: Queue Infrastructure (Days 1-3)
**Priority: CRITICAL**

Create the foundational queue system with Firestore persistence.

**Files to Create:**
```bash
src/job_finder/queue/__init__.py
src/job_finder/queue/base_queue.py           # Abstract base class
src/job_finder/queue/manager.py              # Queue manager with Firestore persistence
src/job_finder/queue/models.py               # Job/Company queue item Pydantic models
tests/test_queue_manager.py
```

**Key Features:**
- Firestore-backed queue with state persistence
- Priority ordering (company > job, high-tier > low-tier)
- Retry logic with exponential backoff
- Dead letter queue for failed items
- State tracking: pending → processing → complete → failed

**Queue Item Model:**
```python
{
  "id": str,
  "type": "job" | "company",
  "status": "pending" | "processing" | "complete" | "failed",
  "priority": int,  # Higher = process first
  "url": str,
  "company_name": str,
  "company_id": str,  # Reference to companies collection
  "retry_count": int,
  "max_retries": int,
  "error": str,
  "created_at": timestamp,
  "updated_at": timestamp,
  "processed_at": timestamp
}
```

---

### Phase 2: Intake System (Days 4-5)
**Priority: HIGH**

Build the intake queue that validates and routes incoming jobs.

**Files to Create:**
```bash
src/job_finder/queue/intake_queue.py
src/job_finder/filters/stop_list.py          # Excluded companies/keywords
src/job_finder/api/__init__.py
src/job_finder/api/webhook_receiver.py       # Flask/FastAPI endpoint
config/stop_list.yaml                         # Excluded companies/keywords
tests/test_intake_queue.py
tests/test_webhook_receiver.py
```

**Key Features:**
- Webhook authentication with HMAC signatures
- Stop list filtering (excluded companies, spam keywords)
- Duplicate detection via URL hashing
- Input validation and normalization
- Route to company queue if company doesn't exist
- Route to job queue if company exists

**Stop List Format:**
```yaml
excluded_companies:
  - "MLM Company"
  - "Known Scam Inc"

excluded_keywords:
  - "commission only"
  - "pay to apply"
  - "investment required"

excluded_domains:
  - "spam-jobs.com"
```

---

### Phase 3: Company Processing (Days 6-8)
**Priority: HIGH**

Implement company scraping and AI analysis queue.

**Files to Create:**
```bash
src/job_finder/queue/company_queue.py
src/job_finder/processors/company_processor.py  # Company scraping + AI
tests/test_company_processor.py
```

**Files to Modify:**
```bash
src/job_finder/company_info_fetcher.py        # Adapt for queue usage
src/job_finder/storage/companies_manager.py   # Add state tracking fields
```

**Company State Flow:**
```
pending → scraping → analyzing → complete/failed
```

**New Company Fields:**
```python
{
  # Existing fields...
  "analysis_status": str,     # pending, analyzing, complete, failed
  "analyzed_at": timestamp,
  "job_board_url": str,       # Discovered job board URL (Greenhouse, etc.)
  "job_board_type": str,      # greenhouse, workday, lever, etc.
}
```

**Key Features:**
- Company website scraping
- AI analysis of culture/mission/size/HQ
- Auto-detection of job board URLs
- Create job-source entries for discovered boards
- Update company analysis status

---

### Phase 4: Job Processing (Days 9-11)
**Priority: HIGH**

Implement job scraping queue with company dependency checking.

**Files to Create:**
```bash
src/job_finder/queue/job_queue.py
src/job_finder/processors/job_processor.py     # Job scraping + waiting
tests/test_job_processor.py
```

**Job State Flow:**
```
pending → scraping → waiting_company → analyzing → complete/failed
```

**Key Features:**
- Job detail scraping from URLs
- Company analysis dependency checking
- Waiting mechanism with timeout (max 5 minutes)
- Fallback to minimal company data on timeout
- Job state tracking in Firestore

---

### Phase 5: AI Analysis Queue (Days 12-14)
**Priority: MEDIUM**

Centralize AI analysis with rate limiting and cost control.

**Files to Create:**
```bash
src/job_finder/queue/analysis_queue.py
src/job_finder/processors/analysis_processor.py  # Unified AI analysis
tests/test_analysis_processor.py
```

**Files to Modify:**
```bash
src/job_finder/ai/matcher.py                  # Extract analysis logic for reuse
```

**Key Features:**
- Rate limiting (max 10 concurrent AI calls)
- Cost tracking and daily budget enforcement
- Retry logic for transient API failures
- Batch processing optimization (future)
- Token usage monitoring

---

### Phase 6: Integration & Migration (Days 15-17)
**Priority: MEDIUM**

Integrate queues with existing system and create migration path.

**Files to Modify:**
```bash
src/job_finder/search_orchestrator.py         # Use intake queue instead of direct processing
run_job_search.py                              # Add queue processing mode
```

**Files to Create:**
```bash
run_queue_worker.py                            # Background queue processor daemon
run_webhook_server.py                          # Webhook API server
```

**Migration Strategy:**
1. **Parallel Operation**: Both old and new pipelines run
2. **Gradual Migration**: Point scrapers to intake queue one by one
3. **Validation**: Compare results between old and new
4. **Full Migration**: Remove old synchronous code

**Key Features:**
- Backward compatibility with existing scrapers
- Queue worker daemon for background processing
- Webhook server for external integrations
- Migration scripts for existing data

---

### Phase 7: Monitoring & Admin (Days 18-20)
**Priority: LOW**

Add monitoring, admin tools, and observability.

**Files to Create:**
```bash
src/job_finder/queue/monitor.py               # Queue health monitoring
src/job_finder/api/admin.py                   # Admin API endpoints
scripts/queue_admin.py                         # CLI for queue management
```

**Key Features:**
- Queue depth monitoring and alerts
- Failed job inspection and manual retry
- Manual job submission via CLI
- Queue statistics dashboard
- Dead letter queue management

---

## Configuration Changes

### New Config Sections in `config/config.yaml`

```yaml
queue:
  enabled: true
  max_workers: 5                    # Concurrent queue processors
  poll_interval: 10                 # Seconds between queue polls
  max_retries: 3
  retry_delay: 60                   # Seconds before retry

webhook:
  enabled: true
  host: "0.0.0.0"
  port: 5000
  secret_key_env: "WEBHOOK_SECRET_KEY"

intake:
  stop_list_path: "config/stop_list.yaml"
  duplicate_window_days: 30         # How far back to check for duplicates

processing:
  company_analysis_timeout: 300     # Max wait for company analysis (seconds)
  concurrent_ai_requests: 10        # Max simultaneous AI calls
  ai_cost_budget_daily: 50.00       # USD
```

---

## Database Schema Changes

### New Collection: `job-queue`

Stores queue items for processing.

```python
{
  "id": str,                        # Auto-generated
  "type": "job" | "company",
  "status": "pending" | "processing" | "complete" | "failed",
  "priority": int,                  # Higher = process first
  "url": str,
  "company_name": str,
  "company_id": str,                # Reference to companies collection
  "company_status": str,            # For jobs: pending, complete
  "data": dict,                     # Scraped data (flexible)
  "retry_count": int,
  "max_retries": int,
  "error": str,                     # Last error message
  "created_at": timestamp,
  "updated_at": timestamp,
  "processed_at": timestamp
}
```

### Updates to `companies` Collection

```python
{
  # Existing fields...
  "analysis_status": str,           # pending, analyzing, complete, failed
  "analyzed_at": timestamp,
  "job_board_url": str,             # Discovered job board URL
  "job_board_type": str,            # greenhouse, workday, lever, etc.
}
```

### Updates to `job-matches` Collection

```python
{
  # Existing fields...
  "source": str,                    # webhook, scraper, manual
  "intake_at": timestamp,           # When received by intake queue
}
```

---

## Testing Strategy

### Unit Tests
- Each queue component individually
- Queue manager CRUD operations
- State transitions and retry logic
- Stop list filtering

### Integration Tests
- Full pipeline flow with mocked external services
- Company → Job dependency handling
- Webhook → Database verification

### Load Tests
- Queue performance with 1000+ items
- Concurrent worker processing
- Rate limiting under load

### End-to-End Tests
- Webhook → Firestore job-match verification
- Existing scraper → Queue → Analysis flow

---

## Future Enhancements (Post-MVP)

1. **Gmail Integration** - Parse job emails and submit to intake
2. **Perfect Match Alerts** - Real-time notifications for score >= 90
3. **Queue UI** - Web dashboard for monitoring and management
4. **Auto Source Discovery** - Find company job boards automatically
5. **Batch Analysis** - Analyze multiple jobs in single AI call
6. **Smart Retry** - ML-based retry decision making

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Queue processing delays | HIGH | Priority system, multiple workers, monitoring |
| Company analysis blocking jobs | MEDIUM | Timeout mechanism, fallback to minimal company data |
| AI cost overruns | HIGH | Budget limits, rate limiting, daily caps |
| Data inconsistency | MEDIUM | Transactional updates, state reconciliation |
| Webhook security | HIGH | HMAC authentication, rate limiting, IP whitelist |

---

## Success Metrics

- ✅ Webhook successfully receives and processes job postings
- ✅ Companies analyzed before their jobs (100% guarantee)
- ✅ Queue processes 100+ jobs without failures
- ✅ Average processing time < 5 minutes per job
- ✅ Zero duplicate job analyses
- ✅ All existing scrapers migrated to new architecture
- ✅ AI cost stays within budget (< $50/day)

---

## Current Session State

### Repository
- **Branch:** `feature/separate-companies-from-sources`
- **Latest Commit:** `3d6d7ab` - Update session context with CI fix completion
- **Modified:** `.claude/settings.json`
- **Coverage:** 49% (414 tests passing)

### What's Uncommitted
- Changes to `.claude/settings.json` (staged)

---

## Quick Start Commands

### Branch Setup
```bash
# Option 1: Continue on current branch
git add .
git commit -m "Add pipeline refactor plan to NEXT_SESSION.md"
git push origin feature/separate-companies-from-sources

# Option 2: Create new feature branch for queue refactor
git checkout -b feature/queue-based-pipeline
git add NEXT_SESSION.md
git commit -m "Add queue-based pipeline refactor plan"
git push -u origin feature/queue-based-pipeline
```

### Phase 1: Start Development
```bash
# Create queue module structure
mkdir -p src/job_finder/queue
touch src/job_finder/queue/__init__.py
touch src/job_finder/queue/base_queue.py
touch src/job_finder/queue/manager.py
touch src/job_finder/queue/models.py
touch tests/test_queue_manager.py

# Start with base queue class
code src/job_finder/queue/base_queue.py
```

---

## Questions for Next Session

1. **Queue Backend**: Use Firestore or Redis for queue storage?
   - Firestore: Already integrated, good for persistence
   - Redis: Better performance for queue operations

2. **Webhook Framework**: Flask or FastAPI?
   - Flask: Simpler, lightweight
   - FastAPI: Better async support, auto docs

3. **Worker Model**: Single worker or multiple specialized workers?
   - Single: Simpler, processes all queue types
   - Multiple: Better parallelism (company worker, job worker, AI worker)

4. **Processing Mode**: Real-time vs batch?
   - Real-time: Process as soon as items added
   - Batch: Process in scheduled intervals (current behavior)

5. **Migration Timeline**: Big bang or gradual?
   - Big bang: Replace entire pipeline at once
   - Gradual: Migrate one scraper at a time

---

**Ready to build!** Start with Phase 1 (Queue Infrastructure) and work through systematically. 🚀
