# Manual Pipeline Testing Guide

## Overview

This guide provides step-by-step instructions for manually testing the job-finder pipeline to verify decision tree logic and entity processing flows.

**Purpose**: Submit single entities, monitor logs in real-time, and verify that each entity type traverses the decision tree correctly.

## Prerequisites

1. **Worker Running**: Portainer staging worker must be running
2. **Database**: Connected to `portfolio-staging` Firestore
3. **Credentials**: `GOOGLE_APPLICATION_CREDENTIALS` configured
4. **Terminal Setup**: Multiple terminal windows for monitoring

## Entity Types & Decision Trees

### 1. Company Entity

**Decision Tree**: COMPANY_FETCH → COMPANY_EXTRACT → COMPANY_ANALYZE → COMPANY_SAVE

**Submit Company**:
```python
from job_finder.queue.scraper_intake import ScraperIntake
from job_finder.queue.manager import QueueManager

queue_manager = QueueManager("portfolio-staging")
intake = ScraperIntake(queue_manager)

# Submit company for analysis
doc_id = intake.submit_company(
    company_name="Netflix",
    company_website="https://jobs.netflix.com",
    source="manual_test"
)

print(f"Submitted company: {doc_id}")
```

**Expected Traversal**:
1. **COMPANY_FETCH** (0-30s):
   - Scrapes `/about`, `/careers`, homepage
   - Status: `processing` → `success`
   - Spawns: COMPANY_EXTRACT

2. **COMPANY_EXTRACT** (30-60s):
   - AI extraction of company info
   - Status: `processing` → `success`
   - Spawns: COMPANY_ANALYZE

3. **COMPANY_ANALYZE** (5-10s):
   - Tech stack detection
   - Job board discovery
   - Priority scoring (S/A/B/C/D tier)
   - Status: `processing` → `success`
   - Spawns: COMPANY_SAVE + SOURCE_DISCOVERY (if board found)

4. **COMPANY_SAVE** (2-5s):
   - Creates/updates `companies` document
   - Status: `processing` → `success`

**Verification Steps**:
```python
# Check company document created
from job_finder.storage.companies_manager import CompaniesManager

companies = CompaniesManager("portfolio-staging")
company = companies.get_company_by_website("https://jobs.netflix.com")

assert company is not None
assert company["about"] is not None
assert "tech_stack" in company
assert "priority_tier" in company

print(f"✓ Company created: {company['name']}")
print(f"✓ Tech stack: {company['tech_stack']}")
print(f"✓ Priority tier: {company['priority_tier']}")
```

### 2. Job Source Entity

**Decision Tree**: SOURCE_DISCOVERY → (validation) → job-sources document

**Submit Job Source** (auto-spawned by Company or manual):
```python
# Manually submit source for discovery
doc_id = queue_manager.create_item(
    type="source_discovery",
    url="",  # Not used for source_discovery
    company_name="Netflix",
    company_id="company_123",
    source="manual_test",
    source_discovery_config={
        "url": "https://boards.greenhouse.io/netflix",
        "type_hint": "greenhouse",
        "company_id": "company_123",
        "company_name": "Netflix",
        "auto_enable": True,
        "validation_required": False,
    }
)

print(f"Submitted source discovery: {doc_id}")
```

**Expected Traversal**:
1. **SOURCE_DISCOVERY** (10-30s):
   - Detects source type (Greenhouse, Workday, RSS, generic)
   - Validates configuration
   - Creates `job-sources` document
   - Status: `processing` → `success`

**Verification Steps**:
```python
from job_finder.storage.job_sources_manager import JobSourcesManager

sources = JobSourcesManager("portfolio-staging")
source = sources.get_source_for_url("https://boards.greenhouse.io/netflix")

assert source is not None
assert source["sourceType"] == "greenhouse"
assert source["enabled"] == True
assert "config" in source

print(f"✓ Source created: {source['name']}")
print(f"✓ Source type: {source['sourceType']}")
print(f"✓ Enabled: {source['enabled']}")
```

### 3. Job Listing Entity

**Decision Tree**: JOB_SCRAPE → JOB_FILTER → JOB_ANALYZE → JOB_SAVE

**Submit Job Listing**:
```python
# Submit job for processing
doc_id = intake.submit_job(
    url="https://jobs.netflix.com/jobs/123456",
    company_name="Netflix",
    source="manual_test"
)

print(f"Submitted job: {doc_id}")
```

**Expected Traversal**:
1. **JOB_SCRAPE** (10-30s):
   - Extracts job data (title, location, description)
   - Uses source-specific selectors or AI
   - Status: `processing` → `success`
   - Spawns: JOB_FILTER

2. **JOB_FILTER** (5-10s):
   - Strike-based filtering
   - No AI (rule-based, $0 cost)
   - Status: `processing` → `success` (passed) OR `filtered` (rejected)
   - If passed, spawns: JOB_ANALYZE
   - If filtered, stops here

