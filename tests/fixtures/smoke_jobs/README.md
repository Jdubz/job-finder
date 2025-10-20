# Smoke Test Job Fixtures

This directory contains representative job postings used for end-to-end smoke testing of the queue pipeline.

## Test Scenarios

### 1. `remote_job.json` - Remote Position with Tech Stack Alignment
- **Purpose**: Tests standard remote job processing with clear tech stack match
- **Key Features**:
  - Fully remote position (US-based)
  - Strong tech stack alignment (Python, Django, PostgreSQL)
  - Clear experience requirements (5+ years)
  - Competitive salary range
- **Expected Behavior**:
  - Should pass all filters
  - Should score well in AI matching (tech stack alignment)
  - Tests remote location preference handling

### 2. `hybrid_portland.json` - Portland Hybrid Position
- **Purpose**: Tests Portland office bonus and hybrid work arrangement
- **Key Features**:
  - Portland, OR location
  - Hybrid work model (2-3 days in office)
  - Local company with Pearl District office
  - Full-stack role with modern tech stack
- **Expected Behavior**:
  - Should receive +15 Portland office bonus in scoring
  - Tests timezone scoring (Pacific Time - same as user)
  - Tests hybrid location filtering
  - Validates company location detection

### 3. `onsite_california.json` - On-site Only Position
- **Purpose**: Tests filtering of non-remote, non-Portland positions
- **Key Features**:
  - San Francisco on-site requirement (5 days/week)
  - Startup environment
  - Good tech stack but location constraint
- **Expected Behavior**:
  - May be filtered out depending on remote preference strictness
  - If not filtered, should score lower due to location mismatch
  - Tests hard rejection for on-site requirements

### 4. `global_company.json` - Large Global Company (Fortune 500)
- **Purpose**: Tests handling of large global companies
- **Key Features**:
  - Amazon (Fortune 500 company)
  - Seattle HQ but with remote options
  - Distributed systems focus
  - High compensation
- **Expected Behavior**:
  - Should NOT be penalized for HQ timezone (large company exception)
  - Tests company size detection and scoring
  - Tests global company handling logic
  - Should receive large company bonus if `prefer_large_companies: true`

### 5. `high_seniority.json` - Principal Level Position
- **Purpose**: Tests seniority matching and experience level scoring
- **Key Features**:
  - Principal Engineer role (very high seniority)
  - 10+ years experience required
  - Remote-first global company
  - High compensation range
- **Expected Behavior**:
  - Tests seniority matching logic
  - Should match if user has sufficient experience
  - May note seniority gap if user is at lower level
  - Tests experience level scoring adjustments

## Fixture Format

All fixtures follow the standard job dictionary structure:

```json
{
  "title": "Job Title",
  "company": "Company Name",
  "company_website": "https://example.com",
  "location": "Location",
  "description": "Full job description with requirements and tech stack",
  "url": "https://example.com/job/123",
  "posted_date": "YYYY-MM-DD",
  "salary": "$XXX,XXX - $XXX,XXX",
  "test_case_notes": "Notes explaining this test case"
}
```

## Adding New Test Cases

When adding new fixtures:

1. **Choose a distinct test scenario** - Identify a specific edge case or important path
2. **Use realistic data** - Base on actual job postings but anonymize/genericize
3. **Document the purpose** - Add clear `test_case_notes` and update this README
4. **Ensure uniqueness** - Use unique URLs to avoid deduplication
5. **Cover key dimensions**:
   - Location types (remote, hybrid, on-site)
   - Company sizes (startup, mid-size, large)
   - Seniority levels (junior, mid, senior, principal)
   - Tech stack variations (exact match, partial match, no match)
   - Timezone scenarios (same, different, global)

## Usage in Tests

These fixtures are loaded by `scripts/smoke/queue_pipeline_smoke.py` and submitted to the queue for end-to-end validation. Each fixture tests a specific aspect of the pipeline:

- **Scraping**: Can we extract job data correctly?
- **Filtering**: Does the strike-based filter work as expected?
- **Analysis**: Does AI matching produce valid scores and insights?
- **Storage**: Are results properly saved to Firestore?
- **Data Quality**: Are all required fields present and valid?

## Maintenance

Update fixtures when:
- Filter logic changes and test expectations need adjustment
- New scoring features are added (e.g., new bonuses)
- Edge cases are discovered that should be tested
- Tech stack preferences change in the profile

Keep fixtures realistic but ensure they remain valid test cases as the system evolves.
