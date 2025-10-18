# E2E Test Suite - Complete Integration Guide

## Overview

You now have a **comprehensive E2E testing infrastructure** with three integrated capabilities:

1. **Real-time Log Streaming** - See what's happening in Google Cloud Logs as tests run
2. **Data Quality Monitoring** - Validate that data is accurate and complete
3. **Queue Monitoring** - Track job pipeline execution and status

Together, these systems provide **end-to-end observability** for automated job discovery.

---

## The Three Pillars

### 1. Log Streaming (`LogStreamer`)

**What it does:**
- Real-time connection to Google Cloud Logging
- Streams logs to console as they're written
- Color-coded by severity (ERROR, WARNING, INFO, DEBUG)
- Supports filtering by test_run_id, stage, severity

**When you need it:**
- Debugging test failures
- Understanding what the system is doing
- Finding where things go wrong
- Following the execution flow

**Quick command:**
```bash
python tests/e2e/run_with_streaming.py --database portfolio-staging
```

### 2. Data Quality Monitor (`DataQualityMonitor`)

**What it does:**
- Validates company, source, and job data
- Checks completeness (all fields present?)
- Checks accuracy (fields pass validation?)
- Scores each entity 0-100
- Reports trends and improvements

**When you need it:**
- Ensuring data quality improves
- Validating that fixes work
- Identifying which data types have issues
- Tracking improvement over time

**Example:**
```python
monitor = DataQualityMonitor()
monitor.start_test_run("test_123")
monitor.track_company(company_id, company_data, is_new=True)
report = monitor.end_test_run()
print(format_quality_report(report))
```

### 3. Queue Monitor (`QueueMonitor`)

**What it does:**
- Tracks job queue items through the pipeline
- Waits for specific status changes
- Monitors timeouts and failures
- Verifies processing completed

**When you need it:**
- Ensuring jobs process end-to-end
- Detecting stuck/stalled jobs
- Verifying multi-stage pipelines work
- Monitoring queue health

**Example:**
```python
monitor = QueueMonitor(db, timeout=300)
status = monitor.wait_for_status(
    queue_id="job_123",
    expected_status="success",
)
```

---

## How They Work Together

```
TEST RUN STARTS
    ↓
[LOG STREAMER] → Connects to Google Cloud Logs
    ↓
[SCENARIOS EXECUTE]
    ├─ Execute test logic
    ├─ Query & create data
    └─ Track metrics
    ↓
[QUEUE MONITOR] → Wait for pipeline processing
    ├─ Poll job-queue collection
    ├─ Detect status changes
    └─ Verify completion
    ↓
[DATA QUALITY MONITOR] → Validate created data
    ├─ Check completeness
    ├─ Validate accuracy
    ├─ Score quality
    └─ Track improvements
    ↓
[LOGS STREAM] → Real-time insights to console
    ├─ Show errors/warnings
    ├─ Display key events
    └─ Color-coded output
    ↓
REPORT GENERATION
    ├─ Test results (pass/fail)
    ├─ Log summary (entries by severity)
    ├─ Data quality report
    └─ Improvement metrics
```

---

## Running Tests

### Basic Run (All Three Features)

```bash
export GCP_PROJECT_ID="your-gcp-project-id"
python tests/e2e/run_with_streaming.py --database portfolio-staging
```

**Output includes:**
- Real-time logs streaming to console
- Test pass/fail status
- Data quality metrics
- Improvement tracking

### With Specific Options

```bash
# Run without log streaming (just quality metrics)
python tests/e2e/run_with_streaming.py --database portfolio-staging --no-logs

# Run without quality monitoring (just logs)
python tests/e2e/run_with_streaming.py --database portfolio-staging --no-quality

# Run specific scenarios only
python tests/e2e/run_with_streaming.py \
  --database portfolio-staging \
  --scenarios JobSubmissionScenario CompanySourceDiscoveryScenario

# Verbose output with debug logs
python tests/e2e/run_with_streaming.py \
  --database portfolio-staging \
  --verbose
```

---

## Understanding Reports

### Test Results Section

