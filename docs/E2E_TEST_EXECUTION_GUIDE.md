# E2E Test Execution Guide

**Quick Start for Running Tests Against Staging Environment**

## Prerequisites

1. **Environment Setup**
```bash
# Navigate to job-finder directory
cd /home/jdubz/Development/job-finder-app/job-finder

# Verify Python environment
source venv/bin/activate
python --version  # Should be 3.11+

# Verify Google Cloud credentials
export GOOGLE_APPLICATION_CREDENTIALS=./credentials/serviceAccountKey.json
ls -la $GOOGLE_APPLICATION_CREDENTIALS
```

2. **Verify Portainer Worker is Running**
```bash
# Check if Portainer deployment is healthy
# Access: http://your-nas-ip:9000 (or configure in environment)

# Test connection to staging Firestore
python -c "
from job_finder.storage.firestore_client import FirestoreClient
db = FirestoreClient.get_client('portfolio-staging')
print('✓ Firestore connected')
"
```

## Running Tests

### Option 1: Run All Scenarios (Full Suite)
```bash
cd /home/jdubz/Development/job-finder-app/job-finder

export GOOGLE_APPLICATION_CREDENTIALS=./credentials/serviceAccountKey.json

# Run with standard output
python tests/e2e/run_all_scenarios.py --verbose

# Run and save output
python tests/e2e/run_all_scenarios.py --verbose 2>&1 | tee e2e_test_run_$(date +%Y%m%d_%H%M%S).log
```

### Option 2: Run Specific Scenarios
```bash
# List available scenarios
python tests/e2e/run_all_scenarios.py --list

# Run only job submission scenario
python tests/e2e/run_all_scenarios.py --scenarios job_submission

# Run multiple scenarios
python tests/e2e/run_all_scenarios.py --scenarios job_submission filtered_job scrape_rotation
```

### Option 3: Run with Custom Configuration
```bash
# Run against different database
python tests/e2e/run_all_scenarios.py --database portfolio-production

# Disable cleanup (keep test data)
python tests/e2e/run_all_scenarios.py --no-cleanup

# Disable cleanup and verbose
python tests/e2e/run_all_scenarios.py --verbose --no-cleanup
```

## Monitoring Tests

### During Execution
- Watch console output for real-time progress
- Look for ✓ (pass) and ✗ (fail) symbols
- Check for assertions that fail

### After Execution
```bash
# View test summary at end of output
# Shows: Total, Passed, Failed, Errors, Skipped

# Check test log file for details
tail -100 e2e_test_run_*.log
```

### Monitoring in Google Cloud

```bash
# 1. Open Google Cloud Logs in browser
# https://console.cloud.google.com/logs

# 2. Create filter for E2E test logs
resource.type="gce_instance"
labels.test_run_id="e2e_test_*"

# 3. Search for errors
severity>=ERROR

# 4. Track specific document
jsonPayload.doc_id="your_document_id"
```

## Understanding Test Output

### Successful Test
```
[ScrapeRotationScenario] ✓ Scrape succeeded
[ScrapeRotationScenario] ✓ Scraped 5 sources
[ScrapeRotationScenario] ✓ Respected max_sources limit (5)
[ScrapeRotationScenario] ✓ Rotation prioritized oldest sources (3/5)
```

### Failed Test
```
[JobSubmissionScenario] ✗ FAILURE: Queue item not found after scraping
[JobSubmissionScenario]   Message: Scrape queue item not found
[JobSubmissionScenario]   Error: Document not found in collection
```

### Timeout
```
TimeoutError: Timeout waiting for doc_id_123 to reach 'success'
  Waited: 300.1s (max: 300s)
  Last status: processing
  Message: Scraping source 2/5
  Error: N/A
  See Google Cloud Logging for details
```

## Cleanup

### Manual Cleanup (if tests hang)
```bash
# List test data to be cleaned up
python tests/e2e/cleanup.py --dry-run

# Clean all test data from last 24 hours
python tests/e2e/cleanup.py

# Clean specific test run
python tests/e2e/cleanup.py --test-run-id e2e_test_abc12345
```

## Troubleshooting

### Connection Issues
```bash
# Test Firestore connectivity
python -c "
from job_finder.storage.firestore_client import FirestoreClient
from datetime import datetime
db = FirestoreClient.get_client('portfolio-staging')
doc = db.collection('_health_check').document('ping')
doc.set({'ping': datetime.utcnow()})
print('✓ Firestore write successful')
"

# Test Google Cloud Logging
python -c "
from google.cloud import logging as cloud_logging
client = cloud_logging.Client()
print('✓ Google Cloud Logging connected')
"
```

### Test Hangs
```bash
# Check if Portainer worker is processing queue items
# Monitor job-queue collection for status changes:
# - pending → (pulling data) → running → (processing) → success/failed

# If stuck, check Portainer logs for errors

# If still hung after 5 mins, Ctrl+C and run cleanup
```

### Google Cloud Credentials Error
```bash
# Verify credentials file exists and is readable
ls -la credentials/serviceAccountKey.json

# Set environment variable explicitly
export GOOGLE_APPLICATION_CREDENTIALS=/home/jdubz/Development/job-finder-app/job-finder/credentials/serviceAccountKey.json

# Test credentials
python -c "
import json
with open('$GOOGLE_APPLICATION_CREDENTIALS') as f:
    creds = json.load(f)
    print(f'Project: {creds.get(\"project_id\")}')
    print(f'Type: {creds.get(\"type\")}')
"
```

## Capturing Results

### Save Test Output
```bash
# Run test and save with timestamp
python tests/e2e/run_all_scenarios.py --verbose > results_$(date +%Y%m%d_%H%M%S).txt 2>&1

# Extract pass/fail summary
grep -E "(✓|✗|SUMMARY)" results_*.txt
```

### Create Monitoring Report
```bash
# Watch multiple test runs
for i in {1..3}; do
  echo "=== Test Run $i ===" >> test_monitoring.log
  python tests/e2e/run_all_scenarios.py >> test_monitoring.log 2>&1
  sleep 60  # Wait before next run
done
```

## Performance Baseline

**Expected timings (staging environment):**
- Scenario 1 (Job Submission): 2-3 min
- Scenario 2 (Filtered Job): 1-2 min
- Scenario 3 (Company Discovery): 2-3 min
- Scenario 4 (Scrape Rotation): 8-10 min (with 5 sources)
- Scenario 5 (Full Discovery): 10-15 min

**If tests consistently exceed:**
- 2x baseline → Check Portainer resource usage
- 3x baseline → Check network/Firestore latency
- Timeout after 10 min → Check Google Cloud logs for errors

## Next Steps

1. Run baseline E2E tests to establish current behavior
2. Monitor test logs for errors and patterns
3. Review improvement plan at `docs/E2E_TEST_IMPROVEMENT_PLAN.md`
4. Implement fixes incrementally
5. Re-run tests after each fix to validate improvements
