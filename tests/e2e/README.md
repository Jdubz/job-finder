# E2E Test Suite

End-to-end tests for the job-finder-FE + Job-Finder integration in the staging environment.

**⚠️ IMPORTANT: These tests are for MANUAL execution only. They are NOT part of CI/CD pipelines.**

## Overview

This test suite validates the complete job processing pipeline from submission through AI analysis to match creation.

**How it works:**
- Tests run **locally** from your development machine (no local Docker needed)
- Tests connect to `portfolio-staging` Firestore database
- Tests submit queue items and monitor their processing
- Queue processing happens in the **Portainer staging worker** (remote)

**Prerequisites:**
- Python environment with job-finder dependencies installed
- Firebase credentials configured (`GOOGLE_APPLICATION_CREDENTIALS`)
- Portainer staging worker **must be running and healthy**

## Test Scenarios

### Scenario 1: Job Submission Flow
**File:** `scenario_01_job_submission.py`

Tests the complete happy path:
1. Submit job URL to queue
2. Job scraping (granular pipeline)
3. Filter evaluation
4. AI matching analysis
5. Match creation in Firestore

**Verifies:**
- Queue item creation and status updates
- Job data extraction
- Pipeline stage progression
- Match score calculation
- Firestore document creation

### Scenario 2: Filtered Job
**File:** `scenario_02_filtered_job.py`

Tests cost optimization - filtered jobs should not reach AI analysis:
1. Submit job that fails filter criteria
2. Verify rejection before AI
3. Verify no match created

**Verifies:**
- Strike-based filtering works
- Pipeline stops at filter stage
- No AI analysis for filtered jobs
- Fast processing time (< 5 seconds)

### Scenario 3: Company Source Discovery
**File:** `scenario_03_company_source_discovery.py`

Tests company processing and automatic source discovery:
1. Submit company with Greenhouse job board
2. Company pipeline processes and detects job board
3. SOURCE_DISCOVERY queue item spawned automatically
4. Source is validated and configured
5. Both company and source exist in Firestore

**Verifies:**
- Company granular pipeline (FETCH → EXTRACT → ANALYZE → SAVE)
- Job board detection from company website
- Automatic source discovery spawning
- Source configuration and validation
- Data enrichment (tech stack, company info)

### Scenario 4: Scrape Rotation
**File:** `scenario_04_scrape_rotation.py`

Tests intelligent source rotation and health tracking:
1. Submit SCRAPE request without specific sources
2. Verify sources fetched with rotation (oldest first)
3. Verify source priority scoring
4. Respect target_matches and max_sources limits
5. Update source health tracking

**Verifies:**
- Source rotation algorithm (oldest scraped_at first)
- Priority scoring (S/A/B/C/D tiers)
- Scrape limits respected
- Health tracking (success/failure counts)
- Source timestamp updates

### Scenario 5: Full Discovery Cycle
**File:** `scenario_05_full_discovery_cycle.py`

**INTEGRATION TEST** - Tests complete intelligent data population:
1. Submit company → discovers Greenhouse source
2. Run scrape → finds jobs from discovered source
3. Jobs filter → only high-quality matches analyzed
4. AI analysis → creates job-match documents
5. Verify complete chain exists

**Verifies:**
- Complete data chain: Company → Source → Jobs → Matches
- System fills itself with valuable data automatically
- All pipeline stages work together
- Data quality maintained throughout
- Match scores meet thresholds

## Verifying Worker is Running

Before running tests, **verify the Portainer staging worker is running:**

**Worker Location**: The `job-finder-staging` container runs on a NAS in a Portainer instance. The container sends logs to **Google Cloud Logging**, not local Portainer logs.

### Method 1: Google Cloud Logging

The worker is configured to send logs to Google Cloud Logging (via `ENABLE_CLOUD_LOGGING=true`):

```bash
# Search for job-finder logs by environment (RECOMMENDED)
# Staging logs
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" AND labels.environment="staging"' \
  --limit 20 \
  --format json \
  --freshness 1h | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        entry = json.loads(line)
        if 'textPayload' in entry:
            timestamp = entry.get('timestamp', '')
            text = entry['textPayload']
            print(f'[{timestamp}] {text}')
        elif 'jsonPayload' in entry:
            timestamp = entry.get('timestamp', '')
            msg = entry['jsonPayload'].get('message', str(entry['jsonPayload']))
            print(f'[{timestamp}] {msg}')
    except: pass
"

# Production logs
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" AND labels.environment="production"' \
  --limit 20 \
  --freshness 1h

# Filter by specific operation types (uses structured logging tags)
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" AND labels.environment="staging" AND textPayload:"[WORKER]"' \
  --limit 10 \
  --freshness 1h

gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" AND labels.environment="staging" AND textPayload:"[QUEUE:"' \
  --limit 10 \
  --freshness 1h

gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" AND labels.environment="staging" AND textPayload:"[PIPELINE:"' \
  --limit 10 \
  --freshness 1h
```

