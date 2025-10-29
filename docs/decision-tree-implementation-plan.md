# Decision Tree Implementation Plan

This document outlines the plan to fully implement the decision tree architecture documented in `decision-tree.md`.

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Implementation Gaps](#implementation-gaps)
3. [New Queue Item Types](#new-queue-item-types)
4. [Data Structure Changes](#data-structure-changes)
5. [Implementation Phases](#implementation-phases)
6. [Testing Strategy](#testing-strategy)

---

## Current State Analysis

### ✅ Already Implemented

#### 1. Job Pipeline (SCRAPE → FILTER → ANALYZE → SAVE)

**Location**: `processor.py` lines 851-1111
**Status**: ✅ **COMPLETE**

- Uses state-based routing (checks `pipeline_state` for next action)
- Four stages fully implemented:
  - `_do_job_scrape()`: Fetch job data from URL
  - `_do_job_filter()`: Strike-based filtering
  - `_do_job_analyze()`: AI matching with profile
  - `_do_job_save()`: Save to job-matches collection
- Cost optimization: Cheap AI for scrape, expensive for analysis

#### 2. Company Pipeline (FETCH → EXTRACT → ANALYZE → SAVE)

**Location**: `processor.py` lines 1119-1519
**Status**: ✅ **COMPLETE**

- Uses `company_sub_task` enum for explicit stage tracking
- Four stages fully implemented:
  - `_process_company_fetch()`: Fetch HTML from multiple pages
  - `_process_company_extract()`: AI extraction of company info
  - `_process_company_analyze()`: Tech stack, job board discovery, priority scoring
  - `_process_company_save()`: Save to companies collection, spawn SOURCE_DISCOVERY
- Spawning logic: High confidence job boards auto-spawn SOURCE_DISCOVERY

#### 3. Source Discovery

**Location**: `processor.py` lines 1032-1111
**Status**: ✅ **COMPLETE**

- Handles Greenhouse, Workday, RSS, Generic sources
- Type detection, validation, configuration
- Creates `job-sources` documents with appropriate confidence levels

#### 4. Loop Prevention

**Location**: `manager.py` lines 653-799
**Status**: ✅ **COMPLETE**

- `tracking_id`: UUID for lineage grouping
- `ancestry_chain`: Parent document ID list
- `spawn_depth`: Recursion depth counter (max: 10)
- `can_spawn_item()`: 4-check validation
- `spawn_item_safely()`: Safe spawning wrapper

#### 5. Source Health Tracking

**Location**: `job_sources_manager.py` lines 669-751
**Status**: ✅ **COMPLETE**

- `consecutiveFailures` counter
- `record_scraping_failure()` / `record_scraping_success()`
- Auto-disable after 5 consecutive failures

#### 6. Strike-Based Filtering

**Location**: `filters/strike_filter_engine.py`
**Status**: ✅ **COMPLETE**

- Hard rejections (immediate fail)
- Strike accumulation (threshold: 5)
- Filter result tracking with rejection reasons

---

## Implementation Gaps

### ❌ Gap 1: Job → Company Spawning

**Current Behavior** (`processor.py:1034-1038`):

```python
company = self.companies_manager.get_or_create_company(
    company_name=company_name,
    company_website=company_website,
    fetch_info_func=self.company_info_fetcher.fetch_company_info,
)
```

Creates company record **inline** with basic scraping. No queue item spawned.

**Problem**:

- Company gets minimal info (about/culture scraped inline)
- No tech stack detection
- No priority scoring
- No job board discovery
- Blocks job analysis until company fetch completes

**Decision Tree Requirement**:
When processing a job with unknown company → Spawn COMPANY_FETCH item for full analysis

**Impact**: Medium priority - Current approach works but misses optimization opportunities

---

### ❌ Gap 2: Record Status Tracking

**Current State**: Companies and sources lack status field

**Decision Tree Requirement**:

- `status: "analyzing"` - Currently being processed
- `status: "pending_validation"` - Awaiting manual approval
- `status: "active"` - Validated and ready for use
- `status: "failed"` - Analysis failed permanently

**Required Changes**:

1. Add `status` field to companies collection
2. Add `status` field to job-sources collection (already has `enabled` boolean)
3. Update status at each pipeline stage
4. Query by status for monitoring dashboards

**Impact**: Low priority - Nice-to-have for visibility

---

### ❌ Gap 3: Data Quality Thresholds

**Current Behavior** (`companies_manager.py:233-240`):

```python
has_about = len(company.get("about", "")) > 100
has_culture = len(company.get("culture", "")) > 50

if has_about or has_culture:
    logger.info(f"Using cached company info for {company_name}")
    return company
```

Checks exist but **not comprehensive**.

**Decision Tree Requirement**:

```python
# Before re-analyzing company
def should_reanalyze_company(company_data):
    # Check completeness threshold
    is_minimal = (about > 50 or culture > 25)
    is_good = (about > 100 and culture > 50)

    # Check freshness
    updated_at = company_data.get("updatedAt")
    is_stale = (now - updated_at) > 30 days

    # Re-analyze if sparse OR stale
    return (not is_good) or is_stale
```

**Impact**: Medium priority - Prevents redundant AI calls

---

### ❌ Gap 4: Job Board Confidence Level Handling

**Current Behavior** (`processor.py:1423-1450`):

```python
# Spawn SOURCE_DISCOVERY if job board found
if job_board_url and job_board_url != company_website:
    self._spawn_source_discovery(...)
```

Always spawns, regardless of confidence.

**Decision Tree Requirement**:

- **High confidence** (Greenhouse, RSS): Auto-spawn SOURCE_DISCOVERY
- **Medium confidence** (Workday, Lever): Store as metadata, require approval
- **Low confidence** (Generic HTML): Store as metadata, require validation

**Required Changes**:

1. Return confidence level from job board detection
2. Conditional spawning based on confidence
3. Store low/medium confidence URLs in company metadata for manual review

**Impact**: Medium priority - Prevents false positive source creation

---

### ❌ Gap 5: Source Scraping Queue Items

**Current State**: No queue item type for "scrape this specific source"

**Decision Tree Implication**:
When a job source is discovered and validated, we need a way to:

1. Schedule scraping for that source
2. Track scraping progress
3. Handle failures per source

**Potential Solution**: New queue item type `SCRAPE_SOURCE`

```python
{
  "type": "scrape_source",
  "source_id": "job-source-doc-id",
  "url": "https://boards.greenhouse.io/netflix",
  "source_type": "greenhouse",
  "config": { "board_token": "netflix" }
}
```

**Impact**: High priority - Enables automated source scraping workflow

---

## New Queue Item Types

### Option A: Add SCRAPE_SOURCE Type

**Pros**:

- Explicit queue item for source scraping
- Easy to track scraping jobs per source
- Can implement priority by source tier (S/A/B/C/D)

**Cons**:

- New type requires TypeScript shared-types update
- Additional code paths in processor
- More complex than current SCRAPE type

**Schema**:

```typescript
// In job-finder-shared-types/src/queue.types.ts
export type QueueItemType =
  | "job"
  | "company"
  | "scrape"
  | "source_discovery"
  | "scrape_source"; // NEW

export interface ScrapeSourceQueueItem extends BaseQueueItem {
  type: "scrape_source";
  source_id: string; // Reference to job-sources document
  url: string; // Source URL to scrape
  source_type: SourceType; // greenhouse, rss, workday, etc.
  config: Record<string, any>; // Source-specific config
  tier?: "S" | "A" | "B" | "C" | "D"; // Priority tier
}
```

---

### Option B: Reuse SCRAPE Type with source_id

**Pros**:

- No TypeScript changes needed
- Reuses existing SCRAPE handler
- Simpler implementation

**Cons**:

- Less explicit
- Harder to distinguish manual scrapes from source-based
- Mixing concerns in one type

**Schema**:

```typescript
// Extend existing SCRAPE type
export interface ScrapeQueueItem extends BaseQueueItem {
  type: "scrape";
  url: string;
  source_id?: string; // If provided, scrape comes from source
  company_name?: string;
  company_id?: string;
}
```

---

### Recommendation: Option A (SCRAPE_SOURCE)

**Rationale**:

- Clearer separation of concerns
- Enables source-specific handling (priority, scheduling, health tracking)
- Better observability (can query for all source scraping jobs)
- Supports future features like tier-based batching

---

## Data Structure Changes

### 1. Companies Collection - Add Status Field

**Current Schema**:

```typescript
{
  name: string;
  website: string;
  about: string;
  culture: string;
  // ... other fields
}
```

**New Schema**:

```typescript
{
  name: string;
  website: string;
  about: string;
  culture: string;
  // NEW FIELDS
  status: "pending" | "analyzing" | "active" | "failed";
  analysis_progress?: {
    fetch: boolean;
    extract: boolean;
    analyze: boolean;
    save: boolean;
  };
  last_analyzed_at?: Timestamp;
  // ... other fields
}
```

**Migration**: Add status="active" to existing companies, analysis_progress can be null

---

### 2. Job-Sources Collection - Enhance Status

**Current Schema**:

```typescript
{
  enabled: boolean;
  discoveryConfidence: "high" | "medium" | "low";
  consecutiveFailures: number;
  // ... other fields
}
```

**New Schema**:

```typescript
{
  enabled: boolean;
  status: "pending_validation" | "active" | "disabled" | "failed";  // NEW
  discoveryConfidence: "high" | "medium" | "low";
  consecutiveFailures: number;
  // NEW FIELDS
  validation_required: boolean;
  auto_enabled: boolean;  // Auto-enabled vs manual
  scraping_schedule?: {
    frequency: "hourly" | "daily" | "weekly";
    last_scraped_at: Timestamp;
    next_scrape_at: Timestamp;
  };
  // ... other fields
}
```

**Migration**: Convert enabled → status mapping:

- `enabled: true` → `status: "active"`
- `enabled: false` → `status: "disabled"`

---

### 3. Queue Item Model - Add SCRAPE_SOURCE

**File**: `queue/models.py`

```python
class QueueItemType(str, Enum):
    JOB = "job"
    COMPANY = "company"
    SCRAPE = "scrape"
    SOURCE_DISCOVERY = "source_discovery"
    SCRAPE_SOURCE = "scrape_source"  # NEW


class SourceTier(str, Enum):
    """Priority tier for source scraping."""
    S = "S"  # 150+ points
    A = "A"  # 100-149
    B = "B"  # 70-99
    C = "C"  # 50-69
    D = "D"  # 0-49


class JobQueueItem(BaseModel):
    # ... existing fields ...

    # NEW: For scrape_source items
    source_id: Optional[str] = None
    source_type: Optional[str] = None
    source_config: Optional[Dict[str, Any]] = None
    source_tier: Optional[SourceTier] = None
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)

**Goal**: Add missing data structures and status tracking

#### Tasks:

1. **Update shared-types** (TypeScript)
   - [ ] Add `SCRAPE_SOURCE` to QueueItemType enum
   - [ ] Create `ScrapeSourceQueueItem` interface
   - [ ] Add status enums for companies and sources
   - [ ] Publish new npm version

2. **Update Python models** (`queue/models.py`)
   - [ ] Add `SCRAPE_SOURCE` to QueueItemType enum
   - [ ] Add `SourceTier` enum
   - [ ] Add new fields to `JobQueueItem`

3. **Add status tracking** (`companies_manager.py`, `job_sources_manager.py`)
   - [ ] Add `status` parameter to `save_company()`
   - [ ] Add `update_company_status()` method
   - [ ] Add `update_source_status()` method
   - [ ] Migration script: Add status="active" to existing records

**Deliverables**:

- Updated type definitions
- Database migration script
- Status tracking methods

---

### Phase 2: Job → Company Spawning (Week 2)

**Goal**: Spawn COMPANY items when encountering unknown companies during job analysis

#### Tasks:

1. **Add company spawning logic** (`processor.py:_do_job_analyze()`)
   - [ ] Check if company exists in DB
   - [ ] Check if company has "good" data quality (threshold check)
   - [ ] If missing or sparse → Spawn COMPANY_FETCH item
   - [ ] If existing and good → Use cached data (current behavior)
   - [ ] Link spawned COMPANY item to job via tracking_id

2. **Modify company creation** (`companies_manager.py`)
   - [ ] Add `create_company_stub()` method
     - Creates minimal record with name + website + status="analyzing"
     - Returns company_id immediately
     - Does NOT fetch full info
   - [ ] Update `get_or_create_company()` to use stub if queue mode

3. **Handle async company data** (`processor.py`)
   - [ ] Job ANALYZE stage: Check if company is being analyzed
   - [ ] If status="analyzing" → Mark job as PENDING, retry later
   - [ ] If status="active" → Proceed with analysis

**Deliverables**:

- Company spawning logic
- Stub company creation
- Async handling for pending companies

**Testing**:

- E2E test: Submit job with unknown company → Verify COMPANY_FETCH spawned
- E2E test: Job waits for company analysis to complete
- E2E test: Multiple jobs for same company don't spawn duplicates

---

### Phase 3: Source Scraping Workflow (Week 3)

**Goal**: Implement SCRAPE_SOURCE queue items for automated source scraping

#### Tasks:

1. **Add processor handler** (`processor.py`)
   - [ ] Implement `_process_scrape_source()` method
   - [ ] Fetch source config from job-sources collection
   - [ ] Dispatch to source-specific scraper:
     - Greenhouse: Use API scraper
     - Workday: Use Workday scraper
     - RSS: Use feed parser
     - Generic: Use selector-based scraper
   - [ ] Submit found jobs via `ScraperIntake.submit_jobs()`
   - [ ] Update source health tracking (success/failure)

2. **Add source scheduler** (new module: `queue/source_scheduler.py`)
   - [ ] Query active sources from job-sources
   - [ ] Filter by tier (prioritize S/A)
   - [ ] Check last_scraped_at to avoid too-frequent scraping
   - [ ] Create SCRAPE_SOURCE queue items
   - [ ] Track scheduling in source document

3. **Integrate with COMPANY_SAVE** (`processor.py:_process_company_save()`)
   - [ ] After spawning SOURCE_DISCOVERY for high confidence
   - [ ] Once source is created and enabled
   - [ ] Immediately spawn first SCRAPE_SOURCE item

**Deliverables**:

- SCRAPE_SOURCE processor
- Source scheduler
- Integration with company pipeline

**Testing**:

- E2E test: Company analysis discovers Greenhouse board → SOURCE_DISCOVERY → SCRAPE_SOURCE → Jobs
- E2E test: Scheduler creates SCRAPE_SOURCE for active sources
- E2E test: Failed source scrapes update health tracking

---

### Phase 4: Confidence-Based Source Handling (Week 4)

**Goal**: Differentiate handling by source confidence level

#### Tasks:

1. **Enhance job board detection** (`processor.py:_detect_job_board()`)
   - [ ] Return tuple: `(url, confidence_level)`
   - [ ] High: Greenhouse API URLs, valid RSS feeds
   - [ ] Medium: Workday, Lever (need validation)
   - [ ] Low: Generic career page URLs

2. **Conditional spawning** (`processor.py:_process_company_save()`)

   ```python
   if confidence == "high":
       # Spawn SOURCE_DISCOVERY immediately
       spawn_source_discovery(url, company_id, auto_enable=True)
   elif confidence == "medium":
       # Store as metadata, manual approval
       save_company({
           ...existing_data,
           "pending_job_boards": [
               {"url": url, "confidence": "medium", "requires_validation": True}
           ]
       })
   else:  # low
       # Just log, don't spawn
       logger.info(f"Low confidence job board detected: {url}")
   ```

3. **Add validation UI hooks** (backend only - FE implementation separate)
   - [ ] Add `get_companies_pending_validation()` query
   - [ ] Add `approve_job_board(company_id, url)` method → Spawns SOURCE_DISCOVERY

**Deliverables**:

- Confidence-based detection
- Conditional spawning logic
- Validation API methods

**Testing**:

- Unit test: Greenhouse URL → high confidence
- Unit test: Generic URL → low confidence
- E2E test: High confidence auto-spawns
- E2E test: Medium confidence stores metadata

---

### Phase 5: Data Quality & Optimization (Week 5)

**Goal**: Implement threshold checks and prevent redundant analysis

#### Tasks:

1. **Add quality assessment** (`companies_manager.py`)

   ```python
   def assess_company_quality(company_data):
       """Return quality level: minimal, good, excellent."""
       about_len = len(company_data.get("about", ""))
       culture_len = len(company_data.get("culture", ""))

       if about_len > 200 and culture_len > 100 and "mission" in company_data:
           return "excellent"
       elif about_len > 100 and culture_len > 50:
           return "good"
       elif about_len > 50 or culture_len > 25:
           return "minimal"
       else:
           return "poor"

   def should_reanalyze_company(company_data):
       """Check if company needs re-analysis."""
       quality = assess_company_quality(company_data)

       # Poor/minimal always re-analyze
       if quality in ["poor", "minimal"]:
           return True

       # Good/excellent: Check freshness
       updated_at = company_data.get("updatedAt")
       if not updated_at:
           return True

       age_days = (datetime.now() - updated_at).days
       return age_days > 30  # Re-analyze if > 30 days old
   ```

2. **Integrate threshold checks** (`processor.py`, `scraper_intake.py`)
   - [ ] Before spawning COMPANY_FETCH: Check if company meets threshold
   - [ ] Before creating company stub: Check if existing company is stale
   - [ ] Log skip reason: "Company data is good and fresh, skipping re-analysis"

3. **Add metrics tracking**
   - [ ] Log: Companies skipped due to good quality
   - [ ] Log: Companies re-analyzed due to staleness
   - [ ] Track: Average time between re-analysis

**Deliverables**:

- Quality assessment methods
- Threshold integration
- Metrics logging

**Testing**:

- Unit test: Quality levels correctly assessed
- Unit test: 29-day-old company not re-analyzed
- Unit test: 31-day-old company re-analyzed
- E2E test: Good company not spawned again

---

## Testing Strategy

### Unit Tests

**New files to create**:

1. `tests/queue/test_scrape_source_processing.py`
   - Test SCRAPE_SOURCE handler for each source type
   - Test health tracking updates
   - Test job submission from source scrapes

2. `tests/storage/test_company_status.py`
   - Test status transitions
   - Test quality assessment
   - Test threshold checks

3. `tests/queue/test_company_spawning.py`
   - Test job → company spawning logic
   - Test stub company creation
   - Test async company data handling

### E2E Tests

**New scenarios**:

1. **Full Company Discovery Flow**

   ```
   Submit Job (unknown company)
     → Job SCRAPE
     → Job FILTER
     → Job ANALYZE (spawns COMPANY_FETCH)
     → Job PENDING (waits for company)
     → Company FETCH/EXTRACT/ANALYZE/SAVE
     → Job ANALYZE (retries, now has company data)
     → Job SAVE
   ```

2. **Source Discovery to Scraping Flow**

   ```
   Submit Company
     → Company FETCH/EXTRACT/ANALYZE
     → Discovers Greenhouse board
     → Company SAVE (spawns SOURCE_DISCOVERY)
     → SOURCE_DISCOVERY (creates job-source)
     → Auto-spawn SCRAPE_SOURCE
     → SCRAPE_SOURCE (fetches jobs from Greenhouse)
     → Jobs submitted to queue
   ```

3. **Confidence Level Handling**
   ```
   Company with generic careers page
     → Low confidence detected
     → NO SOURCE_DISCOVERY spawned
     → Metadata stored for manual review
   ```

### Integration Tests

1. **Loop Prevention with Company Spawning**
   - Verify company spawning doesn't create loops
   - Test: Job A spawns Company → Company spawns Source → Source spawns Job B → Job B doesn't re-spawn Company

2. **Concurrent Company Requests**
   - Two jobs for same company submitted simultaneously
   - Only one COMPANY_FETCH should spawn
   - Both jobs should wait and reuse same company data

---

## Migration Plan

### Database Migrations

#### Migration 1: Add Status to Companies

```python
# scripts/migrations/001_add_company_status.py

from job_finder.storage.companies_manager import CompaniesManager

def migrate():
    manager = CompaniesManager(database_name="portfolio-staging")
    companies = manager.get_all_companies(limit=1000)

    for company in companies:
        if "status" not in company:
            manager.db.collection("companies").document(company["id"]).update({
                "status": "active",  # Existing companies assumed analyzed
                "last_analyzed_at": company.get("updatedAt"),
            })

    print(f"Migrated {len(companies)} companies")
```

#### Migration 2: Add Status to Job-Sources

```python
# scripts/migrations/002_add_source_status.py

from job_finder.storage.job_sources_manager import JobSourcesManager

def migrate():
    manager = JobSourcesManager(database_name="portfolio-staging")

    # Query all sources
    query = manager.db.collection("job-sources").stream()

    count = 0
    for doc in query:
        data = doc.to_dict()

        # Map enabled → status
        if data.get("enabled"):
            status = "active"
        else:
            status = "disabled"

        doc.reference.update({
            "status": status,
            "validation_required": data.get("discoveryConfidence") != "high",
            "auto_enabled": data.get("discoveredVia") == "automated_scan",
        })
        count += 1

    print(f"Migrated {count} job sources")
```

### Rollout Strategy

1. **Week 1**: Deploy Phase 1 (data structures only) to staging
   - Run migrations
   - Monitor for issues
   - No behavior changes yet

2. **Week 2**: Deploy Phase 2 (company spawning) to staging
   - Feature flag: `ENABLE_COMPANY_SPAWNING=true`
   - Test with subset of jobs
   - Monitor spawn rates, loop prevention

3. **Week 3**: Deploy Phase 3 (source scraping) to staging
   - Feature flag: `ENABLE_SOURCE_SCRAPING=true`
   - Start with tier S/A companies only
   - Monitor scraping health

4. **Week 4**: Deploy Phase 4 (confidence handling) to staging
   - All sources processed with confidence levels
   - Monitor validation queue

5. **Week 5**: Deploy all phases to production
   - Enable feature flags in production
   - Monitor costs (AI calls)
   - Monitor queue depth

---

## Risks & Mitigations

### Risk 1: Queue Depth Explosion

**Risk**: Spawning COMPANY and SCRAPE_SOURCE items significantly increases queue depth

**Mitigation**:

- Implement queue depth monitoring
- Add rate limiting: Max X new spawns per minute
- Prioritize completion over new spawns (process existing items first)

### Risk 2: AI Cost Increase

**Risk**: More company analysis = more AI calls = higher costs

**Mitigation**:

- Implement strict quality thresholds (prevent re-analysis of good data)
- Monitor daily AI spend
- Add budget alerts ($X/day threshold)
- Cache company data aggressively

### Risk 3: Circular Dependencies

**Risk**: Job → Company → Source → Job creates loops despite prevention

**Mitigation**:

- Existing loop prevention should handle this
- Add extensive E2E tests for circular cases
- Add alerts for spawn_depth > 5 (should never happen)
- Manual review of any blocked spawns

### Risk 4: Stale Data Handling

**Risk**: Jobs waiting for company analysis might timeout or get stale

**Mitigation**:

- Implement retry with exponential backoff
- Max wait time: 5 minutes before marking job as FAILED
- Alert on jobs stuck in PENDING state

---

## Success Metrics

### Phase 1

- ✅ All existing records migrated with status field
- ✅ Zero errors in staging for 48 hours

### Phase 2

- ✅ 90%+ of unknown companies spawn COMPANY items
- ✅ Company data quality improves (more complete fields)
- ✅ Zero circular dependencies detected

### Phase 3

- ✅ S/A tier sources scraped within 24 hours of discovery
- ✅ Source health tracking prevents repeated failures
- ✅ 80%+ of scrape attempts succeed

### Phase 4

- ✅ 95%+ high confidence sources auto-enabled
- ✅ 0% low confidence sources auto-enabled
- ✅ Medium confidence sources flagged for review

### Phase 5

- ✅ 70%+ reduction in redundant company analyses
- ✅ AI costs remain flat or decrease despite more features
- ✅ Cache hit rate > 60% for company data

---

## Next Steps

1. **Review & Approval**: Get stakeholder approval on this plan
2. **TypeScript PR**: Create PR in job-finder-shared-types for new queue types
3. **Feature Branch**: Create `feature/decision-tree-implementation` branch
4. **Phased Development**: Implement phases 1-5 over 5 weeks
5. **Continuous Testing**: Write tests alongside each phase
6. **Monitoring**: Set up dashboards for new metrics

---

## Conclusion

This implementation plan builds on the solid foundation already in place (job/company pipelines, loop prevention, health tracking) and adds the missing pieces to fully realize the decision tree architecture. Key improvements:

1. **Automated discovery flow**: Jobs → Companies → Sources → Jobs (full circle)
2. **Cost optimization**: Quality thresholds prevent redundant AI calls
3. **Better reliability**: Confidence-based handling reduces false positives
4. **Observability**: Status tracking and metrics for monitoring

Estimated **5 weeks** for full implementation with phased rollout to minimize risk.
