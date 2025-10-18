# E2E Test Data Collection Guide

This guide explains how to use the E2E test data collection tools for periodic automated testing, data quality monitoring, and results analysis.

## Overview

The test data collection system automates the workflow:

```
┌──────────────┐     ┌───────────┐     ┌──────────────┐     ┌─────────────┐
│   Backup     │ --> │   Clear   │ --> │   Submit     │ --> │   Analyze   │
│  Collections │     │ Firestore │     │   Test Jobs  │     │   Results   │
└──────────────┘     └───────────┘     └──────────────┘     └─────────────┘
     ↓                                                            ↓
 JSON backups                                         JSON reports + metrics
 (for restore)                                        (for review later)
```

## Tools

### 1. `data_collector.py` - Main Test Runner

**Purpose:** Orchestrates the complete test data collection workflow

**Location:** `tests/e2e/data_collector.py`

**What it does:**
1. Backs up Firestore collections to JSON files
2. Clears test collections (job-listings, companies, job-sources, job-queue)
3. Submits 4 test jobs with known data
4. Records all results (logs, snapshots, metrics)
5. Validates results (checks created documents, success rates, etc)
6. Saves everything locally for later analysis

**Output directory structure:**
```
./test_results/e2e_collect_20251018_143022/
├── test_run.log                    # Complete execution log
├── test_results.json               # Main results data
├── summary.txt                     # Human-readable summary
├── backup_original/
│   ├── backup_metadata.json        # Backup information
│   ├── job-listings.json           # Original job listings
│   ├── companies.json              # Original companies
│   ├── job-sources.json            # Original job sources
│   └── job-queue.json              # Original queue
├── final_job-matches.json          # Final job matches snapshot
├── final_companies.json            # Final companies snapshot
├── final_job-sources.json          # Final job sources snapshot
├── final_job-queue.json            # Final queue snapshot
└── final_job-listings.json         # Final listings snapshot
```

### 2. `results_analyzer.py` - Results Analysis

**Purpose:** Analyzes collected test data and generates comprehensive reports

**Location:** `tests/e2e/results_analyzer.py`

**What it does:**
1. Loads backup and final collection snapshots
2. Compares collection changes (created, deleted, modified counts)
3. Analyzes job submission success rates
4. Calculates data quality before/after
5. Generates health assessment (PASS/WARN/FAIL)
6. Produces JSON analysis and text report

**Output:**
```
./analysis_reports/
├── analysis.json                   # Complete analysis as JSON
└── report.txt                      # Human-readable analysis report
```

## Quick Start

### Setup

```bash
# 1. Set your GCP project
export GCP_PROJECT_ID="your-gcp-project-id"

# 2. Ensure credentials are available
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/serviceAccountKey.json"
```

### Run Full Workflow

```bash
# 1. Run data collection
python tests/e2e/data_collector.py \
    --database portfolio-staging \
    --output-dir ./test_results/run_001 \
    --verbose

# 2. Analyze the results
python tests/e2e/results_analyzer.py \
    --results-dir ./test_results/run_001 \
    --output-dir ./analysis_reports/run_001
```

## Detailed Usage

### data_collector.py

#### Command-line Options

```bash
python tests/e2e/data_collector.py \
    --database DBNAME              # Firestore database (default: portfolio-staging)
    --output-dir PATH              # Where to save results (default: ./test_results)
    --verbose                      # Enable debug logging
```

#### Example Commands

```bash
# Staging database with default output
python tests/e2e/data_collector.py

# Production database (careful!) with verbose logging
python tests/e2e/data_collector.py \
    --database portfolio-production \
    --verbose

# Custom output directory
python tests/e2e/data_collector.py \
    --output-dir ./my_test_results/2025_10_18_run
```

#### What Gets Backed Up

Before clearing collections, these are backed up to JSON:
- `job-listings` - All job listings
- `companies` - All companies
- `job-sources` - All job sources
- `job-queue` - All queue items

#### What Gets Tested

Four test jobs are submitted:
1. MongoDB - Senior Backend Engineer
2. Netflix - Machine Learning Engineer
3. Shopify - Full Stack Engineer
4. Stripe - Platform Engineer

These create new documents in `job-matches` collection.

#### Output Files Explained

