# Loop Prevention Design - Tracking IDs & Ancestry

## Problem: Infinite Loop Risk

In a state-driven pipeline where jobs can spawn other jobs automatically, we risk **infinite loops**:

### Scenario 1: Direct Loop
```
Job A → discovers missing company
     → spawns Company scraper
     → Company scraper fails (no data)
     → re-queues Job A
     → Job A discovers missing company again
     → spawns Company scraper again
     → INFINITE LOOP
```

### Scenario 2: Circular Dependencies
```
Job A → needs Company X
     → Company X scraper needs job board data
     → Job board discovery needs Company X data
     → CIRCULAR DEPENDENCY LOOP
```

### Scenario 3: Duplicate Spawning
```
Job A spawns Company X scraper (id: item-123)
Job B spawns Company X scraper (id: item-456)
Job C spawns Company X scraper (id: item-789)
→ Same company scraped 3 times in parallel
```

### Scenario 4: Retry Storm
```
Job fails → re-queues itself
Re-queue fails → re-queues itself
Re-queue fails → re-queues itself
→ EXPONENTIAL GROWTH
```

## Solution: Multi-Layer Loop Prevention

### 1. Tracking ID (Root Identifier)

Add a **tracking_id** that follows the entire job lineage:

```python
class JobQueueItem(BaseModel):
    # Existing fields...
    
    # NEW: Loop prevention fields
    tracking_id: str = Field(
        description="UUID that tracks entire job lineage. All spawned items inherit this."
    )
    ancestry_chain: List[str] = Field(
        default_factory=list,
        description="Chain of item IDs from root to current (prevents circular dependencies)"
    )
    spawn_depth: int = Field(
        default=0,
        description="How many levels deep in spawn chain (prevents infinite depth)"
    )
    max_spawn_depth: int = Field(
        default=10,
        description="Maximum allowed spawn depth before blocking"
    )
```

### 2. Usage Example

```python
# Initial job submission
job_1 = JobQueueItem(
    type="job",
    url="https://stripe.com/jobs/123",
    tracking_id=str(uuid.uuid4()),  # "abc-123-def"
    ancestry_chain=["abc-123-def"],  # Root of chain
    spawn_depth=0
)

# Job discovers missing company, spawns company scraper
company_scraper = JobQueueItem(
    type="company",
    url="https://stripe.com",
    tracking_id="abc-123-def",  # SAME tracking_id
    ancestry_chain=["abc-123-def", "item-job-1"],  # Add parent
    spawn_depth=1,  # Increment depth
    parent_item_id="item-job-1"
)

# Company scraper spawns source discovery
source_discovery = JobQueueItem(
    type="source_discovery",
    url="https://stripe.com/careers",
    tracking_id="abc-123-def",  # SAME tracking_id
    ancestry_chain=["abc-123-def", "item-job-1", "item-company-2"],
    spawn_depth=2,  # Increment depth
    parent_item_id="item-company-2"
)
```

### 3. Loop Detection Logic

```python
def can_spawn_item(
    current_item: JobQueueItem,
    target_url: str,
    target_type: QueueItemType
) -> tuple[bool, str]:
    """
    Check if spawning a new item would create a loop.
    
    Returns:
        (can_spawn, reason)
    """
    
    # Check 1: Depth limit
    if current_item.spawn_depth >= current_item.max_spawn_depth:
        return False, f"Max spawn depth ({current_item.max_spawn_depth}) reached"
    
    # Check 2: Same URL already in ancestry chain
    if target_url in [get_url_from_item_id(id) for id in current_item.ancestry_chain]:
        return False, f"Circular dependency detected: {target_url} already in chain"
    
    # Check 3: Duplicate work (same URL + type already queued in this tracking_id)
    existing = queue_manager.get_items_by_tracking_id(current_item.tracking_id)
    for item in existing:
        if item.url == target_url and item.type == target_type and item.status == "pending":
            return False, f"Duplicate work: {target_type} for {target_url} already queued"
    
    # Check 4: Same URL + type already completed successfully in this tracking_id
    for item in existing:
        if item.url == target_url and item.type == target_type and item.status == "success":
            return False, f"Already completed: {target_type} for {target_url}"
    
    return True, "OK"


def spawn_item_safely(
    current_item: JobQueueItem,
    new_item_data: dict
) -> Optional[str]:
    """
    Spawn a new queue item with loop prevention.
    """
    
    # Check if spawning is allowed
    can_spawn, reason = can_spawn_item(
        current_item,
        new_item_data["url"],
        new_item_data["type"]
    )
    
    if not can_spawn:
        logger.warning(
            f"Blocked spawn to prevent loop: {reason}. "
            f"Current item: {current_item.id}, tracking_id: {current_item.tracking_id}"
        )
        return None
    
    # Create new item with inherited tracking data
    new_item = JobQueueItem(
        **new_item_data,
        tracking_id=current_item.tracking_id,  # Inherit tracking_id
        ancestry_chain=current_item.ancestry_chain + [current_item.id],  # Append to chain
        spawn_depth=current_item.spawn_depth + 1,  # Increment depth
        parent_item_id=current_item.id
    )
    
    # Add to queue
    item_id = queue_manager.add_item(new_item)
    
    logger.info(
        f"Spawned item {item_id} (depth: {new_item.spawn_depth}, "
        f"tracking_id: {new_item.tracking_id}, "
        f"chain length: {len(new_item.ancestry_chain)})"
    )
    
    return item_id
```

