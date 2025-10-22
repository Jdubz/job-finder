# Test Entity List (From Production Data)

This document lists real companies and job sources from production to use for manual and automated testing of the decision tree logic.

## Production Data Summary

- **Total Companies**: 19
- **Total Job Sources**: 25
- **Source Types**: Greenhouse (13), RSS (4), API (3), Company-page (3), Unknown (2)
- **Companies by Tier**:
  - S Tier (150+): 1 company
  - A Tier (100-149): 5 companies
  - B Tier (70-99): 5 companies
  - C Tier (50-69): 5 companies
  - Unknown: 3 companies

---

## Test Entities by Category

### Category 1: Companies with Greenhouse Sources (High Confidence)

These companies have known Greenhouse job boards that can be reliably scraped.

#### 1.1 S Tier - Highest Priority

| Company | Website | Priority Score | Tech Stack | Has Portland Office | Source Type |
|---------|---------|---------------|------------|-------------------|-------------|
| **Coinbase** | https://www.coinbase.com | 106 | TypeScript, Node.js, React, Python, Kubernetes, Docker | ✅ Yes | Greenhouse (`coinbase`) |

**Test Cases**:
- [ ] Company already exists → verify no duplicate creation
- [ ] Source exists → verify scraping uses existing source
- [ ] Portland bonus → verify +50 points applied
- [ ] Tech stack alignment → verify scoring with user profile

---

#### 1.2 A Tier - High Priority

| Company | Website | Priority Score | Tech Stack | Source Type |
|---------|---------|---------------|------------|-------------|
| **MongoDB** | https://www.mongodb.com | 88 | MongoDB, Node.js, TypeScript, Python, Kubernetes, GCP, Docker | Greenhouse (`mongodb`) |
| **GitLab** | https://gitlab.com | 86 | TypeScript, React, Python, Kubernetes, GCP, Docker, Redis | Greenhouse (`gitlab`) |
| **Cloudflare** | https://www.cloudflare.com | 80 | TypeScript, Kubernetes, Docker | Greenhouse (`cloudflare`) |
| **Redis** | https://redis.io | 73 | Redis, Node.js, TypeScript, Python, Kubernetes, GCP, Docker | Greenhouse (`redis`) |
| **Twilio** | https://www.twilio.com | 71 | Node.js, TypeScript, Python, Kubernetes, PubSub, Docker | Greenhouse (`twilio`) |

**Test Cases**:
- [ ] Full pipeline: Company submission → analysis → source discovery → scraping
- [ ] Tech stack detection from company info
- [ ] Job filtering with strike-based engine
- [ ] AI matching with score calculations

---

#### 1.3 B Tier - Medium Priority

| Company | Website | Priority Score | Tech Stack | Source Type |
|---------|---------|---------------|------------|-------------|
| **Netflix** | https://www.netflix.com | 61 | React, Node.js, TypeScript, Python, Kubernetes, Docker | API (custom) |
| **Datadog** | https://www.datadoghq.com | 58 | Python, Kubernetes, GCP, Docker | Greenhouse (`datadog`) |
| **Databricks** | https://www.databricks.com | 53 | Python, Kubernetes, Docker | Greenhouse (`databricks`) |
| **Stripe** | https://stripe.com | 51 | TypeScript, React, Python, Kubernetes, Docker | API (custom) |
| **HashiCorp** | https://www.hashicorp.com | 50 | Kubernetes, GCP, Docker | Greenhouse (`hashicorp`) |

**Test Cases**:
- [ ] API-based sources (Netflix, Stripe) vs Greenhouse sources
- [ ] Medium priority scraping rotation
- [ ] Filter rejection paths (missing tech stack alignment)

---

#### 1.4 C Tier - Lower Priority

| Company | Website | Priority Score | Tech Stack | Source Type |
|---------|---------|---------------|------------|-------------|
| **Brex** | https://www.brex.com | 41 (disabled) | TypeScript, React, Python, Kubernetes, Docker | Greenhouse (`brex`) |
| **Grammarly** | https://www.grammarly.com | 41 (disabled) | TypeScript, React, Python, Docker | Greenhouse (`grammarly`) |
| **Waymo** | https://waymo.com | 38 (disabled) | Python, Kubernetes, Docker | Greenhouse (`waymo`) |
| **PagerDuty** | https://www.pagerduty.com | 38 (disabled) | TypeScript, Python, Kubernetes, Docker | Greenhouse (`pagerduty`) |
| **Scale AI** | https://scale.com | 38 | Python, Kubernetes, Docker | Greenhouse (`scaleai`) |

**Test Cases**:
- [ ] Disabled sources → verify not scraped in rotation
- [ ] Source health tracking → test consecutive failures
- [ ] Lower priority queuing

