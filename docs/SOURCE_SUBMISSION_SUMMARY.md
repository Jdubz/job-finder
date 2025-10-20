# Source Submission Interface - Summary

Complete source submission interface for the job-finder queue system.

---

## What Is This?

The **source submission interface** allows your job-finder-FE frontend to submit job boards, RSS feeds, APIs, and career pages for automated scraping. The job-finder backend will:

1. **Detect** the source type (Greenhouse, Workday, RSS, etc.)
2. **Configure** the source automatically
3. **Validate** it works (test scrape)
4. **Create** a job-source document
5. **Enable** it for automated scraping (if validation passes)

---

## Quick Start

### TypeScript (job-finder-FE Frontend)

```typescript
import { addDoc, collection, Timestamp } from 'firebase/firestore'
import { db, auth } from '@/lib/firebase'

// Submit a Greenhouse board
const queueItem = {
  type: 'source_discovery',
  url: '',
  company_name: 'Stripe',
  company_id: 'stripe-doc-id',
  source: 'user_submission',
  submitted_by: auth.currentUser?.uid,
  source_discovery_config: {
    url: 'https://boards.greenhouse.io/stripe',
    type_hint: 'auto',  // System will auto-detect
    company_id: 'stripe-doc-id',
    company_name: 'Stripe',
    auto_enable: true,
    validation_required: false,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}

await addDoc(collection(db, 'job-queue'), queueItem)
```

---

## Supported Source Types

| Type | Example URL | Auto-Enable | Detection |
|------|-------------|-------------|-----------|
| **Greenhouse** | `boards.greenhouse.io/stripe` | ✅ Safe | URL pattern |
| **Workday** | `walmart.wd5.myworkdayjobs.com/...` | ⚠️ Needs validation | URL pattern |
| **RSS Feed** | `example.com/jobs/feed` | ✅ If valid | URL pattern |
| **Lever** | `jobs.lever.co/netflix` | 🚧 Planned | URL pattern |
| **Generic HTML** | `example.com/careers` | ⚠️ Needs validation | AI discovery |
| **API** | Custom endpoint | ⚠️ Needs config | Manual |

---

## Interface Definition

### TypeScript (Source of Truth)

```typescript
export type SourceTypeHint =
  | 'auto'        // Auto-detect from URL
  | 'greenhouse'  // Greenhouse board
  | 'workday'     // Workday board
  | 'lever'       // Lever board
  | 'rss'         // RSS feed
  | 'api'         // External API
  | 'generic'     // Generic HTML scraper

export interface SourceDiscoveryConfig {
  url: string                          // URL to discover
  type_hint?: SourceTypeHint           // Optional type hint (default: 'auto')
  company_id?: string | null           // Link to company document
  company_name?: string | null         // Company name
  auto_enable?: boolean                // Auto-enable if valid (default: true)
  validation_required?: boolean        // Require manual review (default: false)
  api_config?: Record<string, any>     // Custom API config (for API sources)
}

export interface QueueItem {
  type: 'source_discovery'
  url: string  // Empty for SOURCE_DISCOVERY
  company_name: string
  company_id: string | null
  source: 'user_submission'
  submitted_by: string | null
  source_discovery_config?: SourceDiscoveryConfig
  status: 'pending' | 'processing' | 'success' | 'failed'
  created_at: Date
  result_message?: string
  error_details?: string
}
```

### Python (Mirror)

```python
class SourceTypeHint(str, Enum):
    AUTO = "auto"
    GREENHOUSE = "greenhouse"
    WORKDAY = "workday"
    LEVER = "lever"
    RSS = "rss"
    API = "api"
    GENERIC = "generic"

class SourceDiscoveryConfig(BaseModel):
    url: str
    type_hint: Optional[SourceTypeHint] = SourceTypeHint.AUTO
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    auto_enable: bool = True
    validation_required: bool = False
    api_config: Optional[Dict[str, Any]] = None
```

---

## Processing Flow

```
User submits URL
     ↓
Queue item created (type: source_discovery)
     ↓
Job-finder processes item
     ├─ Detects source type (greenhouse/workday/rss/generic)
     ├─ Extracts configuration
     ├─ Validates (test scrape)
     └─ Creates job-source document
     ↓
Queue item updated (status: success/failed)
     ↓
job-finder-FE monitors and shows result
```

---

## Examples by Source Type

### 1. Greenhouse Board

