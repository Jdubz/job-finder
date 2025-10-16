# Queue-Based Job Processing System Guide

**Last Updated**: October 16, 2025

## Overview

The Job Finder application now uses a **queue-based architecture** for asynchronous job processing. This enables better scalability, reliability, and separation of concerns between job discovery and job analysis.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│   Scrapers  │ ──> │  Job Queue   │ ──> │ Queue Processor│ ──> │  Job Matches │
│  (Sources)  │     │  (Firestore) │     │   (Worker)     │     │  (Firestore) │
└─────────────┘     └──────────────┘     └────────────────┘     └──────────────┘
                            │                      │
                            │                      ├──> Company Info Fetcher
                            │                      └──> AI Job Matcher
                            │
                    ┌───────▼────────┐
                    │ Queue Config   │
                    │  (Stop List)   │
                    └────────────────┘
```

### Components

1. **Scrapers** - Find job postings from various sources
2. **Queue Intake** - Add jobs to processing queue
3. **Job Queue** - Firestore-backed FIFO queue
4. **Queue Processor** - Processes items from queue
5. **AI Matcher** - Analyzes jobs against profile
6. **Job Matches** - Stores successful matches

## Key Features

### ✅ Successfully Implemented

- **FIFO Queue Processing** - Jobs processed in order of creation
- **Duplicate Detection** - URLs checked before adding to queue
- **Stop List Filtering** - Exclude companies, keywords, domains
- **AI-Powered Matching** - Claude Haiku analyzes job fit
- **Score Thresholds** - Jobs below 80 are automatically filtered
- **Company Info Fetching** - Automatic company data enrichment
- **Resume Intake Generation** - AI generates tailored resume data
- **Retry Logic** - Failed items retry up to 3 times
- **Status Tracking** - pending → processing → success/failed/skipped

### 📊 Data Flow

1. **Scraper** finds job → creates job data
2. **ScraperIntake** adds to `job-queue` collection
3. **QueueProcessor** picks up pending items
4. **Stop List** filter applied (company/keyword/domain)
5. **Company Info** fetched if needed
6. **AI Matcher** analyzes job against profile
7. **Score Threshold** applied (min 80)
8. **Job Match** saved to `job-matches` collection

## Database Schema

### Collections

#### `job-queue` (portfolio-staging)

Queue items awaiting processing.

```typescript
{
  id: string,                    // Auto-generated
  type: "job" | "company",       // Item type
  status: "pending" | "processing" | "success" | "failed" | "skipped",
  url: string,                   // Job or company URL
  company_name?: string,
  company_id?: string,           // Reference to companies collection
  source: string,                // e.g., "greenhouse_scraper", "user_submission"
  submitted_by?: string,         // User ID if manual submission
  scraped_data?: object,         // Full job data from scraper
  result_message?: string,       // Success/failure details
  retry_count: number,           // Current retry attempt (max 3)
  created_at: timestamp,         // For FIFO ordering
  updated_at: timestamp,
  processed_at?: timestamp,
  completed_at?: timestamp
}
```

**Composite Index Required**:
```json
{
  "fields": [
    { "fieldPath": "status", "order": "ASCENDING" },
    { "fieldPath": "created_at", "order": "ASCENDING" }
  ]
}
```

#### `job-finder-config` (portfolio-staging)

Configuration for queue processing.

**Document: `stop-list`**
```typescript
{
  excludedCompanies: string[],   // Company names to skip
  excludedKeywords: string[],    // Keywords to exclude
  excludedDomains: string[]      // Domains to block
}
```

**Document: `queue-settings`** (optional)
```typescript
{
  maxRetries: number,            // Default: 3
  retryDelaySeconds: number,     // Default: 60
  processingTimeout: number      // Default: 300
}
```

**Document: `ai-settings`** (optional)
```typescript
{
  provider: "claude" | "openai",
  model: string,
  minMatchScore: number,         // Default: 70
  costBudgetDaily: number        // Default: 50.0
}
```

#### `job-matches` (portfolio-staging)

Successfully matched jobs.

```typescript
{
  id: string,
  title: string,
  company: string,
  companyWebsite?: string,
  companyInfo?: string,          // About/culture/mission
  location: string,
  description: string,
  url: string,
  matchScore: number,            // 0-100
  applicationPriority: "High" | "Medium" | "Low",
  resumeIntake?: object,         // AI-generated resume data
  skillsMatched: string[],
  skillGaps: string[],
  createdAt: timestamp,
  source: string
}
```

#### `companies` (portfolio-staging)

Company information cache.

```typescript
{
  id: string,
  name: string,
  name_lower: string,
  website: string,
  about?: string,
  culture?: string,
  mission?: string,
  industry?: string,
  founded?: string,
  size?: string,
  company_size_category?: "large" | "medium" | "small",
  headquarters_location?: string,
  tier?: "S" | "A" | "B" | "C" | "D",
  priorityScore?: number,
  createdAt: timestamp,
  updatedAt: timestamp
}
```

## Configuration

### Environment Variables

Required in `.env`:

```bash
# AI Provider
ANTHROPIC_API_KEY=sk-ant-...

