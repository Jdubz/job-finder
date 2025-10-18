# Data Quality and Completeness Monitoring

## Overview

The Data Quality Monitor tracks the accuracy and completeness of your data across E2E tests. It ensures that improvements to the automation tool actually improve the quality of collected company data, job source configurations, and job listings.

**Key Goal:** Make E2E tests validate that data quality improves, not just that the system doesn't crash.

---

## Why Data Quality Matters

Your automation tool collects data in three main categories:

### 1. **Company Data** (companies collection)
- Company name, website, about description
- Tech stack, Portland office presence, priority tier
- These feed into job search relevance and filtering

### 2. **Job Source Data** (job-sources collection)
- Source name and type (Greenhouse, RSS, API, etc.)
- Configuration for each source (board tokens, API endpoints)
- Enable/disable status, tags, company linking
- These drive the scraping pipeline

### 3. **Job Listings** (job-matches collection)
- Job title, company, location, description
- AI match scores, company info, deduplication hashes
- Source attribution, timestamps
- These are the actual output users see

Poor quality in any of these directly impacts:
- **Search Accuracy** - Users get irrelevant jobs if company data is incomplete
- **Scraping Efficiency** - Invalid source configs waste API calls
- **Deduplication** - Missing fields make duplicate detection fail
- **User Experience** - Incomplete listings frustrate users

---

## Data Quality Metrics

### Completeness Scoring

Measures what percentage of expected fields are present:

```
Completeness Score = (Required Fields % × 0.7) + (Recommended Fields % × 0.3)
```

**Levels:**
- **Complete (100%+)**: All required + all recommended fields present
- **Partial (50-100%)**: All required + most recommended fields present
- **Minimal (0-50%)**: Only required fields or less

### Accuracy Scoring

Measures what percentage of fields pass validation:

```
Accuracy Score = 100% - (Validation Errors / Total Fields × 100%)
```

**Examples of validation errors:**
- Missing required fields
- Invalid URL format
- Invalid data types
- Out-of-range values
- Invalid enum values

### Overall Quality Score

Combines completeness and accuracy:

```
Overall Score = (Completeness % × 0.6) + (Accuracy % × 0.4)
```

**Interpretation:**
- **80-100**: Excellent - Data is ready for production
- **60-80**: Good - Minor issues to clean up
- **40-60**: Fair - Significant missing data or validation issues
- **0-40**: Poor - Major problems, not recommended for use

---

## Data Schemas and Requirements

### Company Schema

**Required Fields:**
```python
{
    "name": str,              # Company name (2+ chars)
    "website": str,           # Valid HTTPS URL
}
```

**Recommended Fields:**
```python
{
    "about": str,             # Company description
    "techStack": list,        # ["Python", "React", ...]
    "hasPortlandOffice": bool,
    "tier": str,              # S, A, B, C, or D
    "priorityScore": int,     # 0-200+
}
```

**Optional Fields:**
```python
{
    "company_size_category": str,  # "large", "medium", "small"
    "headquarters_location": str,  # "San Francisco, CA"
}
```

### Job Source Schema

**Required Fields:**
```python
{
    "name": str,              # Source name (2+ chars)
    "sourceType": str,        # greenhouse|rss|api|company-page|workday
    "config": dict,           # Source-specific config
    "enabled": bool,          # Is source active?
}
```

**Recommended Fields:**
```python
{
    "companyId": str,         # Link to companies collection
    "company_name": str,      # Company name (denormalized)
    "tags": list,             # ["remote", "tech", ...]
}
```

**Optional Tracking Fields:**
```python
{
    "lastScrapedAt": str,     # ISO timestamp
    "totalJobsFound": int,    # Count of jobs found
    "totalJobsMatched": int,  # Count of matches
}
```

### Job Match Schema

**Required Fields:**
```python
{
    "title": str,             # Job title (3+ chars)
    "company": str,           # Company name (2+ chars)
    "link": str,              # Valid HTTPS URL
}
```

