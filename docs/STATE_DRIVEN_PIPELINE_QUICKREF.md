# State-Driven Pipeline - Quick Reference

## 📚 Documentation Index

1. **STATE_DRIVEN_PIPELINE_SUMMARY.md** - Executive overview (start here!)
2. **STATE_DRIVEN_PIPELINE_DESIGN.md** - Full technical design & implementation
3. **LOOP_PREVENTION_DESIGN.md** - Protection against infinite loops
4. **This file** - Quick reference for common scenarios

---

## 🎯 Core Concepts

### Problem We're Solving
**Current:** Jobs need explicit `sub_task` at every step, can't adapt to state, can't discover missing data

**Future:** Jobs examine database state, intelligently decide what's needed, automatically discover and fix missing data

---

## 🔑 Key Fields for Loop Prevention

```python
class JobQueueItem:
    # Identity
    tracking_id: str              # UUID that follows entire lineage
    ancestry_chain: List[str]     # Parent IDs (prevents circular deps)
    spawn_depth: int              # Recursion level (prevents infinite depth)
    max_spawn_depth: int = 10     # Maximum allowed depth
    
    # Context
    parent_item_id: Optional[str] # Immediate parent
    discovered_from: Optional[str] # Where was this found?
```

---

## 🛡️ Loop Prevention Checks

### Before Spawning Any Item

```python
def can_spawn_item(current_item, target_url, target_type):
    # ✅ Check 1: Depth limit
    if current_item.spawn_depth >= max_spawn_depth:
        return False, "Max depth reached"
    
    # ✅ Check 2: Circular dependency
    if target_url in ancestry_chain_urls:
        return False, "Circular dependency"
    
    # ✅ Check 3: Duplicate work (pending)
    if same_url_type_already_pending():
        return False, "Already queued"
    
    # ✅ Check 4: Already completed
    if same_url_type_already_succeeded():
        return False, "Already done"
    
    return True, "OK"
```

---

## 📋 Common Scenarios

### Scenario 1: Submit New Job URL

```python
# Input: Just a URL
url = "https://newcompany.com/jobs/engineer"

# System does:
1. Creates tracking_id: "abc-123"
2. Checks if company "New Company" exists → NO
3. Spawns company scraper (inherits tracking_id)
4. Re-queues job after company completes
5. Scrapes job
6. Filters job
7. Analyzes job
8. Saves to job-matches

# All automatic from single URL!
```

### Scenario 2: Company Discovery During Job Processing

```python
# Processing: https://stripe.com/jobs/12345

def process_job(item):
    company = extract_company_from_url(item.url)  # "Stripe"
    
    if not db.company_exists("Stripe"):
        # Spawn company scraper
        can_spawn, reason = can_spawn_item(
            current_item=item,
            target_url="https://stripe.com",
            target_type="company"
        )
        
        if can_spawn:
            spawn_item_safely(item, {
                "type": "company",
                "url": "https://stripe.com",
                "name": "Stripe",
                "tracking_id": item.tracking_id,  # Inherit
                "ancestry_chain": item.ancestry_chain + [item.id],
                "spawn_depth": item.spawn_depth + 1
            })
            
            # Re-queue this job after company
            requeue_after_dependency(item, company_id)
        else:
            logger.warning(f"Blocked spawn: {reason}")
```

### Scenario 3: Preventing Circular Loop

```python
# Bad: Job A → Company X → Source Discovery → Job A (LOOP!)

# tracking_id: "xyz-789"
# ancestry_chain: ["xyz-789", "job-A", "company-X", "source-disc"]

# System tries to spawn Job A again:
can_spawn_item(
    current_item=source_discovery,
    target_url="https://company.com/job/1",  # Job A URL
    target_type="job"
)

# Returns: (False, "Circular dependency: URL already in chain")
# Job A NOT spawned, loop prevented ✅
```

### Scenario 4: Preventing Duplicate Work

```python
# Job 1 discovers missing Company X → spawns company scraper
# Job 2 discovers missing Company X → tries to spawn company scraper

# First spawn succeeds:
company_scraper_1 = spawn_item_safely(job_1, {
    "type": "company",
    "url": "https://companyx.com",
    "tracking_id": "abc-123"
})
# ✅ Created (status: pending)

# Second spawn blocked:
company_scraper_2 = spawn_item_safely(job_2, {
    "type": "company",
    "url": "https://companyx.com",
    "tracking_id": "abc-123"  # Same tracking_id
})
# ❌ Blocked: "Duplicate work: company for companyx.com already queued"
```

### Scenario 5: Smart Retry (No Retry Storm)

```python
# Retry attempt checks ancestors:

def handle_retry(item, error):
    # Get all items in this lineage
    ancestors = queue_manager.get_items_by_tracking_id(item.tracking_id)
    
    # Check if same error occurred before
    for ancestor in ancestors:
        if (
            ancestor.url == item.url
            and ancestor.type == item.type
            and ancestor.error_details == error
            and ancestor.status == "failed"
        ):
            # Don't retry - ancestor failed same way
            logger.error(f"Ancestor {ancestor.id} failed with same error")
            mark_failed(item, "Not retrying - ancestor failed identically")
            return
    
    # Safe to retry
    retry_with_exponential_backoff(item)
```

---

## 🔍 Monitoring Queries

### Find Deep Spawn Chains

```python
# Alert if spawn_depth > 8
deep_items = db.collection("job-queue").where(
    "spawn_depth", ">", 8
).get()

for item in deep_items:
    logger.warning(
        f"Deep spawn detected: {item.id} "
        f"(depth: {item.spawn_depth}, tracking_id: {item.tracking_id})"
    )
```

