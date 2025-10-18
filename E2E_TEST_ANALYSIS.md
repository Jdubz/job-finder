# E2E Test Analysis & Troubleshooting

## Issue Summary

The `make test-e2e-full` command failed with:
- **Exit Code**: 1 (test validation failure)
- **Collections Empty**: `job-listings`, `companies`, `job-sources`, `job-queue` all have 0 documents
- **Job-matches Collection**: Has 159 documents (likely from previous runs)
- **Test Result**: "Too few companies: 0 (expected at least 3)"

## Root Cause Analysis

### 1. **Fundamental Design Flaw**

The `tests/e2e/data_collector.py` script has a critical design flaw:

```python
# tests/e2e/data_collector.py:341-355
# Create new job-matches document directly
job_match = {
    "title": test_job["job_title"],
    "company": test_job["company_name"],
    "link": test_job["job_url"],
    "description": test_job["description"],
    "sourceId": "test",
    "scrapedAt": datetime.utcnow().isoformat(),
    "test_run_id": test_run_id,
    "created_at": datetime.utcnow().isoformat(),
}

# Save directly to Firestore
doc_ref = self.db.collection("job-matches").document()
doc_ref.set(job_match)
```

**Problem**: The test is **directly creating job-matches**, completely bypassing:
- The job-queue system
- The queue worker processing pipeline
- Job scraping/extraction
- Company creation
- Source tracking
- The entire granular pipeline (SCRAPE → EXTRACT → ANALYZE → SAVE)

### 2. **Missing Worker Process**

The test expects these collections to be populated:
- `job-listings` (created during JOB_SCRAPE/JOB_EXTRACT)
- `companies` (created during JOB_ANALYZE)
- `job-sources` (created during source discovery)

**But**: No queue worker is running to process jobs and create these documents!

### 3. **Incorrect Test Flow**

**Current (Broken) Flow**:
```
data_collector.py → Direct Firestore write → job-matches created
                                           → No pipeline processing
                                           → Empty collections
                                           → Test fails
```

**Expected Flow**:
```
data_collector.py → job-queue created → Worker processes queue
                                     → JOB_SCRAPE
                                     → JOB_EXTRACT  
                                     → JOB_ANALYZE (creates company)
                                     → JOB_SAVE (creates job-match)
                                     → Collections populated
                                     → Test passes
```

## The Correct Architecture

Based on the codebase analysis, here's how jobs should be submitted:

### Option 1: Use ScraperIntake (Recommended)

```python
from job_finder.queue import QueueManager
from job_finder.queue.scraper_intake import ScraperIntake

# Initialize
queue_manager = QueueManager(database_name)
intake = ScraperIntake(queue_manager)

# Submit jobs (creates granular pipeline items)
jobs = [{
    "url": "https://test.example.com/job/123",
    "company": "MongoDB", 
    "title": "Senior Backend Engineer",
    "description": "Build things",
}]

count = intake.submit_jobs(jobs, source="e2e_test")
```

This creates a `job-queue` item with:
- `type`: "job"
- `sub_task`: "JOB_SCRAPE"  
- `status`: "pending"

### Option 2: Direct Queue Item Creation

```python
from job_finder.queue import QueueManager, JobQueueItem, QueueItemType

queue_manager = QueueManager(database_name)

item = JobQueueItem(
    type=QueueItemType.JOB,
    url="https://test.example.com/job/123",
    company_name="MongoDB",
    source="e2e_test",
    sub_task="JOB_SCRAPE",  # Important!
)

queue_id = queue_manager.add_item(item)
```

## Solution Options

### Solution A: Fix data_collector.py (Recommended)

Modify `TestJobSubmitter` to use proper queue submission:

```python
class TestJobSubmitter:
    def __init__(self, database_name: str):
        self.queue_manager = QueueManager(database_name)
        self.intake = ScraperIntake(self.queue_manager)
    
    def submit_test_job(self, test_job: Dict[str, Any], test_run_id: str):
        # Use proper queue submission
        job = {
            "url": test_job["job_url"],
            "company": test_job["company_name"],
            "title": test_job["job_title"],
            "description": test_job["description"],
        }
        
        submitted = self.intake.submit_jobs([job], source="e2e_test")
        return queue_id
```

**Then**: Add a worker startup step to `test-e2e-full` in Makefile

### Solution B: Start Worker in Test