**test_results.json:**
```json
{
  "test_run_id": "e2e_collect_20251018_143022",
  "start_time": "2025-10-18T14:30:22.000000",
  "end_time": "2025-10-18T14:30:45.000000",
  "duration_seconds": 23.5,
  "jobs_submitted": 4,
  "jobs_succeeded": 4,
  "jobs_failed": 0,
  "backup_metadata": {...},
  "final_collection_counts": {
    "job-matches": 4,
    "job-listings": 0,
    "companies": 0,
    ...
  },
  "issues_found": []
}
```

**summary.txt:**
```
E2E TEST RUN SUMMARY
════════════════════════════════════════════════════════════════

Test Run ID:     e2e_collect_20251018_143022
Start Time:      2025-10-18T14:30:22.000000
End Time:        2025-10-18T14:30:45.000000
Duration:        23.5s

JOB SUBMISSIONS
────────────────────────────────────────────────────────────────
Total Submitted: 4
Succeeded:       4
Failed:          0
Success Rate:    100.0%

FINAL COLLECTION COUNTS
────────────────────────────────────────────────────────────────
job-matches                4 documents
job-listings               0 documents
companies                  0 documents
...
```

### results_analyzer.py

#### Command-line Options

```bash
python tests/e2e/results_analyzer.py \
    --results-dir PATH             # Directory containing test results (REQUIRED)
    --output-dir PATH              # Where to save analysis (default: ./analysis_reports)
```

#### Example Commands

```bash
# Analyze latest run
python tests/e2e/results_analyzer.py \
    --results-dir ./test_results/run_001

# Analyze with custom output
python tests/e2e/results_analyzer.py \
    --results-dir ./test_results/run_001 \
    --output-dir ./reports/detailed_analysis
```

#### Output Files Explained

**analysis.json:**
```json
{
  "test_run_id": "e2e_collect_20251018_143022",
  "timestamp": "2025-10-18T14:32:10.000000",
  "duration_seconds": 23.5,
  "collection_comparisons": {
    "job-matches": {
      "collection_name": "job-matches",
      "original_count": 0,
      "final_count": 4,
      "created_count": 4,
      "deleted_count": 0,
      "modified_count": 0,
      "change_percentage": 100.0
    }
  },
  "submission_analysis": {
    "total_submitted": 4,
    "total_succeeded": 4,
    "total_failed": 0,
    "success_rate": 100.0
  },
  "overall_health_score": 85.5,
  "assessment": "PASS",
  "key_findings": [
    "Excellent job submission success: 100.0%",
    "Created 4 new documents",
    "Good data quality in final state"
  ]
}
```

**report.txt:**
```
E2E TEST RESULTS ANALYSIS REPORT
════════════════════════════════════════════════════════════════

Test Run ID:        e2e_collect_20251018_143022
Analysis Time:      2025-10-18T14:32:10.000000
Duration:           23.5s
Assessment:         PASS
Health Score:       85.5/100

COLLECTION CHANGES
────────────────────────────────────────────────────────────────
job-matches              0 → 4 (+4, -0) +100.0%
companies                0 → 0 (+0, -0) ±0.0%
...

JOB SUBMISSIONS
────────────────────────────────────────────────────────────────
Total Submitted:    4
Succeeded:          4
Failed:             0
Success Rate:       100.0%

DATA QUALITY
────────────────────────────────────────────────────────────────
Before:             0.0/100
After:              78.5/100
Improvement:        +78.5%

KEY FINDINGS
────────────────────────────────────────────────────────────────
  • Excellent job submission success: 100.0%
  • Created 4 new documents
  • Good data quality in final state
```

## Workflow Examples

### Example 1: Single Test Run

```bash
# Run test collection with staging database
python tests/e2e/data_collector.py \
    --database portfolio-staging \
    --output-dir ./test_results/baseline

# Analyze results
python tests/e2e/results_analyzer.py \
    --results-dir ./test_results/baseline \
    --output-dir ./reports/baseline

# Review summary
cat ./test_results/baseline/summary.txt
cat ./reports/baseline/report.txt
```

### Example 2: Weekly Monitoring Run

```bash
#!/bin/bash
# save as: weekly_test_run.sh

DATE=$(date +%Y%m%d_%H%M%S)
RUN_NAME="weekly_${DATE}"

echo "Starting weekly E2E test run: $RUN_NAME"

# Create run
python tests/e2e/data_collector.py \
    --database portfolio-staging \
    --output-dir "./test_results/${RUN_NAME}"

# Analyze
python tests/e2e/results_analyzer.py \
    --results-dir "./test_results/${RUN_NAME}" \
    --output-dir "./reports/${RUN_NAME}"

# Display results
echo ""
echo "================================"
echo "Test Run Complete: $RUN_NAME"
echo "================================"
cat "./reports/${RUN_NAME}/report.txt"
```

