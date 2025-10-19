# E2E Sequential Job Submission Strategy

## Overview

E2E tests now use a **sequential submission strategy** instead of submitting all jobs at once and monitoring. This provides better debugging, clearer cause-and-effect, and more reliable test results.

## Strategy: Submit → Monitor → Next

```
Job 1: Submit → Wait for completion → ✓ Complete
Job 2: Submit → Wait for completion → ✓ Complete
Job 3: Submit → Wait for completion → ✓ Complete
```

Instead of:
```
Jobs 1-3: Submit all → Monitor all → Hope they complete
```

## Benefits

### 1. **Clear Cause-and-Effect**
- See exactly what each job spawns
- Trace lineage from root job to all children
- Identify which job caused any issues

### 2. **Better Resource Usage**
- No queue flooding with all jobs at once
- Worker processes jobs in clean sequence
- Easier to debug with less concurrent activity

### 3. **Fail Fast**
- Stop after first failure instead of waiting for all
- Quicker feedback loop during development
- Don't waste time processing remaining jobs if first fails

### 4. **Sequential Validation**
- Each job's entire lineage completes before next
- Validate loop prevention per job
- Easier to verify tracking_id inheritance

### 5. **Predictable Timing**
- Know exact duration per job
- Easy to estimate total test time
- Can adjust timeout per job independently

## Implementation

### wait_for_queue_completion()

```python
def wait_for_queue_completion(self, timeout: int = 180, poll_interval: int = 5) -> bool:
    """
    Wait for queue to complete (no pending/processing items).
    
    - Polls every 5 seconds
    - Checks pending + processing counts
    - Returns True when queue empty
    - Returns False on timeout
    """
```

**Output:**
```
Waiting for queue to complete...
  [5s] Active: 3 (pending: 2, processing: 1)
  [10s] Active: 2 (pending: 1, processing: 1)
  [15s] Active: 0 (pending: 0, processing: 0)
✓ Queue complete in 15.2s
```

### submit_all_test_jobs() - Sequential

```python
def submit_all_test_jobs(self, test_run_id: str) -> List[TestJobSubmission]:
    """
    Submit jobs one at a time, waiting for each to complete.
    """
    for i, test_job in enumerate(self.TEST_JOBS, 1):
        # 1. Submit job
        record = self.submit_test_job(test_job, test_run_id)
        
        if record.actual_result == "queued":
            # 2. Wait for completion
            completed = self.wait_for_queue_completion(timeout=180)
            
            if not completed:
                logger.warning("Job did not complete. Stopping test.")
                break
        
        # 3. Move to next job
```

## Test Flow

### Fast E2E Test (`make test-e2e`)

```
1. Fetch 2 real job URLs from production
2. Submit job 1 → Monitor → Wait for completion
3. Submit job 2 → Monitor → Wait for completion
4. Validate decision tree (tracking_id, ancestry_chain, etc.)
5. Generate report
```

**Expected output:**
```
================================================================================
SUBMITTING JOB 1/2
================================================================================
Submitting test job: Senior Engineer at Example Corp
  → Job submitted to queue successfully
Monitoring queue until job 1 completes...
  [5s] Active: 2 (pending: 1, processing: 1)
  [10s] Active: 1 (pending: 0, processing: 1)
  [15s] Active: 0 (pending: 0, processing: 0)
✓ Queue complete in 15.3s
✓ Job 1 complete. Ready for next job.

================================================================================
SUBMITTING JOB 2/2
================================================================================
Submitting test job: ML Engineer at Tech Company
  → Job submitted to queue successfully
Monitoring queue until job 2 completes...
  [5s] Active: 1 (pending: 0, processing: 1)
  [10s] Active: 0 (pending: 0, processing: 0)
✓ Queue complete in 10.1s
✓ Job 2 complete. Ready for next job.

================================================================================
ALL JOBS SUBMITTED: 2/2
================================================================================
```

## Timing

### Per Job (average):
- **Scrape:** 5-10s
- **Filter:** 1-2s
- **Analyze:** 3-5s
- **Save:** 1-2s
- **Total:** ~15-20s per job

### Test Durations:
- **1 job:** ~20 seconds
- **2 jobs:** ~40 seconds (default for fast test)
- **4 jobs:** ~80 seconds

## Debugging

### If Job Hangs

The test will timeout after 180s per job:

```
Monitoring queue until job 1 completes...
  [180s] Active: 1 (pending: 0, processing: 1)
Timeout waiting for queue completion (180s)
Job 1 did not complete in time. Stopping test.
```

**Action:** Check the stuck item in Firestore:
```python
# Find processing items
items = db.collection('job-queue').where('status', '==', 'processing').get()
```

### If Job Fails

Check the test results:

```json
{
  "submission_id": "a1b2c3d4",
  "actual_result": "failed",
  "errors": ["Error details here"]
}
```

### Trace Lineage

With sequential submission, you can easily trace what each job spawned:

```
Job 1 (tracking_id: abc-123)
├─> JOB_SCRAPE (queued)
├─> JOB_FILTER (spawned from scrape)
├─> JOB_ANALYZE (spawned from filter)
└─> JOB_SAVE (spawned from analyze)
```

All items will have `tracking_id: abc-123` and proper `ancestry_chain`.

## Comparison: Old vs New

### Old Approach (Batch)
```python
# Submit all
for job in jobs:
    submit(job)

# Monitor all
wait_for_all_complete()
```

**Problems:**
- Can't tell which job caused issue
- All jobs run concurrently (complex)
- Must wait for slowest job
- Debugging is difficult

### New Approach (Sequential)
```python
# Submit one at a time
for job in jobs:
    submit(job)
    wait_for_completion()  # Before next job
```

**Benefits:**
- Clear cause-and-effect
- Simple to debug
- Fail fast
- Clean lineage per job

## Configuration

### Adjust Timeout Per Job
```bash
# Default: 180s per job
--timeout 180

# Longer for complex jobs
--timeout 300

# Shorter for quick tests
--timeout 60
```

### Adjust Poll Interval
```bash
# Default: check every 5s
--poll-interval 5

# More frequent checks
--poll-interval 2

# Less frequent (save API calls)
--poll-interval 10
```

### Number of Test Jobs
```bash
# Default: 2 jobs (fast test)
--test-count 2

# Single job (fastest)
--test-count 1

# More jobs (comprehensive)
--test-count 4
```

## Usage

### Run Fast E2E Test
```bash
make test-e2e
```

This will:
1. Fetch 2 real job URLs from production
2. Submit each sequentially with monitoring
3. Validate loop prevention works
4. Generate validation report

### Customize Test
```bash
python tests/e2e/data_collector.py \
    --database portfolio-staging \
    --source-database portfolio \
    --test-count 1 \
    --verbose
```

## Summary

The sequential submission strategy makes E2E tests:
- ✅ **More reliable** - Clear pass/fail per job
- ✅ **Easier to debug** - Trace lineage per job
- ✅ **Faster to fail** - Stop at first issue
- ✅ **Better resource usage** - No queue flooding
- ✅ **Clearer output** - See progress per job

This approach is ideal for validating loop prevention and state-driven pipeline logic with real production data.