## 4. Database Queries for Loop Prevention

```python
class QueueManager:
    
    def get_items_by_tracking_id(
        self,
        tracking_id: str,
        status_filter: Optional[List[QueueStatus]] = None
    ) -> List[JobQueueItem]:
        """
        Get all items in the same tracking lineage.
        
        Used for loop detection and duplicate work prevention.
        """
        query = self.db.collection(self.collection_name).where(
            "tracking_id", "==", tracking_id
        )
        
        if status_filter:
            # Note: Firestore doesn't support multiple where clauses on different fields
            # We'll filter in-memory
            docs = query.stream()
            items = [JobQueueItem.from_firestore(doc.id, doc.to_dict()) for doc in docs]
            items = [i for i in items if i.status in status_filter]
        else:
            docs = query.stream()
            items = [JobQueueItem.from_firestore(doc.id, doc.to_dict()) for doc in docs]
        
        return items
    
    def has_pending_work_for_url(
        self,
        url: str,
        item_type: QueueItemType,
        tracking_id: Optional[str] = None
    ) -> bool:
        """
        Check if URL is already queued for processing.
        
        Args:
            url: URL to check
            item_type: Type of work (job, company, etc.)
            tracking_id: Optional tracking_id to scope check
        
        Returns:
            True if work is pending/processing
        """
        query = (
            self.db.collection(self.collection_name)
            .where("url", "==", url)
            .where("type", "==", item_type.value)
            .where("status", "in", ["pending", "processing"])
        )
        
        if tracking_id:
            query = query.where("tracking_id", "==", tracking_id)
        
        docs = query.limit(1).stream()
        return any(True for _ in docs)
```

## 5. Retry Logic with Loop Prevention

```python
def handle_retry(item: JobQueueItem, error: str):
    """
    Retry with loop prevention.
    """
    
    # Check 1: Max retries
    if item.retry_count >= item.max_retries:
        logger.error(f"Max retries ({item.max_retries}) reached for {item.id}")
        queue_manager.update_status(
            item.id,
            QueueStatus.FAILED,
            f"Failed after {item.retry_count} retries: {error}"
        )
        return
    
    # Check 2: Exponential backoff to prevent retry storm
    delay_seconds = 2 ** item.retry_count  # 1s, 2s, 4s, 8s...
    
    # Check 3: Don't retry if same error occurred in ancestry
    ancestor_items = queue_manager.get_items_by_tracking_id(item.tracking_id)
    for ancestor in ancestor_items:
        if (
            ancestor.url == item.url 
            and ancestor.type == item.type
            and ancestor.error_details == error
            and ancestor.status == "failed"
        ):
            logger.error(
                f"Same error occurred in ancestor {ancestor.id}: {error}. "
                f"Not retrying to prevent loop."
            )
            queue_manager.update_status(
                item.id,
                QueueStatus.FAILED,
                f"Ancestor item failed with same error, not retrying"
            )
            return
    
    # Safe to retry
    logger.info(
        f"Retrying {item.id} (attempt {item.retry_count + 1}/{item.max_retries}) "
        f"after {delay_seconds}s delay"
    )
    
    time.sleep(delay_seconds)
    
    item.retry_count += 1
    item.status = QueueStatus.PENDING
    queue_manager.update_item(item)
```

## 6. Monitoring & Alerting

```python
def check_for_suspicious_patterns():
    """
    Monitor queue for loop patterns.
    
    Run this periodically (e.g., every 5 minutes).
    """
    
    # Alert 1: Multiple items with same URL + type in same tracking_id
    tracking_ids = queue_manager.get_all_tracking_ids()
    
    for tracking_id in tracking_ids:
        items = queue_manager.get_items_by_tracking_id(tracking_id)
        
        # Group by (url, type)
        url_type_counts = {}
        for item in items:
            key = (item.url, item.type)
            url_type_counts[key] = url_type_counts.get(key, 0) + 1
        
        # Alert if duplicates
        for (url, item_type), count in url_type_counts.items():
            if count > 3:
                logger.warning(
                    f"Suspicious pattern: {count} items for {url} ({item_type}) "
                    f"in tracking_id {tracking_id}"
                )
                send_alert(
                    "Possible queue loop detected",
                    f"tracking_id: {tracking_id}\nURL: {url}\nCount: {count}"
                )
    
    # Alert 2: Items with excessive spawn depth
    deep_items = queue_manager.get_items_with_depth_above(threshold=8)
    if deep_items:
        logger.warning(f"Found {len(deep_items)} items with spawn_depth > 8")
        for item in deep_items:
            logger.warning(
                f"Deep spawn: {item.id} (depth: {item.spawn_depth}, "
                f"tracking_id: {item.tracking_id})"
            )
    
    # Alert 3: Circular dependencies
    for tracking_id in tracking_ids:
        items = queue_manager.get_items_by_tracking_id(tracking_id)
        urls = [item.url for item in items]
        
        # Check if any URL appears multiple times
        url_counts = {}
        for url in urls:
            url_counts[url] = url_counts.get(url, 0) + 1
        
        for url, count in url_counts.items():
            if count > 2:
                logger.warning(
                    f"Circular dependency suspected: {url} appears {count} times "
                    f"in tracking_id {tracking_id}"
                )
```

