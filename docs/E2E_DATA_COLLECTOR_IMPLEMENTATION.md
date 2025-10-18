# Phase 3: E2E Test Data Collector - Implementation Summary

## Overview

Phase 3 delivers a complete automated test data collection system for periodic E2E testing. The system backs up your Firestore collections, clears them for testing, submits known test jobs, collects all results, and saves everything locally for later analysis.

**Focus:** Data collection and analysis - NO UI components.

## Files Delivered

### Code (2 files, 1100+ lines total)

**1. `tests/e2e/data_collector.py` (550+ lines)**

Main orchestrator for test data collection.

**Classes:**

- `BackupMetadata` (dataclass)
  - Records backup details: timestamp, database name, collections backed up, document counts, file size
  
- `TestJobSubmission` (dataclass)
  - Records each job submission: ID, company, title, URL, expected vs actual result, duration, errors
  
- `TestRunResult` (dataclass)
  - Complete test run results with backup info, submission records, final metrics, issues found

- `FirestoreBackupRestore`
  - `backup_collection()` - Backup single collection to list of documents
  - `backup_all()` - Backup multiple collections to JSON files with metadata
  - `clear_collection()` - Delete all documents from a collection
  - `clear_collections()` - Clear multiple collections
  - `restore_collection()` - Restore collection from JSON backup

- `TestJobSubmitter`
  - `TEST_JOBS` - 4 predefined test jobs (MongoDB, Netflix, Shopify, Stripe)
  - `submit_test_job()` - Submit single test job, track result
  - `submit_all_test_jobs()` - Submit all test jobs
  - `_count_existing_jobs()` - Check if job already exists

- `TestResultsCollector`
  - `get_collection_counts()` - Get current document counts for collections
  - `save_collection_snapshot()` - Save collection as JSON file
  - `save_results()` - Save complete test results with snapshots and summary

- `E2ETestDataCollector` (Main class)
  - `run_collection()` - Execute complete workflow
    1. Backs up existing collections
    2. Clears test collections
    3. Submits test jobs
    4. Waits for processing
    5. Collects final state
    6. Validates results
    7. Saves everything
  - `_setup_logging()` - File + console logging
  - `_validate_results()` - Checks: enough job matches, enough companies, success rate, no failed submissions
  - Command-line interface with `--database`, `--output-dir`, `--verbose` flags

**2. `tests/e2e/results_analyzer.py` (550+ lines)**

Analyzes collected test data and generates reports.

**Classes:**

- `CollectionComparison` (dataclass)
  - Tracks changes: original count, final count, created, deleted, modified
  - Properties: `net_change`, `change_percentage`

- `JobSubmissionAnalysis` (dataclass)
  - Tracks: total submitted, succeeded, failed, by status, by company, duration stats
  - Properties: `success_rate`, `failure_rate`

- `TestRunAnalysis` (dataclass)
  - Complete analysis: test ID, duration, collection comparisons, submission analysis
  - Data quality scores before/after
  - Overall health score and assessment
  - Key findings list

- `ResultsAnalyzer`
  - `__init__()` - Load test results, backups, and collection snapshots
  - `analyze()` - Perform complete analysis
  - `_analyze_collection_changes()` - Compare original vs final snapshots
  - `_analyze_submissions()` - Analyze job submission patterns
  - `_calculate_quality()` - Calculate data quality scores
  - `_calculate_collection_completeness()` - Score individual collections
  - `_assess_results()` - Generate health assessment
  - `generate_report()` - Format analysis as human-readable text
  - `save_analysis()` - Save JSON analysis and text report
  - Command-line interface with `--results-dir`, `--output-dir` flags

### Documentation (1 file)

**`docs/E2E_DATA_COLLECTION_GUIDE.md` (500+ lines)**

Complete user guide covering:
- Overview of tools and workflow
- Quick start instructions
- Detailed usage of each tool
- Command-line reference
- Output file descriptions
- Workflow examples (single run, weekly monitoring, troubleshooting)
- File format explanations
- Troubleshooting section
- Integration notes for Phase 2 (AI analysis)
- Data retention recommendations

## How It Works

### Step 1: Backup
```python
backup_restore = FirestoreBackupRestore("portfolio-staging")
metadata = backup_restore.backup_all(
    ["job-listings", "companies", "job-sources", "job-queue"],
    Path("./backup_original")
)
```
- Saves each collection as JSON array of documents
- Includes document IDs for restoration
- Records metadata (timestamp, counts, size)

### Step 2: Clear
```python
backup_restore.clear_collections([
    "job-listings", "companies", "job-sources", "job-queue"
])
```
- Deletes all documents in batches
- Logs how many deleted
- Collections now empty for testing

### Step 3: Submit Test Jobs
```python
submitter = TestJobSubmitter("portfolio-staging")
records = submitter.submit_all_test_jobs(test_run_id)
```
- Submits 4 predefined test jobs
- Each submission tracked: ID, timestamp, result (created/failed)
- Documents saved directly to `job-matches` collection
- Success/failure recorded

### Step 4: Collect Results
```python
collector = TestResultsCollector("portfolio-staging", output_dir)
counts = collector.get_collection_counts(all_collections)
collector.save_results(test_result, all_collections)
```
- Gets final document counts in all collections
- Snapshots each collection as JSON
- Saves test results JSON with all metrics
- Creates human-readable summary