Run weekly:
```bash
# Run manually
bash weekly_test_run.sh

# Or schedule with cron (every Monday at 9am)
# 0 9 * * 1 cd /path/to/job-finder && bash weekly_test_run.sh
```

### Example 3: Troubleshooting - Verbose Output

If tests fail, run with verbose logging to see details:

```bash
python tests/e2e/data_collector.py \
    --database portfolio-staging \
    --output-dir ./test_results/debug_run \
    --verbose

# Check the detailed log
tail -100 ./test_results/debug_run/test_run.log
```

## File Descriptions

### JSON Files (Collections)

Collection JSON files are arrays of documents:

```json
[
  {
    "id": "document-id-1",
    "field1": "value1",
    "field2": "value2",
    "timestamp": "2025-10-18T14:30:22.000000"
  },
  {
    "id": "document-id-2",
    "field1": "value3",
    "field2": "value4",
    "timestamp": "2025-10-18T14:30:23.000000"
  }
]
```

The `id` field is the document's Firestore ID.

### Backup Metadata

Contains information about what was backed up:

```json
{
  "timestamp": "2025-10-18T14:30:22.000000",
  "database_name": "portfolio-staging",
  "collections_backed_up": ["job-listings", "companies", "job-sources", "job-queue"],
  "document_counts": {
    "job-listings": 150,
    "companies": 42,
    "job-sources": 28,
    "job-queue": 5
  },
  "total_documents": 225,
  "backup_path": "./test_results/backup_original",
  "backup_size_bytes": 245782
}
```

## Troubleshooting

### Issue: "Firestore not initialized"

**Cause:** Missing or invalid credentials

**Solution:**
```bash
# Check credentials file
ls -la ./credentials/serviceAccountKey.json

# Or set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

### Issue: Collections not being cleared

**Cause:** Insufficient permissions or wrong database

**Solution:**
1. Verify you're using staging, not production
2. Check service account has Firestore delete permissions
3. Run with verbose flag to see details:
```bash
python tests/e2e/data_collector.py --verbose
```

### Issue: "No data in final snapshots"

**Cause:** Test jobs didn't create documents

**Solution:**
1. Check test_run.log for job submission errors
2. Verify Firestore collection exists and is writable
3. Try manually creating a document in Firestore
4. Check write rules/permissions

### Issue: Results analyzer shows "0 documents"

**Cause:** test_results.json not found or malformed

**Solution:**
1. Verify results directory:
```bash
ls -la ./test_results/run_001/
```

2. Check test_results.json exists and is valid JSON:
```bash
cat ./test_results/run_001/test_results.json | python3 -m json.tool
```

## Integration with Phase 2 (AI Analysis)

The collected data can later be fed to an AI agent for automated review:

```python
# Phase 2: AI-driven analysis
import json

# Load collected data
with open('./test_results/run_001/test_results.json') as f:
    test_data = json.load(f)

with open('./analysis_reports/run_001/analysis.json') as f:
    analysis = json.load(f)

# Pass to AI agent for recommendations
# ai_agent.review_tooling_vs_data(
#     tooling_implementation=load_tool_code(),
#     collected_data=test_data,
#     analysis_results=analysis,
# )
```

## Data Retention

Test data is stored locally and can grow. Recommendations:

```bash
# Archive old runs (keep for 3 months)
tar czf ./test_results_archive_2025_q3.tar.gz ./test_results/

# Clean up runs older than 30 days
find ./test_results -type d -mtime +30 -exec rm -rf {} \;
```

## Next Steps

1. **Now:** Run data collection and verify data saves correctly
2. **Phase 2:** Develop AI agent to analyze collected data vs. tooling
3. **Phase 3:** Create review interface for trend analysis across runs
4. **Phase 4:** Integrate with CI/CD for automated weekly runs

## Files

- Main collector: `tests/e2e/data_collector.py`
- Results analyzer: `tests/e2e/results_analyzer.py`
- This guide: `docs/E2E_DATA_COLLECTION_GUIDE.md`