3. **JOB_ANALYZE** (30-60s):
   - AI matching with Claude Sonnet
   - Match score 0-100
   - Resume intake data generation
   - Status: `processing` → `success` (score ≥ threshold) OR `skipped` (score < threshold)
   - If score ≥ threshold, spawns: JOB_SAVE
   - If skipped, stops here

4. **JOB_SAVE** (5-10s):
   - Creates `job-matches` document
   - Status: `processing` → `success`

**Verification Steps**:
```python
from job_finder.storage import FirestoreJobStorage

storage = FirestoreJobStorage("portfolio-staging")
match = storage.get_match_by_url("https://jobs.netflix.com/jobs/123456")

assert match is not None
assert match["matchScore"] >= 80
assert "resumeIntakeData" in match
assert match["resumeIntakeData"]["atsKeywords"] is not None

print(f"✓ Match created: {match['title']}")
print(f"✓ Match score: {match['matchScore']}")
print(f"✓ Priority: {match['applicationPriority']}")
```

## Real-Time Log Monitoring

### Setup Log Monitoring Windows

Open 4 terminal windows:

**Window 1: Overall Worker Activity**
```bash
gcloud logging tail "logName='projects/static-sites-257923/logs/job-finder' AND labels.environment='staging'" --format=json | jq -r 'select(.textPayload) | "[" + .timestamp + "] " + .textPayload'
```

**Window 2: Queue Processing**
```bash
gcloud logging tail "logName='projects/static-sites-257923/logs/job-finder' AND labels.environment='staging' AND textPayload:'[QUEUE:'" --format=json | jq -r 'select(.textPayload) | "[" + .timestamp + "] " + .textPayload'
```

**Window 3: Pipeline Stages**
```bash
gcloud logging tail "logName='projects/static-sites-257923/logs/job-finder' AND labels.environment='staging' AND textPayload:'[PIPELINE:'" --format=json | jq -r 'select(.textPayload) | "[" + .timestamp + "] " + .textPayload'
```

**Window 4: AI Operations**
```bash
gcloud logging tail "logName='projects/static-sites-257923/logs/job-finder' AND labels.environment='staging' AND textPayload:'[AI:'" --format=json | jq -r 'select(.textPayload) | "[" + .timestamp + "] " + .textPayload'
```

### Simplified One-Window Monitoring

If you prefer a single window with color-coded output:

```bash
#!/bin/bash
# Save as: watch_pipeline.sh

gcloud logging tail "logName='projects/static-sites-257923/logs/job-finder' AND labels.environment='staging'" --format=json | \
while read -r line; do
    timestamp=$(echo "$line" | jq -r '.timestamp // empty')
    text=$(echo "$line" | jq -r '.textPayload // empty')

    if [[ -z "$text" ]]; then
        continue
    fi

    # Color-code by category
    if [[ "$text" == *"[WORKER]"* ]]; then
        echo -e "\033[1;34m[$timestamp] $text\033[0m"  # Blue
    elif [[ "$text" == *"[QUEUE:"* ]]; then
        echo -e "\033[1;32m[$timestamp] $text\033[0m"  # Green
    elif [[ "$text" == *"[PIPELINE:"* ]]; then
        echo -e "\033[1;33m[$timestamp] $text\033[0m"  # Yellow
    elif [[ "$text" == *"[AI:"* ]]; then
        echo -e "\033[1;35m[$timestamp] $text\033[0m"  # Magenta
    elif [[ "$text" == *"ERROR"* ]] || [[ "$text" == *"FAIL"* ]]; then
        echo -e "\033[1;31m[$timestamp] $text\033[0m"  # Red
    else
        echo "[$timestamp] $text"
    fi
done
```

Usage:
```bash
chmod +x watch_pipeline.sh
./watch_pipeline.sh
```

## Complete Test Flow Example

### Test 1: Company → Source → Jobs → Matches (Full Chain)

**Goal**: Verify complete discovery chain works end-to-end.

**Steps**:

1. **Start log monitoring** (in separate terminal):
```bash
./watch_pipeline.sh
```

2. **Submit company** (Python REPL or script):
```python
from job_finder.queue.scraper_intake import ScraperIntake
from job_finder.queue.manager import QueueManager

queue_manager = QueueManager("portfolio-staging")
intake = ScraperIntake(queue_manager)

# Submit Stripe (known to have Greenhouse board)
company_doc_id = intake.submit_company(
    company_name="Stripe",
    company_website="https://stripe.com/jobs",
    source="manual_test"
)

print(f"✓ Submitted company: {company_doc_id}")
print("Watch logs for COMPANY_FETCH → COMPANY_EXTRACT → COMPANY_ANALYZE → COMPANY_SAVE")
print("Expected: SOURCE_DISCOVERY should spawn automatically")
input("Press Enter when company processing completes...")
```