### Step 5: Analyze
```python
analyzer = ResultsAnalyzer(results_dir, output_dir)
analysis = analyzer.analyze()
analyzer.save_analysis(analysis)
```
- Loads backup and final snapshots
- Compares to find: created, deleted, modified documents
- Calculates quality scores before/after
- Generates health assessment (PASS/WARN/FAIL)
- Saves JSON analysis and text report

## Output Structure

```
test_results/e2e_collect_20251018_143022/
├── test_run.log                    # Execution log (DEBUG/INFO)
├── test_results.json               # Complete results as JSON
├── summary.txt                     # Human-readable summary
├── backup_original/
│   ├── backup_metadata.json        # Backup metadata
│   ├── job-listings.json
│   ├── companies.json
│   ├── job-sources.json
│   └── job-queue.json
├── final_job-matches.json          # After test run
├── final_companies.json
├── final_job-sources.json
├── final_job-queue.json
└── final_job-listings.json

analysis_reports/
├── analysis.json                   # Detailed analysis data
└── report.txt                      # Formatted report
```

## Data Preserved

### Backup Data
- Complete original state of all collections
- Can be restored if needed
- Includes metadata about backup

### Test Results
- Each job submission record with status and timing
- Final success/failure metrics
- Issues discovered during validation
- Exception messages if failures occurred

### Collection Snapshots
- Full state of each collection after test run
- Enables before/after comparison
- Can be analyzed for patterns across multiple runs

### Analysis Results
- Collection change metrics (created, deleted, modified)
- Job submission analysis (success rate, duration)
- Data quality scores
- Health assessment and findings

## Usage Examples

### Basic Single Run
```bash
# Run data collection
python tests/e2e/data_collector.py \
    --database portfolio-staging \
    --output-dir ./test_results/run_001

# Analyze results
python tests/e2e/results_analyzer.py \
    --results-dir ./test_results/run_001 \
    --output-dir ./analysis_reports/run_001

# Review
cat ./test_results/run_001/summary.txt
cat ./analysis_reports/run_001/report.txt
```

### Weekly Automation
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
RUN_ID="weekly_${DATE}"

python tests/e2e/data_collector.py \
    --database portfolio-staging \
    --output-dir "./test_results/${RUN_ID}"

python tests/e2e/results_analyzer.py \
    --results-dir "./test_results/${RUN_ID}" \
    --output-dir "./reports/${RUN_ID}"

echo "Test run complete: $RUN_ID"
cat "./reports/${RUN_ID}/report.txt"
```

Schedule with cron:
```bash
0 9 * * 1 cd /path/to/job-finder && bash weekly_test.sh
```

### Verbose Debugging
```bash
python tests/e2e/data_collector.py \
    --database portfolio-staging \
    --output-dir ./debug_run \
    --verbose

tail -100 ./debug_run/test_run.log
```

## Test Jobs

Four predefined test jobs are submitted:

1. **MongoDB** - Senior Backend Engineer
   - URL: https://test.example.com/mongodb/12345
   - Expected: New job created
   
2. **Netflix** - Machine Learning Engineer
   - URL: https://test.example.com/netflix/12345
   - Expected: New job created

3. **Shopify** - Full Stack Engineer
   - URL: https://test.example.com/shopify/12345
   - Expected: New job created

4. **Stripe** - Platform Engineer
   - URL: https://test.example.com/stripe/12345
   - Expected: New job created

These are simple, predictable test cases for validating basic job creation functionality.

## Quality Metrics

The analyzer calculates:

**Collection Changes:**
- Original count vs final count
- Documents created, deleted, modified
- Percentage change

**Submission Success:**
- Total submitted, succeeded, failed
- Success/failure rates
- Breakdown by status (created_new, found_existing, failed)
- Breakdown by company

**Data Quality:**
- Completeness: % of fields populated
- Accuracy: % of fields valid (no validation errors)
- Before/after scores for comparison

**Health Assessment:**
- PASS: Score >= 80
- WARN: Score >= 60
- FAIL: Score < 60

## Integration Points

### From Phase 1 (Log Streaming)
- Can be run alongside log streaming
- Both save to local files
- Results complement each other

### From Phase 2 (Data Quality Monitoring)
- Uses similar quality scoring concepts
- Before/after comparison capability
- Validation schemas could be integrated

### Phase 2: AI-Driven Analysis (Future)
```python
# Load collected data
with open('./test_results/run_001/test_results.json') as f:
    test_data = json.load(f)

with open('./analysis_reports/run_001/analysis.json') as f:
    analysis = json.load(f)

# Pass to AI agent for recommendations
# ai_agent.review_tooling_vs_collected_data(
#     tooling=tool_implementation,
#     test_data=test_data,
#     analysis=analysis
# )
```

## Verification

Both files compile without syntax errors:
- ✓ `tests/e2e/data_collector.py` - PASS
- ✓ `tests/e2e/results_analyzer.py` - PASS

Ready for integration testing with real Firestore.

## Next Steps

1. **Now:** Test in staging environment
2. **Iteration:** Fix any runtime issues with Firestore
3. **Validation:** Verify all data saves correctly
4. **Automation:** Set up weekly runs
5. **Phase 2:** Develop AI agent for data analysis

## Files

- Main implementation: `tests/e2e/data_collector.py`
- Analysis implementation: `tests/e2e/results_analyzer.py`
- Complete guide: `docs/E2E_DATA_COLLECTION_GUIDE.md`
- This document: `docs/E2E_DATA_COLLECTOR_IMPLEMENTATION.md`