---

### Category 2: Companies with Custom API Sources

These companies use custom APIs requiring specialized scrapers.

| Company | Website | Source Type | Config | Enabled |
|---------|---------|-------------|--------|---------|
| **Netflix** | https://www.netflix.com | API (custom) | `api_endpoint`: explore.jobs.netflix.net/api/careers | ✅ Yes |
| **Stripe** | https://stripe.com | API (custom) | `api_endpoint`: stripe.com/jobs/search | ❌ No |

**Test Cases**:
- [ ] API endpoint validation
- [ ] JSON response parsing
- [ ] Rate limiting handling
- [ ] Authentication (if required)

---

### Category 3: Companies with HTML Scraping (Company-Page)

These companies require HTML scraping with CSS selectors.

| Company | Website | Source Type | Method | Enabled |
|---------|---------|-------------|--------|---------|
| **Shopify** | https://www.shopify.com | company-page | scraper (selectors) | ❌ No |

**Test Cases**:
- [ ] AI selector discovery for new pages
- [ ] Selector validation and fallback
- [ ] Pagination handling
- [ ] Dynamic content loading

---

### Category 4: Companies Without Sources (Discovery Needed)

These companies exist but have no configured job sources.

| Company | Website | Priority Score | Tech Stack | Notes |
|---------|---------|---------------|------------|-------|
| **Shopify** | https://www.shopify.com | 0 | Unknown | Has "about" info, needs analysis |
| **New Relic** | (no website) | 0 | Unknown | Incomplete data |
| **Deepgram** | (no website) | 0 | Unknown | Empty source config |

**Test Cases**:
- [ ] Company analysis → job board discovery
- [ ] SOURCE_DISCOVERY spawning
- [ ] Low confidence source handling
- [ ] Manual validation requirement

---

### Category 5: RSS Feed Sources (Multi-Company)

These sources aggregate jobs from multiple companies.

| Source Name | URL | Parse Format | Enabled |
|-------------|-----|--------------|---------|
| **We Work Remotely - Full Stack** | weworkremotely.com/.../full-stack-programming-jobs.rss | Standard | ✅ Yes |
| **We Work Remotely - Programming** | weworkremotely.com/.../remote-programming-jobs.rss | Standard | ✅ Yes |
| **Remotive - Software Development** | remotive.com/remote-jobs/software-dev/feed | Standard | ✅ Yes |

**Test Cases**:
- [ ] RSS feed parsing
- [ ] Company extraction from job title
- [ ] Multiple companies per source
- [ ] Feed updates and polling

---

### Category 6: Third-Party API Sources

External job aggregator APIs.

| Source Name | API Type | Auth Required | Rate Limit | Enabled |
|-------------|----------|---------------|------------|---------|
| **RemoteOK API** | Public JSON | No | Unknown | ✅ Yes |
| **Adzuna Job Search API** | API Key | Yes | Free tier | ❌ No |

**Test Cases**:
- [ ] External API integration
- [ ] Auth key management
- [ ] Rate limit handling
- [ ] Response format parsing

---

## Test Scenarios by Entity Type

### A. Company Testing

#### Scenario A1: New Company Submission (Full Pipeline)
**Company**: Coinbase (S Tier, Portland office)

**Steps**:
1. Submit company → COMPANY_FETCH
2. Fetch about/careers pages → COMPANY_EXTRACT
3. Extract company info (AI) → COMPANY_ANALYZE
4. Detect tech stack + job board → COMPANY_SAVE
5. Verify: Company document created
6. Verify: SOURCE_DISCOVERY spawned for Greenhouse

**Expected**:
- ✅ Company created with tier "S", score 106
- ✅ Portland office detected (+50 points)
- ✅ Greenhouse source discovered
- ✅ SOURCE_DISCOVERY queue item created

---

#### Scenario A2: Company With Insufficient Data (SKIPPED)
**Company**: New Relic (no website, incomplete)

**Steps**:
1. Submit company → COMPANY_FETCH
2. Fetch fails (no website) → retry
3. Max retries exceeded → FAILED OR
4. Minimal data extracted → COMPANY_ANALYZE
5. Analysis determines insufficient → SKIPPED

**Expected**:
- ⚠️ Status: FAILED (fetch) or SKIPPED (insufficient data)
- 📝 Result message explains issue

---

#### Scenario A3: Existing Company Re-Analysis
**Company**: GitLab (already exists)

**Steps**:
1. Check if company exists → YES
2. Check data completeness → threshold met
3. Check last updated → < 30 days ago
4. Decision: Skip re-analysis

**Expected**:
- ⏭️ No new queue item created
- ✅ Existing company data used

---

### B. Job Source Testing

#### Scenario B1: High Confidence Source (Greenhouse)
**Source**: MongoDB Greenhouse

