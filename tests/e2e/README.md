# End-to-End Pipeline Testing

This directory contains end-to-end tests that validate the complete job processing pipeline from submission to final storage.

## Overview

E2E tests spin up a local Docker environment, submit known job listings, and track them through the entire pipeline:

1. **Job Submission** → Queue item created
2. **Scraping** → HTML fetched, data extracted
3. **Filtering** → Strike-based filtering applied
4. **AI Analysis** → Match score and intake data generated
5. **Storage** → Job match saved to Firestore
6. **Verification** → Results validated

## Test Environment

Tests run against:
- **Docker container**: Isolated job-finder worker
- **Firestore**: `portfolio-staging` database
- **Test data**: Known job listings with predictable results

## Running E2E Tests

### Prerequisites

```bash
# Ensure Docker is running
docker --version

# Ensure Firebase credentials are set
export GOOGLE_APPLICATION_CREDENTIALS=.firebase/static-sites-257923-firebase-adminsdk.json

# Install dependencies
pip install -e ".[dev]"
```

### Run Full E2E Test

```bash
# Run complete pipeline test
python tests/e2e/test_pipeline_e2e.py

# Run with verbose output
python tests/e2e/test_pipeline_e2e.py --verbose

# Run specific test case
python tests/e2e/test_pipeline_e2e.py --test high_match
```

### Run Docker-based Test

```bash
# Build and run in Docker (mirrors production)
./tests/e2e/run_docker_e2e.sh

# Clean up after test
./tests/e2e/run_docker_e2e.sh --cleanup
```

## Test Cases

### 1. High Match Score Job
- **Input**: Senior Python Engineer at well-known tech company
- **Expected**: Match score >85, High priority, saved to job-matches
- **Validates**: Full pipeline success

### 2. Filtered Job
- **Input**: Job with excluded keywords (e.g., "on-site only")
- **Expected**: Rejected at filter stage, not analyzed
- **Validates**: Filter engine working correctly

### 3. Below Threshold Job
- **Input**: Junior position with skill mismatch
- **Expected**: AI analysis runs but score <80, not saved
- **Validates**: AI scoring and threshold enforcement

### 4. Duplicate Detection
- **Input**: Same job URL submitted twice
- **Expected**: Second submission skipped
- **Validates**: Duplicate detection working

### 5. Source Discovery
- **Input**: Greenhouse board URL
- **Expected**: Source created, jobs scraped, matches found
- **Validates**: Source discovery pipeline

## Test Data

Known test jobs are stored in `tests/e2e/fixtures/`:
- `high_match_job.json` - Should score 85+
- `filtered_job.json` - Should be rejected by filters
- `low_match_job.json` - Should score <80
- `greenhouse_board.json` - Source discovery test

## Monitoring Test Progress

The E2E test script provides real-time progress:

```
[1/5] Submitting test job to queue...
✓ Queue item created: abc-123

[2/5] Waiting for SCRAPE step...
✓ SCRAPE completed in 3.2s

[3/5] Waiting for FILTER step...
✓ FILTER passed (8 strikes)

[4/5] Waiting for ANALYZE step...
✓ ANALYZE completed (score: 87, priority: High)

[5/5] Waiting for SAVE step...
✓ Job saved to job-matches: def-456

✓ E2E test passed in 24.5s
```

## Cleanup

Tests automatically clean up:
- Test queue items
- Test job matches
- Test sources
- Docker containers

To manually clean up:

```bash
python tests/e2e/cleanup_test_data.py --all
```

## Troubleshooting

### Test Hangs

If test hangs waiting for pipeline step:
1. Check worker logs: `docker logs job-finder-worker`
2. Check queue item status in Firestore
3. Check for errors in Cloud Logging

### Test Fails

Common failures:
- **AI API errors**: Check API keys in environment
- **Firestore errors**: Verify credentials and database name
- **Docker errors**: Ensure Docker is running and has sufficient resources

### Debug Mode

Run with debug logging:

```bash
python tests/e2e/test_pipeline_e2e.py --debug
```

This enables:
- Verbose logging
- Step-by-step output
- No cleanup (inspect state after failure)

## CI/CD Integration

E2E tests can run in GitHub Actions:

```yaml
- name: Run E2E Tests
  run: |
    docker build -t job-finder:test .
    python tests/e2e/test_pipeline_e2e.py --ci
```

Use `--ci` flag for CI environments (shorter timeouts, fail fast).

## Performance Benchmarks

Expected timings:
- **Full pipeline (SCRAPE → SAVE)**: 15-30 seconds
- **SCRAPE step**: 2-5 seconds
- **FILTER step**: <0.5 seconds
- **ANALYZE step**: 5-15 seconds
- **SAVE step**: <1 second

If tests exceed these timings, investigate:
- AI provider latency
- Firestore query performance
- Docker resource constraints