# Firebase
GOOGLE_APPLICATION_CREDENTIALS=.firebase/static-sites-257923-firebase-adminsdk.json

# Optional Job Boards
ADZUNA_APP_ID=...
ADZUNA_API_KEY=...
```

### Config File (`config/config.yaml`)

```yaml
profile:
  source: "firestore"  # or "json"
  firestore:
    database_name: "portfolio-staging"
    name: "Your Name"

ai:
  enabled: true
  provider: "claude"
  model: "claude-3-5-haiku-20241022"
  min_match_score: 80  # Strict threshold
  generate_intake_data: true
  portland_office_bonus: 15
  user_timezone: -8  # Pacific Time
  prefer_large_companies: true

storage:
  database_name: "portfolio-staging"
  collection_name: "job-matches"
```

## Running the System

### Option 1: Direct Processing (Legacy Mode)

```bash
# Run scraper with direct AI processing
python -m job_finder.main
```

### Option 2: Queue Mode (Recommended)

#### Step 1: Run Scrapers (Add to Queue)

```bash
# Scrape jobs and add to queue
python -m job_finder.search_orchestrator_queue
```

#### Step 2: Run Queue Worker

```bash
# Process queue items
python queue_worker.py
```

The worker will:
1. Poll for pending items every 60 seconds
2. Process up to 10 items per batch
3. Apply stop list filters
4. Fetch company info
5. Run AI matching
6. Save matches to Firestore

### Option 3: Docker (Production)

```bash
# Build and run with queue mode enabled
docker-compose up -d

# View logs
docker-compose logs -f job-finder
```

## Testing

### End-to-End Test

```bash
# Test complete pipeline
python test_e2e_queue.py
```

This will:
1. ✅ Add test jobs to queue
2. ✅ Process through pipeline
3. ✅ Run AI matching (uses real API!)
4. ✅ Verify results in Firestore
5. ✅ Clean up test data

### Unit Tests

```bash
# Run all queue tests (47 tests)
pytest tests/queue/

# Run specific test file
pytest tests/queue/test_processor.py -v
```

## Firestore Setup

### Create Required Index

The queue requires a composite index for efficient queries:

```bash
# Deploy index
firebase deploy --only firestore:indexes --project static-sites-257923
```

Or create manually in Firebase Console:
- Collection: `job-queue`
- Fields: `status` (Ascending), `created_at` (Ascending)

### Initialize Stop List (Optional)

Create document `job-finder-config/stop-list`:

```json
{
  "excludedCompanies": ["BadCorp", "ScamInc"],
  "excludedKeywords": ["commission only", "unpaid"],
  "excludedDomains": ["spam.com"]
}
```

## Profile Loading

The system now loads profiles from the new `content-items` schema:

### New Schema (content-items)

- **Type: company** - Work experience entries
- **Type: skill-group** - Categorized skills
- **Type: project** - Portfolio projects

```python
from job_finder.profile.firestore_loader import FirestoreProfileLoader