**Steps**:
1. Submit SOURCE_DISCOVERY
2. Detect type: Greenhouse
3. Extract board_token: "mongodb"
4. Validate via API: fetch jobs
5. Create source with enabled=true

**Expected**:
- ✅ Source created and enabled
- ✅ Confidence: "high"
- ✅ Ready for immediate scraping

---

#### Scenario B2: Medium Confidence Source (Workday)
**Source**: (Example - not in prod data)

**Steps**:
1. Submit SOURCE_DISCOVERY
2. Detect type: Workday
3. Extract company_id from URL
4. Validation: basic URL check (no full scrape)
5. Create source with enabled=false, validation_required=true

**Expected**:
- ⚠️ Source created but disabled
- ⚠️ Confidence: "medium"
- 📝 Flagged for manual validation

---

#### Scenario B3: Low Confidence Source (Generic HTML)
**Source**: Shopify careers page

**Steps**:
1. Submit SOURCE_DISCOVERY
2. Detect type: generic HTML
3. Use AI to discover selectors
4. Test scrape with discovered selectors
5. If successful → create source (enabled=false)
6. If failed → mark FAILED

**Expected**:
- ⚠️ Source created but disabled
- ⚠️ Confidence: "low"
- 🤖 AI-discovered selectors saved
- 📝 Requires test scrape validation

---

### C. Job Listing Testing

#### Scenario C1: Happy Path (Full Pipeline)
**Source**: Coinbase Greenhouse
**Expected**: High-scoring remote job

**Steps**:
1. Submit job URL → JOB_SCRAPE
2. Extract job data using source config
3. Job scraped → JOB_FILTER
4. Strikes calculated (0-4) → pass
5. Filter passed → JOB_ANALYZE
6. AI matching: score 87 → JOB_SAVE
7. Match created in Firestore

**Expected**:
- ✅ Job match document created
- ✅ Score ≥ 80
- ✅ Resume intake data populated
- ✅ All pipeline stages successful

---

#### Scenario C2: Hard Rejection (Excluded Company)
**Company**: (Add to stop list first)

**Steps**:
1. Submit job URL → JOB_SCRAPE
2. Check stop list → company excluded
3. Mark FILTERED immediately (no scraping)

**Expected**:
- ⏹️ Status: FILTERED
- 📝 Reason: "Excluded by stop list"
- ⚠️ No FILTER stage spawned

---

#### Scenario C3: Filter Rejection (5+ Strikes)
**Job**: Non-remote, junior level, missing primary skills

**Steps**:
1. Submit job URL → JOB_SCRAPE
2. Job scraped successfully
3. Filter evaluation:
   - Non-remote location: +3 strikes
   - Seniority mismatch: +2 strikes
   - Missing React: +3 strikes
   - **Total: 8 strikes (threshold: 5)**
4. Mark FILTERED

**Expected**:
- ⏹️ Status: FILTERED
- 📝 Reason: "8 strikes (threshold: 5)"
- ⚠️ No ANALYZE stage spawned
- 💰 Cost: $0 (no AI used)

---

#### Scenario C4: Score Rejection (Below Threshold)
**Job**: Marginal fit, score 65

**Steps**:
1. Submit job → JOB_SCRAPE → success
2. JOB_FILTER → pass (4 strikes)
3. JOB_ANALYZE → AI scoring
4. Match score: 65 (threshold: 80)
5. Mark SKIPPED

**Expected**:
- ⏹️ Status: SKIPPED
- 📝 Reason: "Match score 65 below threshold 80"
- ⚠️ No SAVE stage spawned
- 💰 Cost: ~$0.02-0.075 (AI used for analysis)

---

#### Scenario C5: Scrape Failure (Retry Logic)
**Job**: Invalid URL or changed page structure

**Steps**:
1. Submit job → JOB_SCRAPE
2. Scraping fails (selector not found)
3. Retry 1/3 → PENDING
4. Retry 2/3 → PENDING
5. Retry 3/3 → FAILED

**Expected**:
- ⏹️ Status: FAILED (after 3 retries)
- 📝 Error details saved
- 🔧 Source health tracking updated (consecutive failure)

---

## Test Execution Plan

### Phase 1: Single Entity Tests (Manual)
Test each entity type individually to verify pipeline stages.

**Companies**:
- [ ] Coinbase (S tier, Portland, Greenhouse)
- [ ] MongoDB (A tier, high tech alignment)
- [ ] Netflix (B tier, custom API)
- [ ] New Relic (incomplete data)

**Job Sources**:
- [ ] GitLab Greenhouse (high confidence)
- [ ] Shopify careers page (low confidence, requires AI discovery)
- [ ] RemoteOK API (external aggregator)

