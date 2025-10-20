# BUG-1 — Duplicate Jobs in Matches

**Priority**: P1 (High Impact)  
**Status**: In Progress  
**Owner**: Worker A  

## Summary

Job matches are being duplicated in the `job-matches` Firestore collection despite URL normalization being implemented. This issue affects data quality and user experience by showing the same job posting multiple times.

## Problem Statement

### Current Behavior

1. **URL Normalization Exists**: The `url_utils.py` module provides `normalize_url()` function that:
   - Converts domain to lowercase
   - Removes trailing slashes
   - Removes tracking parameters (utm_*, fbclid, etc.)
   - Sorts query parameters
   - Removes URL fragments

2. **Duplicate Prevention in Intake**: The `scraper_intake.py` checks for duplicates:
   - Checks if URL exists in queue
   - Checks if job exists in job-matches collection
   - Uses normalized URLs for comparison

3. **Gap in Save Pipeline**: The `save_job_match()` method in `firestore_storage.py`:
   - ✅ Normalizes URL before saving
   - ❌ Does NOT check if URL already exists before creating new document
   - ❌ No structured logging for duplicate detection
   - **Result**: Duplicates can be created if the same job goes through the pipeline multiple times

### Root Cause

The granular pipeline (JOB_SCRAPE → JOB_FILTER → JOB_ANALYZE → JOB_SAVE) can create duplicates when:
1. The same job URL is submitted multiple times before the first one completes
2. Race conditions between queue check and final save
3. Manual reprocessing of jobs
4. Source updates causing re-scrapes of existing jobs

### Example Duplicates

```
URL: https://example.com/jobs/123
Document IDs: abc123, def456, ghi789

All three documents have:
- Same normalized URL
- Same job title and company
- Different createdAt timestamps
- Different match scores (due to profile/timing changes)
```

## Solution

### 1. Add Duplicate Check in Save Pipeline

**File**: `src/job_finder/storage/firestore_storage.py`

Add duplicate check in `save_job_match()` method:
- Check if normalized URL already exists before saving
- If exists, log and skip (don't create duplicate)
- Add structured logging with [DB:DUPLICATE] tag

### 2. Add normalize_job_url Alias

**File**: `src/job_finder/utils/url_utils.py`

Create `normalize_job_url()` as an alias for `normalize_url()`:
- Provides domain-specific naming for job URLs
- Maintains backward compatibility
- Documents job-specific normalization

### 3. Update Cleanup Script

**File**: `scripts/database/cleanup_job_matches.py`

Verify the cleanup script:
- Uses normalized URLs for duplicate detection
- Keeps the most complete record when merging
- Logs actions with structured format

### 4. Add Structured Logging

Add logging categories for duplicate detection:
- `[DB:DUPLICATE]` - Duplicate detected and skipped
- `[DB:CREATE]` - New job match created
- `[DB:UPDATE]` - Existing job match updated

### 5. Create Operations Documentation

**File**: `docs/operations/duplicate-prevention.md`

Document:
- How duplicate prevention works
- How to identify duplicates
- How to clean up existing duplicates
- How to prevent future duplicates

## Implementation Tasks

- [x] Document current duplicate behavior
- [ ] Add duplicate check in `save_job_match` method
- [ ] Add `normalize_job_url` alias function
- [ ] Add structured logging for duplicates
- [ ] Add tests for duplicate prevention
- [ ] Update cleanup script documentation
- [ ] Create operations documentation
- [ ] Run cleanup on staging database
- [ ] Verify with DATA-QA-1 smoke test

## Testing Strategy

### Unit Tests

1. Test `save_job_match` with duplicate URL:
   - First call: Creates new document
   - Second call: Skips and logs duplicate
   - Returns existing document ID

2. Test URL normalization variants:
   - Same URL with different tracking params
   - Same URL with/without trailing slash
   - Same URL with different case

### Integration Tests

1. Test full pipeline with duplicate submission:
   - Submit same job twice
   - Verify only one job-match created
   - Verify structured logs show duplicate detection

### Smoke Tests (DATA-QA-1)

1. Run cleanup script on staging
2. Verify no duplicates remain
3. Submit test jobs through pipeline
4. Verify no new duplicates created

## Acceptance Criteria

- [x] `normalize_job_url` utility implemented (alias)
- [ ] `save_job_match` checks for duplicates before creating
- [ ] Structured logs show duplicate detection with [DB:DUPLICATE] tag
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Cleanup script executed on staging
- [ ] Operations documentation created
- [ ] No duplicate jobs in staging after cleanup
- [ ] New job submissions don't create duplicates

## Related Documentation

- [ISSUE_CONTEXT.md](./ISSUE_CONTEXT.md) - Repository structure and patterns
- [url_utils.py](../../src/job_finder/utils/url_utils.py) - URL normalization implementation
- [firestore_storage.py](../../src/job_finder/storage/firestore_storage.py) - Job storage implementation
- [cleanup_job_matches.py](../../scripts/database/cleanup_job_matches.py) - Cleanup script

## Notes

- URL normalization is already implemented and well-tested
- The issue is in the save pipeline, not the intake pipeline
- Cleanup script already exists and is production-safe
- Need to ensure backward compatibility with existing code

## Related Issues

- DATA-QA-1: Data quality smoke test
- Related to company duplicate detection (different issue)
