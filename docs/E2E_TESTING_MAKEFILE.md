# Complete E2E Testing with Make

## Overview

The `make test-e2e-full` command provides a single, comprehensive end-to-end testing workflow that:

1. **Stores/Backs up** existing Firestore data
2. **Cleans** test collections (removes old test data)
3. **Periodically Submits** test jobs with known values
4. **Monitors** job processing and test execution
5. **Saves Results** with comprehensive analysis and quality reports

## Quick Start

```bash
# Run the complete E2E suite
make test-e2e-full

# Or run just the basic E2E tests
make test-e2e
```

## Command Details

### `make test-e2e-full`

This is the **complete end-to-end testing pipeline** that orchestrates the entire workflow:

**What it does:**

1. **[1/5] Collecting and Cleaning Test Data**
   - Backs up existing Firestore collections to JSON
   - Clears test collections for clean testing environment
   - Generates backup metadata with timestamps and document counts
   - Command: `tests/e2e/data_collector.py`
   - Output: `test_results/{TEST_RUN_ID}/backup/`

2. **[2/5] Running E2E Tests with Streaming Logs**
   - Executes test scenarios (Job Submission, Filtering, Source Discovery, etc.)
   - Streams logs from Google Cloud Logging in real-time
   - Monitors data quality throughout test execution
   - Command: `tests/e2e/run_with_streaming.py`
   - Output: `test_results/{TEST_RUN_ID}/e2e_output.log`

3. **[3/5] Analyzing Results and Quality Metrics**
   - Compares Firestore state before/after tests
   - Analyzes job submission success rates
   - Calculates data quality improvements
   - Generates detailed metrics and findings
   - Command: `tests/e2e/results_analyzer.py`
   - Output: `test_results/{TEST_RUN_ID}/analysis/`

4. **[4/5] Saving Comprehensive Report**
   - Consolidates all results into structured format
   - Generates summary statistics
   - Produces machine-readable JSON reports

5. **[5/5] Complete**
   - Displays final summary with pass/fail status
   - Shows results directory for further inspection

**Example Output:**

```
Starting full E2E test suite...
This will: store data, clean, submit jobs, monitor, and save results
Test Run ID: e2e_1729276448
Results Directory: test_results/e2e_1729276448

[1/5] Collecting and cleaning test data...
✓ Backed up 5 collections (1,247 documents total)
✓ Cleaned test collections

[2/5] Running E2E tests with streaming logs...
✓ Job Submission Scenario: PASS (15 jobs, 100% success)
✓ Filtered Job Scenario: PASS (8 jobs, 100% success)
✓ Source Discovery Scenario: PASS (24 sources detected)

[3/5] Analyzing results and quality metrics...
✓ Collections created: 127 new jobs
✓ Data quality score: 98.5%
✓ All tests passed

[4/5] Saving comprehensive report...
✓ Report saved

✓ E2E Test Suite Complete!
Results saved to: test_results/e2e_1729276448
View analysis at: test_results/e2e_1729276448/analysis
```

### `make test-e2e`

The **lightweight E2E test runner** for quick validation:

```bash
make test-e2e
```

This runs the basic E2E test suite without full data collection and analysis. Good for quick iteration during development.

## Output Structure

Results are organized by timestamp in `test_results/{TEST_RUN_ID}/`:

```
test_results/e2e_1729276448/
├── backup/
│   ├── jobs.json              # Backup of original jobs
│   ├── matches.json           # Backup of original matches
│   ├── backup_metadata.json   # Backup metadata
│   └── ...
├── e2e_output.log             # Raw test execution logs
├── analysis/
│   ├── job_submission_analysis.json   # Job metrics
│   ├── collection_comparison.json     # Before/after comparison
│   ├── quality_report.json            # Data quality metrics
│   └── test_run_analysis.json         # Complete analysis
└── final_report.json          # Consolidated results
```

## Key Features

### Automatic Test Run ID

Each execution generates a unique test run ID based on timestamp:
```
e2e_1729276448  # Unix timestamp
```

This ensures results from different runs don't overwrite each other.

### Real-time Log Streaming