```
TEST SUMMARY
────────────────────────────────
✓ Passed:  4
✗ Failed:  0
⚠ Errors:  0
Total time: 45.3s

Results:
✓ JobSubmissionScenario: success (12.1s)
✓ FilteredJobScenario: success (9.8s)
✓ CompanySourceDiscoveryScenario: success (15.2s)
✓ ScrapeRotationScenario: success (8.2s)
```

### Log Summary Section

```
LOG SUMMARY
────────────────────────────────
Total log entries: 342
Duration: 45.3s
By severity: {'INFO': 289, 'DEBUG': 34, 'WARNING': 15, 'ERROR': 4}
By stage: {'fetch': 98, 'extract': 87, 'analyze': 95, 'save': 62}

Errors (4):
  - Job URL validation failed for MongoDB careers page
  - Timeout waiting for source discovery completion
  - Firestore write error: quota exceeded
  - Invalid JSON in API response

Warnings (15):
  - Company website unreachable (3 times)
  - Below match threshold (8 times)
  - Retry attempt 2/3 (4 times)
```

### Data Quality Section

```
DATA QUALITY REPORT
════════════════════════════════════════════════════════════════════════

ENTITIES PROCESSED
  Companies:     12
  Job Sources:   28
  Job Matches:   341
  Total:         381

CREATED & IMPROVED
  New Companies:     3
  New Sources:       5
  New Jobs:          156
  Improved Companies: 2
  Improved Sources:   3
  Improved Jobs:      18

QUALITY METRICS
  Average Quality Score:     87.3/100  ← Good!
  Average Completeness:      92.1/100
  Healthy Entities:          364/381   ← 95% healthy

DATA ISSUES
  Validation Errors:         17
  Data Issues:               12
  By Type:
    errors: {'missing_field': 9, 'invalid_format': 8}
    issues: {'duplicate_detected': 7, 'link_broken': 5}
```

---

## Interpreting Quality Scores

### Quality Score Tiers

```
Score Range    | Status           | Interpretation
─────────────────────────────────────────────────────
90-100         | Excellent ✓✓     | Production ready
80-90          | Good ✓           | Minor issues
70-80          | Fair ⚠           | Needs work
60-70          | Poor ⚠⚠          | Significant issues
0-60           | Critical ✗       | Major problems
```

### Completeness vs Accuracy

**Completeness (What % of fields are present?)**
```
95-100: All fields present (COMPLETE)
  ✓ Company has: name, website, about, tier, techStack, etc.

80-95: Most fields present (PARTIAL)
  ⚠ Company has: name, website, about, tier (missing techStack, priority)

60-80: Some fields present (MINIMAL)
  ✗ Company has: name, website (missing everything else)
```

**Accuracy (What % of fields pass validation?)**
```
95-100: All fields valid
  ✓ URLs are properly formatted, types match, enums are correct

80-95: Minor issues
  ⚠ One or two validation errors

60-80: Multiple issues
  ✗ Several fields don't match schema
```

### Example Interpretation

```
Company: MongoDB (quality_score=89.2)

Completeness: 95.0 (95% of fields present)
  ✓ ALL required fields present (name, website)
  ✓ ALL recommended fields present (about, tier, techStack, etc.)
  ✓ MOST optional fields present (2 out of 3)

Accuracy: 100.0 (100% of fields valid)
  ✓ All URLs properly formatted
  ✓ All data types match schema
  ✓ All enums are valid values

Overall: EXCELLENT (80-100 range)
  → Ready for production
  → No immediate improvements needed
  → Data is accurate and complete
```

---

## Data Quality Targets

### Phase 1 Goals (Current - Deduplication)

After implementing deduplication fixes:
- Average Quality: **85+/100**
- Average Completeness: **90+/100**
- Healthy Entities: **95%+**
- Expected timeframe: 2-3 weeks

### Phase 2 Goals (Rotation)

After implementing rotation improvements:
- Average Quality: **90+/100**
- Average Completeness: **95+/100**
- Healthy Entities: **98%+**
- Expected timeframe: 3-4 weeks after Phase 1

