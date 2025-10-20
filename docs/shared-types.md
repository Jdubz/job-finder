# Shared Types Integration

## Overview

The job-finder and portfolio projects share type definitions through the `@jdubz/job-finder-shared-types` npm package. This document explains how the type system works and how to keep Python and TypeScript in sync.

## Architecture

### Single Source of Truth

**TypeScript types in `@jdubz/job-finder-shared-types` are the authoritative definitions.**

**Repository:** https://github.com/Jdubz/job-finder-shared-types

```
@jdubz/job-finder-shared-types (TypeScript - Source of Truth)
    Repository: https://github.com/Jdubz/job-finder-shared-types
    ├── src/queue.types.ts          # Queue-related types
    └── dist/                        # Compiled JavaScript + TypeScript definitions

job-finder-FE (TypeScript)
    └── imports @jdubz/job-finder-shared-types directly via npm

Job-finder (Python)
    └── mirrors TypeScript types with Python equivalents
```

### Why TypeScript is the Source of Truth

1. **Type Safety**: TypeScript provides compile-time type checking
2. **Documentation**: JSDoc comments and interfaces serve as schema documentation
3. **job-finder-FE Integration**: job-finder-FE is TypeScript and imports types directly
4. **Single Definition**: One place to define the contract between projects

## Type Mapping

### Basic Types

| TypeScript | Python | Example |
|------------|--------|---------|
| `string` | `str` | `company_name: string` → `company_name: str` |
| `number` | `int` or `float` | `retry_count: number` → `retry_count: int` |
| `boolean` | `bool` | `enabled: boolean` → `enabled: bool` |
| `Date` | `datetime` | `created_at: Date` → `created_at: datetime` |
| `string[]` | `List[str]` | `tags: string[]` → `tags: List[str]` |
| `Record<string, any>` | `Dict[str, Any]` | `config: Record<string, any>` → `config: Dict[str, Any]` |
| `Type \| null` | `Optional[Type]` | `id?: string \| null` → `id: Optional[str]` |
| `"a" \| "b"` | `Literal["a", "b"]` | `source: QueueSource` → `source: QueueSource` |

### Enum Types

TypeScript enums map to Python string enums:

**TypeScript:**
```typescript
export type QueueStatus = "pending" | "processing" | "success" | "failed" | "skipped"
```

**Python:**
```python
class QueueStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
```

**Key Points:**
- Python enum values must match TypeScript string literals **exactly**
- Python enum names can use UPPER_CASE (Python convention)
- Use `str, Enum` for string enums to ensure proper serialization

### Literal Types

TypeScript literal unions map to Python Literal types:

**TypeScript:**
```typescript
export type QueueSource = "user_submission" | "automated_scan" | "scraper" | "webhook" | "email"
```

**Python:**
```python
from typing import Literal

QueueSource = Literal["user_submission", "automated_scan", "scraper", "webhook", "email"]
```

### Interface to Pydantic Model

TypeScript interfaces map to Pydantic BaseModel classes:

**TypeScript (https://github.com/Jdubz/job-finder-shared-types/blob/main/src/queue.types.ts):**
```typescript
export interface QueueItem {
  id?: string
  type: QueueItemType
  status: QueueStatus
  url: string
  company_name: string
  company_id: string | null
  source: QueueSource
  submitted_by: string | null
  retry_count: number
  max_retries: number
  result_message?: string
  error_details?: string
  created_at: Date | any
  updated_at: Date | any
  processed_at?: Date | any | null
  completed_at?: Date | any | null
}
```

**Python (src/job_finder/queue/models.py):**
```python
class JobQueueItem(BaseModel):
    """
    TypeScript equivalent: QueueItem interface in queue.types.ts
    """
    # Identity
    id: Optional[str] = None
    type: QueueItemType

    # Status tracking
    status: QueueStatus = Field(default=QueueStatus.PENDING)
    result_message: Optional[str] = None
    error_details: Optional[str] = None

    # Input data
    url: str
    company_name: str
    company_id: Optional[str] = None
    source: QueueSource = "scraper"
    submitted_by: Optional[str] = None

    # Processing data
    retry_count: int = 0
    max_retries: int = 3

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
```

**Mapping Rules:**
- `?` (optional) → `Optional[Type]` with default `None`
- Required fields → No Optional, no default value
- `Date | any` → `Optional[datetime]` (Firestore timestamps handled automatically)

## Keeping Types in Sync

### Modification Workflow

**ALWAYS follow this order:**

1. **Update TypeScript first** in the shared-types repository
   ```bash
   # Clone the repo if you haven't already
   git clone https://github.com/Jdubz/job-finder-shared-types.git
   cd job-finder-shared-types

   # Create feature branch and edit types
   git checkout -b feature/update-queue-types
   # Edit src/queue.types.ts
   ```

2. **Create PR and merge to main**
   ```bash
   git add src/queue.types.ts
   git commit -m "feat: update queue types"
   git push origin feature/update-queue-types
   # Create PR on GitHub and merge
   ```

3. **Publish new version to npm**
   - GitHub Actions will automatically publish when PR is merged to main
   - Or manually: `npm version patch && npm publish`

4. **Update Python models** in `src/job_finder/queue/models.py`
   ```bash
   cd /home/jdubz/Development/job-finder
   # Edit src/job_finder/queue/models.py to match TypeScript changes
   ```

5. **Test both projects**
   ```bash
   # Test job-finder
   cd /home/jdubz/Development/job-finder
   pytest tests/queue/

   # Test portfolio (after updating @jdubz/job-finder-shared-types version)
   cd /home/jdubz/Development/portfolio
   npm test
   ```

6. **Verify integration**
   - Run queue processor and check Firestore data structure
   - Verify portfolio UI displays queue data correctly
   - Check that status updates work in both directions

### Common Sync Issues

#### Issue 1: Missing Field in Python

**Symptom:** TypeScript has field that Python doesn't

**Fix:**
```python
# Add missing field to Python model
error_details: Optional[str] = Field(default=None, description="Error details")
```

#### Issue 2: Enum Value Mismatch

**Symptom:** `QueueStatus.PENDING` doesn't match TypeScript `"pending"`

**Fix:**
```python
# Ensure enum value (right side) matches TypeScript exactly
class QueueStatus(str, Enum):
    PENDING = "pending"  # Must match TypeScript "pending"
```

#### Issue 3: Optional vs Required Mismatch

**Symptom:** Field is optional in TypeScript but required in Python (or vice versa)

**Fix:**
```python
# TypeScript: company_name: string (required)
company_name: str  # Required in Python too

# TypeScript: company_id: string | null (optional)
company_id: Optional[str] = None  # Optional in Python
```

#### Issue 4: Timestamp Handling

**Symptom:** Timestamps not converting properly between Firestore and Python

**Fix:**
```python
# Python: Use Optional[datetime]
created_at: Optional[datetime] = None

# Firestore conversion happens automatically via FirestoreClient
```

## Firestore Integration

### Writing to Firestore (Python → Firestore)

```python
from job_finder.queue.models import JobQueueItem, QueueStatus

# Create queue item
item = JobQueueItem(
    type="job",
    url="https://example.com/job",
    company_name="Acme Corp",
    status=QueueStatus.PENDING
)

# Convert to Firestore document
data = item.to_firestore()  # Excludes None values, handles datetime conversion
```

### Reading from Firestore (Firestore → Python)

```python
# Get document from Firestore
doc = db.collection("job-queue").document(doc_id).get()
data = doc.to_dict()

# Convert to Python model
item = JobQueueItem.from_firestore(doc.id, data)
```

### Reading from Firestore (Firestore → TypeScript)

```typescript
import { QueueItem } from '@jdubz/job-finder-shared-types'

// Get document from Firestore
const doc = await db.collection('job-queue').doc(docId).get()
const item = doc.data() as QueueItem
```

## Available Types

### Queue Types (queue.types.ts)

All queue-related types from `@jdubz/job-finder-shared-types`:

- **`QueueStatus`** - Status enum for queue processing
- **`QueueItemType`** - Type of queue item (job or company)
- **`QueueSource`** - Source of queue submission
- **`QueueItem`** - Complete queue item structure (Python: `JobQueueItem`)
- **`StopList`** - Configuration for filtering jobs
- **`QueueSettings`** - Queue processing configuration
- **`AISettings`** - AI provider configuration
- **`JobMatch`** - AI-analyzed job match results
- **`QueueStats`** - Queue statistics
- **`SubmitJobRequest`** / **`SubmitJobResponse`** - API types

See https://github.com/Jdubz/job-finder-shared-types/blob/main/src/queue.types.ts for complete definitions.

## Testing Type Compatibility

### Unit Tests

Test that Python models can serialize/deserialize correctly:

```python
def test_queue_item_typescript_compatibility():
    """Ensure Python model matches TypeScript QueueItem interface."""
    item = JobQueueItem(
        type=QueueItemType.JOB,
        status=QueueStatus.PENDING,
        url="https://example.com/job",
        company_name="Test Corp",
        source="scraper"
    )

    # Should serialize without errors
    data = item.to_firestore()

    # Should deserialize without errors
    restored = JobQueueItem.from_firestore("test-id", data)

    assert restored.company_name == "Test Corp"
    assert restored.status == QueueStatus.PENDING
```

### Integration Tests

Test that Python writes data that TypeScript can read:

1. Python writes queue item to Firestore
2. Check Firestore console - verify field names match TypeScript
3. job-finder-FE reads queue item - verify no errors
4. job-finder-FE updates status - Python reads updated status

## Troubleshooting

### Type Mismatch Errors

**Error:** `ValidationError: company_name field required`

**Cause:** TypeScript changed `company_name` from optional to required, but Python still has `Optional[str]`

**Fix:** Update Python model to match TypeScript

### Enum Serialization Issues

**Error:** Firestore has `"PENDING"` instead of `"pending"`

**Cause:** Python enum not using `str, Enum` pattern

**Fix:**
```python
class QueueStatus(str, Enum):  # Must inherit from str first
    PENDING = "pending"
```

### Timestamp Conversion Errors

**Error:** `TypeError: Object of type datetime is not JSON serializable`

**Cause:** Using `model.model_dump()` instead of `model.to_firestore()`

**Fix:**
```python
# Use custom serialization
data = item.to_firestore()  # Handles datetime conversion
```

## Best Practices

1. **Always update TypeScript first** - It's the source of truth
2. **Add JSDoc comments in TypeScript** - They serve as documentation for Python developers
3. **Mirror field names exactly** - Don't use different names in Python
4. **Test both directions** - Python → Firestore → TypeScript and vice versa
5. **Use type hints everywhere** - Even if not strictly required
6. **Document deviations** - If Python must differ from TypeScript, document why

## Related Documentation

- **Shared Types Repository:** https://github.com/Jdubz/job-finder-shared-types
- **Shared Types README:** https://github.com/Jdubz/job-finder-shared-types#readme
- **Queue Types (TypeScript):** https://github.com/Jdubz/job-finder-shared-types/blob/main/src/queue.types.ts
- **Python Models:** `/home/jdubz/Development/job-finder/src/job_finder/queue/models.py`
- **Context Document:** `/home/jdubz/Development/job-finder/.claude/context.md`
- **job-finder-FE Integration:** `/home/jdubz/Development/job-finder/docs/integrations/portfolio.md`

---

**Last Updated:** 2025-10-17