**Recommended Fields:**
```python
{
    "description": str,       # Job description
    "location": str,          # Job location
    "companyId": str,         # Link to companies
    "matchScore": float,      # 0-100
    "company_info": str,      # Company summary
}
```

**Optional Tracking Fields:**
```python
{
    "sourceId": str,          # Source ID
    "scrapedAt": str,         # ISO timestamp
    "matchedAt": str,         # ISO timestamp
    "urlHash": str,           # Dedup hash (SHA256)
}
```

---

## Using the Data Quality Monitor

### Basic Usage

```python
from tests.e2e.helpers import DataQualityMonitor

# Create monitor
monitor = DataQualityMonitor()

# Start test run
monitor.start_test_run("e2e_test_12345")

# Track entities as they're processed
company_metrics = monitor.track_company(
    company_id="company_123",
    company_data={
        "name": "MongoDB",
        "website": "https://mongodb.com",
        "about": "Leading document database",
        "techStack": ["Python", "Node.js"],
        "tier": "S",
    },
    is_new=True,
)

source_metrics = monitor.track_job_source(
    source_id="source_456",
    source_data={
        "name": "MongoDB Careers",
        "sourceType": "greenhouse",
        "config": {"board_token": "mongodb"},
        "enabled": True,
        "companyId": "company_123",
    },
    is_new=True,
)

job_metrics = monitor.track_job_match(
    job_id="job_789",
    job_data={
        "title": "Senior Engineer",
        "company": "MongoDB",
        "link": "https://boards.greenhouse.io/mongodb/jobs/123",
        "matchScore": 92.5,
        "companyId": "company_123",
    },
    is_new=True,
)

# Check if entity is healthy
if company_metrics.is_healthy:
    print(f"✓ Company data is healthy (score: {company_metrics.overall_quality_score:.1f})")
else:
    print(f"✗ Company has issues:")
    for error in company_metrics.validation_errors:
        print(f"  - {error}")

# Log any issues found
monitor.log_data_issue("company_123", "Missing: tech stack for MongoDB")

# Get the report
report = monitor.end_test_run()
summary = monitor.get_report_summary()

print(f"Processed: {summary['entities_processed']['total']} entities")
print(f"Average Quality: {summary['quality_scores']['average']:.1f}/100")
print(f"Healthy: {summary['quality_scores']['healthy_entities']} entities")
```

### Tracking Improvements

The monitor can distinguish between new entities and improved existing ones:

```python
# New entity
monitor.track_company(
    company_id="company_new",
    company_data=company_data,
    is_new=True,  # ← This is new
)

# Improved entity (more complete data added)
monitor.track_company(
    company_id="company_123",
    company_data=company_data_with_more_fields,
    is_new=False,
    was_improved=True,  # ← This was improved
)
```

### Accessing Quality Data

```python
# Get current report while test is running
report = monitor.get_report()
if report:
    print(f"Companies processed: {report.companies_processed}")
    print(f"Average quality: {report.average_quality_score:.1f}/100")

# Get detailed summary
summary = monitor.get_report_summary()
print(summary)
# {
#     "test_run_id": "e2e_test_12345",
#     "duration_seconds": 45.3,
#     "entities_processed": {
#         "companies": 5,
#         "sources": 8,
#         "jobs": 127,
#         "total": 140,
#     },
#     "created_entities": {
#         "company": 2,
#         "source": 3,
#         "job": 95,
#     },
#     "improved_entities": {
#         "company": 1,
#         "source": 2,
#         "job": 12,
#     },
#     "quality_scores": {
#         "average": 87.3,
#         "average_completeness": 92.1,
#         "healthy_entities": 132,
#     },
#     "issues": {
#         "validation_errors": 8,
#         "data_issues": 5,
#         "by_type": {...},
#     },
# }

# Format and print the full report
from tests.e2e.helpers import format_quality_report
report = monitor.end_test_run()
print(format_quality_report(report))
```

