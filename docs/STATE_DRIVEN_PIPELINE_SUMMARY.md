# State-Driven Pipeline - Executive Summary

## The Vision

Transform the job finder from a **rigid, scripted pipeline** into an **intelligent, self-healing system** that examines database state and dynamically decides what work needs to happen next.

## Current Problem

```python
# Today: Rigid and fragile
queue_item = JobQueueItem(
    type="job",
    url="https://stripe.com/jobs/123",
    sub_task="scrape"  # ❌ Must explicitly specify every step
)
```

**Issues:**
- Requires explicit `sub_task` on every queue item
- Can't adapt to existing data state
- Fails if company data is missing rather than discovering it
- Re-processes completed work
- Can't discover new job sources organically

## Proposed Solution

```python
# Future: Smart and adaptive
queue_item = JobQueueItem(
    type="job",
    url="https://stripe.com/jobs/123"
    # ✅ System figures out what needs to happen
)

# Processor examines state and decides:
def process_job(item):
    job = db.get_job(item.url)
    
    # Missing company? Discover it
    if not db.company_exists(extract_company(item.url)):
        spawn_company_scraper()
        requeue_job_after_company()
        return
    
    # Already processed? Skip
    if job.has_analysis:
        return
    
    # Missing scrape data? Get it
    if not job.scraped_data:
        scrape_and_save()
        spawn_next_step("filter")
        return
    
    # And so on... system is intelligent!
```

## Key Benefits

### 1. Self-Healing
- **Before:** Job fails because company unknown
- **After:** Automatically discovers and scrapes company, then retries job

### 2. Idempotent
- **Before:** Re-processes everything on retry (wastes money)
- **After:** Checks state, skips completed work

### 3. Automatic Discovery
- **Before:** Manual configuration of job sources
- **After:** System discovers `careers.stripe.com` during processing, adds it automatically

### 4. Cost Optimization
- **Before:** Re-scrapes and re-analyzes on every error
- **After:** Resumes from exact failure point

### 5. Simple API
- **Before:** Complex submission with sub_tasks and pipeline state
- **After:** Just submit URL, system figures out everything else

## Implementation Phases

### Phase 1: Remove `sub_task` Requirement (This Week)

Make `sub_task` optional, implement intelligent processor:

```python
def process_item(item):
    if item.sub_task:
        # Legacy: Use explicit sub_task
        process_with_subtask(item)
    else:
        # New: Use intelligent state-driven processing
        determine_what_needs_doing(item)
        do_one_atomic_operation()
        spawn_next_steps()
```

### Phase 2: Add Company Discovery (Next Week)

When processing job from unknown company:

```python
# Discover company is unknown
if not db.company_exists("Stripe"):
    # Spawn company scraper
    spawn_company_scraper("Stripe", "https://stripe.com")
    # Re-queue job to process after
    requeue_job_after_company()
```

### Phase 3: Add Source Discovery (Future)

System organically grows its job source database:

```python
# While scraping company website
if found_careers_page("https://stripe.com/careers"):
    spawn_source_discovery("https://stripe.com/careers")
```

### Phase 4: Smart Prioritization (Future)

Queue intelligently orders work:
1. High-value companies first
2. Cheap operations before expensive
3. Fresh data needs vs stale data

## Migration Strategy

**Backward Compatible:** Existing code with `sub_task` continues working

**Gradual Adoption:** New submissions can omit `sub_task`, use intelligent processing

**No Breaking Changes:** Old queue items process normally, new items use state-driven logic

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| **Queue Item Complexity** | Must specify 4-step pipeline | Just URL and type |
| **Handling Missing Data** | Fails with error | Auto-discovers and fixes |
| **Duplicate Processing** | Re-processes everything | Skips completed work |
| **Company Discovery** | Manual configuration | Automatic |
| **Job Source Growth** | Requires code changes | Self-expanding |
| **API Cost on Retry** | Full re-process | Resume from failure |

## Next Actions

1. **Review Design Doc:** `docs/STATE_DRIVEN_PIPELINE_DESIGN.md`
2. **Phase 1 Implementation:**
   - Make `sub_task` optional in `JobQueueItem` model
   - Add `process_job_intelligently()` function
   - Implement state-checking logic
3. **Testing:** Verify both legacy and new paths work
4. **Rollout:** Gradually migrate queue submissions

## Philosophy

> "The system should be smart, not scripted. Each processor examines what exists, determines what's missing, fixes it, and spawns the next logical step."

This creates a **resilient, self-healing pipeline** that grows more intelligent over time, automatically discovering data and filling in gaps rather than failing on missing information.
