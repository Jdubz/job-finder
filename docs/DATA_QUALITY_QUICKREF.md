#!/usr/bin/env python3
"""
Quick Reference: Data Quality Monitoring for E2E Tests

This guide shows practical examples of using the data quality monitor.
"""

# ============================================================================
# QUICK START - Basic Usage
# ============================================================================

from tests.e2e.helpers import DataQualityMonitor, format_quality_report

# Create monitor and start tracking
monitor = DataQualityMonitor()
monitor.start_test_run("e2e_test_12345")

# Track a company
monitor.track_company(
    company_id="mongodb_123",
    company_data={
        "name": "MongoDB",
        "website": "https://mongodb.com",
        "about": "Document database",
        "tier": "S",
        "techStack": ["Python", "Go"],
    },
    is_new=True,  # Mark as newly created
)

# Track a job source
monitor.track_job_source(
    source_id="source_456",
    source_data={
        "name": "MongoDB Careers",
        "sourceType": "greenhouse",
        "config": {"board_token": "mongodb"},
        "enabled": True,
        "companyId": "mongodb_123",
    },
    is_new=True,
)

# Track job matches
monitor.track_job_match(
    job_id="job_789",
    job_data={
        "title": "Senior Engineer",
        "company": "MongoDB",
        "link": "https://boards.greenhouse.io/mongodb/jobs/1234",
        "matchScore": 94.5,
        "companyId": "mongodb_123",
    },
    is_new=True,
)

# Get report
report = monitor.end_test_run()

# Display formatted report
print(format_quality_report(report))

# ============================================================================
# CHECKING QUALITY SCORES
# ============================================================================

# Check individual entity quality
if company_metrics.is_healthy:
    print(f"✓ Company data is ready for production")
    print(f"  Quality: {company_metrics.overall_quality_score:.1f}/100")
    print(f"  Completeness: {company_metrics.completeness_score:.1f}/100")
    print(f"  Accuracy: {company_metrics.accuracy_score:.1f}/100")
else:
    print(f"✗ Company data has issues:")
    print(f"  Errors: {company_metrics.validation_errors}")
    print(f"  Issues: {company_metrics.data_issues}")

# ============================================================================
# INTERPRETING SCORES
# ============================================================================

# Completeness Score tells you what % of fields are populated
# 100 = all fields present
# 75 = most fields present (missing some optional fields)
# 50 = about half the fields present
# 25 = only a few fields present

completeness = company_metrics.completeness_score
if completeness >= 95:
    print("✓ Data is very complete")
elif completeness >= 80:
    print("✓ Data is mostly complete (minor gaps)")
elif completeness >= 60:
    print("⚠ Data is partially complete (missing some fields)")
else:
    print("✗ Data is incomplete (significant gaps)")

# Accuracy Score tells you what % of fields are valid
# 100 = all fields pass validation
# 90 = mostly valid (minor validation issues)
# 75 = some validation issues
# Below 50 = many validation problems

accuracy = company_metrics.accuracy_score
if accuracy >= 95:
    print("✓ Data is very accurate")
elif accuracy >= 80:
    print("✓ Data is mostly accurate (minor issues)")
elif accuracy >= 60:
    print("⚠ Data has validation issues")
else:
    print("✗ Data has significant problems")

# Overall Quality Score combines both
# = Completeness × 0.6 + Accuracy × 0.4
# Weights completeness more because missing data is worse than validation issues

overall = company_metrics.overall_quality_score
if overall >= 90:
    print("✓✓ Excellent - Production ready")
elif overall >= 80:
    print("✓ Good - Minor improvements needed")
elif overall >= 70:
    print("⚠ Fair - Moderate improvements needed")
else:
    print("✗ Poor - Significant work needed")

# ============================================================================
# TRACKING CREATED vs IMPROVED DATA
# ============================================================================

# New company discovered
monitor.track_company(
    company_id="new_company_001",
    company_data=new_company_data,
    is_new=True,  # ← This is NEW
)

# Existing company enriched with more data
monitor.track_company(
    company_id="existing_company_002",
    company_data=enriched_data,  # More complete than before
    is_new=False,
    was_improved=True,  # ← This was IMPROVED
)

# View counts in report
summary = monitor.get_report_summary()
print(f"New companies: {summary['created_entities'].get('company', 0)}")
print(f"Improved companies: {summary['improved_entities'].get('company', 0)}")

# ============================================================================
# LOGGING DATA ISSUES
# ============================================================================

# When you detect a problem, log it
monitor.log_data_issue(
    entity_id="company_001",
    issue="Missing Tech Stack: MongoDB doesn't list Python skills"
)

monitor.log_data_issue(
    entity_id="source_456",
    issue="Invalid Config: board_token is empty string"
)

# Check logged issues in report
report = monitor.get_report()
for issue_type, count in report.issues_by_type.items():
    print(f"{issue_type}: {count} issues found")

# ============================================================================
# UNDERSTANDING COMPLETION LEVELS
# ============================================================================

# CompletionLevel.MINIMAL
# Only required fields present
# Example: Company has name and website only
minimal_completion = {
    "name": "Company Inc",
    "website": "https://company.com",
    # Missing: about, tier, techStack, etc.
}

# CompletionLevel.PARTIAL
# Required fields + most recommended fields present
# Example: Company has good coverage but missing one optional field
partial_completion = {
    "name": "MongoDB",
    "website": "https://mongodb.com",
    "about": "Leading document database",
    "tier": "S",
    "techStack": ["Python", "Go"],
    # Missing: company_size_category, headquarters_location
}