```typescript
{
  type: 'source_discovery',
  url: '',
  company_name: 'Stripe',
  company_id: 'stripe-id',
  source: 'user_submission',
  submitted_by: auth.currentUser?.uid,
  source_discovery_config: {
    url: 'https://boards.greenhouse.io/stripe',
    type_hint: 'greenhouse',
    company_id: 'stripe-id',
    company_name: 'Stripe',
    auto_enable: true,  // ✅ Safe
    validation_required: false,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

**Result**: Creates source with high confidence, auto-enabled.

---

### 2. Workday Board

```typescript
{
  type: 'source_discovery',
  url: '',
  company_name: 'Walmart',
  company_id: 'walmart-id',
  source: 'user_submission',
  submitted_by: auth.currentUser?.uid,
  source_discovery_config: {
    url: 'https://walmart.wd5.myworkdayjobs.com/WalmartExternal',
    type_hint: 'workday',
    company_id: 'walmart-id',
    company_name: 'Walmart',
    auto_enable: false,  // ⚠️ Needs validation
    validation_required: true,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

**Result**: Creates source with medium confidence, requires manual test.

---

### 3. RSS Feed

```typescript
{
  type: 'source_discovery',
  url: '',
  company_name: 'Example Corp',
  company_id: 'example-id',
  source: 'user_submission',
  submitted_by: auth.currentUser?.uid,
  source_discovery_config: {
    url: 'https://example.com/jobs/feed',
    type_hint: 'rss',
    company_id: 'example-id',
    company_name: 'Example Corp',
    auto_enable: true,  // ✅ Safe if feed is valid
    validation_required: false,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

**Result**: Creates source with high confidence if feed is valid, auto-enabled.

---

### 4. Generic Career Page

```typescript
{
  type: 'source_discovery',
  url: '',
  company_name: 'Example Corp',
  company_id: 'example-id',
  source: 'user_submission',
  submitted_by: auth.currentUser?.uid,
  source_discovery_config: {
    url: 'https://example.com/careers',
    type_hint: 'generic',
    company_id: 'example-id',
    company_name: 'Example Corp',
    auto_enable: false,  // ⚠️ AI discovery needs validation
    validation_required: true,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

**Result**: Uses AI to discover CSS selectors, requires manual validation.

---

## Monitoring Results

```typescript
import { onSnapshot, doc } from 'firebase/firestore'

const unsubscribe = onSnapshot(
  doc(db, 'job-queue', queueItemId),
  (snapshot) => {
    const item = snapshot.data()

    if (item.status === 'success') {
      // Extract source ID from result_message
      // Format: "Created source: {source_id}"
      const sourceId = item.result_message?.split(': ')[1]
      console.log('Source created:', sourceId)
    } else if (item.status === 'failed') {
      console.error('Failed:', item.result_message)
      console.error('Details:', item.error_details)
    } else if (item.status === 'processing') {
      console.log('Processing...')
    }
  }
)
```

---

## Best Practices

### DO ✅

- **Auto-detect types** with `type_hint: 'auto'`
- **Provide company_id** when submitting from company page
- **Auto-enable Greenhouse/RSS** (safe, high confidence)
- **Require validation for generic scrapers** (AI-discovered)
- **Monitor queue items** to show status to users
- **Handle errors gracefully** in UI

### DON'T ❌

- **Don't auto-enable Workday** (requires manual testing)
- **Don't auto-enable generic** (AI selectors need validation)
- **Don't submit duplicates** (check existing sources first)
- **Don't ignore error_details** (useful for debugging)
- **Don't assume immediate success** (processing takes time)

---

## Error Handling

### Common Errors

**URL not accessible**:
```
status: "failed"
result_message: "Failed to fetch URL"
error_details: "HTTP 404: Not Found"
```

**No jobs found**:
```
status: "failed"
result_message: "Failed to validate source"
error_details: "No jobs found at URL"
```

**Invalid RSS feed**:
```
status: "failed"
result_message: "Failed to parse RSS feed"
error_details: "Invalid XML format"
```

**AI discovery failed**:
```
status: "failed"
result_message: "Failed to discover selectors"
error_details: "Could not identify job listings on page"
```

---

## Helper Functions

### Submit Source

```typescript
export async function submitSource(
  url: string,
  companyId: string | null,
  companyName: string,
  typeHint: SourceTypeHint = 'auto',
  autoEnable: boolean = true
): Promise<string> {
  const queueItem = {
    type: 'source_discovery' as const,
    url: '',
    company_name: companyName,
    company_id: companyId,
    source: 'user_submission' as const,
    submitted_by: auth.currentUser?.uid || null,
    source_discovery_config: {
      url,
      type_hint: typeHint,
      company_id: companyId,
      company_name: companyName,
      auto_enable: autoEnable,
      validation_required: !autoEnable,
    },
    status: 'pending' as const,
    created_at: Timestamp.now(),
  }

  const docRef = await addDoc(collection(db, 'job-queue'), queueItem)
  return docRef.id
}
```

### Monitor Submission

```typescript
export function monitorSubmission(
  queueItemId: string,
  onSuccess: (sourceId: string) => void,
  onFailure: (error: string) => void
) {
  return onSnapshot(doc(db, 'job-queue', queueItemId), (snapshot) => {
    const item = snapshot.data()

    if (item.status === 'success') {
      const sourceId = item.result_message?.split(': ')[1]
      if (sourceId) onSuccess(sourceId)
    } else if (item.status === 'failed') {
      onFailure(item.result_message || 'Unknown error')
    }
  })
}
```

---

## Documentation

**Complete guides**:
- [SOURCE_SUBMISSION_API.md](SOURCE_SUBMISSION_API.md) - Full API reference
- [SOURCE_SUBMISSION_QUICK_REF.md](SOURCE_SUBMISSION_QUICK_REF.md) - Code snippets
- [SOURCE_SUBMISSION_DESIGN.md](SOURCE_SUBMISSION_DESIGN.md) - Architecture

**Related docs**:
- [shared-types.md](shared-types.md) - TypeScript/Python type mapping
- [CLAUDE.md](../CLAUDE.md) - System overview

---

## Summary

**The source submission interface handles all types of job sources:**

✅ **Job boards** - Greenhouse, Workday, Lever (auto-configured)
✅ **RSS feeds** - Job posting feeds (validated)
✅ **APIs** - Custom job APIs (manual config)
✅ **Generic scrapers** - Any career page (AI discovery)

**Submit via `SOURCE_DISCOVERY` queue type with:**
- `url` - The URL to discover
- `type_hint` - Type hint or `'auto'`
- `company_id` - Link to company
- `auto_enable` - Safe for Greenhouse/RSS, false for others
- `validation_required` - True for low-confidence sources

**Monitor queue item status** to show results to users.

**Simple, flexible, handles all cases.** 🚀
