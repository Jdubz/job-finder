# E2E Test Suite

End-to-end tests for the Portfolio + Job-Finder integration in the staging environment.

## Overview

This test suite validates the complete job processing pipeline from submission through AI analysis to match creation. Tests run against the `portfolio-staging` Firestore database.

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

## Running Tests

### Run All Scenarios

```bash
cd /home/jdubz/Development/job-finder-e2e-tests
python tests/e2e/run_all_scenarios.py
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

## CI/CD Integration

Tests can be run automatically via GitHub Actions:

```yaml
- name: Run E2E Tests
  run: |
    cd job-finder-e2e-tests
    python tests/e2e/run_all_scenarios.py --database portfolio-staging
```

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

**"Document not found" errors:**
- Check database name is correct
- Verify queue item was created
- Check cleanup isn't running too early

**"Timeout" errors:**
- Increase timeout in QueueMonitor
- Check job-finder worker is running
- Verify network connectivity

**"Permission denied" errors:**
- Check Firestore credentials
- Verify service account has proper roles
- Check Firestore rules allow test writes

## Design Document

For detailed design and implementation specifications, see:
- `/home/jdubz/Development/E2E_TEST_DESIGN.md`
