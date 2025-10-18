# State-Driven Pipeline Design

## Vision: Self-Healing, Intelligent Data Pipeline

Transform the current rigid, linear pipeline into an **intelligent, state-driven system** where each atomic operation examines the database state, performs its task, and dynamically decides what work needs to happen next.

**Related Documentation:**
- Loop Prevention: See `LOOP_PREVENTION_DESIGN.md` for details on preventing infinite loops and circular dependencies

## Current Architecture (Linear & Rigid)

```
Job Pipeline:
JOB_SCRAPE → JOB_FILTER → JOB_ANALYZE → JOB_SAVE
(Hardcoded sequence, no intelligence)

Company Pipeline:
COMPANY_FETCH → COMPANY_EXTRACT → COMPANY_ANALYZE → COMPANY_SAVE
(Hardcoded sequence, no intelligence)
```

**Problems:**
- ❌ Requires explicit `sub_task` field on every queue item
- ❌ Can't adapt to existing data state
- ❌ Can't discover missing data and fill it in
- ❌ Can't spawn related work (e.g., company discovery during job scraping)
- ❌ Fails if data is incomplete rather than fixing it

## New Architecture (State-Driven & Intelligent)

```
Queue Item Types:
- JOB: Process a job posting URL
- COMPANY: Process a company
- SOURCE_DISCOVERY: Discover job boards on company website

Each processor:
1. Reads current database state
2. Determines what data is missing
3. Performs ONE atomic operation
4. Writes results to database
5. Spawns next queue items based on what's needed
```

### Example: Job Processing Flow

```python
# Queue Item: { type: "JOB", url: "https://stripe.com/jobs/12345" }

def process_job(item):
    """
    Smart job processor that adapts to current state.
    """
    
    # 1. READ STATE: Check what we already have
    job_doc = firestore.get_job_by_url(item.url)
    company = extract_company_from_url(item.url)
    company_doc = firestore.get_company(company.name)
    
    # 2. DECISION TREE: What needs to happen?
    
    # Missing company data? Spawn company scraper first
    if not company_doc or company_doc.needs_refresh():
        queue_manager.spawn_item({
            "type": "COMPANY",
            "url": company.website,
            "name": company.name,
            "priority": "high"  # Block job processing until done
        })
        # Re-queue this job to process after company completes
        queue_manager.spawn_item({
            "type": "JOB",
            "url": item.url,
            "after": company_job_id  # Wait for company
        })
        return
    
    # Job already fully processed? Skip
    if job_doc and job_doc.has_analysis and job_doc.has_match_score:
        logger.info(f"Job {item.url} already processed, skipping")
        return
    
    # Need to scrape HTML?
    if not job_doc or not job_doc.scraped_data:
        html = scrape_url(item.url)
        job_data = extract_job_data(html)  # AI extraction
        
        firestore.upsert_job({
            "url": item.url,
            "scraped_data": job_data,
            "scraped_at": datetime.now()
        })
        
        # Spawn next step: filtering
        queue_manager.spawn_item({
            "type": "JOB",
            "url": item.url,
            "operation": "filter"  # Hint for next processor
        })
        return
    
    # Need to filter?
    if job_doc.scraped_data and not job_doc.filter_result:
        filter_result = apply_filters(job_doc.scraped_data)
        
        firestore.update_job(item.url, {
            "filter_result": filter_result,
            "filtered_at": datetime.now()
        })
        
        if filter_result.rejected:
            # Job filtered out, don't continue
            return
        
        # Passed filters, spawn analysis
        queue_manager.spawn_item({
            "type": "JOB",
            "url": item.url,
            "operation": "analyze"
        })
        return
    
    # Need to analyze?
    if job_doc.filter_result.passed and not job_doc.analysis:
        analysis = ai_analyze_job(job_doc.scraped_data, profile)
        
        firestore.update_job(item.url, {
            "analysis": analysis,
            "match_score": analysis.score,
            "analyzed_at": datetime.now()
        })
        
        # If excellent match, spawn notification
        if analysis.score >= 90:
            queue_manager.spawn_item({
                "type": "NOTIFICATION",
                "job_url": item.url,
                "urgency": "high"
            })
        
        return
    
    # All done!
    logger.info(f"Job {item.url} fully processed")
```

