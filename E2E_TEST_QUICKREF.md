# E2E Test Quick Reference

## What Changed

The E2E test now **properly submits jobs to the queue** instead of bypassing the worker pipeline.

## Running the Test

```bash
make test-e2e-full
```

**Duration**: ~4-5 minutes (previously 16 seconds)

## What Happens

1. **Backs up existing data** → Saves to `test_results/e2e_*/backup_original/`
2. **Clears collections** → Removes test data (job-listings, companies, job-sources, job-queue)
3. **Submits 4 test jobs** → Adds to `job-queue` collection
4. **Waits 3 minutes** → Shows progress every 30 seconds
5. **Validates results** → Checks collections are populated

## Expected Results

### Collections After Test

| Collection | Expected Count | Purpose |
|------------|---------------|---------|
| `job-queue` | 0 | All jobs processed (none pending) |
| `job-matches` | ≥4 | AI-analyzed job matches |
| `companies` | ≥1 | Company records created |
| `job-listings` | ≥1 | Extracted job data |
| `job-sources` | varies | Source tracking |

### Test Jobs Submitted

1. **MongoDB** - Senior Backend Engineer
2. **Netflix** - Machine Learning Engineer  
3. **Shopify** - Full Stack Engineer
4. **Stripe** - Platform Engineer

## Monitoring

### View Worker Logs (Google Cloud)

```bash
# The staging worker processes jobs and logs to Google Cloud
# Check logs to see jobs being picked up and processed
```

Look for log entries like:
- `"Processing queue item: {job_url}"`
- `"JOB_SCRAPE complete"`
- `"JOB_ANALYZE complete - Company created"`
- `"Job matched and saved"`

### Check Queue Status Manually

```python
from job_finder.queue import QueueManager

manager = QueueManager("portfolio-staging")
pending = manager.get_pending_items(limit=10)
print(f"Pending items: {len(pending)}")
```

## Troubleshooting

### Test Fails: "Queue still has X items"

**Problem**: Worker hasn't finished processing all jobs

**Solutions**:
- Increase wait time in `data_collector.py` (line ~670)
- Check worker is running in staging
- Review Google Cloud logs for worker errors

### Test Fails: "No companies created"

**Problem**: Worker hasn't reached JOB_ANALYZE phase yet

**Solutions**:
- Increase wait time to 240 seconds (4 minutes)
- Check if jobs are being filtered out
- Verify AI provider is configured correctly

### Test Fails: "Too few job matches"

**Problem**: Jobs may already exist from previous runs

**Solutions**:
- Check if test URLs are unique
- Clear job-matches collection before testing
- Review duplicate detection logic

### Worker Not Processing Jobs

**Checklist**:
- [ ] Worker is running in staging environment
- [ ] GOOGLE_APPLICATION_CREDENTIALS is set correctly
- [ ] Firebase credentials are valid
- [ ] Worker has correct database name configured
- [ ] No errors in worker logs

## Configuration

### Adjust Wait Time

Edit `tests/e2e/data_collector.py`:

```python
# Line ~670
wait_time = 240  # Change from 180 to 240 seconds (4 minutes)
```

### Change Database

```bash
make test-e2e-full DATABASE=portfolio  # Use production (careful!)
```

Or edit `Makefile` line 166:
```makefile
--database portfolio-staging \  # Change database here
```

### Adjust Validation Thresholds

Edit `tests/e2e/data_collector.py` around line 750:

```python
if companies_count < 1:  # Change minimum company count
    issues.append(...)

if matches_count < 4:  # Change minimum match count
    issues.append(...)
```

## Understanding the Pipeline

### Job Processing Stages

```
job-queue (status: pending)
    ↓
JOB_SCRAPE (status: processing)
    ↓ Fetches HTML, extracts basic data
JOB_EXTRACT (status: processing)  
    ↓ Creates job-listings document
JOB_ANALYZE (status: processing)
    ↓ AI analysis, creates companies document
JOB_SAVE (status: success)
    ↓ Creates job-matches document
COMPLETE ✓
```

### Timing Breakdown

- **Worker polling**: 60 seconds between polls
- **JOB_SCRAPE**: 5-15 seconds
- **JOB_EXTRACT**: 5-10 seconds  
- **JOB_ANALYZE**: 10-20 seconds (AI call)
- **JOB_SAVE**: 1-2 seconds
- **Total per job**: ~30-60 seconds
- **4 jobs in sequence**: ~2-4 minutes

## Files Modified

- `tests/e2e/data_collector.py` - Test implementation
- `Makefile` - Added GOOGLE_APPLICATION_CREDENTIALS

## Related Documentation

- `E2E_TEST_FIX_SUMMARY.md` - Detailed changes made
- `E2E_TEST_ANALYSIS.md` - Original issue analysis
- `docs/E2E_TESTING_QUICK_REF.md` - General E2E testing guide