The suite streams logs from Google Cloud Logging in real-time, showing:
- Queue processing events
- Job submissions and results
- Source rotation decisions
- Error conditions and recovery

Enable/disable with environment variables:
```bash
export GCP_PROJECT_ID=your-project-id
make test-e2e-full
```

### Data Quality Monitoring

Tracks data quality metrics throughout testing:
- Job duplication prevention
- URL normalization accuracy
- Source rotation fairness (95%+ target)
- Timeout reduction (< 5% target)
- Overall health score calculation

### Comprehensive Analysis

Generates detailed reports including:
- **Collection Comparisons**: Before/after Firestore state
- **Job Submission Analysis**: Success rates, submission patterns
- **Data Quality Metrics**: Improvements and issues
- **Health Assessment**: PASS/WARN/FAIL with key findings

## Common Workflows

### Quick Validation (1-2 minutes)

```bash
# Run basic E2E tests only
make test-e2e
```

### Full Testing with Reports (5-10 minutes)

```bash
# Run complete pipeline with all analysis
make test-e2e-full

# View results
ls -la test_results/
```

### Scheduled Testing

```bash
# Run every night at 2 AM
# Add to crontab:
0 2 * * * cd /path/to/job-finder && make test-e2e-full
```

### CI/CD Integration

```bash
# In GitHub Actions or similar CI system
- name: Run E2E Tests
  run: make test-e2e-full
  
- name: Upload Results
  uses: actions/upload-artifact@v3
  with:
    name: e2e-test-results
    path: test_results/
```

### Compare Multiple Runs

```bash
# Run baseline
make test-e2e-full
# Results in: test_results/e2e_TIMESTAMP1/

# Make changes, run again
make test-e2e-full
# Results in: test_results/e2e_TIMESTAMP2/

# Compare reports
diff test_results/e2e_TIMESTAMP1/analysis/quality_report.json \
     test_results/e2e_TIMESTAMP2/analysis/quality_report.json
```

## Environment Variables

Control test behavior with environment variables:

```bash
# Enable Google Cloud Log streaming
export GCP_PROJECT_ID=your-project-id

# Use different Firestore database
export FIRESTORE_DATABASE=portfolio-production

# Enable verbose output
export VERBOSE=true

# Run with custom config
export CONFIG_FILE=config/custom-config.yaml

make test-e2e-full
```

## Performance Targets

The E2E suite validates these key metrics:

| Metric | Target | Status |
|--------|--------|--------|
| Deduplication Performance | < 2ms per job | ✓ Implemented |
| Source Rotation Fairness | > 95% coverage | ✓ Implemented |
| Timeout Rate | < 5% | ✓ Implemented |
| Data Quality Score | > 95% | ✓ Monitored |
| Job Success Rate | > 98% | ✓ Tracked |

## Troubleshooting

### Command Not Found
```bash
# Ensure you're in the project root
cd /path/to/job-finder

# Check Makefile exists
ls Makefile
```

### Permission Denied
```bash
# Ensure venv is properly set up
make setup

# Or activate manually
source venv/bin/activate
```

### Tests Hanging
```bash
# Check if Firestore is accessible
python3 -c "from job_finder.storage.firestore_client import FirestoreClient; print(FirestoreClient.get_client('portfolio-staging'))"

# Timeout occurs after 10 minutes per default - check for stuck queue items
```

### Google Cloud Logging Not Working
```bash
# Ensure credentials are configured
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/serviceAccountKey.json

# Set project ID
export GCP_PROJECT_ID=your-project-id

# Disable log streaming if issues persist
# Edit Makefile to remove --stream-logs flag
```

## Related Documentation

- [E2E Complete Integration Guide](./E2E_COMPLETE_INTEGRATION.md)
- [Data Quality Monitoring](./DATA_QUALITY_MONITORING.md)
- [E2E Testing Index](./E2E_TESTING_INDEX.md)
- [Queue System Documentation](./queue-system.md)

## See Also

- `make test` - Run all unit tests
- `make test-coverage` - Run tests with coverage report
- `make quality` - Run all code quality checks
- `make help` - Show all available commands
