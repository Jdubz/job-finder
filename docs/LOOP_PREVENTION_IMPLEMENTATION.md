# Loop Prevention - Implementation Plan (No Backward Compatibility)

## 🎯 Implementation Strategy: Clean Slate

**Context:** No existing users, no legacy data concerns
**Approach:** Make all loop prevention fields **required**, implement from scratch with best practices

---

## Phase 1: Update Models (IMMEDIATE)

### 1.1 Update JobQueueItem Model
**File:** `src/job_finder/queue/models.py`

**Changes:**
```python
class JobQueueItem(BaseModel):
    # ... existing fields ...
    
    # NEW REQUIRED FIELDS (no Optional, no backward compatibility)
    tracking_id: str = Field(
        description="UUID that tracks entire job lineage. Generated at root, inherited by children."
    )
    ancestry_chain: List[str] = Field(
        default_factory=list,
        description="Chain of parent item IDs. Used to detect circular dependencies."
    )
    spawn_depth: int = Field(
        default=0,
        description="Recursion depth. Root=0, each spawn increments by 1."
    )
    max_spawn_depth: int = Field(
        default=10,
        description="Maximum allowed spawn depth before blocking."
    )
```

### 1.2 Update Firestore Indexes
**File:** `firestore.indexes.json`

**Add:**
```json
{
  "indexes": [
    {
      "collectionGroup": "job-queue",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "tracking_id", "order": "ASCENDING" },
        { "fieldPath": "status", "order": "ASCENDING" }
      ]
    },
    {
      "collectionGroup": "job-queue",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "url", "order": "ASCENDING" },
        { "fieldPath": "type", "order": "ASCENDING" },
        { "fieldPath": "status", "order": "ASCENDING" }
      ]
    },
    {
      "collectionGroup": "job-queue",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "spawn_depth", "order": "DESCENDING" }
      ]
    }
  ]
}
```

---

## Phase 2: Add Loop Prevention Logic (IMMEDIATE)

### 2.1 Add Helper Methods to QueueManager
**File:** `src/job_finder/queue/manager.py`

**New methods:**
```python
def get_items_by_tracking_id(
    self,
    tracking_id: str,
    status_filter: Optional[List[QueueStatus]] = None
) -> List[JobQueueItem]:
    """Get all items in the same tracking lineage."""
    
def has_pending_work_for_url(
    self,
    url: str,
    item_type: QueueItemType,
    tracking_id: str
) -> bool:
    """Check if URL is already queued for processing in this lineage."""
    
def can_spawn_item(
    self,
    current_item: JobQueueItem,
    target_url: str,
    target_type: QueueItemType
) -> tuple[bool, str]:
    """Check if spawning would create a loop."""
    
def spawn_item_safely(
    self,
    current_item: JobQueueItem,
    new_item_data: dict
) -> Optional[str]:
    """Spawn with loop prevention."""
```

---

## Phase 3: Update All Spawn Points (IMMEDIATE)

### 3.1 Update ScraperIntake
**File:** `src/job_finder/queue/scraper_intake.py`

**Changes:**
- Generate `tracking_id` for root submissions
- Remove `sub_task` requirement (use state-driven instead)

### 3.2 Update spawn_next_pipeline_step
**File:** `src/job_finder/queue/manager.py`

**Changes:**
- Inherit `tracking_id`, `ancestry_chain`, `spawn_depth`
- Use `spawn_item_safely()` instead of direct `add_item()`

### 3.3 Update Processor
**File:** `src/job_finder/queue/processor.py`

**Changes:**
- Use `spawn_item_safely()` for all spawning
- Remove `sub_task` requirement checks

---

## Phase 4: State-Driven Processing (NEXT)

### 4.1 Add Intelligent Job Processor
**File:** `src/job_finder/queue/processor.py`

**New function:**
```python
def process_job_intelligently(self, item: JobQueueItem) -> None:
    """Process job based on current database state."""
    
    # Determine what needs to happen
    next_operation = self._determine_job_operation(item)
    
    if next_operation == "scrape":
        self._scrape_and_save(item)
    elif next_operation == "filter":
        self._filter_and_decide(item)
    elif next_operation == "analyze":
        self._analyze_and_save(item)
    elif next_operation == "complete":
        logger.info("Job fully processed")
```

---

## Phase 5: Testing (PARALLEL)

### 5.1 Unit Tests
**File:** `tests/unit/test_loop_prevention.py` (NEW)

Tests:
- `test_circular_dependency_blocked`
- `test_max_spawn_depth_enforced`
- `test_duplicate_work_prevented`
- `test_tracking_id_inheritance`

### 5.2 Integration Tests
**File:** `tests/integration/test_queue_spawning.py` (NEW)

Tests:
- `test_company_discovery_with_loop_prevention`
- `test_parallel_spawns_deduplicated`

---

## Implementation Order (Today)

### Step 1: Models ✅ START HERE
1. Update `JobQueueItem` in `models.py`
2. Make `tracking_id` required
3. Add `ancestry_chain`, `spawn_depth`, `max_spawn_depth`

### Step 2: QueueManager ✅
1. Add `get_items_by_tracking_id()`
2. Add `has_pending_work_for_url()`
3. Add `can_spawn_item()`
4. Add `spawn_item_safely()`

### Step 3: Update Spawning ✅
1. Update `ScraperIntake.submit_jobs()` to generate tracking_id
2. Update `spawn_next_pipeline_step()` to inherit tracking fields
3. Replace all `add_item()` with `spawn_item_safely()`

### Step 4: Remove sub_task Requirement ✅
1. Make `sub_task` optional in model
2. Update processor to handle both explicit and intelligent modes
3. Add `process_job_intelligently()` function

### Step 5: Test ✅
1. Write unit tests
2. Run `make test-e2e-full`
3. Verify loop prevention works

---

## Breaking Changes (Acceptable)

✅ **tracking_id now required** - All new queue items must have it
✅ **ancestry_chain tracked** - Firestore documents get new field
✅ **spawn_depth tracked** - New required field
✅ **Old queue items won't work** - Clear queue before deploying (no users)

---

## Timeline

- **Models + Manager methods:** 30 minutes
- **Update spawn points:** 30 minutes  
- **Remove sub_task requirement:** 20 minutes
- **Testing:** 20 minutes
- **Total:** ~2 hours

---

## Success Criteria

After implementation:
- ✅ All queue items have `tracking_id`
- ✅ All queue items track `ancestry_chain`
- ✅ All queue items track `spawn_depth`
- ✅ Circular dependencies blocked
- ✅ Max spawn depth enforced
- ✅ Duplicate work prevented
- ✅ Tests pass
- ✅ No backward compatibility code

Let's build this! 🚀
