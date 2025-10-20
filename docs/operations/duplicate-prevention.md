# Duplicate Prevention Operations Guide

**Last Updated**: 2025-10-20  
**Related**: BUG-1 — Duplicate Jobs in Matches  

## Overview

This guide explains how the job-finder-worker prevents duplicate job matches in Firestore and how to identify and clean up any existing duplicates.

## How Duplicate Prevention Works

### URL Normalization

All job URLs are normalized before storage using the `normalize_url()` function (alias: `normalize_job_url()`):

**Normalization Steps:**
1. Convert domain to lowercase
2. Remove trailing slashes (except root `/`)
3. Remove tracking parameters:
   - UTM parameters: `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`
   - Social tracking: `fbclid`, `ref`, `source`
   - Ad tracking: `msclkid`, `gclid`, `gclsrc`, `dclid`
   - Analytics: `_ga`, `_gid`, `_gat`
   - Job board tokens: `t` (Greenhouse, etc.)
4. Sort query parameters alphabetically
5. Remove URL fragments (#section)

**Example:**
```python
from job_finder.utils.url_utils import normalize_job_url

# Input URLs (all different)
url1 = "https://boards.greenhouse.io/company/jobs/123?t=abc&utm_source=linkedin"
url2 = "HTTPS://BOARDS.GREENHOUSE.IO/company/jobs/123/"
url3 = "https://boards.greenhouse.io/company/jobs/123#apply"

# All normalize to the same value
normalized = normalize_job_url(url1)
# Result: "https://boards.greenhouse.io/company/jobs/123"
```

### Duplicate Detection Points

The system checks for duplicates at two stages:

#### 1. Job Intake (Queue Submission)

**File**: `src/job_finder/queue/scraper_intake.py`  
**Method**: `submit_jobs()`

Checks before adding to queue:
- URL exists in `job-queue` collection (pending jobs)
- URL exists in `job-matches` collection (completed jobs)

**Result**: Skips submission with debug log

#### 2. Job Save (Final Storage)

**File**: `src/job_finder/storage/firestore_storage.py`  
**Method**: `save_job_match()`

Checks before saving to `job-matches`:
- URL exists in `job-matches` collection

**Result**: Returns existing document ID with structured log

### Structured Logging

Duplicate detection uses structured logging for monitoring:

```
[DB:DUPLICATE] Job already exists: Senior Software Engineer at Example Corp 
               (URL: https://example.com/jobs/123, existing ID: abc123)

[DB:CREATE] Saved job match: Senior Software Engineer at Example Corp 
            (ID: def456, Score: 85)
```

**Monitoring Commands:**
```bash
# Check for duplicates in staging
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" 
  AND labels.environment="staging" 
  AND textPayload:"[DB:DUPLICATE]"' \
  --limit 20 \
  --freshness 1h

# Check successful saves
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" 
  AND labels.environment="staging" 
  AND textPayload:"[DB:CREATE]"' \
  --limit 20 \
  --freshness 1h
```

## Identifying Duplicates

### Using Firestore Console

1. Open Firestore console
2. Navigate to `job-matches` collection
3. Query by URL:
   ```
   url == "https://example.com/jobs/123"
   ```
4. Multiple results = duplicates

### Using Cleanup Script

**File**: `scripts/database/cleanup_job_matches.py`

**Analyze only (safe):**
```bash
python scripts/database/cleanup_job_matches.py \
  --database portfolio-staging \
  --analyze-only
```

**Output:**
```
Data Quality Report
==================
Duplicate URLs: 15

Sample duplicate URLs:
  URL: https://boards.greenhouse.io/company/jobs/123
  Document IDs: abc123, def456, ghi789
```

## Cleaning Up Existing Duplicates

### Safety Precautions

⚠️ **IMPORTANT**: Always test on staging first!

**Safety Features:**
- Requires explicit `--database` flag
- Staging is default and safe
- Production requires `--allow-production` flag
- 10-second countdown before production cleanup

### Staging Cleanup (Safe)

```bash
# 1. Analyze first (no changes)
python scripts/database/cleanup_job_matches.py \
  --database portfolio-staging \
  --analyze-only

# 2. Review output, then clean
python scripts/database/cleanup_job_matches.py \
  --database portfolio-staging
```

### Production Cleanup (Dangerous)

```bash
# ⚠️ ONLY use if absolutely necessary
# Test on staging first!
python scripts/database/cleanup_job_matches.py \
  --database portfolio \
  --allow-production
```

### Cleanup Algorithm

When duplicates are found, the script:

1. **Groups** jobs by normalized URL
2. **Scores** each duplicate based on completeness:
   - Non-empty fields (company, website, info, description, etc.): +1 each
   - Has resume intake data: +10
   - Match score: +score/10
3. **Keeps** the highest-scoring record
4. **Deletes** all other duplicates

**Example:**
```
Duplicate found: https://example.com/jobs/123
  3 copies
  Keeping: abc123 (score: 16.5)
  Deleting: 2 duplicates
    ✓ Deleted: def456
    ✓ Deleted: ghi789
```

## Preventing Future Duplicates

### Best Practices

1. **Always normalize URLs** when working with job data:
   ```python
   from job_finder.utils.url_utils import normalize_job_url
   
   normalized_url = normalize_job_url(raw_url)
   ```

2. **Use ScraperIntake** for submitting jobs (has built-in duplicate checks):
   ```python
   from job_finder.queue.scraper_intake import ScraperIntake
   
   intake = ScraperIntake(queue_manager)
   added = intake.submit_jobs(jobs, source="scraper_name")
   ```

3. **Monitor logs** for duplicate detection:
   - Watch for `[DB:DUPLICATE]` tags
   - Investigate if duplicates increase suddenly

4. **Run periodic cleanup** on staging:
   ```bash
   # Weekly or after major scraping runs
   python scripts/database/cleanup_job_matches.py \
     --database portfolio-staging
   ```

### Pipeline Safeguards

The granular pipeline now has multiple checkpoints:

```
JOB_SCRAPE → JOB_FILTER → JOB_ANALYZE → JOB_SAVE
     ↓            ↓            ↓            ↓
  Check #1    Check #2     Check #3     Check #4
  (Intake)    (N/A)        (N/A)        (Save)
```

- **Check #1**: Before adding to queue (intake)
- **Check #4**: Before saving to job-matches (save)

## Common Issues

### Issue: Duplicates Still Being Created

**Symptoms:**
- Same URL appears multiple times in job-matches
- `[DB:DUPLICATE]` not appearing in logs

**Diagnosis:**
```bash
# Check if duplicates are being created
python scripts/database/cleanup_job_matches.py \
  --database portfolio-staging \
  --analyze-only
```

**Solutions:**
1. Verify URL normalization is working:
   ```python
   from job_finder.utils.url_utils import normalize_job_url
   
   url1 = "your-url-here"
   url2 = "similar-url-here"
   print(normalize_job_url(url1) == normalize_job_url(url2))
   ```

2. Check if race conditions occurring:
   - Multiple workers processing same job simultaneously
   - Solution: Ensure proper queue locking

3. Verify save_job_match is checking for duplicates:
   - Check logs for `[DB:DUPLICATE]` tags
   - Review firestore_storage.py implementation

### Issue: Cleanup Script Not Finding Duplicates

**Symptoms:**
- Know duplicates exist but script reports 0

**Diagnosis:**
- URLs may not be normalized consistently
- Check URL field values in Firestore console

**Solution:**
```bash
# Re-normalize all URLs in database
python scripts/database/normalize_job_urls.py \
  --database portfolio-staging
```

### Issue: Want to Merge Duplicate Data

**Symptoms:**
- Duplicates have different information
- Want to combine data rather than delete

**Solution:**
The cleanup script keeps the most complete record automatically. If you need custom merging:

1. Export duplicates:
   ```python
   from job_finder.storage.firestore_storage import FirestoreJobStorage
   
   storage = FirestoreJobStorage(database_name="portfolio-staging")
   
   # Get all jobs with specific URL
   query = storage.db.collection("job-matches").where("url", "==", normalized_url)
   duplicates = [doc.to_dict() for doc in query.stream()]
   ```

2. Manually merge data as needed
3. Delete old records, save merged record

## Testing Duplicate Prevention

### Unit Tests

Run duplicate prevention tests:
```bash
pytest tests/test_firestore_storage_duplicates.py -v
pytest tests/test_url_utils.py -v
```

### Integration Test

Test full pipeline:
```python
from job_finder.queue.scraper_intake import ScraperIntake
from job_finder.queue.manager import QueueManager

queue_manager = QueueManager()
intake = ScraperIntake(queue_manager)

# Submit same job twice
job_data = {
    "title": "Test Job",
    "company": "Test Corp",
    "url": "https://example.com/test",
    "location": "Remote",
    "description": "Test description",
}

# First submission
doc_id1 = intake.submit_jobs([job_data], source="test")
# Should add: 1

# Second submission (should skip)
doc_id2 = intake.submit_jobs([job_data], source="test")  
# Should add: 0 (duplicate)
```

## Monitoring Dashboard

### Key Metrics

Track these metrics in your monitoring dashboard:

1. **Duplicate Detection Rate**
   - Count of `[DB:DUPLICATE]` logs per hour
   - Should be low after cleanup

2. **New Job Creation Rate**
   - Count of `[DB:CREATE]` logs per hour
   - Should match scraping activity

3. **Duplicate Ratio**
   - `duplicates / (duplicates + new_jobs)`
   - Should be < 5% in healthy system

### Alerts

Set up alerts for:
- Duplicate ratio > 10% (indicates problem)
- No `[DB:CREATE]` logs for 1 hour (pipeline stopped)
- Sudden spike in duplicates (source configuration issue)

## References

### Code Files

- `src/job_finder/utils/url_utils.py` - URL normalization
- `src/job_finder/storage/firestore_storage.py` - Duplicate detection in save
- `src/job_finder/queue/scraper_intake.py` - Duplicate detection in intake
- `scripts/database/cleanup_job_matches.py` - Cleanup script

### Documentation

- `docs/issues/bug-1-duplicate-jobs-in-matches.md` - Bug details
- `docs/issues/ISSUE_CONTEXT.md` - Repository context
- `CLAUDE.md` - Project overview

### Tests

- `tests/test_url_utils.py` - URL normalization tests
- `tests/test_firestore_storage_duplicates.py` - Duplicate prevention tests

## Support

If you encounter issues with duplicate prevention:

1. Check logs for `[DB:DUPLICATE]` and `[DB:CREATE]` tags
2. Run analysis script on staging
3. Review this guide for common issues
4. Create GitHub issue with:
   - Database name (staging/production)
   - Sample duplicate URLs
   - Log excerpts showing the problem

---

**Last Updated**: 2025-10-20  
**Maintained By**: Project Team  
**Related Issues**: BUG-1