## Benefits of State-Driven Design

### 1. **Self-Healing**
```python
# Scenario: Job exists but missing company data
# Old: Fail with error "Company not found"
# New: Automatically spawn company scraper and retry
```

### 2. **Automatic Data Discovery**
```python
# Scenario: Processing stripe.com job
# System discovers: "stripe.com/careers" job board
# Automatically spawns: SOURCE_DISCOVERY queue item
# Result: System learns new job sources organically
```

### 3. **Idempotent & Safe**
```python
# Scenario: Same job queued twice
# Old: Process twice, waste API calls
# New: Check state, see it's done, skip gracefully
```

### 4. **Resumable After Failures**
```python
# Scenario: AI analysis fails mid-pipeline
# Old: Entire pipeline fails, start from scratch
# New: Resume from exact point of failure
```

### 5. **Smart About Costs**
```python
# Scenario: Job already scraped but never analyzed
# Old: Re-scrape everything (waste money)
# New: Detect scraped_data exists, skip to analysis
```

## Implementation Strategy

### Phase 1: Remove `sub_task` Requirement ✅ (Current Issue)

**Problem:** Current code requires explicit `sub_task`:
```python
# scraper_intake.py line 85
queue_item = JobQueueItem(
    type=QueueItemType.JOB,
    url=normalized_url,
    sub_task=JobSubTask.SCRAPE,  # ❌ Required but shouldn't be
    ...
)
```

**Solution:** Make `sub_task` optional, add intelligent processor:
```python
# New intelligent processor
def process_job(item: JobQueueItem):
    """Process job intelligently based on current state."""
    
    # Determine what needs to happen by examining DB state
    next_operation = determine_next_operation(item)
    
    if next_operation == "scrape":
        scrape_job_html(item)
    elif next_operation == "filter":
        apply_filters(item)
    elif next_operation == "analyze":
        run_ai_analysis(item)
    elif next_operation == "complete":
        logger.info("Job fully processed")
    
def determine_next_operation(item: JobQueueItem) -> str:
    """
    Decision tree: What does this job need?
    """
    job_doc = get_job_from_db(item.url)
    
    if not job_doc:
        return "scrape"  # Nothing exists, start from scratch
    
    if not job_doc.get("scraped_data"):
        return "scrape"  # Missing scrape data
    
    if not job_doc.get("filter_result"):
        return "filter"  # Need to filter
    
    if job_doc["filter_result"]["rejected"]:
        return "complete"  # Filtered out, done
    
    if not job_doc.get("analysis"):
        return "analyze"  # Need AI analysis
    
    return "complete"  # Fully processed
```

### Phase 2: Add Company Discovery Logic

**Current:** Job processing ignores company data

**New:** Automatically discover and enrich company data:

```python
def process_job(item: JobQueueItem):
    # Extract company from URL
    company_name = extract_company_from_url(item.url)
    
    # Check if company exists
    company_doc = get_company_from_db(company_name)
    
    if not company_doc:
        logger.info(f"Unknown company: {company_name}, spawning company scraper")
        
        # Spawn company scraper
        company_id = queue_manager.spawn_item({
            "type": "COMPANY",
            "name": company_name,
            "website": extract_base_url(item.url),
            "discovered_from": item.url
        })
        
        # Re-queue this job with company context
        queue_manager.spawn_item({
            "type": "JOB",
            "url": item.url,
            "company_id": company_id,
            "wait_for": company_id  # Process after company completes
        })
        
        return  # Exit, will resume after company processing
    
    # Continue with job processing...
```