Add worker processing to the test flow:

```python
def run_collection(self):
    # ... submit jobs to queue ...
    
    # Start worker to process queue
    processor = QueueItemProcessor(...)
    
    # Process all pending items
    while True:
        items = queue_manager.get_pending_items(limit=10)
        if not items:
            break
        for item in items:
            processor.process_item(item)
    
    # ... validate results ...
```

### Solution C: Adjust Test Expectations (Not Recommended)

Change the validation to not expect `companies`, `job-listings`, etc. This defeats the purpose of E2E testing.

## Recommended Fix

### Step 1: Update TestJobSubmitter

```python
class TestJobSubmitter:
    def __init__(self, database_name: str):
        self.db = FirestoreClient.get_client(database_name)
        self.queue_manager = QueueManager(database_name)
        self.intake = ScraperIntake(self.queue_manager)

    def submit_test_job(self, test_job: Dict[str, Any], test_run_id: str) -> TestJobSubmission:
        import time
        from uuid import uuid4

        submission_id = str(uuid4())[:8]
        start_time = time.time()

        logger.info(f"Submitting test job: {test_job['job_title']} at {test_job['company_name']}")

        record = TestJobSubmission(
            submission_id=submission_id,
            timestamp=datetime.utcnow().isoformat(),
            company_name=test_job["company_name"],
            job_title=test_job["job_title"],
            job_url=test_job["job_url"],
            source_type="e2e_test",
            expected_status=test_job["expected_behavior"],
        )

        try:
            # Submit through proper queue
            job = {
                "url": test_job["job_url"],
                "company": test_job["company_name"],
                "title": test_job["job_title"],
                "description": test_job.get("description", ""),
            }
            
            submitted = self.intake.submit_jobs([job], source="e2e_test")
            
            if submitted > 0:
                record.actual_result = "queued"
                logger.info(f"  → Job queued successfully")
            else:
                record.actual_result = "skipped_duplicate"
                logger.info(f"  → Job skipped (duplicate)")

        except Exception as e:
            record.actual_result = "failed"
            record.errors.append(str(e))
            logger.error(f"  ✗ Error: {e}")

        record.duration_seconds = time.time() - start_time
        return record
```

### Step 2: Update Makefile to Start Worker

```makefile
test-e2e-full:
	@export GOOGLE_APPLICATION_CREDENTIALS="$(shell pwd)/credentials/serviceAccountKey.json" && \
	export TEST_RUN_ID="e2e_$$(date +%s)" && \
	export RESULTS_DIR="test_results/$${TEST_RUN_ID}" && \
	mkdir -p "$${RESULTS_DIR}" && \
	echo "[1/6] Collecting and cleaning test data..." && \
	$(PYTHON) tests/e2e/data_collector.py --database portfolio-staging --output-dir "$${RESULTS_DIR}" && \
	echo "[2/6] Starting queue worker..." && \
	$(PYTHON) scripts/workers/queue_worker.py --max-iterations 10 --database portfolio-staging &
	WORKER_PID=$! && \
	echo "[3/6] Waiting for processing..." && \
	sleep 60 && \
	echo "[4/6] Stopping worker..." && \
	kill $${WORKER_PID} && \
	echo "[5/6] Validating results..." && \
	$(PYTHON) tests/e2e/validate_results.py --results-dir "$${RESULTS_DIR}"
```

### Step 3: Update Wait Time

The current 10-second wait is too short. Jobs need time to process through:
1. JOB_SCRAPE (5-15s)
2. JOB_EXTRACT (5-10s)
3. JOB_ANALYZE (10-20s with AI)
4. JOB_SAVE (1-2s)

**Total**: ~30-50 seconds per job

Change to at least 120 seconds or poll for completion.

## Quick Fix for Now

To get tests running immediately, adjust the wait time:

```python
# tests/e2e/data_collector.py:665
logger.info("Waiting for job processing (120 seconds)...")
time.sleep(120)
```

But this still won't work without proper queue submission and worker processing.

## Summary

The E2E test infrastructure needs to:
1. ✅ Submit jobs to `job-queue` (not directly to `job-matches`)
2. ✅ Start a queue worker to process jobs
3. ✅ Wait for full pipeline completion (2+ minutes)
4. ✅ Validate that collections are properly populated

The test is currently bypassing steps 1-2, making it impossible to validate the actual production pipeline.