### Phase 3 Goals (Reliability)

After implementing reliability improvements:
- Average Quality: **95+/100**
- Average Completeness: **98+/100**
- Healthy Entities: **99%+**
- Expected timeframe: 2-3 weeks after Phase 2

---

## Tracking Improvements

### Method 1: Weekly Tracking

Run tests every week and track metrics:

```
Week 1:  Quality=75.2, Completeness=78, Healthy=85%
Week 2:  Quality=78.5, Completeness=82, Healthy=88%
Week 3:  Quality=82.1, Completeness=87, Healthy=91%
Week 4:  Quality=85.3, Completeness=91, Healthy=94%
Week 5:  Quality=89.2, Completeness=95, Healthy=97%

Trend: ↑ Steadily improving ✓
```

### Method 2: Before/After Comparison

Before fix:
```
python tests/e2e/run_with_streaming.py > before_fix.log
```

After fix:
```
python tests/e2e/run_with_streaming.py > after_fix.log
```

Compare metrics in the reports.

### Method 3: Export and Analyze

Save reports as JSON for analysis:

```python
import json
from tests.e2e.helpers import DataQualityMonitor

monitor = DataQualityMonitor()
monitor.start_test_run("test_123")
# ... run tests ...
report = monitor.end_test_run()
summary = monitor.get_report_summary()

# Save for analysis
with open("quality_report.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

# Later: Load and compare
with open("quality_report.json") as f:
    results = json.load(f)
    print(f"Average quality: {results['quality_scores']['average']}")
```

---

## Common Workflows

### Workflow 1: Finding and Fixing Issues

```
1. Run tests
   python tests/e2e/run_with_streaming.py

2. Review data quality report
   → Look for low quality scores
   → Identify which data types have issues
   → Note validation errors

3. Check logs for clues
   → Search for ERROR logs
   → Look for data transformation issues
   → Find where fields go missing

4. Fix the issue
   → Update scraper, transformer, or validator
   → Re-run tests

5. Verify improvement
   → Check quality score went up
   → Confirm validation errors decreased
```

### Workflow 2: Tracking a Specific Fix

```
Before fix:
  → Run tests, note quality baseline
  → Document validation errors
  → Record completeness score

Implement fix

After fix:
  → Run tests again
  → Compare quality scores
  → Verify improvement
  → Document what changed
```

### Workflow 3: Continuous Monitoring

```
Schedule weekly test runs:

  Every Monday 9 AM:
  → Run full E2E test suite
  → Save report with timestamp
  → Update trend dashboard
  → Review for new issues

  Track metrics over time:
  → Quality score trend
  → Completeness trend
  → Healthy entity count
  → New vs improved entities
```

---

## Troubleshooting

### Issue: Log Streaming Not Working

**Check:**
1. `GCP_PROJECT_ID` environment variable is set
2. Credentials file exists at `./credentials/serviceAccountKey.json`
3. Credentials have Cloud Logging permissions

**Solution:**
```bash
# Verify project ID
echo $GCP_PROJECT_ID

# Check credentials
ls -la credentials/serviceAccountKey.json

# Run without logs
python tests/e2e/run_with_streaming.py --no-logs
```

### Issue: Data Quality Scores Low

**Check:**
1. Which fields are missing?
2. Which validation errors appear most?
3. Is the data being created at all?

**Solutions:**
```bash
# Run with verbose output for more details
python tests/e2e/run_with_streaming.py --verbose

# Check what's in database
python tests/e2e/helpers/firestore_helper.py query companies

# Run specific scenario
python tests/e2e/run_with_streaming.py --scenarios CompanySourceDiscoveryScenario
```

### Issue: Tests Timing Out

**Check:**
1. Are queue items getting stuck?
2. Are pipelines processing too slowly?
3. Is there a resource bottleneck?

**Solutions:**
```bash
# Check queue status in logs
# Look for ERROR logs in PROCESS stage

# Check Firestore queue collection
firebase firestore:inspect

# Increase timeout (in code):
monitor = QueueMonitor(db, timeout=600)  # 10 minutes instead of 5
```

