# Queue Pipeline Smoke Testing

End-to-end smoke tests for the queue-based job processing pipeline.

## Overview

The smoke test validates the complete pipeline from job submission to final storage:

1. **Load Fixtures** - Representative job postings from `tests/fixtures/smoke_jobs/`
2. **Submit to Queue** - Uses `ScraperIntake` to enqueue jobs
3. **Poll for Completion** - Monitors Firestore until all jobs reach terminal state
4. **Validate Data Quality** - Checks for duplicates, missing fields, and consistency
5. **Generate Reports** - Outputs markdown and JSON summaries

## Test Scenarios

The smoke test includes 5 representative job postings:

### 1. Remote Job with Tech Stack Alignment
- **File:** `remote_job.json`
- **Tests:** Remote filtering, tech stack matching, standard scoring
- **Expected:** Pass filters, high match score

### 2. Hybrid Portland Position
- **File:** `hybrid_portland.json`
- **Tests:** Portland office bonus, timezone scoring, hybrid location
- **Expected:** +15 Portland bonus, good match score

### 3. On-site California Position
- **File:** `onsite_california.json`
- **Tests:** Hard rejection for non-remote, non-Portland
- **Expected:** Filtered out or low score

### 4. Global Company (Fortune 500)
- **File:** `global_company.json`
- **Tests:** Large company handling, no timezone penalty
- **Expected:** No HQ timezone penalty, company size bonus

### 5. High Seniority Position
- **File:** `high_seniority.json`
- **Tests:** Seniority matching, experience level scoring
- **Expected:** Match with seniority gap note if applicable

See [tests/fixtures/smoke_jobs/README.md](../../tests/fixtures/smoke_jobs/README.md) for detailed scenario descriptions.

## Running Smoke Tests

### Prerequisites