**Log Message Structure** (New structured format):
```
[ENVIRONMENT] timestamp - module - level - [CATEGORY] message | key=value details

Examples:
[STAGING] 2025-10-18 09:15:00 - queue_worker - INFO - [WORKER] STARTED | poll_interval=60, environment=staging
[STAGING] 2025-10-18 09:15:30 - queue_worker - INFO - [WORKER] PROCESSING_BATCH | iteration=1, items_count=3
[STAGING] 2025-10-18 09:15:31 - processor - INFO - [QUEUE:JOB] processing - ID:abc123 | url=https://...
[STAGING] 2025-10-18 09:15:32 - processor - INFO - [PIPELINE:SCRAPE] COMPLETED - ID:abc123 | method=greenhouse
[STAGING] 2025-10-18 09:15:33 - processor - INFO - [PIPELINE:FILTER] COMPLETED - ID:abc123 | strikes=2
[STAGING] 2025-10-18 09:15:35 - processor - INFO - [AI:MATCH] completed | model=claude-3-5-sonnet, score=85
```

**Log Categories**:
- `[WORKER]` - Worker status (started, idle, processing, stopped)
- `[QUEUE:type]` - Queue item processing (JOB, COMPANY, SCRAPE, SOURCE_DISCOVERY)
- `[PIPELINE:stage]` - Pipeline stages (SCRAPE, FILTER, ANALYZE, SAVE)
- `[SCRAPE]` - Web scraping activity
- `[AI:operation]` - AI operations (MATCH, ANALYZE, EXTRACT)
- `[DB:operation]` - Database operations (CREATE, UPDATE, QUERY)

**What to look for**:
- `Queue worker started` - Worker initialized successfully
- `Polling queue for new items...` - Worker actively polling
- `Processing queue item <id>` - Worker picked up an item
- `Item <id> processed successfully` - Item completed
- Recent timestamps (< 5 minutes old) indicate worker is active

**If no logs appear in Cloud Logging**:
- Worker container may not be running (check Portainer)
- Cloud Logging integration may have failed to initialize
- Check Portainer container logs for startup errors

### Method 2: Portainer UI (Container Status Only)

Portainer UI shows container status but **not application logs** (those go to Google Cloud):

1. Open Portainer → **Stacks** → `job-finder-staging`
2. Click on the stack → **Containers**
3. Verify `job-finder-staging` container status is **running** (green)
4. Check uptime and restart count (high restarts = crashing)

**Note**: Portainer container logs will only show Docker/Python startup messages. Application logs (queue processing) are in Google Cloud Logging.

### Method 3: Firestore Console (Test Processing)
1. Open Firebase Console → Firestore Database
2. Select `portfolio-staging` database
3. Navigate to `job-queue` collection
4. Submit a test item manually and watch for status changes from `pending` → `processing` → `success`/`failed`

### Expected Behavior
- Worker polls queue every 10-30 seconds (configurable)
- Items should transition from `pending` to `processing` within 30 seconds
- If items stay `pending` for > 2 minutes → worker may be stuck/crashed
- Check Google Cloud Logging for worker activity and errors

## Running Tests

### Run All Scenarios

```bash
# From repository root
python tests/e2e/run_all_scenarios.py

# Or from tests/e2e directory
cd tests/e2e
python run_all_scenarios.py
```

### Run Specific Scenarios

```bash
# Run only job submission test
python tests/e2e/run_all_scenarios.py --scenarios job_submission

# Run only filter test
python tests/e2e/run_all_scenarios.py --scenarios filtered_job

# Run company source discovery test
python tests/e2e/run_all_scenarios.py --scenarios company_source_discovery

# Run scrape rotation test
python tests/e2e/run_all_scenarios.py --scenarios scrape_rotation

# Run full integration test
python tests/e2e/run_all_scenarios.py --scenarios full_discovery_cycle

# Run multiple specific scenarios
python tests/e2e/run_all_scenarios.py --scenarios job_submission filtered_job company_source_discovery
```

### Run with Verbose Logging

```bash
python tests/e2e/run_all_scenarios.py --verbose
```

### Run Without Cleanup (for debugging)

```bash
python tests/e2e/run_all_scenarios.py --no-cleanup
```

### List Available Scenarios

```bash
python tests/e2e/run_all_scenarios.py --list
```

## Cleanup

The test suite automatically cleans up test data after each run. To manually clean up old test data:

### Clean All Test Data (24+ hours old)

```bash
python tests/e2e/cleanup.py
```

### Clean Specific Test Run

```bash
python tests/e2e/cleanup.py --test-run-id e2e_test_abc123
```

### Clean Failed Items Only

```bash
python tests/e2e/cleanup.py --failed-only
```

### Dry Run (preview what would be deleted)

```bash
python tests/e2e/cleanup.py --dry-run
```

### Custom Age Threshold

```bash
# Clean data older than 1 hour
python tests/e2e/cleanup.py --max-age 1
```

## Architecture

### Base Classes

**`BaseE2EScenario`** (`base_scenario.py`)
- Base class for all test scenarios
- Provides lifecycle methods: `setup()`, `execute()`, `verify()`, `cleanup()`
- Automatic cleanup tracking
- Standardized logging and output