# CompletionLevel.COMPLETE
# All fields present (required + recommended + optional)
# Example: Company fully populated
complete_completion = {
    "name": "MongoDB",
    "website": "https://mongodb.com",
    "about": "Leading document database",
    "tier": "S",
    "techStack": ["Python", "Go"],
    "hasPortlandOffice": False,
    "priorityScore": 180,
    "company_size_category": "large",
    "headquarters_location": "New York, NY",
}

# Check completion level
if company_metrics.completion_level.value == "complete":
    print("✓ Data is completely populated")
elif company_metrics.completion_level.value == "partial":
    print("⚠ Data is mostly complete")
else:
    print("✗ Data is minimal - many fields missing")

# ============================================================================
# GETTING DETAILED REPORTS
# ============================================================================

# Get a summary (dictionary format)
summary = monitor.get_report_summary()

# View processed entities
print(f"Companies: {summary['entities_processed']['companies']}")
print(f"Sources: {summary['entities_processed']['sources']}")
print(f"Jobs: {summary['entities_processed']['jobs']}")
print(f"Total: {summary['entities_processed']['total']}")

# View created and improved counts
print(f"New companies: {summary['created_entities'].get('company', 0)}")
print(f"Improved sources: {summary['improved_entities'].get('source', 0)}")

# View quality metrics
print(f"Avg Quality: {summary['quality_scores']['average']:.1f}/100")
print(f"Avg Completeness: {summary['quality_scores']['average_completeness']:.1f}/100")
print(f"Healthy: {summary['quality_scores']['healthy_entities']}/total")

# View issues
print(f"Validation Errors: {summary['issues']['validation_errors']}")
print(f"Data Issues: {summary['issues']['data_issues']}")

# Get full formatted report
report = monitor.end_test_run()
print(format_quality_report(report))

# ============================================================================
# VALIDATION ERROR EXAMPLES
# ============================================================================

# These validation errors will be reported:

# Missing required field
"Required field missing: website"

# Invalid data type
"name: Expected str, got int"

# String too short
"name: Too short (min 2 chars)"

# Invalid URL format
"website: Invalid URL format"

# Invalid enum value
"sourceType: Invalid value 'unknown'. Allowed: greenhouse, rss, api, company-page, workday"

# ============================================================================
# QUALITY TARGETS BY TEST
# ============================================================================

# After Phase 1 fixes:
# - Avg Quality: 85+/100
# - Avg Completeness: 90+/100
# - Healthy Entities: 95%+

# After Phase 2 fixes:
# - Avg Quality: 90+/100
# - Avg Completeness: 95+/100
# - Healthy Entities: 98%+

# After Phase 3 fixes:
# - Avg Quality: 95+/100
# - Avg Completeness: 98+/100
# - Healthy Entities: 99%+

# ============================================================================
# INTEGRATION WITH E2E TEST RUNNER
# ============================================================================

# The test runner automatically creates and uses the monitor:

# python tests/e2e/run_with_streaming.py --database portfolio-staging

# In your test scenario, check if monitor is available:

class MyScenario(BaseE2EScenario):
    def execute(self):
        # Create company
        company_id = self._create_company(...)
        company_data = self._fetch_company(company_id)
        
        # Track if monitor is available
        if hasattr(self, 'quality_monitor') and self.quality_monitor:
            self.quality_monitor.track_company(
                company_id=company_id,
                company_data=company_data,
                is_new=True,
            )

# ============================================================================
# EXPORTING RESULTS
# ============================================================================

import json
from datetime import datetime

# Save report as JSON for analysis
report = monitor.end_test_run()
summary = monitor.get_report_summary()

timestamp = datetime.now().isoformat()
filename = f"quality_report_{report.test_run_id}.json"

with open(filename, "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"Report saved to {filename}")

# ============================================================================
# COMPARING ACROSS TEST RUNS
# ============================================================================

# Collect multiple runs to see trends:

import json
from pathlib import Path

reports = []
for report_file in sorted(Path(".").glob("quality_report_*.json")):
    with open(report_file) as f:
        reports.append(json.load(f))

# Show trend
print("Quality Score Trend:")
for report in reports[-10:]:  # Last 10 runs
    avg = report["quality_scores"]["average"]
    print(f"  {report['test_run_id']}: {avg:.1f}")

# ============================================================================
# CONFIGURATION REFERENCE
# ============================================================================

# DATA TYPES SUPPORTED IN VALIDATION
str      # Text fields
int      # Integer fields  
float    # Decimal numbers
bool     # True/False
list     # Arrays
dict     # Objects

# REQUIRED vs OPTIONAL FIELDS
# Required: Must be present and non-null for data to pass validation
# Recommended: Should be present, good to have but not critical
# Optional: Nice to have, doesn't affect scores as much

# ALLOWED TIER VALUES
# "S" - Top tier (S = Strategic)
# "A" - High priority
# "B" - Medium priority
# "C" - Lower priority
# "D" - Lowest priority

# ALLOWED SOURCE TYPES
# "greenhouse" - Greenhouse job board
# "rss" - RSS feed
# "api" - Custom API
# "company-page" - Company career page
# "workday" - Workday ATS

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# Q: Quality score always 0
# A: Check that start_test_run() was called before tracking entities

# Q: Validation always passes with bad data
# A: Check field names in schema match your entity keys

# Q: Too many "Required field missing" errors
# A: Your data transformation layer isn't populating required fields

# Q: Low completeness but validation passes
# A: You're missing optional/recommended fields - focus on required first

# Q: How do I make quality scores higher?
# A: 1. Fix validation errors (add required fields)
#    2. Add optional/recommended fields (better scrapers)
#    3. Normalize and clean data (URL validation, etc.)
#    4. Link entities (companyId, sourceId)

# See full documentation: docs/DATA_QUALITY_MONITORING.md