---

## Integration with E2E Tests

### Using with Test Runner

The data quality monitor is automatically integrated into the E2E test runner:

```bash
# Run tests with data quality monitoring (default)
python tests/e2e/run_with_streaming.py --database portfolio-staging

# Run without quality monitoring
python tests/e2e/run_with_streaming.py --database portfolio-staging --no-quality

# Run with quality monitoring but no logs
python tests/e2e/run_with_streaming.py --database portfolio-staging --no-logs
```

### Using in Scenarios

Pass the monitor to your scenario:

```python
scenario = CompanySourceDiscoveryScenario(database_name="portfolio-staging")

# Inject monitor from runner
scenario.quality_monitor = monitor

# In scenario.execute():
if self.quality_monitor:
    # Track created company
    self.quality_monitor.track_company(
        company_id=company_id,
        company_data=company_data,
        is_new=True,
    )
    
    # Track created source
    self.quality_monitor.track_job_source(
        source_id=source_id,
        source_data=source_data,
        is_new=True,
    )

# Run scenario
scenario.setup()
scenario.execute()
scenario.verify()
```

---

## Interpreting Results

### Quality Score Breakdown

```
TEST RUN: e2e_test_abc123
Duration: 45.3 seconds

ENTITIES PROCESSED
  Companies:     5
  Job Sources:   12
  Job Matches:   127
  Total:         144

QUALITY METRICS
  Average Quality Score:     89.2/100  ← Excellent
  Average Completeness:      91.5/100  ← Almost complete
  Healthy Entities:          140/144   ← 97% healthy

DATA ISSUES
  Validation Errors:         4
  Data Issues:               3
```

**What this means:**
- Almost all data is complete (91.5% of fields present)
- 97% of entities passed validation
- Overall quality is excellent (89.2)
- Only 7 entities have issues to address
- The tool is improving data quality effectively

### Healthy vs Unhealthy Entities

**Healthy entity** (✓):
- ✓ All validation checks pass
- ✓ No data issues logged
- ✓ Quality score ≥ 80

**Unhealthy entity** (✗):
- ✗ Validation errors present
- ✗ Data issues logged
- ✗ Quality score < 80

Example:
```python
if company_metrics.is_healthy:
    print(f"✓ Company {company_id} is production-ready")
else:
    print(f"✗ Company {company_id} needs attention:")
    print(f"  Errors: {company_metrics.validation_errors}")
    print(f"  Issues: {company_metrics.data_issues}")
    print(f"  Quality Score: {company_metrics.overall_quality_score:.1f}/100")
```

---

## Data Quality Goals

### Target Metrics by Phase

| Phase | Avg Quality | Completeness | Healthy % | Created | Improved |
|-------|-------------|--------------|-----------|---------|----------|
| Phase 1 (Current) | 80+ | 85+ | 90+ | Baseline | Low |
| Phase 2 | 85+ | 90+ | 95+ | Increasing | Increasing |
| Phase 3 | 90+ | 95+ | 98+ | High | High |
| Production | 95+ | 98+ | 99+ | Stable | Minimal |

### Improvement Tracking

Each E2E test run generates a snapshot of data quality. Over time, you'll see:

**Positive trends (good):**
- ↑ Average quality score increasing
- ↑ Completeness improving
- ↑ More healthy entities
- ↑ Fewer validation errors
- ↑ More improved vs created entities

**Negative trends (concerning):**
- ↓ Average quality declining
- ↓ More validation errors
- ↓ Fewer healthy entities
- ↓ Data issues increasing

---

## Common Issues and Solutions

### Issue: Low Completeness Score

**Possible causes:**
- Required fields missing (critical)
- Recommended fields not populated
- Optional fields not being collected

**Solutions:**
- Check source scrapers for missing field extraction
- Verify company enrichment is running
- Add missing field collection to data pipelines

