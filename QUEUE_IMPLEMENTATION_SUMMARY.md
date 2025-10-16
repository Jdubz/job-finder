# Queue-Based Pipeline Implementation Summary

**Implementation Date:** 2025-10-16
**Status:** ✅ Phase 1 Complete - Ready for Testing

---

## What Was Built

### Core Queue Infrastructure

1. **Queue Models** (`src/job_finder/queue/models.py`)
   - `JobQueueItem` - Pydantic model for queue items
   - `QueueItemType` - Enum: job | company
   - `QueueStatus` - Enum: pending | processing | skipped | failed | success

2. **Queue Manager** (`src/job_finder/queue/manager.py`)
   - FIFO queue backed by Firestore
   - CRUD operations for queue items
   - Duplicate detection
   - Batch operations
   - Statistics and cleanup methods

3. **Configuration Loader** (`src/job_finder/queue/config_loader.py`)
   - Loads settings from Firestore `job-finder-config` collection
   - Stop list (excluded companies/keywords/domains)
   - Queue settings (max retries, timeout, etc.)
   - AI settings (provider, model, thresholds)
   - Cache support for performance

4. **Job Processor** (`src/job_finder/queue/processor.py`)
   - Processes queue items based on type
   - Stop list filtering
   - Company scraping and AI analysis
   - Job scraping and AI matching
   - Retry logic with exponential backoff

5. **Queue Worker Daemon** (`queue_worker.py`)
   - Polls Firestore every 60 seconds
   - Processes pending items in FIFO order
   - Graceful shutdown handling
   - Comprehensive logging

6. **Scraper Integration** (`src/job_finder/queue/scraper_intake.py`)
   - Helper for scrapers to submit jobs to queue
   - Duplicate detection before submission
   - Batch submission support

7. **Queue-Enabled Orchestrator** (`src/job_finder/search_orchestrator_queue.py`)
   - Scrapes jobs from sources
   - Applies basic filters
   - Submits to queue (no AI processing)
   - Lighter weight than original orchestrator

---

## Docker Integration

### Updated Files

1. **`docker/entrypoint.sh`**
   - Dual-process mode support
   - Starts cron daemon (scraping every 6h)
   - Optionally starts queue worker (continuous processing)
   - Controlled by `ENABLE_QUEUE_MODE` environment variable

2. **`Dockerfile`**
   - Added `queue_worker.py` to container
   - No other changes needed

---

## Firestore Schema

### New Collection: `job-queue`

```typescript
{
  id: string,                        // Auto-generated
  type: "job" | "company",
  status: "pending" | "processing" | "skipped" | "failed" | "success",
  result_message?: string,           // Why skipped/failed, or success details

  url: string,
  company_name?: string,
  company_id?: string,
  source: string,                    // scraper, user_submission, webhook, email
  submitted_by?: string,             // User ID if applicable

  scraped_data?: object,
  retry_count: number,
  max_retries: number,

  created_at: timestamp,             // For FIFO ordering
  updated_at: timestamp,
  processed_at?: timestamp,
  completed_at?: timestamp
}
```

### New Collection: `job-finder-config`

**Document: `stop-list`**
```typescript
{
  excludedCompanies: string[],
  excludedKeywords: string[],
  excludedDomains: string[]
}
```

**Document: `queue-settings`**
```typescript
{
  maxRetries: number,                // Default: 3
  retryDelaySeconds: number,         // Default: 60
  processingTimeout: number          // Default: 300
}
```

**Document: `ai-settings`**
```typescript
{
  provider: "claude" | "openai",
  model: string,
  minMatchScore: number,
  costBudgetDaily: number
}
```

---

## How It Works

### Architecture Flow

```
┌─────────────────┐
│  Portfolio UI   │ (Your side - submits jobs directly to Firestore)
└────────┬────────┘
         │ Writes to job-queue collection
         ▼
┌─────────────────────────────────────────────────────┐
│              Firestore (job-queue)                   │
│  Stores: pending jobs waiting for processing         │
└─────────────┬───────────────────────────────────────┘
              │
              │ ◄─── Scrapers also write here
              │
              ▼
┌─────────────────────────────────────────────────────┐
│          Queue Worker (continuous daemon)            │
│  • Polls every 60 seconds                            │
│  • Gets pending items (FIFO)                         │
│  • Checks stop list                                  │
│  • Scrapes job details                               │
│  • Runs AI analysis                                  │
│  • Saves to job-matches                              │
│  • Updates queue item status                         │
└─────────────────────────────────────────────────────┘
```

### Dual-Process Container

```
Docker Container:
├── Process 1: Cron (every 6h)
│   └── Runs scheduler.py → scrapes sources → submits to queue
│
└── Process 2: Queue Worker (continuous)
    └── Polls queue → processes items → updates status
```

---

## How to Use

### Enable Queue Mode

**In docker-compose:**
```yaml
services:
  job-finder:
    environment:
      - ENABLE_QUEUE_MODE=true  # Enable dual-process mode
```

**Without queue mode:**
- Container runs legacy direct processing
- Works exactly as before

**With queue mode:**
- Cron scrapes and submits to queue
- Queue worker processes asynchronously
- Portfolio can submit jobs directly to Firestore

---

## Portfolio Integration

### What You Need to Build

**API Route:** `app/api/jobs/submit/route.ts`