1. **Credentials:**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/serviceAccountKey.json
   ```

2. **Environment Setup:**
   ```bash
   # Install dependencies
   make setup
   # Or manually:
   pip install -e ".[dev]"
   ```

3. **Worker Running** (for non-dry-run tests):
   - Staging: Portainer stack `job-finder-staging` must be running
   - Local: Start worker with `make worker` or Docker Compose

### Command Line Usage

**Quick test (dry run):**
```bash
python scripts/smoke/queue_pipeline_smoke.py --env staging --dry-run
```

**Full smoke test on staging:**
```bash
python scripts/smoke/queue_pipeline_smoke.py --env staging
```

**With custom timeout:**
```bash
python scripts/smoke/queue_pipeline_smoke.py --env staging --timeout 900
```

**Verbose logging:**
```bash
python scripts/smoke/queue_pipeline_smoke.py --env staging --verbose
```

**Custom fixtures directory:**
```bash
python scripts/smoke/queue_pipeline_smoke.py --fixtures /path/to/fixtures
```

### Makefile Target

```bash
make smoke-queue
```

This is equivalent to:
```bash
python scripts/smoke/queue_pipeline_smoke.py --env staging
```

### Test Output

Results are saved to `test_results/queue_smoke/<timestamp>/`:

- **`report.md`** - Human-readable markdown report with:
  - Summary statistics (total jobs, status breakdown, avg time)
  - Validation results (pass/fail for each check)
  - Individual job results with details
  
- **`report.json`** - Machine-readable JSON report with:
  - All metadata and timestamps
  - Complete job results
  - Validation details
  - Submitted fixture data

Example output location:
```
test_results/queue_smoke/20251020_142530/
├── report.md
└── report.json
```

## Validation Checks

The smoke test performs the following data quality validations:

### 1. Duplicate URL Detection
- Normalizes all URLs using `url_utils.normalize_url()`
- Ensures no duplicate jobs were processed
- **Fails if:** Multiple jobs share the same normalized URL

### 2. Scoring Fields Validation
For jobs that reach `SUCCESS` status:
- Checks `job-matches` collection for required fields:
  - `matchScore` - Overall match score (0-100)
  - `matchedSkills` - List of matched skills
  - `applicationPriority` - High/Medium/Low priority
  - `resumeIntakeData` - Resume customization data
- **Fails if:** Any required field is missing

### 3. Document References (Future)
- Validates document generation if enabled
- Checks for broken references
- Currently returns informational message

## Environment Configuration

### Staging
- **Database:** `portfolio-staging`
- **Worker:** Portainer stack `job-finder-staging`
- **Safe:** Does not affect production data
- **Use for:** Pre-deployment validation

### Local
- **Database:** `portfolio-staging` (same as staging)
- **Worker:** Local Docker or `make worker`
- **Use for:** Development and debugging

### Production
- **Database:** `portfolio`
- **Worker:** Portainer stack `job-finder-production`
- **⚠️ WARNING:** Affects real production data
- **Use for:** Post-deployment validation only

## CI/CD Integration

### GitHub Actions Workflow

The smoke test can be triggered manually via GitHub Actions:

```yaml
# .github/workflows/smoke-queue.yml
name: Queue Smoke Test

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to test'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production
```

**Trigger manually:**
1. Go to Actions tab in GitHub
2. Select "Queue Smoke Test" workflow
3. Click "Run workflow"
4. Choose environment
5. Review results in workflow logs

### AI Stubs for Cost Control

When running in CI, set environment variable to avoid AI API costs:

```bash
export USE_AI_STUBS=true
python scripts/smoke/queue_pipeline_smoke.py --env staging
```

This causes the AI matcher to return mock results instead of calling Claude/GPT-4.

## Troubleshooting

### No Jobs Submitted

**Symptoms:** "No jobs submitted" error

**Causes:**
- Jobs already in queue (deduplicated)
- Invalid fixtures (missing required fields)
- Firestore connection issues

**Solutions:**
1. Check queue for existing smoke test jobs:
   ```bash
   # Remove old smoke test jobs if needed
   python scripts/database/cleanup_firestore.py --source smoke_test
   ```

2. Validate fixtures have all required fields
3. Check `GOOGLE_APPLICATION_CREDENTIALS` is set

### Timeout Reached

**Symptoms:** Jobs still in `PROCESSING` state after timeout

**Causes:**
- Worker not running
- Worker stuck on a job
- AI API rate limiting

**Solutions:**
1. Check worker is running and healthy
2. Increase timeout: `--timeout 1200`
3. Check worker logs for errors
4. Verify AI API keys are valid

### Validation Failures

**Symptoms:** Validation report shows failures

**Causes:**
- Pipeline bug causing missing fields
- Firestore schema mismatch
- Data quality regression

**Solutions:**
1. Review specific validation errors in report
2. Check recent code changes
3. Run targeted tests for failing component
4. File a bug report with report.json attached

### Permission Denied

**Symptoms:** Firestore permission errors

**Causes:**
- Invalid service account key
- Insufficient permissions
- Wrong database name

**Solutions:**
1. Verify credentials file exists and is valid
2. Check service account has Firestore permissions
3. Ensure database name matches environment

## Adding New Test Cases

To add new smoke test scenarios:

1. **Create fixture JSON** in `tests/fixtures/smoke_jobs/`:
   ```json
   {
     "title": "Job Title",
     "company": "Company Name",
     "company_website": "https://example.com",
     "location": "Location",
     "description": "Full description with tech stack and requirements",
     "url": "https://example.com/unique-url-123",
     "posted_date": "2025-10-20",
     "salary": "$X - $Y",
     "test_case_notes": "Explain what this tests"
   }
   ```

2. **Document the scenario** in `tests/fixtures/smoke_jobs/README.md`

3. **Ensure unique URL** to avoid deduplication

4. **Run smoke test** to validate the new fixture:
   ```bash
   python scripts/smoke/queue_pipeline_smoke.py --env staging --dry-run
   ```

5. **Update this documentation** if the scenario tests a new dimension

## Best Practices

### Regular Testing
- Run smoke tests before each deployment
- Run after infrastructure changes
- Run when filter logic changes
- Run when AI prompts are modified

### Cleanup
- Clean up smoke test data periodically
- Don't let test results accumulate in `test_results/`
- Remove old fixtures that are no longer relevant

### Monitoring
- Review smoke test results for trends
- Track processing times over releases
- Monitor validation failure patterns
- Keep reports for regression analysis

### Security
- Never commit credentials to repository
- Use environment variables for sensitive data
- Store service account keys securely
- Rotate credentials regularly

## Future Enhancements

Planned improvements to smoke testing:

- [ ] Performance benchmarking (compare against baselines)
- [ ] Cost tracking (estimate AI API costs)
- [ ] Document generation validation
- [ ] Parallel job submission for speed
- [ ] Integration with Slack/email notifications
- [ ] Historical trend analysis
- [ ] Automated cleanup of test data
- [ ] Support for custom validation rules

## Related Documentation

- [Queue System Architecture](../queue-system.md)
- [Granular Pipeline Design](../GRANULAR_PIPELINE_DEPLOYMENT.md)
- [State-Driven Pipeline](../STATE_DRIVEN_PIPELINE_DESIGN.md)
- [Data Quality Monitoring](../DATA_QUALITY_MONITORING.md)
- [E2E Testing](../e2e/README.md)
