# Job Finder Queue Decision Tree

This document describes the decision tree logic for the worker job queue system. It provides both a high-level conceptual flow and detailed implementation specifics.

## Table of Contents

1. [High-Level Overview](#high-level-overview)
2. [Loop Prevention Mechanisms](#loop-prevention-mechanisms)
3. [Data Quality Standards](#data-quality-standards)
4. [Queue Processing States](#queue-processing-states)
5. [Company Pipeline](#company-pipeline)
6. [Job Source Pipeline](#job-source-pipeline)
7. [Job Listing Pipeline](#job-listing-pipeline)
8. [Scraper Instruction Schemas](#scraper-instruction-schemas)
9. [Error Handling](#error-handling)

---

## High-Level Overview

The system processes three main entity types that interconnect:

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│  Companies  │────────▶│ Job Sources  │────────▶│ Job Listings │
└─────────────┘         └──────────────┘         └──────────────┘
      │                       │                         │
      │                       │                         └──▶ Analyze Match ──▶ Success!
      │                       └──▶ Scrape Jobs
      └──▶ Discover Job Boards
```

### Key Relationships:

- **Companies** can spawn **Job Sources** when career pages/job boards are discovered
- **Job Sources** spawn **Job Listings** when scraping finds new postings
- **Job Listings** may spawn **Companies** if the company is unknown
- **Each spawn path uses loop prevention** to avoid circular dependencies

---

## Loop Prevention Mechanisms

**Critical**: Every queue item spawn is protected against infinite loops using three mechanisms:

### 1. Tracking ID

- UUID generated at root item, inherited by all spawned children
- Groups related items into a processing lineage
- Used to query for duplicate work and circular dependencies

### 2. Ancestry Chain

- List of parent item document IDs from root to current
- Before spawning, check if target URL already exists in ancestry
- Prevents circular patterns: `Job → Company → Source → Job` (same URL)

### 3. Spawn Depth

- Counter incremented with each spawn
- Default maximum: 10 levels deep
- Prevents runaway spawning even without circular URLs

### Spawn Safety Checks

Before creating a new queue item, the system verifies:

1. ✅ Spawn depth < max_spawn_depth (default: 10)
2. ✅ Target URL not in ancestry chain (no circular dependency)
3. ✅ No pending/processing item for same URL+type in this lineage
4. ✅ Item hasn't already reached terminal state (FILTERED, SKIPPED, FAILED, or final SUCCESS)

**If any check fails, spawning is blocked and logged as a warning.**

---

## Data Quality Standards

### Record Creation Policy

To prevent race conditions while keeping the database clean:

**Create immediately with:**

- Primary identifiers: `name`, `website`/`url`
- Reference IDs: `companyId`, `sourceId`, `parentItemId`
- Status field: `'analyzing'`, `'pending_validation'`, `'active'`
- Tracking metadata: `tracking_id`, `ancestry_chain`, `spawn_depth`

**Omit until analysis completes:**

- Company: `about`, `culture`, `mission`, `size`, `techStack`, `tier`, `priorityScore`
- Job Source: `selectors`, `api_endpoints`, `scraper_config`, `discovery_confidence`
- Job: `description`, `title`, `location`, `requirements`

### Data Completeness Thresholds

#### Company:

- **Minimal**: `name + website + (about > 50 chars OR culture > 25 chars)`
- **Good**: `name + website + about > 100 chars + culture > 50 chars`
- **Skip re-analysis**: Good threshold met AND `updatedAt < 30 days ago`

#### Job Source:

- **Valid**: `url + sourceType + basic config` (e.g., `board_token` OR `base_url` OR `selectors`)
- **Complete**: Valid + tested successfully + `confidence = 'high'`
- **Requires manual validation**: `confidence = 'medium'` OR `confidence = 'low'`

#### Job Listing:

- **Minimal**: `url + title + company + description > 100 chars`
- **Good**: Minimal + `location + posted_date + requirements`

---

## Queue Processing States

Every queue item progresses through states with terminal exit points:

### States

- **PENDING**: Waiting to be processed (entry state)
- **PROCESSING**: Currently being processed
- **SUCCESS**: Completed successfully (may spawn next stage)
- **FILTERED**: Rejected by filter engine (terminal - jobs only)
- **SKIPPED**: Below threshold or duplicate (terminal)
- **FAILED**: Error after max retries (terminal)

### State Transitions

```
PENDING ──▶ PROCESSING ──┬──▶ SUCCESS ──▶ (spawn next stage or terminal)
                         │
                         ├──▶ FILTERED (terminal - failed filters)
                         │
                         ├──▶ SKIPPED (terminal - below threshold/duplicate)
                         │
                         └──▶ FAILED ──▶ retry ──▶ PENDING (if retries < max_retries)
                                     └──▶ FAILED (terminal - max retries exceeded)
```

### Terminal vs Non-Terminal SUCCESS

- **Non-terminal SUCCESS**: Intermediate pipeline stages (SCRAPE, FILTER, ANALYZE for jobs)
  - Item marked SUCCESS, spawns next stage
  - Allows same URL to progress through pipeline
- **Terminal SUCCESS**: Final stage (SAVE)
  - Item marked SUCCESS, no further spawning
  - Blocks future spawns for same URL in this lineage

---

## Company Pipeline

**Full pipeline**: `FETCH → EXTRACT → ANALYZE → SAVE`

Each stage is an independent queue item with `company_sub_task` field.

### Stage 1: COMPANY_FETCH

**Input**: `company_name`, `company_website`

**Process**:

1. Create company record with status `'analyzing'` (if not exists)
2. Attempt to fetch HTML from multiple pages:
   - `{website}/about`
   - `{website}/about-us`
   - `{website}/company`
   - `{website}/careers`
   - `{website}` (homepage fallback)
3. Store fetched HTML in `pipeline_state.html_content`

**Success**: Spawn `COMPANY_EXTRACT`
**Failure**: Mark FAILED (retry up to 3 times)

---

### Stage 2: COMPANY_EXTRACT

**Input**: `pipeline_state.html_content` from FETCH

**Process**:

1. Combine all HTML content
2. Use AI (Claude Sonnet - expensive but accurate) to extract:
   - `about`: Company description
   - `culture`: Culture/values information
   - `mission`: Mission statement
   - `size`: Employee count or size description
   - `headquarters_location`: HQ location
   - `industry`: Industry/sector
   - `founded`: Year founded
3. Fallback to heuristics if AI extraction fails
4. Store extracted info in `pipeline_state.extracted_info`

**Success**: Spawn `COMPANY_ANALYZE`
**Failure**: Mark FAILED (retry up to 3 times)

---

### Stage 3: COMPANY_ANALYZE

**Input**: `pipeline_state.extracted_info` from EXTRACT

**Process** (rule-based, no AI cost):

#### 3.1 Tech Stack Detection

Pattern match from company info + HTML for technologies:

- Languages: Python, JavaScript, Java, Go, Rust, Ruby, PHP, C#
- Frontend: React, Vue, Angular, Svelte
- Backend/Infra: Docker, Kubernetes, AWS, GCP, Azure
- Databases: PostgreSQL, MySQL, MongoDB, Redis
- ML/AI: TensorFlow, PyTorch, machine learning keywords

#### 3.2 Job Board Discovery

Search for job board patterns in careers page:

- Greenhouse: `boards.greenhouse.io/{board_token}`
- Workday: `{company}.myworkdayjobs.com`
- Lever, Jobvite, SmartRecruiters, etc.
- Generic careers pages: `{website}/careers`, `{website}/jobs`

**Confidence Levels**:

- **High**: Greenhouse (API available), Workday (standard structure), RSS feeds
- **Medium**: Lever, Jobvite (requires testing)
- **Low**: Generic HTML careers pages (AI selector discovery needed)

#### 3.3 Priority Scoring

Calculate numeric score and assign tier (S/A/B/C/D):

- Portland office: **+50 points**
- Tech stack alignment: **up to +100 points** (based on user's tech ranks from config)
- Remote-first culture: **+15 points**
- AI/ML focus: **+10 points**

**Tiers**:

- **S**: 150+ points (top priority)
- **A**: 100-149 points (high priority)
- **B**: 70-99 points (medium priority)
- **C**: 50-69 points (low priority)
- **D**: 0-49 points (minimal priority)

#### 3.4 Job Board Spawn Decision

If job board found:

- **High confidence**: Immediately spawn `SOURCE_DISCOVERY` queue item
- **Medium/Low confidence**: Store as company metadata `{ job_board_url, confidence }`, require manual approval

**Success**: Spawn `COMPANY_SAVE`
**Skip**: If insufficient data extracted, mark SKIPPED

---

### Stage 4: COMPANY_SAVE

**Input**: All `pipeline_state` data from previous stages

**Process**:

1. Build complete company record:
   ```json
   {
     "name": "Company Name",
     "website": "https://...",
     "about": "...",
     "culture": "...",
     "mission": "...",
     "size": "...",
     "company_size_category": "large|medium|small",
     "headquarters_location": "...",
     "industry": "...",
     "founded": "...",
     "techStack": ["python", "react", ...],
     "tier": "A",
     "priorityScore": 105,
     "analysis_status": "complete"
   }
   ```
2. Save to Firestore `companies` collection
3. If job board URL exists AND high confidence:
   - Spawn `SOURCE_DISCOVERY` queue item
   - Links back to this company via `company_id`

**Success**: Mark item SUCCESS (terminal - no further spawning)
**Failure**: Mark FAILED (retry up to 3 times)

---

## Job Source Pipeline

**Full pipeline**: `DISCOVER → VALIDATE → CONFIGURE → (optional: TEST)`

Sources are discovered either:

1. During `COMPANY_ANALYZE` (finds job board)
2. User submission via frontend
3. Automated scanning

### SOURCE_DISCOVERY Queue Item

**Input**: `source_discovery_config` with:

- `url`: URL to analyze
- `type_hint`: `'auto'`, `'greenhouse'`, `'workday'`, `'rss'`, `'generic'`
- `company_id`: Optional company reference
- `company_name`: Optional company name
- `auto_enable`: Whether to enable if high confidence (default: true)
- `validation_required`: Force manual validation (default: false)

---

### Source Type Detection

**Auto-detect from URL patterns:**

#### Greenhouse (High Confidence)

- **Pattern**: `boards.greenhouse.io/{board_token}`
- **Config**: `{ "board_token": "netflix" }`
- **Validation**: Fetch `https://boards-api.greenhouse.io/v1/boards/{token}/jobs`
- **Auto-enable**: Yes (API validation ensures reliability)

#### Workday (Medium Confidence)

- **Pattern**: `{company}.myworkdayjobs.com`
- **Config**: `{ "company_id": "netflix", "base_url": "https://..." }`
- **Validation**: Basic URL check (full scraping needs testing)
- **Auto-enable**: No (requires manual validation)

#### RSS Feed (High Confidence)

- **Pattern**: `.xml`, `/feed`, `/rss`, `/jobs.rss`
- **Config**: `{ "url": "...", "parse_format": "standard" }`
- **Validation**: Parse feed with `feedparser`, check for entries
- **Auto-enable**: Yes (valid feed format is reliable)

#### Generic HTML (Low Confidence)

- **Pattern**: Any careers page URL
- **Config**: `{ "url": "...", "method": "requests", "selectors": {...} }`
- **Validation**: Use AI (Claude Haiku) to discover CSS selectors
- **Auto-enable**: No (requires test scrape validation)

---

### Source Creation

Create `job-sources` document:

```json
{
  "name": "Netflix Greenhouse",
  "sourceType": "greenhouse",
  "config": { "board_token": "netflix" },
  "enabled": true, // or false if validation_required
  "companyId": "company-doc-id",
  "companyName": "Netflix",
  "discoveredVia": "user_submission|automated_scan",
  "discoveredBy": "user-uid",
  "discoveredAt": "2025-01-01T...",
  "discoveryConfidence": "high|medium|low",
  "validationRequired": false,
  "consecutiveFailures": 0,
  "lastScrapedAt": null,
  "lastScrapedStatus": null
}
```

**Success**: Mark SOURCE_DISCOVERY item SUCCESS, return `source_id`
**Failure**: Mark FAILED with error details

---

## Job Listing Pipeline

**Full pipeline**: `SCRAPE → FILTER → ANALYZE → SAVE`

### Decision Tree Routing

Unlike companies/sources which have explicit `sub_task` fields, job processing uses **state-based routing**. The processor examines `pipeline_state` to determine next action:

```python
has_job_data = "job_data" in pipeline_state
has_filter_result = "filter_result" in pipeline_state
has_match_result = "match_result" in pipeline_state

if not has_job_data:
    → do_job_scrape()
elif not has_filter_result:
    → do_job_filter()
elif not has_match_result:
    → do_job_analyze()
else:
    → do_job_save()
```

This allows the SAME queue item to progress through all stages (easier for E2E tests to monitor).

---

### Stage 1: JOB_SCRAPE

**Input**: `url`, optional `scraped_data` (if pre-scraped)

**Process**:

1. Check if source configuration exists for this URL
   - Use `JobSourcesManager.get_source_for_url(url)`
   - Matches URL domain/pattern against configured sources
2. If source config found:
   - Use source-specific scraping with selectors/API
   - More reliable, structured data extraction
3. If no source config:
   - Fall back to generic scraping (BeautifulSoup)
   - Or use AI extraction (Claude Haiku) for structured data
4. Extract job data:
   ```json
   {
     "title": "Senior Software Engineer",
     "company": "Company Name",
     "company_website": "https://...",
     "location": "Remote",
     "description": "Full job description...",
     "url": "https://...",
     "posted_date": "2025-01-01",
     "salary": "$150k-$200k"
   }
   ```
5. Update `pipeline_state.job_data` and `pipeline_state.scrape_method`

**Success**: Re-queue same item with updated state, `pipeline_stage='scrape'`
**Failure**: Mark FAILED (retry up to 3 times)

**Cost**: $0.001/1K tokens if using AI (Claude Haiku)

---

### Stage 2: JOB_FILTER

**Input**: `pipeline_state.job_data` from SCRAPE

**Process**: Apply two-tier strike-based filtering (NO AI, $0 cost)

#### Hard Rejections (Immediate FILTERED)

- Non-remote jobs (unless Portland, OR hybrid)
- Excluded companies (from stop list)
- Excluded keywords in title/URL (from stop list)
- Job types mismatching preferences (e.g., management role when user prefers IC)

#### Strike Accumulation (Threshold: 5 strikes)

- **Location mismatches**:
  - Non-Portland, non-remote: 2-3 strikes
- **Seniority mismatches**:
  - Senior vs Junior: 2-3 strikes
- **Tech stack mismatches**:
  - Each missing required skill: 1-3 strikes
  - Weight by importance (primary tech = 3 strikes, nice-to-have = 1 strike)
- **Experience level mismatches**: 2-3 strikes

**Filter Result Structure**:

```json
{
  "passed": false,
  "total_strikes": 7,
  "hard_rejections": [],
  "strikes": [
    { "reason": "Missing primary skill: React", "strikes": 3 },
    { "reason": "Location not remote or Portland", "strikes": 2 },
    { "reason": "Seniority mismatch (too junior)", "strikes": 2 }
  ],
  "rejection_summary": "7 strikes (threshold: 5)"
}
```

**Passed**: Re-queue same item with `pipeline_state.filter_result`, `pipeline_stage='filter'`
**Failed**: Mark FILTERED (terminal) with rejection details
**Cost**: $0 (rule-based only)

---

### Stage 3: JOB_ANALYZE

**Input**: `pipeline_state.job_data` and `pipeline_state.filter_result` (passed)

**Process**:

1. **Ensure company exists**:
   - Get or create company via `CompaniesManager.get_or_create_company()`
   - Fetches company info if not cached or sparse
   - Adds `company_id` and `company_info` to job_data
2. **Run AI matching** (Claude Sonnet - expensive):
   - Analyze job description against user profile
   - Generate match score (0-100)
   - Apply timezone adjustment (-15 to +5 points based on team location)
   - Apply company size preference (+10 for large if preferred, -5 for small/startup)
   - Identify matched skills and skill gaps
   - Assign application priority (High: 85-100, Medium: 70-84, Low: 0-69)
   - Generate resume intake data:
     - Target professional summary tailored to job
     - Priority-ordered skills list
     - Experience highlights to emphasize
     - Projects to include
     - Achievement angles
     - ATS keywords to incorporate
3. **Check threshold**:
   - Minimum match score: 80 (65 with Portland office bonus)
   - Below threshold → SKIPPED (terminal)

**Match Result Structure**:

```json
{
  "match_score": 87,
  "application_priority": "High",
  "matched_skills": ["Python", "React", "AWS"],
  "skill_gaps": ["Kubernetes", "GraphQL"],
  "resumeIntakeData": {
    "professionalSummary": "...",
    "prioritizedSkills": [...],
    "experienceHighlights": [...],
    "projectsToInclude": [...],
    "achievementAngles": [...],
    "atsKeywords": [...]
  }
}
```

**Success**: Re-queue same item with `pipeline_state.match_result`, `pipeline_stage='analyze'`
**Skipped**: Mark SKIPPED (terminal) if score < threshold
**Cost**: $0.015-$0.075/1K tokens (Claude Sonnet)

---

### Stage 4: JOB_SAVE

**Input**: All `pipeline_state` data (job_data, filter_result, match_result)

**Process**:

1. Reconstruct `JobMatchResult` from dict
2. Save to `job-matches` Firestore collection:
   ```json
   {
     "url": "...",
     "title": "...",
     "company": "...",
     "companyId": "company-doc-id",
     "location": "...",
     "description": "...",
     "matchScore": 87,
     "applicationPriority": "High",
     "matchedSkills": [...],
     "skillGaps": [...],
     "resumeIntakeData": {...},
     "createdAt": "2025-01-01T...",
     "status": "new"
   }
   ```
3. Log success with document ID

**Success**: Mark item SUCCESS (terminal - no further spawning)
**Failure**: Mark FAILED (retry up to 3 times)
**Cost**: $0 (Firestore write only)

---

## Scraper Instruction Schemas

Scraper instructions vary by source type and are stored in `job-sources` collection under the `config` field.

### Greenhouse (API)

```json
{
  "board_token": "netflix"
}
```

**Usage**: Fetch `https://boards-api.greenhouse.io/v1/boards/netflix/jobs`

---

### Workday (API)

```json
{
  "company_id": "netflix",
  "base_url": "https://netflix.wd1.myworkdayjobs.com"
}
```

**Usage**: Construct URLs for job listings and details

---

### RSS Feed

```json
{
  "url": "https://example.com/jobs.rss",
  "parse_format": "standard",
  "title_field": "title",
  "description_field": "description",
  "link_field": "link",
  "company_field": "company"
}
```

**Usage**: Parse with `feedparser`, extract items using field mappings

---

### Generic HTML (Selectors)

```json
{
  "url": "https://example.com/careers",
  "method": "requests",
  "selectors": {
    "job_list": ".job-card",
    "title": ".job-title",
    "company": ".company-name",
    "location": ".location",
    "description": ".description",
    "link": "a.apply-button[href]",
    "posted_date": ".date",
    "salary": ".salary"
  },
  "alternative_selectors": [
    {
      "title": ".alt-title",
      "description": ".alt-desc"
    }
  ],
  "pagination": {
    "next_button": ".next-page",
    "max_pages": 10
  }
}
```

**Usage**:

1. Fetch HTML with `requests` or `selenium` (if `method = "selenium"`)
2. Use primary `selectors` to extract job data
3. If primary fails, try `alternative_selectors` in order
4. Handle pagination if configured

**AI Discovery**: For new sources, use Claude Haiku to analyze HTML and suggest selectors

---

### API (Custom Endpoints)

```json
{
  "base_url": "https://api.example.com",
  "auth_type": "api_key",
  "api_key_env": "EXAMPLE_API_KEY",
  "endpoints": {
    "search": "/jobs/search",
    "details": "/jobs/{id}"
  },
  "headers": {
    "Accept": "application/json"
  },
  "params": {
    "remote": "true",
    "limit": 100
  }
}
```

**Usage**: Construct API requests with authentication, fetch JSON responses

**Note**: APIs requiring OAuth or manual account creation should be flagged for custom integration and implemented as dedicated scrapers.

---

## Error Handling

Every pipeline stage has consistent error handling:

### Retry Logic

- **Max retries**: 3 (configurable in queue settings)
- **On error**:
  1. Increment `retry_count`
  2. If `retry_count < max_retries`:
     - Reset status to PENDING
     - Add retry message: `"Processing failed. Will retry (1/3)"`
     - Keep error details for debugging
  3. If `retry_count >= max_retries`:
     - Mark as FAILED (terminal)
     - Add detailed failure message with troubleshooting steps

### Race Conditions

**Strategy**: Accept minor duplication risk for performance

- Firestore transactions guarantee atomicity for critical operations
- Queue deduplication catches most races:
  - Check URL not in queue before adding
  - Check URL not in job-matches before adding
- Spawn safety checks prevent loops but may allow duplicate analysis attempts
- **Trade-off**: Better performance vs 100% deduplication guarantee

### Source Health Tracking

**Auto-disable failing sources:**

1. Track `consecutiveFailures` counter per source
2. Increment on each scraping failure
3. Reset to 0 on successful scrape
4. **Auto-disable** after 5 consecutive failures
5. Require manual re-enable after auto-disable

**Purpose**: Prevent wasting resources on broken scrapers while allowing transient failures

### Terminal State Handling

Once an item reaches a terminal state, it cannot be re-processed in the same lineage:

- **FILTERED**: Job failed strike-based filters (no retry)
- **SKIPPED**: Job below match threshold or duplicate (no retry)
- **FAILED**: Error after max retries (requires manual intervention)
- **SUCCESS (final)**: Completed SAVE stage (no further processing)

**Non-terminal SUCCESS**: Intermediate stages (SCRAPE, FILTER, ANALYZE) mark SUCCESS then spawn next stage

---

## Processing Notes

### Queue Priority

- **Current**: FIFO by `created_at` (oldest first)
- **Future optimization**: Prioritize S/A tier companies
  - Could batch process by tier
  - Balance between priority and fairness

### Stop Lists

**Early rejection before scraping:**

- Excluded companies: Match against configured stop list
- Excluded domains: Block entire domains (e.g., competitors)
- Excluded keywords: Filter by patterns in URL/title

**Location**: `config/config.yaml` under `filters.stopList`

### Performance Optimization

**Current approach** (serial processing):

- Company analysis: Fetch → extract → analyze → save (one at a time)
- Simpler coordination, atomic operations
- All-or-nothing success

**Future optimization** (TODO in code):

```python
# TODO: Consider parallelizing company parameter fetches (size, location, etc.)
# Could spawn multiple queue items:
#   - COMPANY_SIZE (web search for employee count)
#   - COMPANY_LOCATION (web search for offices)
#   - COMPANY_CULTURE (scrape about page)
#   - COMPANY_JOB_BOARD (scrape careers page)
# Benefits: Parallel processing, fine-grained retry
# Trade-offs: Complex coordination, partial success handling
# Decision: Start with serial, optimize if it becomes a bottleneck
```

---

## Summary

This decision tree provides a comprehensive framework for processing companies, job sources, and job listings through a queue-based system. Key design principles:

1. **Safety First**: Loop prevention mechanisms protect against infinite recursion
2. **Cost Optimization**: Cheap models for scraping, expensive only for analysis
3. **Clean Data**: Create records immediately with known info, fill in after analysis
4. **Graceful Degradation**: Retry logic, health tracking, and terminal states handle failures
5. **Clear Thresholds**: Quantitative criteria for data quality and match scoring
6. **Future-Proof**: TODO markers for optimization opportunities without over-engineering

**Remember**: Any failed scrape should save data as "unknown" to flag it for inspection.