### Phase 3: Add Source Discovery

**Goal:** System automatically discovers job boards

```python
def process_company(item: JobQueueItem):
    """Process company and discover job sources."""
    
    company_doc = get_company_from_db(item.company_id)
    
    # Scrape company website
    html = fetch_url(company_doc.website)
    
    # Extract company info
    company_info = extract_company_info(html)
    
    # Look for careers page
    careers_links = find_careers_links(html)
    
    if careers_links:
        logger.info(f"Found {len(careers_links)} potential job sources")
        
        # Spawn source discovery for each
        for link in careers_links:
            queue_manager.spawn_item({
                "type": "SOURCE_DISCOVERY",
                "url": link,
                "company_id": item.company_id,
                "discovered_at": datetime.now()
            })
    
    # Save company data
    save_company_to_db(company_info)
```

### Phase 4: Add Smart Retry & Prioritization

```python
class SmartQueueManager:
    def get_next_item(self) -> JobQueueItem:
        """
        Intelligent queue ordering based on:
        - Priority (high-value companies first)
        - Freshness (stale data needs refresh)
        - Dependencies (wait_for completed)
        - Cost (cheap operations first)
        """
        
        # High priority: Jobs from target companies
        priority_items = self.get_priority_items()
        if priority_items:
            return priority_items[0]
        
        # Next: Cheap operations (filtering, no AI)
        cheap_items = self.get_cheap_items()
        if cheap_items:
            return cheap_items[0]
        
        # Finally: Expensive operations (AI analysis)
        return self.get_oldest_pending()
```

## Data Model Changes

### Current JobQueueItem
```python
class JobQueueItem:
    type: QueueItemType  # Required: "job", "company", etc.
    sub_task: JobSubTask  # ❌ Required: "scrape", "filter", etc.
    url: str
    status: QueueStatus
```

### New JobQueueItem (Simplified)
```python
class JobQueueItem:
    type: QueueItemType  # Required: "job", "company", etc.
    url: str
    status: QueueStatus
    
    # Optional hints for optimization
    operation_hint: Optional[str]  # "scrape", "analyze", etc.
    priority: int = 0  # Higher = process first
    wait_for: Optional[str]  # Wait for this item_id to complete
    dependencies: List[str] = []  # List of required items
    
    # Context for decision-making
    discovered_from: Optional[str]  # Where was this found?
    retry_count: int = 0
    last_error: Optional[str]
    
    # Loop Prevention (see LOOP_PREVENTION_DESIGN.md)
    tracking_id: str  # UUID that follows entire job lineage
    ancestry_chain: List[str] = []  # Chain of parent IDs (prevents circular dependencies)
    spawn_depth: int = 0  # Recursion depth (prevents infinite spawning)
    max_spawn_depth: int = 10  # Maximum allowed depth
```

**Loop Prevention Example:**
```python
# Initial job
job_1 = JobQueueItem(
    type="job",
    url="https://stripe.com/jobs/123",
    tracking_id="abc-123-def",  # Generated UUID
    ancestry_chain=["abc-123-def"],
    spawn_depth=0
)

# Spawned company scraper inherits tracking_id
company = JobQueueItem(
    type="company",
    url="https://stripe.com",
    tracking_id="abc-123-def",  # SAME tracking_id
    ancestry_chain=["abc-123-def", "job-1-id"],  # Adds parent
    spawn_depth=1  # Incremented
)

# System blocks circular dependency:
# - If trying to spawn job for same URL already in ancestry_chain
# - If spawn_depth >= max_spawn_depth
# - If same (url, type) already pending in this tracking_id
```

## Migration Path

### Step 1: Make `sub_task` Optional (Immediate)
```python
# processor.py
def process_item(item: JobQueueItem):
    if item.sub_task:
        # Legacy: Use explicit sub_task
        process_with_subtask(item)
    else:
        # New: Use intelligent state-driven processing
        process_intelligently(item)
```