### Issue: Validation Errors

**Common errors:**
- "Required field missing: X" → Field not being set
- "Invalid URL format" → Scraper extracting bad URLs
- "Invalid enum value" → Wrong source type specified
- "Type mismatch" → Field has wrong data type

**Solutions:**
- Add validation to scrapers before saving
- Normalize URLs in data transformation
- Check enum allowed values in schema
- Fix type conversion in data processors

### Issue: Low Quality on Specific Entity Type

Example: Companies are healthy but sources are not

**Diagnosis:**
- Check source-specific validation schema
- Look at errors by type in report
- Find which sources have issues

**Solutions:**
- Improve source discovery logic
- Add better config validation
- Fix config building for problematic source types

---

## Advanced Usage

### Custom Validation Rules

Extend validation for your specific needs:

```python
monitor = DataQualityMonitor()

# Override company schema with stricter requirements
from tests.e2e.helpers import FieldValidation

custom_schema = monitor._get_company_schema()
custom_schema.append(
    FieldValidation(
        "customField",
        required=True,
        data_type=str,
        min_length=5,
    )
)

# Use custom schema in validation
metrics = monitor._validate_entity(
    entity_id="company_123",
    data=company_data,
    schema=custom_schema,
    entity_type=monitor.DataEntityType.COMPANY,
)
```

### Exporting Data for Analysis

```python
import json

report = monitor.end_test_run()
summary = monitor.get_report_summary()

# Save summary as JSON
with open(f"quality_report_{report.test_run_id}.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

# Export individual entity metrics
metrics_export = {
    entity_key: {
        "quality_score": metric.overall_quality_score,
        "completeness": metric.completeness_score,
        "accuracy": metric.accuracy_score,
        "errors": metric.validation_errors,
        "issues": metric.data_issues,
    }
    for entity_key, metric in report.entity_metrics.items()
}

with open(f"entity_metrics_{report.test_run_id}.json", "w") as f:
    json.dump(metrics_export, f, indent=2)
```

### Trend Analysis Across Test Runs

```python
import json
from pathlib import Path

# Collect reports from multiple runs
reports = []
for report_file in Path("quality_reports").glob("*.json"):
    with open(report_file) as f:
        reports.append(json.load(f))

# Sort by date
reports.sort(key=lambda r: r["test_run_id"])

# Track trends
print("Quality Trends:")
for report in reports:
    avg_quality = report["quality_scores"]["average"]
    completeness = report["quality_scores"]["average_completeness"]
    healthy_pct = (
        report["quality_scores"]["healthy_entities"] 
        / report["entities_processed"]["total"] * 100
    )
    print(f"{report['test_run_id']}: Quality={avg_quality:.1f} "
          f"Completeness={completeness:.1f} Healthy={healthy_pct:.1f}%")
```

---

## See Also

- **E2E Test Improvement Plan**: `docs/E2E_TEST_IMPROVEMENT_PLAN.md`
- **Log Streaming**: `docs/E2E_LOG_STREAMING.md`
- **E2E Testing Index**: `docs/E2E_TESTING_INDEX.md`
- **Data Schema Reference**: `docs/shared-types.md`

---

## Troubleshooting

### Monitor Not Recording Data

```python
# Make sure you call start_test_run() first
monitor = DataQualityMonitor()
monitor.start_test_run("test_id")  # ← Important!
monitor.track_company(...)
```

### Validation Always Passes Even With Bad Data

- Check that field names in schema match entity keys
- Verify data types in validation rule
- Look at validation error messages in metrics

### Quality Scores Always Low

- Review schema - may be too strict
- Check that data is being populated
- Verify source scrapers are extracting data
- Look at specific validation errors in report

---

**Questions?** See the examples in `tests/e2e/run_with_streaming.py` or check out the quick reference in `docs/DATA_QUALITY_QUICKREF.md`.