loader = FirestoreProfileLoader(database_name="portfolio-staging")
profile = loader.load_profile(name="Your Name")

# Loads:
# - 7 experiences from content-items (type='company')
# - 73 skills from content-items (type='skill-group')
```

### Fallback to Old Schema

If `content-items` is empty, automatically falls back to:
- `experience-entries` collection
- `experience-blurbs` collection

## Monitoring

### Queue Statistics

```python
from job_finder.queue.manager import QueueManager

manager = QueueManager(database_name="portfolio-staging")
stats = manager.get_queue_stats()

# Returns:
# {
#   "pending": 10,
#   "processing": 2,
#   "success": 45,
#   "failed": 3,
#   "skipped": 8,
#   "total": 68
# }
```

### View Logs

```bash
# Docker logs
docker-compose logs -f job-finder

# Queue worker log
tail -f /app/logs/queue_worker.log

# Cron log
tail -f /var/log/cron.log
```

## Troubleshooting

### Issue: Queue items not processing

**Check:**
1. Composite index created? → `firebase deploy --only firestore:indexes`
2. Queue worker running? → `docker-compose ps` or `ps aux | grep queue_worker`
3. Items stuck in processing? → Check for crashed worker

**Fix:**
```python
# Reset stuck items to pending
from job_finder.queue.manager import QueueManager
manager = QueueManager()
# Manually update stuck items in Firestore Console
```

### Issue: All jobs being skipped

**Check:**
1. Stop list too aggressive? → Review `job-finder-config/stop-list`
2. Score threshold too high? → Check `config.yaml` min_match_score
3. Company domain blocked? → Check excludedDomains

### Issue: No AI analysis happening

**Check:**
1. API key set? → `echo $ANTHROPIC_API_KEY`
2. AI enabled in config? → `ai.enabled: true` in config.yaml
3. Provider initialized? → Check logs for provider errors

### Issue: Duplicate jobs in matches

**Cause**: URL already existed before queue system

**Fix:**
```bash
# Clean up duplicates
python cleanup_job_matches.py
```

## Performance

### Benchmarks (E2E Test Results)

- **Profile Loading**: ~2s (7 experiences, 73 skills)
- **Queue Intake**: ~0.5s per job
- **AI Analysis**: ~7-10s per job (Claude Haiku)
- **Total Processing**: ~12s per job

### Cost Optimization

- **Model**: Claude 3.5 Haiku (fast, cost-effective)
- **Caching**: Company info cached in Firestore
- **Batching**: Process 10 items per worker cycle
- **Filtering**: Stop list applied before AI (saves API calls)

## Next Steps

1. **Deploy Queue Worker** - Docker with `ENABLE_QUEUE_MODE=true`
2. **Configure Stop List** - Add excluded companies/keywords
3. **Monitor Queue** - Set up alerts for failed items
4. **Tune Thresholds** - Adjust min_match_score based on results
5. **Portfolio Integration** - Implement job submission API

## Files Reference

### Core Queue Files

- `src/job_finder/queue/manager.py` - Queue CRUD operations
- `src/job_finder/queue/processor.py` - Item processing logic
- `src/job_finder/queue/models.py` - Pydantic models
- `src/job_finder/queue/config_loader.py` - Firestore config
- `src/job_finder/queue/scraper_intake.py` - Add jobs to queue

### Test Files

- `test_e2e_queue.py` - End-to-end test
- `tests/queue/test_manager.py` - Queue manager tests
- `tests/queue/test_processor.py` - Processor tests
- `tests/queue/test_integration.py` - Integration tests

### Configuration

- `firestore.indexes.json` - Index definitions
- `firebase.json` - Firebase configuration
- `config/config.yaml` - Application config
- `.env` - Environment variables

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Run tests: `pytest tests/queue/ -v`
- Review this guide: `QUEUE_SYSTEM_GUIDE.md`