3. **Verify company created**:
```python
from job_finder.storage.companies_manager import CompaniesManager

companies = CompaniesManager("portfolio-staging")
company = companies.get_company_by_name("Stripe")

print(f"\n✓ Company: {company['name']}")
print(f"  About: {company.get('about', 'N/A')[:100]}...")
print(f"  Tech stack: {company.get('tech_stack', [])}")
print(f"  Priority tier: {company.get('priority_tier', 'N/A')}")
print(f"  Job board: {company.get('job_board_url', 'N/A')}")

company_id = company['id']
```

4. **Verify source created** (should auto-spawn from company):
```python
from job_finder.storage.job_sources_manager import JobSourcesManager

sources = JobSourcesManager("portfolio-staging")

# Wait for SOURCE_DISCOVERY to complete
import time
time.sleep(30)

# Find Stripe source
stripe_sources = sources.get_sources_by_company(company_id)

if stripe_sources:
    source = stripe_sources[0]
    print(f"\n✓ Source: {source['name']}")
    print(f"  Type: {source['sourceType']}")
    print(f"  URL: {source.get('url', 'N/A')}")
    print(f"  Enabled: {source['enabled']}")
    source_id = source['id']
else:
    print("✗ No source found - check logs for SOURCE_DISCOVERY errors")
    source_id = None
```

5. **Submit SCRAPE request** (will use discovered source):
```python
if source_id:
    scrape_doc_id = queue_manager.create_item(
        type="scrape",
        url="",  # Not used for SCRAPE
        source="manual_test",
        scrape_config={
            "target_matches": 5,  # Stop after 5 matches
            "max_sources": 1,  # Only use Stripe source
            "source_ids": [source_id],
        }
    )

    print(f"\n✓ Submitted SCRAPE request: {scrape_doc_id}")
    print("Watch logs for:")
    print("  1. SCRAPE fetches jobs from source")
    print("  2. Multiple JOB_SCRAPE items spawned")
    print("  3. JOB_FILTER for each job")
    print("  4. JOB_ANALYZE for filtered jobs")
    print("  5. JOB_SAVE for high-scoring jobs")

    input("Press Enter when scraping completes (may take 2-5 minutes)...")
```

6. **Verify matches created**:
```python
from job_finder.storage import FirestoreJobStorage

storage = FirestoreJobStorage("portfolio-staging")
matches = storage.get_matches_by_company(company_id, limit=10)

print(f"\n✓ Found {len(matches)} matches for {company['name']}")
for match in matches:
    print(f"  - {match['title']} (score: {match['matchScore']})")
```

### Test 2: Individual Job Submission (Manual Entry)

**Goal**: Test decision tree for a single job URL.

**Steps**:

1. **Start log monitoring**:
```bash
./watch_pipeline.sh
```

2. **Submit job URL**:
```python
from job_finder.queue.scraper_intake import ScraperIntake
from job_finder.queue.manager import QueueManager

queue_manager = QueueManager("portfolio-staging")
intake = ScraperIntake(queue_manager)

# Submit specific job
job_doc_id = intake.submit_job(
    url="https://jobs.lever.co/1password/12345678",
    company_name="1Password",
    source="manual_test"
)

print(f"✓ Submitted job: {job_doc_id}")
print("\nExpected decision tree:")
print("  1. JOB_SCRAPE (10-30s) - Extract job data")
print("  2. JOB_FILTER (5-10s) - Strike-based filtering")
print("  3. JOB_ANALYZE (30-60s) - AI matching (if passed filter)")
print("  4. JOB_SAVE (5s) - Create match (if score ≥ 80)")
```

3. **Monitor queue item status**:
```python
import time

def check_status():
    item = queue_manager.get_item(job_doc_id)
    print(f"Status: {item.status}")
    if hasattr(item, 'sub_task') and item.sub_task:
        print(f"Sub-task: {item.sub_task}")
    if item.result_message:
        print(f"Message: {item.result_message}")
    return item

# Check every 10 seconds
for i in range(12):  # 2 minutes max
    print(f"\n--- Check {i+1} ---")
    item = check_status()

    if item.status in ["success", "failed", "filtered", "skipped"]:
        print(f"\n✓ Final status: {item.status}")
        break

    time.sleep(10)
```