**Jobs**:
- [ ] Happy path: Coinbase remote senior engineer
- [ ] Filter rejection: Junior, non-remote, missing skills
- [ ] Score rejection: Marginal fit
- [ ] Scrape failure: Invalid URL

---

### Phase 2: Decision Tree Path Coverage (Manual)

Test all decision tree paths systematically:

**Company Paths**:
- [ ] FETCH → EXTRACT → ANALYZE → SAVE (success)
- [ ] FETCH → retry → FAILED
- [ ] EXTRACT → ANALYZE → SKIPPED (insufficient data)

**Job Source Paths**:
- [ ] High confidence → enabled
- [ ] Medium confidence → validation required
- [ ] Low confidence → AI discovery

**Job Paths**:
- [ ] SCRAPE → FILTER → ANALYZE → SAVE (happy)
- [ ] SCRAPE → stop (hard rejection)
- [ ] SCRAPE → FILTER → FILTERED (strikes)
- [ ] SCRAPE → FILTER → ANALYZE → SKIPPED (score)
- [ ] SCRAPE → retry → FAILED

---

### Phase 3: Complete Chain Tests (Manual)

Test full discovery chains:
- [ ] **Chain 1**: Company → Source → Jobs → Matches
  - Submit: Databricks
  - Expect: Company analysis → Greenhouse discovered → scrape → 2+ matches
- [ ] **Chain 2**: RSS Feed → Multiple Companies → Matches
  - Submit: We Work Remotely SCRAPE
  - Expect: 10+ jobs → multiple companies → filtered → matches
- [ ] **Chain 3**: Existing Company → Existing Source → New Jobs
  - Submit: Coinbase (already exists)
  - Expect: Use existing data → scrape source → new jobs only

---

### Phase 4: Automated E2E Tests

Convert manual tests to automated scenarios:
- [ ] scenario_06_job_hard_rejection.py
- [ ] scenario_07_job_strike_filtering.py
- [ ] scenario_08_job_low_score.py
- [ ] scenario_09_company_insufficient_data.py
- [ ] scenario_10_source_low_confidence.py
- [ ] scenario_11_pipeline_retry_logic.py
- [ ] scenario_12_all_rejection_paths.py

---

## Quick Reference: Test Entity URLs

### Companies (for manual submission)
```python
# S Tier
coinbase = {"name": "Coinbase Careers", "website": "https://www.coinbase.com"}

# A Tier
mongodb = {"name": "MongoDB Careers", "website": "https://www.mongodb.com"}
gitlab = {"name": "GitLab Careers", "website": "https://gitlab.com"}
cloudflare = {"name": "Cloudflare Careers", "website": "https://www.cloudflare.com"}

# B Tier
netflix = {"name": "Netflix Careers", "website": "https://www.netflix.com"}
stripe = {"name": "Stripe Careers", "website": "https://stripe.com"}
```

### Job Sources (for manual scraping)
```python
# Greenhouse (high confidence)
greenhouse_sources = [
    "https://boards.greenhouse.io/coinbase",
    "https://boards.greenhouse.io/mongodb",
    "https://boards.greenhouse.io/gitlab",
    "https://boards.greenhouse.io/cloudflare",
]

# RSS Feeds
rss_sources = [
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "https://remotive.com/remote-jobs/software-dev/feed",
]

# APIs
api_sources = [
    "https://explore.jobs.netflix.net/api/careers",
    "https://remoteok.com/api",
]
```

### Individual Jobs (for testing)
**Note**: Use actual job URLs from sources above. Examples:
```python
# From Greenhouse boards
coinbase_job = "https://boards.greenhouse.io/coinbase/jobs/123456"
gitlab_job = "https://boards.greenhouse.io/gitlab/jobs/789012"

# From Netflix API
netflix_job = "https://explore.jobs.netflix.net/careers/job/123456"

# From RSS feeds (extracted from feed)
remote_job = "https://weworkremotely.com/remote-jobs/example-123"
```

---

## Success Criteria

### Coverage Goals
- [ ] 100% company pipeline stages tested
- [ ] 100% job source types tested (Greenhouse, RSS, API, HTML)
- [ ] 100% job pipeline paths tested (happy + all rejections)
- [ ] All 5 rejection types verified (stop list, hard rejection, filter, score, failure)
- [ ] All retry logic tested (3 retries per entity type)

### Quality Goals
- [ ] All production companies processable
- [ ] All production sources scrapable (or correctly disabled)
- [ ] Decision tree paths documented with examples
- [ ] Edge cases identified and handled
- [ ] Test scenarios automated

---

**Last Updated**: 2025-10-22
**Data Source**: `/job-finder-worker/test_results/e2e_quick_1760854855/production_snapshot/`