```typescript
export async function POST(request: Request) {
  // 1. Authenticate user
  const session = await getSession();
  if (!session) return unauthorized();

  // 2. Parse and validate request
  const { url, companyName } = await request.json();
  if (!url) return badRequest();

  // 3. Check if already exists
  const exists = await checkIfJobExists(url);
  if (exists) {
    return json({
      status: "skipped",
      message: "Job already exists"
    });
  }

  // 4. Write to Firestore job-queue
  await db.collection("job-queue").add({
    type: "job",
    status: "pending",
    url: url,
    company_name: companyName || "",
    source: "user_submission",
    submitted_by: session.user.id,
    retry_count: 0,
    max_retries: 3,
    created_at: FieldValue.serverTimestamp(),
    updated_at: FieldValue.serverTimestamp()
  });

  return json({
    status: "success",
    message: "Job submitted for processing"
  });
}
```

**Stop List Check:**
```typescript
// Load from Firestore job-finder-config/stop-list
const stopList = await db
  .collection("job-finder-config")
  .doc("stop-list")
  .get();

const { excludedCompanies, excludedKeywords, excludedDomains } =
  stopList.data();

// Check if should be rejected
if (excludedCompanies.some(c => companyName.includes(c))) {
  return json({
    status: "skipped",
    message: "Company is on stop list"
  });
}
```

---

## Testing

### Run Tests

```bash
# Run queue tests
pytest tests/queue/ -v

# Run with coverage
pytest tests/queue/ --cov=src/job_finder/queue --cov-report=html
```

### Manual Testing

**1. Test Queue Manager:**
```python
from job_finder.queue import QueueManager, JobQueueItem, QueueItemType

manager = QueueManager(database_name="portfolio-staging")

# Add test item
item = JobQueueItem(
    type=QueueItemType.JOB,
    url="https://example.com/job/123",
    company_name="Test Company",
    source="test"
)

doc_id = manager.add_item(item)
print(f"Added: {doc_id}")

# Get pending items
items = manager.get_pending_items()
print(f"Pending: {len(items)}")
```

**2. Test Queue Worker:**
```bash
# Run worker locally
python queue_worker.py

# Watch logs
tail -f logs/queue_worker.log
```

**3. Test in Docker:**
```bash
# Build image
docker build -t job-finder:queue-test .

# Run with queue mode
docker run -e ENABLE_QUEUE_MODE=true \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/key.json \
  -v ./credentials:/app/credentials:ro \
  job-finder:queue-test
```

---

## Configuration

### Firestore Setup

**Create these documents manually in Firebase Console:**

1. Navigate to Firestore
2. Create collection: `job-finder-config`
3. Add documents:

**stop-list:**
```json
{
  "excludedCompanies": [],
  "excludedKeywords": ["commission only", "pay to play"],
  "excludedDomains": ["spam.com"]
}
```

**queue-settings:**
```json
{
  "maxRetries": 3,
  "retryDelaySeconds": 60,
  "processingTimeout": 300
}
```

**ai-settings:**
```json
{
  "provider": "claude",
  "model": "claude-3-haiku-20240307",
  "minMatchScore": 70,
  "costBudgetDaily": 50.0
}
```

---

## Next Steps

### Immediate (Your Side - Portfolio)

1. **Create API Route** (`/api/jobs/submit`)
   - Authentication check
   - Duplicate detection
   - Stop list filtering
   - Write to `job-queue` collection

2. **Create UI Form**
   - Simple form: URL + Company Name
   - Submit button → calls API
   - Show success/error message

3. **Setup Firestore Config**
   - Create `job-finder-config` collection
   - Add the 3 documents above
   - Test from Firebase Console

### Testing (Shared)

1. **Test End-to-End**
   - Submit job via portfolio UI
   - Verify appears in `job-queue`
   - Verify queue worker processes it
   - Verify appears in `job-matches`

2. **Test Edge Cases**
   - Duplicate submission
   - Stop list filtering
   - Failed job retry logic
   - Max retries exceeded

### Future Enhancements

1. **Queue Monitoring UI** (portfolio)
   - Show queue depth
   - Show failed jobs
   - Manual retry button

2. **Gmail Integration**
   - Parse job emails
   - Submit to queue

3. **Perfect Match Alerts**
   - Real-time notifications
   - Score >= 90 threshold

---

## Files Created/Modified

### New Files
- `src/job_finder/queue/__init__.py`
- `src/job_finder/queue/models.py`
- `src/job_finder/queue/manager.py`
- `src/job_finder/queue/config_loader.py`
- `src/job_finder/queue/processor.py`
- `src/job_finder/queue/scraper_intake.py`
- `src/job_finder/search_orchestrator_queue.py`
- `queue_worker.py`
- `tests/queue/test_queue_manager.py`

### Modified Files
- `docker/entrypoint.sh` - Added dual-process mode
- `Dockerfile` - Added queue_worker.py

### Not Modified (Backwards Compatible)
- `src/job_finder/search_orchestrator.py` - Original still works
- `scheduler.py` - Can use either orchestrator
- All scrapers - Work with both modes

---

## Rollback Plan

If you need to revert to the old system:

1. Set `ENABLE_QUEUE_MODE=false` in docker-compose
2. Container runs in legacy mode
3. No code changes needed

Queue infrastructure remains dormant but ready to re-enable anytime.

---

## Success! 🎉

Phase 1 implementation is complete. The queue infrastructure is ready for:
- Portfolio UI integration
- User job submissions
- Asynchronous processing
- Future enhancements

**Next:** Implement the portfolio API route and test end-to-end!