**`TestResult`** (`base_scenario.py`)
- Test result container with status, duration, message, error
- Status types: SUCCESS, FAILURE, SKIPPED, ERROR

### Helper Modules

**`QueueMonitor`** (`helpers/queue_monitor.py`)
- Monitor queue item status and pipeline stages
- Wait for specific statuses or completion
- Timeout handling
- Status history tracking

**`FirestoreHelper`** (`helpers/firestore_helper.py`)
- Firestore CRUD operations
- Queue item creation and querying
- Match document access
- Field validation utilities

**`CleanupHelper`** (`helpers/cleanup_helper.py`)
- Batch deletion operations
- Age-based cleanup
- Test run ID filtering
- Dry run support

### Test Flow

```
1. Setup
   ├── Initialize Firestore client
   ├── Create helper instances
   └── Configure logging

2. Execute
   ├── Create queue item
   ├── Track for cleanup
   ├── Wait for pipeline progression
   └── Collect results

3. Verify
   ├── Assert expected statuses
   ├── Verify document data
   ├── Check pipeline state
   └── Validate match creation

4. Cleanup
   └── Delete tracked documents
```

## Adding New Scenarios

1. Create new file: `scenario_XX_description.py`
2. Inherit from `BaseE2EScenario`
3. Implement required methods:
   - `setup()` - Initialize dependencies
   - `execute()` - Run test logic
   - `verify()` - Assert expected results
4. Export in `scenarios/__init__.py`
5. Add to `run_all_scenarios.py` in `all_scenarios` dict

### Example Template

```python
from .base_scenario import BaseE2EScenario
from ..helpers import QueueMonitor, FirestoreHelper, CleanupHelper

class MyTestScenario(BaseE2EScenario):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.test_data = "..."

    def setup(self):
        super().setup()
        # Initialize helpers

    def execute(self):
        # Run test actions
        # Track items for cleanup

    def verify(self):
        # Assert expected results
```

## Manual Execution Only

**These tests are NOT automated.** They must be run manually from the local repository when needed.

E2E tests are excluded from CI/CD because they:
- Require a live staging environment with running queue workers **in Portainer**
- Depend on remote infrastructure availability (Portainer staging worker must be running)
- Take significant time to complete (minutes per scenario)
- Consume AI API credits (real Claude API calls)
- May interfere with actual staging data if not properly isolated

### Architecture
```
┌─────────────────────┐         ┌──────────────────────┐         ┌─────────────────┐
│  Local Machine      │         │  Firestore           │         │  Portainer      │
│                     │         │  (portfolio-staging) │         │  Staging Worker │
│  • Run e2e tests    │────────▶│  • job-queue         │◀────────│  • Polls queue  │
│  • Submit items     │         │  • job-matches       │         │  • Processes    │
│  • Monitor status   │────────▶│  • companies         │         │  • Updates DB   │
│                     │         │  • job-sources       │         │                 │
└─────────────────────┘         └──────────────────────┘         └─────────────────┘
```

To run tests, execute the scripts directly from your local environment with proper credentials configured **and ensure the Portainer staging worker is running**.

## Environment Variables

Tests use the staging environment by default:
- Database: `portfolio-staging`
- Firestore: Named database in staging project
- Credentials: Service account from environment

## Debugging

### View Test Run Logs

Enable verbose logging:
```bash
python tests/e2e/run_all_scenarios.py --verbose
```

### Inspect Test Data

Disable cleanup:
```bash
python tests/e2e/run_all_scenarios.py --no-cleanup
```

Then inspect Firestore manually via Firebase Console or:
```python
from job_finder.storage.firestore_client import FirestoreClient
db = FirestoreClient.get_client("portfolio-staging")
items = db.collection("job-queue").where("source", "==", "e2e_test").get()
for item in items:
    print(item.id, item.to_dict())
```

### Common Issues

**"Timeout" errors (most common):**
- **Worker not running:** Check Portainer staging worker status (see "Verifying Worker is Running" above)
- **Worker crashed:** Check container logs in Portainer for errors
- **Worker stuck:** Restart the container in Portainer
- **Database mismatch:** Verify worker is using `portfolio-staging` database
- Test timeout default is 300s (5 min) - adjust if needed for slow operations

**"Document not found" errors:**
- Check database name is correct (`portfolio-staging`)
- Verify queue item was created in Firestore
- Check cleanup isn't running too early
- Verify test is using correct Firestore client instance

**"Permission denied" errors:**
- Check `GOOGLE_APPLICATION_CREDENTIALS` environment variable is set
- Verify service account has Firestore read/write permissions
- Check service account has access to `portfolio-staging` database
- Verify Firestore rules allow writes to `job-queue` collection

**Worker is running but not processing:**
- Check worker environment variables in Portainer (especially `ENABLE_QUEUE_MODE=true`)
- Verify `STORAGE_DATABASE_NAME=portfolio-staging` in worker config
- Check for Python errors in worker logs
- Verify worker has valid API keys (`ANTHROPIC_API_KEY`)

## Design Document

For detailed design and implementation specifications, see:
- `../../E2E_README.md` (repository root)