### Step 2: Implement State-Driven Processor (Next)
```python
def process_intelligently(item: JobQueueItem):
    """Smart processor that reads DB state."""
    
    if item.type == QueueItemType.JOB:
        process_job_intelligently(item)
    elif item.type == QueueItemType.COMPANY:
        process_company_intelligently(item)
    elif item.type == QueueItemType.SOURCE_DISCOVERY:
        process_source_discovery(item)
```

### Step 3: Deprecate `sub_task` (Future)
```python
# Once all queue items use intelligent processing:
# - Remove sub_task field
# - Remove legacy pipeline code
# - Simplify models
```

## Testing Strategy

### Unit Tests
```python
def test_job_processing_skips_if_complete():
    """Verify idempotency: Don't reprocess completed jobs."""
    
    # Setup: Job already fully processed
    firestore.save_job({
        "url": "https://stripe.com/jobs/123",
        "scraped_data": {...},
        "filter_result": {"passed": True},
        "analysis": {"score": 85}
    })
    
    # Queue same job
    item = JobQueueItem(type="job", url="https://stripe.com/jobs/123")
    
    # Should skip gracefully
    process_job(item)
    
    # Verify: No API calls made
    assert mock_ai_client.call_count == 0

def test_job_spawns_company_if_missing():
    """Verify automatic company discovery."""
    
    # Setup: No company data
    firestore.delete_company("Stripe")
    
    # Queue job
    item = JobQueueItem(type="job", url="https://stripe.com/jobs/123")
    
    process_job(item)
    
    # Verify: Company scraper spawned
    spawned_items = queue_manager.get_spawned_items()
    assert any(i.type == "company" for i in spawned_items)
```

### E2E Tests
```python
def test_full_pipeline_from_bare_url():
    """
    Submit just a URL, verify system:
    1. Discovers company is unknown
    2. Scrapes company info
    3. Discovers job board
    4. Scrapes job
    5. Filters job
    6. Analyzes job
    7. Saves to job-matches
    """
    
    # Empty database
    firestore.clear_all()
    
    # Submit single URL
    queue_manager.submit_job("https://newcompany.com/jobs/engineer")
    
    # Wait for processing
    wait_for_queue_empty(timeout=180)
    
    # Verify all steps happened automatically
    assert firestore.company_exists("New Company")
    assert firestore.source_exists("newcompany.com/jobs")
    assert firestore.job_exists("https://newcompany.com/jobs/engineer")
```

## Success Metrics

**Before (Rigid Pipeline):**
- ❌ Requires explicit sub_task on every queue item
- ❌ Fails if company data missing
- ❌ Re-scrapes everything on retry
- ❌ Can't adapt to incomplete data
- ❌ Wastes API calls on duplicate work

**After (State-Driven):**
- ✅ Submit just `{type: "job", url: "..."}` and system figures it out
- ✅ Automatically discovers and scrapes missing companies
- ✅ Skips completed work (idempotent)
- ✅ Resumes from failure point
- ✅ Organically grows job source database
- ✅ Minimizes API costs through smart state checking

## Next Steps

1. **Immediate:** Remove `sub_task` requirement from `scraper_intake.py`
   - Make field optional in models
   - Add backward compatibility layer
   
2. **This Week:** Implement `process_job_intelligently()`
   - Add `determine_next_operation()` decision tree
   - Read job state from Firestore
   - Spawn next steps based on state
   
3. **Next Week:** Add company discovery
   - Extract company from job URLs
   - Check if company exists
   - Spawn company scraper if missing
   
4. **Future:** Full state-driven system
   - Source discovery
   - Smart prioritization
   - Cost optimization
   - Self-healing on errors

---

**Philosophy:** The system should be **smart, not scripted**. Each processor should look at what exists, determine what's missing, fix it, and spawn the next logical step. This creates a resilient, self-healing pipeline that grows more intelligent over time.