## 7. Migration Strategy

### Phase 1: Add Fields (Backward Compatible)

```python
class JobQueueItem(BaseModel):
    # Existing fields...
    
    # NEW: Optional at first (for backward compatibility)
    tracking_id: Optional[str] = Field(
        default=None,
        description="UUID that tracks entire job lineage"
    )
    ancestry_chain: Optional[List[str]] = Field(
        default=None,
        description="Chain of item IDs from root to current"
    )
    spawn_depth: Optional[int] = Field(
        default=None,
        description="How many levels deep in spawn chain"
    )
```

### Phase 2: Auto-Initialize on Read

```python
@classmethod
def from_firestore(cls, doc_id: str, data: Dict[str, Any]) -> "JobQueueItem":
    """Create JobQueueItem from Firestore document."""
    
    # Auto-initialize tracking fields if missing (for legacy items)
    if "tracking_id" not in data or data["tracking_id"] is None:
        data["tracking_id"] = str(uuid.uuid4())
    
    if "ancestry_chain" not in data or data["ancestry_chain"] is None:
        data["ancestry_chain"] = [data.get("id", doc_id)]
    
    if "spawn_depth" not in data or data["spawn_depth"] is None:
        data["spawn_depth"] = 0
    
    data["id"] = doc_id
    return cls(**data)
```

### Phase 3: Make Required (After Migration)

Once all items have tracking fields populated:

```python
tracking_id: str = Field(...)  # No longer optional
ancestry_chain: List[str] = Field(default_factory=list)
spawn_depth: int = Field(default=0)
```

## 8. Testing Strategy

```python
def test_prevents_circular_dependency():
    """Test that circular dependencies are blocked."""
    
    # Create root item
    root = JobQueueItem(
        type="job",
        url="https://company.com/job/1",
        tracking_id="test-123"
    )
    root_id = queue_manager.add_item(root)
    root.id = root_id
    
    # Spawn company scraper
    company = spawn_item_safely(root, {
        "type": "company",
        "url": "https://company.com"
    })
    
    # Try to spawn job again (circular)
    job_again = spawn_item_safely(company, {
        "type": "job",
        "url": "https://company.com/job/1"  # Same as root!
    })
    
    # Should be blocked
    assert job_again is None


def test_prevents_excessive_depth():
    """Test that excessive spawn depth is blocked."""
    
    item = JobQueueItem(
        type="job",
        url="https://test.com/1",
        tracking_id="test-456",
        spawn_depth=10,
        max_spawn_depth=10
    )
    
    # Try to spawn at max depth
    spawned = spawn_item_safely(item, {
        "type": "company",
        "url": "https://test.com"
    })
    
    # Should be blocked
    assert spawned is None


def test_prevents_duplicate_work():
    """Test that duplicate work is prevented."""
    
    tracking_id = str(uuid.uuid4())
    
    # Create two items that want to spawn same company
    job1 = JobQueueItem(
        type="job",
        url="https://company.com/job/1",
        tracking_id=tracking_id
    )
    job2 = JobQueueItem(
        type="job",
        url="https://company.com/job/2",
        tracking_id=tracking_id
    )
    
    # First spawn succeeds
    company1 = spawn_item_safely(job1, {
        "type": "company",
        "url": "https://company.com"
    })
    assert company1 is not None
    
    # Second spawn blocked (duplicate)
    company2 = spawn_item_safely(job2, {
        "type": "company",
        "url": "https://company.com"
    })
    assert company2 is None
```

## Summary

**Key Protection Mechanisms:**

1. ✅ **tracking_id**: Identifies entire job lineage
2. ✅ **ancestry_chain**: Prevents circular dependencies
3. ✅ **spawn_depth**: Limits recursion depth
4. ✅ **Duplicate detection**: Prevents same work multiple times
5. ✅ **Retry intelligence**: Blocks retries if ancestor failed same way
6. ✅ **Monitoring**: Alerts on suspicious patterns

**Database Indexes Needed:**

```javascript
// Firestore indexes
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
}
```

This design ensures the state-driven pipeline can safely spawn jobs without risk of infinite loops or exponential growth.