4. **Verify result**:
```python
item = queue_manager.get_item(job_doc_id)

if item.status == "success":
    # Check for match
    match = storage.get_match_by_url(url)
    if match:
        print(f"\n✓ Match created!")
        print(f"  Title: {match['title']}")
        print(f"  Score: {match['matchScore']}")
        print(f"  Priority: {match['applicationPriority']}")
    else:
        print("\n✗ No match found despite success status")

elif item.status == "filtered":
    print(f"\n✓ Job filtered (expected for non-matching jobs)")
    print(f"  Reason: {item.result_message}")

elif item.status == "skipped":
    print(f"\n✓ Job skipped after analysis (score < 80)")
    print(f"  Reason: {item.result_message}")

elif item.status == "failed":
    print(f"\n✗ Job processing failed")
    print(f"  Error: {item.result_message}")
```

## Decision Tree Validation Checklist

Use this checklist to verify decision tree logic:

### Company Pipeline
- [ ] COMPANY_FETCH completes successfully
- [ ] COMPANY_EXTRACT spawns after FETCH
- [ ] COMPANY_ANALYZE spawns after EXTRACT
- [ ] COMPANY_SAVE spawns after ANALYZE
- [ ] SOURCE_DISCOVERY spawns if job board found
- [ ] Company document created in Firestore
- [ ] Tech stack populated
- [ ] Priority tier assigned

### Source Pipeline
- [ ] SOURCE_DISCOVERY validates source type
- [ ] Source configuration created
- [ ] Source enabled based on confidence
- [ ] Source linked to company_id

### Job Pipeline (Happy Path)
- [ ] JOB_SCRAPE extracts job data
- [ ] JOB_FILTER evaluates strikes
- [ ] JOB_ANALYZE runs AI matching (if passed filter)
- [ ] JOB_SAVE creates match (if score ≥ 80)
- [ ] Match document created in Firestore
- [ ] Resume intake data populated

### Job Pipeline (Rejection Paths)
- [ ] Hard rejection: No FILTER spawned
- [ ] Filter rejection: No ANALYZE spawned
- [ ] Score rejection: No SAVE spawned
- [ ] Each rejection properly logged

## Troubleshooting

### Job Stuck in "processing"
1. Check worker is running: `gcloud logging read` should show recent activity
2. Check for errors in logs: Look for `ERROR` or `FAIL` in pipeline logs
3. Check queue item: May have exceeded max retries
4. Restart worker: In Portainer, restart `job-finder-staging` container

### Job Failed with Error
1. Check `result_message` field: Contains error details
2. Check Cloud Logging: Search for queue item ID
3. Common issues:
   - Invalid URL format
   - Selector not found (for scraping)
   - AI API rate limit
   - Network timeout

### Job Filtered/Skipped Unexpectedly
1. Check filter result: `result_message` contains filter details
2. Review profile: Ensure preferences match job
3. Check strike accumulation: May be hitting threshold
4. Test with relaxed filters temporarily

### No Logs Appearing
1. Verify worker running: Check Portainer container status
2. Verify environment: Logs should have `labels.environment='staging'`
3. Check credentials: `GOOGLE_APPLICATION_CREDENTIALS` must be valid
4. Try filtering less: Remove filters from gcloud command

## Next Steps

After manual testing validates the decision tree logic:

1. **Document Findings**: Note any unexpected behavior or edge cases
2. **Update E2E Tests**: Add scenarios for any gaps found
3. **Automation**: Convert manual tests to automated e2e scenarios
4. **Performance**: Measure timing for each pipeline stage
5. **Cost Analysis**: Track AI API costs per entity type

## Helper Scripts

Save these for quick testing:

**submit_test_company.py**:
```python
#!/usr/bin/env python3
"""Submit a company for testing."""
import sys
from job_finder.queue.scraper_intake import ScraperIntake
from job_finder.queue.manager import QueueManager

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python submit_test_company.py <company_name> <company_website>")
        sys.exit(1)

    company_name = sys.argv[1]
    company_website = sys.argv[2]

    queue_manager = QueueManager("portfolio-staging")
    intake = ScraperIntake(queue_manager)

    doc_id = intake.submit_company(
        company_name=company_name,
        company_website=company_website,
        source="manual_test"
    )

    print(f"Submitted: {doc_id}")
    print("Monitor logs with: ./watch_pipeline.sh")
```

**submit_test_job.py**:
```python
#!/usr/bin/env python3
"""Submit a job URL for testing."""
import sys
from job_finder.queue.scraper_intake import ScraperIntake
from job_finder.queue.manager import QueueManager

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python submit_test_job.py <job_url> <company_name>")
        sys.exit(1)

    job_url = sys.argv[1]
    company_name = sys.argv[2]

    queue_manager = QueueManager("portfolio-staging")
    intake = ScraperIntake(queue_manager)

    doc_id = intake.submit_job(
        url=job_url,
        company_name=company_name,
        source="manual_test"
    )

    print(f"Submitted: {doc_id}")
    print("Monitor logs with: ./watch_pipeline.sh")
```

Make them executable:
```bash
chmod +x submit_test_company.py submit_test_job.py
```