### Find Circular Dependencies

```python
# Group by tracking_id, check for duplicate URLs
tracking_ids = get_all_tracking_ids()

for tracking_id in tracking_ids:
    items = get_items_by_tracking_id(tracking_id)
    urls = [item.url for item in items]
    
    # Check for duplicates
    url_counts = Counter(urls)
    for url, count in url_counts.items():
        if count > 2:
            logger.warning(
                f"Circular dependency suspected: {url} appears {count} times "
                f"in tracking_id {tracking_id}"
            )
```

### Find Duplicate Work

```python
# Same (url, type) with multiple pending items
items = db.collection("job-queue").where("status", "==", "pending").get()

# Group by (url, type)
work_keys = {}
for item in items:
    key = (item.url, item.type)
    work_keys.setdefault(key, []).append(item.id)

# Alert on duplicates
for (url, item_type), item_ids in work_keys.items():
    if len(item_ids) > 1:
        logger.warning(
            f"Duplicate work: {len(item_ids)} pending items for "
            f"{item_type} {url}: {item_ids}"
        )
```

---

## 🚀 Implementation Phases

### Phase 1: Add Loop Prevention Fields (This Week)
- ✅ Add `tracking_id`, `ancestry_chain`, `spawn_depth` to `JobQueueItem`
- ✅ Make fields optional (backward compatible)
- ✅ Auto-initialize on read (legacy items get tracking_id)
- ✅ Add `can_spawn_item()` and `spawn_item_safely()` helpers

### Phase 2: Implement State-Driven Processor (Next Week)
- ✅ Add `process_job_intelligently()` function
- ✅ Read job state from Firestore
- ✅ Decision tree: What does this job need?
- ✅ Perform one atomic operation
- ✅ Spawn next steps with loop prevention

### Phase 3: Add Company Discovery (Following Week)
- ✅ Extract company from job URL
- ✅ Check if company exists
- ✅ Spawn company scraper with `spawn_item_safely()`
- ✅ Re-queue job after company completes

### Phase 4: Add Source Discovery (Future)
- ✅ During company scraping, look for careers pages
- ✅ Spawn SOURCE_DISCOVERY items
- ✅ System organically grows job source database

---

## 📊 Success Metrics

| Metric | Before | After Target |
|--------|--------|--------------|
| Loop incidents | Unknown (system crashes) | 0 (prevented) |
| Circular dependencies | Undetected | Blocked before spawning |
| Duplicate work | Common | Prevented by tracking_id |
| Spawn depth issues | Possible infinite | Max 10 levels enforced |
| Retry storms | Occasional | Prevented by ancestor check |

---

## 🔧 Required Database Indexes

```javascript
// Firestore composite indexes
[
  {
    "collectionGroup": "job-queue",
    "fields": [
      { "fieldPath": "tracking_id", "order": "ASCENDING" },
      { "fieldPath": "status", "order": "ASCENDING" }
    ]
  },
  {
    "collectionGroup": "job-queue",
    "fields": [
      { "fieldPath": "url", "order": "ASCENDING" },
      { "fieldPath": "type", "order": "ASCENDING" },
      { "fieldPath": "status", "order": "ASCENDING" }
    ]
  },
  {
    "collectionGroup": "job-queue",
    "fields": [
      { "fieldPath": "spawn_depth", "order": "DESCENDING" }
    ]
  }
]
```

---

## ⚠️ Common Pitfalls to Avoid

### ❌ Don't: Spawn without checking
```python
# BAD: No loop prevention
queue_manager.add_item(JobQueueItem(type="company", url=url))
```

### ✅ Do: Use safe spawn helper
```python
# GOOD: Loop prevention built-in
spawn_item_safely(current_item, {"type": "company", "url": url})
```

### ❌ Don't: Forget to inherit tracking_id
```python
# BAD: Creates orphan lineage
new_item = JobQueueItem(
    type="job",
    url=url,
    tracking_id=str(uuid.uuid4())  # ❌ New ID breaks lineage
)
```

### ✅ Do: Always inherit from parent
```python
# GOOD: Maintains lineage
new_item = JobQueueItem(
    type="job",
    url=url,
    tracking_id=current_item.tracking_id,  # ✅ Inherit
    ancestry_chain=current_item.ancestry_chain + [current_item.id]
)
```

### ❌ Don't: Ignore spawn depth
```python
# BAD: No depth limit
while needs_more_work():
    spawn_item(...)  # Infinite recursion possible
```

### ✅ Do: Check depth limit
```python
# GOOD: Enforces depth limit
if current_item.spawn_depth < max_spawn_depth:
    spawn_item_safely(...)
else:
    logger.error("Max spawn depth reached")
```

---

## 🧪 Testing Checklist

- [ ] Test circular dependency prevention (A → B → A blocked)
- [ ] Test max spawn depth enforcement (stops at 10)
- [ ] Test duplicate work prevention (same URL+type blocked)
- [ ] Test tracking_id inheritance (children get parent's ID)
- [ ] Test ancestry chain building (grows with each spawn)
- [ ] Test retry logic (blocks if ancestor failed identically)
- [ ] Test monitoring queries (find deep spawns, circular deps)
- [ ] Test migration (legacy items get tracking_id on read)

---

## 📞 Need Help?

- **Loop prevention details:** See `LOOP_PREVENTION_DESIGN.md`
- **State-driven architecture:** See `STATE_DRIVEN_PIPELINE_DESIGN.md`
- **Executive overview:** See `STATE_DRIVEN_PIPELINE_SUMMARY.md`