---

## Files and Documentation

### Implementation Files

```
tests/e2e/helpers/
├── data_quality_monitor.py    ← Data quality validation
├── log_streamer.py             ← Log streaming
├── queue_monitor.py            ← Queue tracking
├── firestore_helper.py         ← Database queries
├── cleanup_helper.py           ← Test cleanup
└── __init__.py                 ← Exports

tests/e2e/
├── run_with_streaming.py       ← Test runner with all features
└── scenarios/                  ← Test scenarios
    ├── base_scenario.py
    ├── scenario_01_job_submission.py
    ├── scenario_02_filtered_job.py
    ├── scenario_03_company_source_discovery.py
    ├── scenario_04_scrape_rotation.py
    └── scenario_05_full_discovery_cycle.py
```

### Documentation Files

```
docs/
├── E2E_TESTING_INDEX.md              ← Navigation guide
├── E2E_TEST_IMPROVEMENT_PLAN.md      ← Overall strategy
├── E2E_LOG_STREAMING.md              ← Log streaming guide
├── DATA_QUALITY_MONITORING.md        ← Quality monitoring
├── DATA_QUALITY_QUICKREF.md          ← Quick reference
└── E2E_IMPROVEMENT_STRATEGY.md       ← Strategic overview
```

---

## Quick Reference

### Start Here

```bash
# Install/verify dependencies
pip install google-cloud-logging

# Set environment
export GCP_PROJECT_ID="your-gcp-project-id"

# Run tests
python tests/e2e/run_with_streaming.py --database portfolio-staging

# Review output
# 1. Test results
# 2. Log summary
# 3. Data quality metrics
```

### Key Classes

```python
# Log streaming
from tests.e2e.helpers import LogStreamer
streamer = LogStreamer(project_id, database_name)
with streamer.stream_logs(test_run_id="test_123"):
    run_tests()

# Data quality
from tests.e2e.helpers import DataQualityMonitor
monitor = DataQualityMonitor()
monitor.start_test_run("test_123")
monitor.track_company(company_id, data, is_new=True)
report = monitor.end_test_run()

# Queue monitoring
from tests.e2e.helpers import QueueMonitor
monitor = QueueMonitor(db)
status = monitor.wait_for_status(queue_id, "success")
```

### Important Metrics

```
Quality Score (0-100):
  90+: Excellent
  80+: Good
  70+: Fair
  <70: Poor

Completeness (%):
  How many fields are populated

Accuracy (%):
  How many fields pass validation

Healthy Entities (%):
  Pass all validations + no issues
```

---

## What's Next?

### Immediate (This Week)
1. Run tests with data quality monitoring
2. Review the baseline data quality report
3. Identify top issues

### Short-term (Week 2-3)
1. Implement Phase 1 deduplication fixes
2. Re-run tests to measure improvement
3. Track quality metrics

### Medium-term (Weeks 3-6)
1. Implement Phase 2 rotation improvements
2. Implement Phase 3 reliability fixes
3. Continue weekly test runs
4. Monitor metrics trending toward targets

### Long-term (Week 6+)
1. Maintain quality standards
2. Add more scenarios as needed
3. Scale monitoring to production
4. Continuous improvement

---

## Summary

You now have a complete E2E testing system that:

✅ **Observes** - Real-time logs show what's happening  
✅ **Validates** - Data quality monitoring ensures accuracy  
✅ **Tracks** - Queue monitoring verifies end-to-end processing  
✅ **Reports** - Comprehensive metrics and insights  
✅ **Improves** - Identifies and measures fixes  

**Next step:** Run the tests and start improving your data quality!

```bash
python tests/e2e/run_with_streaming.py --database portfolio-staging
```

For questions, see:
- `docs/E2E_TESTING_INDEX.md` - Navigation guide
- `docs/DATA_QUALITY_MONITORING.md` - Quality details
- `docs/E2E_LOG_STREAMING.md` - Log streaming details
- `docs/DATA_QUALITY_QUICKREF.md` - Quick examples
