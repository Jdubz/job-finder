# Job-Finder E2E Tests

End-to-end test suite for the job-finder-FE + Job-Finder integration.

## Overview

This repository contains E2E tests that validate the complete job processing pipeline from submission through AI analysis to match creation. Tests run against the staging environment (`portfolio-staging` database).

## Quick Start

### Prerequisites

- Python 3.11+
- Job-finder repository installed
- GCP credentials for staging environment

### Setup

```bash
# Install job-finder if not already installed
cd ../job-finder
pip install -r requirements.txt
pip install -e .

# Install test dependencies
cd ../job-finder-e2e-tests
pip install -r requirements-test.txt

# Configure GCP credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### Run Tests

```bash
# Run all scenarios
python tests/e2e/run_all_scenarios.py

# Run with verbose output
python tests/e2e/run_all_scenarios.py --verbose

# Run specific scenarios
python tests/e2e/run_all_scenarios.py --scenarios job_submission

# List available scenarios
python tests/e2e/run_all_scenarios.py --list
```

## Test Scenarios

### Scenario 1: Job Submission Flow
Complete happy path from submission to match creation.

**Tests:**
- Queue item creation
- Job scraping (granular pipeline)
- Filter evaluation
- AI matching analysis
- Match creation in Firestore

### Scenario 2: Filtered Job
Cost optimization - filtered jobs should not reach AI analysis.

**Tests:**
- Strike-based filtering
- Pipeline stops at filter stage
- No AI analysis for filtered jobs
- Fast processing time

## Documentation

- **Test Suite README:** `tests/e2e/README.md`
- **Design Document:** `/home/jdubz/Development/E2E_TEST_DESIGN.md`

## CI/CD

Tests run automatically via GitHub Actions:

- On pull requests to `staging` or `main`
- On push to `staging`
- Nightly at 6 AM UTC
- Manual trigger via workflow_dispatch

### Manual Trigger

```bash
gh workflow run e2e-tests.yml \
  -f database=portfolio-staging \
  -f scenarios="job_submission filtered_job"
```

## Cleanup

Automatic cleanup runs after each test. Manual cleanup:

```bash
# Clean all test data older than 24 hours
python tests/e2e/cleanup.py

# Dry run (preview)
python tests/e2e/cleanup.py --dry-run

# Clean specific test run
python tests/e2e/cleanup.py --test-run-id e2e_test_abc123
```

## Architecture

### Directory Structure

```
job-finder-e2e-tests/
├── tests/
│   └── e2e/
│       ├── scenarios/
│       │   ├── base_scenario.py          # Base test class
│       │   ├── scenario_01_job_submission.py
│       │   └── scenario_02_filtered_job.py
│       ├── helpers/
│       │   ├── queue_monitor.py          # Queue monitoring
│       │   ├── firestore_helper.py       # Firestore operations
│       │   └── cleanup_helper.py         # Cleanup utilities
│       ├── run_all_scenarios.py          # Test runner
│       ├── cleanup.py                    # Cleanup script
│       └── README.md                     # Detailed docs
├── .github/
│   └── workflows/
│       └── e2e-tests.yml                 # CI/CD workflow
└── E2E_README.md                         # This file
```

### Key Components

**BaseE2EScenario**
- Lifecycle methods: setup, execute, verify, cleanup
- Automatic cleanup tracking
- Standardized logging

**QueueMonitor**
- Wait for status changes
- Monitor pipeline stages
- Timeout handling

**FirestoreHelper**
- CRUD operations
- Queue item creation
- Match document access

**CleanupHelper**
- Batch deletion
- Age-based cleanup
- Test run filtering

## Adding New Tests

See `tests/e2e/README.md` for detailed instructions on adding new test scenarios.

## Troubleshooting

### "Permission denied" errors

Check GCP credentials:
```bash
gcloud auth application-default login
# or
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### "Timeout" errors

- Ensure job-finder worker is running
- Increase timeout in QueueMonitor
- Check network connectivity

### "Document not found" errors

- Verify database name is correct
- Check cleanup isn't running too early
- Disable cleanup: `--no-cleanup`

## Related Repositories

- **job-finder:** https://github.com/Jdubz/job-finder
- **portfolio:** https://github.com/Jdubz/portfolio
- **shared-types:** `../shared-types` (local package)

## License

See parent repository license.
