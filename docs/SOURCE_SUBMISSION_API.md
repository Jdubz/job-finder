# Source Submission API Reference

Complete guide to submitting job sources through the queue system.

---

## Overview

The source submission API allows you to discover and configure new job sources for automated scraping. Sources can be:

- **Job boards** (Greenhouse, Workday, Lever, etc.)
- **RSS feeds** (job posting feeds)
- **APIs** (external job APIs)
- **Generic scrapers** (any company career page)

All sources are submitted via the **`SOURCE_DISCOVERY`** queue item type.

---

## Quick Start

### Basic Submission (TypeScript)

```typescript
import { addDoc, collection, Timestamp } from 'firebase/firestore'
import { db } from '@/lib/firebase'

// Submit a source for discovery
const queueItem = {
  type: 'source_discovery',
  url: '',  // Not used for SOURCE_DISCOVERY
  company_name: companyName || '',
  company_id: companyId || null,
  source: 'user_submission',
  submitted_by: currentUser?.uid || null,
  source_discovery_config: {
    url: 'https://boards.greenhouse.io/stripe',  // URL to discover
    type_hint: 'auto',  // Let system auto-detect
    company_id: companyId,
    company_name: companyName,
    auto_enable: true,  // Enable immediately if validation succeeds
    validation_required: false,  // Don't require manual review
  },
  status: 'pending',
  created_at: Timestamp.now(),
}

const docRef = await addDoc(collection(db, 'job-queue'), queueItem)
console.log('Source submitted:', docRef.id)
```

---

## Supported Source Types

### 1. Greenhouse Boards

**Detection**: URL contains `boards.greenhouse.io/{token}`

**Auto-configured**: ✅ Yes (high confidence)

**Example URLs**:
- `https://boards.greenhouse.io/stripe`
- `https://boards.greenhouse.io/netflix/jobs/123` (will extract `netflix`)

**Submission**:
```typescript
const queueItem = {
  type: 'source_discovery',
  url: '',
  company_name: 'Stripe',
  company_id: 'stripe-doc-id',
  source: 'user_submission',
  source_discovery_config: {
    url: 'https://boards.greenhouse.io/stripe',
    type_hint: 'greenhouse',  // or 'auto'
    company_id: 'stripe-doc-id',
    company_name: 'Stripe',
    auto_enable: true,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

**Auto-generated Config**:
```javascript
{
  source_type: "greenhouse",
  config: {
    board_token: "stripe",
    api_url: "https://boards-api.greenhouse.io/v1/boards/stripe/jobs"
  },
  enabled: true,
  confidence: "high"
}
```

---

### 2. Workday Boards

**Detection**: URL contains `*.wd*.myworkdayjobs.com/{company}`

**Auto-configured**: ⚠️ Partial (medium confidence, requires manual validation)

**Example URLs**:
- `https://walmart.wd5.myworkdayjobs.com/WalmartExternal`
- `https://att.wd1.myworkdayjobs.com/ATT_External`

**Submission**:
```typescript
const queueItem = {
  type: 'source_discovery',
  url: '',
  company_name: 'Walmart',
  company_id: 'walmart-doc-id',
  source: 'user_submission',
  source_discovery_config: {
    url: 'https://walmart.wd5.myworkdayjobs.com/WalmartExternal',
    type_hint: 'workday',  // or 'auto'
    company_id: 'walmart-doc-id',
    company_name: 'Walmart',
    auto_enable: false,  // Requires manual validation
    validation_required: true,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

**Auto-generated Config**:
```javascript
{
  source_type: "workday",
  config: {
    company_id: "walmart",
    base_url: "https://walmart.wd5.myworkdayjobs.com"
  },
  enabled: false,  // Requires manual testing
  confidence: "medium"
}
```

---

### 3. RSS Feeds

**Detection**: URL ends with `.xml`, `/feed`, `/rss`, or `.rss`

**Auto-configured**: ✅ Yes (high confidence if feed is valid)

**Example URLs**:
- `https://example.com/jobs/feed`
- `https://example.com/careers.xml`
- `https://example.com/rss`

**Submission**:
```typescript
const queueItem = {
  type: 'source_discovery',
  url: '',
  company_name: 'Example Corp',
  company_id: 'example-doc-id',
  source: 'user_submission',
  source_discovery_config: {
    url: 'https://example.com/jobs/feed',
    type_hint: 'rss',  // or 'auto'
    company_id: 'example-doc-id',
    company_name: 'Example Corp',
    auto_enable: true,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

**Auto-generated Config**:
```javascript
{
  source_type: "rss",
  config: {
    url: "https://example.com/jobs/feed",
    format: "rss2.0"  // or "atom"
  },
  enabled: true,
  confidence: "high"
}
```

---

### 4. Lever Boards (Future)

**Detection**: URL contains `jobs.lever.co/{company}`

**Auto-configured**: 🚧 Planned

**Example URLs**:
- `https://jobs.lever.co/netflix`
- `https://jobs.lever.co/stripe/123`

**Submission**:
```typescript
const queueItem = {
  type: 'source_discovery',
  url: '',
  company_name: 'Netflix',
  company_id: 'netflix-doc-id',
  source: 'user_submission',
  source_discovery_config: {
    url: 'https://jobs.lever.co/netflix',
    type_hint: 'auto',
    company_id: 'netflix-doc-id',
    company_name: 'Netflix',
    auto_enable: true,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

---

### 5. Generic HTML Scrapers

**Detection**: Any URL that doesn't match known patterns

**Auto-configured**: ⚠️ AI-powered (variable confidence)

**Example URLs**:
- `https://example.com/careers`
- `https://example.com/jobs`
- Any company career page

**Submission**:
```typescript
const queueItem = {
  type: 'source_discovery',
  url: '',
  company_name: 'Example Corp',
  company_id: 'example-doc-id',
  source: 'user_submission',
  source_discovery_config: {
    url: 'https://example.com/careers',
    type_hint: 'generic',  // or 'auto'
    company_id: 'example-doc-id',
    company_name: 'Example Corp',
    auto_enable: false,  // Usually requires validation
    validation_required: true,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

**Auto-generated Config** (AI-discovered selectors):
```javascript
{
  source_type: "scraper",
  config: {
    base_url: "https://example.com/careers",
    selectors: {
      job_list: ".job-listing",
      title: ".job-title",
      company: ".company-name",
      location: ".location",
      url: "a.apply-link",
      description: ".job-description"
    },
    alternative_selectors: [
      // Fallback selectors discovered by AI
    ]
  },
  enabled: false,  // Requires manual testing
  confidence: "low" | "medium" | "high"  // Based on AI confidence
}
```

---

### 6. External APIs (Future)

**Detection**: Manual specification via `type_hint: 'api'`

**Auto-configured**: ❌ Requires manual configuration

**Example submission**:
```typescript
const queueItem = {
  type: 'source_discovery',
  url: '',
  company_name: 'LinkedIn Jobs API',
  source: 'user_submission',
  source_discovery_config: {
    url: 'https://api.linkedin.com/v2/jobs',
    type_hint: 'api',
    api_config: {
      // Custom API configuration
      auth_type: 'oauth',
      endpoint: '/jobs/search',
      rate_limit: 100,
    },
    auto_enable: false,
    validation_required: true,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

---

## Type Definitions

### TypeScript (Source of Truth)

**File**: `@jdubz/job-finder-shared-types/src/queue.types.ts`

```typescript
/**
 * Source type hint for discovery.
 * Guides the detection algorithm.
 */
export type SourceTypeHint =
  | 'auto'        // Auto-detect from URL
  | 'greenhouse'  // Greenhouse job board
  | 'workday'     // Workday job board
  | 'lever'       // Lever job board
  | 'rss'         // RSS feed
  | 'api'         // External API
  | 'generic'     // Generic HTML scraper

/**
 * Configuration for source discovery requests.
 */
export interface SourceDiscoveryConfig {
  /**
   * URL to analyze and configure.
   * Can be:
   * - Greenhouse board: https://boards.greenhouse.io/{token}
   * - Workday board: https://{company}.wd{n}.myworkdayjobs.com/{path}
   * - RSS feed: https://example.com/feed
   * - Generic page: https://example.com/careers
   */
  url: string

  /**
   * Optional hint about source type.
   * If not provided or set to 'auto', system will detect automatically.
   * @default 'auto'
   */
  type_hint?: SourceTypeHint

  /**
   * Company document ID in Firestore.
   * Links the source to a specific company.
   * @optional
   */
  company_id?: string | null

  /**
   * Company name.
   * Used for display and if company_id not provided.
   * @optional
   */
  company_name?: string | null

  /**
   * Auto-enable source if discovery succeeds.
   * If false, source will be created but disabled.
   * @default true
   */
  auto_enable?: boolean

  /**
   * Require manual validation before enabling.
   * If true, source will be flagged for review even if discovery succeeds.
   * @default false
   */
  validation_required?: boolean

  /**
   * Custom API configuration (for API sources only).
   * @optional
   */
  api_config?: Record<string, any>
}

/**
 * Queue item for source discovery.
 */
export interface QueueItem {
  id?: string
  type: QueueItemType  // Must be 'source_discovery'
  url: string          // Empty string for SOURCE_DISCOVERY
  company_name: string
  company_id: string | null
  source: QueueSource
  submitted_by: string | null
  status: QueueStatus
  created_at: Date

  /**
   * Source discovery configuration.
   * Required when type is 'source_discovery'.
   */
  source_discovery_config?: SourceDiscoveryConfig
}
```

---

### Python (Mirror of TypeScript)

**File**: `src/job_finder/queue/models.py`

```python
class SourceTypeHint(str, Enum):
    """
    Source type hint for discovery.
    TypeScript equivalent: SourceTypeHint in queue.types.ts
    """
    AUTO = "auto"
    GREENHOUSE = "greenhouse"
    WORKDAY = "workday"
    LEVER = "lever"
    RSS = "rss"
    API = "api"
    GENERIC = "generic"


class SourceDiscoveryConfig(BaseModel):
    """
    Configuration for source discovery requests.
    TypeScript equivalent: SourceDiscoveryConfig in queue.types.ts
    """
    url: str = Field(description="URL to analyze and configure")
    type_hint: Optional[SourceTypeHint] = Field(
        default=SourceTypeHint.AUTO,
        description="Optional hint about source type"
    )
    company_id: Optional[str] = Field(
        default=None,
        description="Optional company reference"
    )
    company_name: Optional[str] = Field(
        default=None,
        description="Optional company name"
    )
    auto_enable: bool = Field(
        default=True,
        description="Auto-enable if discovery succeeds (default: true)"
    )
    validation_required: bool = Field(
        default=False,
        description="Require manual validation before enabling (default: false)"
    )
    api_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Custom API configuration (for API sources only)"
    )
```

---

## Queue Item Structure

### Complete Example

```typescript
{
  // Queue item metadata
  id: "abc123",  // Auto-generated by Firestore
  type: "source_discovery",
  status: "pending",
  created_at: Timestamp,
  updated_at: Timestamp,

  // Submission metadata
  url: "",  // Always empty for SOURCE_DISCOVERY
  company_name: "Stripe",
  company_id: "stripe-doc-id",
  source: "user_submission",
  submitted_by: "user-uid",

  // Discovery configuration
  source_discovery_config: {
    url: "https://boards.greenhouse.io/stripe",
    type_hint: "auto",
    company_id: "stripe-doc-id",
    company_name: "Stripe",
    auto_enable: true,
    validation_required: false
  },

  // Processing results (populated after processing)
  result_message: "Created source: greenhouse-stripe",  // On success
  error_details: null,  // On failure
  retry_count: 0,
  max_retries: 3
}
```

---

## Processing Flow

### 1. Type Detection

```
User submits URL → Auto-detect source type
├─ boards.greenhouse.io/* → greenhouse
├─ *.myworkdayjobs.com/* → workday
├─ jobs.lever.co/* → lever
├─ *.xml, */feed, */rss → rss
└─ * → generic
```

### 2. Configuration Extraction

**Greenhouse**:
- Extract `board_token` from URL
- Build API URL: `https://boards-api.greenhouse.io/v1/boards/{token}/jobs`

**Workday**:
- Extract `company_id` from subdomain
- Extract `base_url` from URL

**RSS**:
- Test feed parsing
- Detect format (RSS 2.0, Atom, etc.)

**Generic**:
- Fetch HTML
- Use AI to discover CSS selectors
- Test selectors on sample jobs

### 3. Validation

**Test scrape**:
- Fetch jobs using discovered configuration
- Verify at least 1 job found
- Verify required fields present

**Assign confidence**:
- **High**: Known type (Greenhouse, valid RSS)
- **Medium**: Workday, validated AI selectors
- **Low**: Unvalidated AI selectors

### 4. Source Creation

**Create job-source document**:
```javascript
{
  id: "greenhouse-stripe",
  name: "Stripe (Greenhouse)",
  company_id: "stripe-doc-id",
  company_name: "Stripe",
  source_type: "greenhouse",
  config: { ... },
  enabled: true,  // Based on auto_enable and confidence
  confidence: "high",
  created_at: Timestamp,
  created_by: "source_discovery",
  health: {
    consecutive_failures: 0,
    last_success: null,
    last_failure: null
  }
}
```

### 5. Queue Item Update

**On success**:
```javascript
{
  status: "success",
  result_message: "Created source: greenhouse-stripe",
  completed_at: Timestamp
}
```

**On failure**:
```javascript
{
  status: "failed",
  result_message: "Failed to validate source",
  error_details: "No jobs found at URL",
  completed_at: Timestamp
}
```

---

## Monitoring Submissions

### Check Queue Item Status

```typescript
// In job-finder-FE project
const unsubscribe = onSnapshot(
  doc(db, 'job-queue', queueItemId),
  (snapshot) => {
    const item = snapshot.data()

    if (item.status === 'success') {
      console.log('Source created:', item.result_message)
      // Extract source ID from result_message
      const sourceId = item.result_message.split(': ')[1]
    } else if (item.status === 'failed') {
      console.error('Discovery failed:', item.result_message)
      console.error('Details:', item.error_details)
    } else if (item.status === 'processing') {
      console.log('Discovery in progress...')
    }
  }
)
```

### Check Created Source

```typescript
// After successful discovery
const sourceDoc = await getDoc(doc(db, 'job-sources', sourceId))
const source = sourceDoc.data()

console.log('Source type:', source.source_type)
console.log('Enabled:', source.enabled)
console.log('Confidence:', source.confidence)
console.log('Config:', source.config)
```

---

## Best Practices

### DO ✅

- **Provide company_id** when known (links source to company)
- **Use type_hint** if you know the source type (faster processing)
- **Set auto_enable=false** for untested sources (requires validation)
- **Set validation_required=true** for low-confidence sources
- **Monitor queue item** to check success/failure
- **Handle failures gracefully** in UI

### DON'T ❌

- **Don't submit duplicates** (check existing sources first)
- **Don't auto-enable generic scrapers** (they need validation)
- **Don't ignore error_details** (contains useful debugging info)
- **Don't assume immediate success** (processing takes time)

---

## Error Handling

### Common Errors

**URL not accessible**:
```javascript
{
  status: "failed",
  result_message: "Failed to fetch URL",
  error_details: "HTTP 404: Not Found"
}
```

**No jobs found**:
```javascript
{
  status: "failed",
  result_message: "Failed to validate source",
  error_details: "No jobs found at URL"
}
```

**Invalid RSS feed**:
```javascript
{
  status: "failed",
  result_message: "Failed to parse RSS feed",
  error_details: "Invalid XML format"
}
```

**AI selector discovery failed**:
```javascript
{
  status: "failed",
  result_message: "Failed to discover selectors",
  error_details: "Could not identify job listings on page"
}
```

---

## Examples by Use Case

### Example 1: User Adds Greenhouse Board

**Scenario**: User finds a Greenhouse board and wants to track it.

**Frontend code**:
```typescript
async function addGreenhouseSource(
  greenhouseUrl: string,
  companyId: string,
  companyName: string
) {
  const queueItem = {
    type: 'source_discovery',
    url: '',
    company_name: companyName,
    company_id: companyId,
    source: 'user_submission',
    submitted_by: currentUser.uid,
    source_discovery_config: {
      url: greenhouseUrl,
      type_hint: 'greenhouse',
      company_id: companyId,
      company_name: companyName,
      auto_enable: true,  // Safe for Greenhouse
      validation_required: false,
    },
    status: 'pending',
    created_at: Timestamp.now(),
  }

  const docRef = await addDoc(collection(db, 'job-queue'), queueItem)
  return docRef.id
}

// Usage
const queueItemId = await addGreenhouseSource(
  'https://boards.greenhouse.io/stripe',
  'stripe-doc-id',
  'Stripe'
)

// Monitor result
const unsubscribe = onSnapshot(doc(db, 'job-queue', queueItemId), (snap) => {
  const item = snap.data()
  if (item.status === 'success') {
    showSuccessToast('Source added successfully!')
  } else if (item.status === 'failed') {
    showErrorToast(`Failed: ${item.result_message}`)
  }
})
```

---

### Example 2: User Adds Generic Career Page

**Scenario**: User finds a company career page without a known job board.

**Frontend code**:
```typescript
async function addGenericSource(
  careerPageUrl: string,
  companyId: string,
  companyName: string
) {
  const queueItem = {
    type: 'source_discovery',
    url: '',
    company_name: companyName,
    company_id: companyId,
    source: 'user_submission',
    submitted_by: currentUser.uid,
    source_discovery_config: {
      url: careerPageUrl,
      type_hint: 'auto',  // Let system detect
      company_id: companyId,
      company_name: companyName,
      auto_enable: false,  // Require validation
      validation_required: true,
    },
    status: 'pending',
    created_at: Timestamp.now(),
  }

  const docRef = await addDoc(collection(db, 'job-queue'), queueItem)
  return docRef.id
}

// Usage
const queueItemId = await addGenericSource(
  'https://example.com/careers',
  'example-doc-id',
  'Example Corp'
)

// Monitor and handle validation requirement
const unsubscribe = onSnapshot(doc(db, 'job-queue', queueItemId), (snap) => {
  const item = snap.data()
  if (item.status === 'success') {
    showInfoToast('Source created but requires validation')
    // Navigate to source validation page
    router.push(`/sources/${item.result_message.split(': ')[1]}/validate`)
  } else if (item.status === 'failed') {
    showErrorToast(`Discovery failed: ${item.result_message}`)
  }
})
```

---

### Example 3: Bulk Import from List

**Scenario**: Import multiple known Greenhouse boards.

**Frontend code**:
```typescript
async function bulkImportSources(
  sources: Array<{url: string, companyId: string, companyName: string}>
) {
  const results = []

  for (const source of sources) {
    try {
      const queueItem = {
        type: 'source_discovery',
        url: '',
        company_name: source.companyName,
        company_id: source.companyId,
        source: 'user_submission',
        submitted_by: currentUser.uid,
        source_discovery_config: {
          url: source.url,
          type_hint: 'auto',
          company_id: source.companyId,
          company_name: source.companyName,
          auto_enable: true,
          validation_required: false,
        },
        status: 'pending',
        created_at: Timestamp.now(),
      }

      const docRef = await addDoc(collection(db, 'job-queue'), queueItem)
      results.push({ success: true, id: docRef.id, source })
    } catch (error) {
      results.push({ success: false, error, source })
    }
  }

  return results
}

// Usage
const greenhouseBoards = [
  { url: 'https://boards.greenhouse.io/stripe', companyId: 'stripe-id', companyName: 'Stripe' },
  { url: 'https://boards.greenhouse.io/netflix', companyId: 'netflix-id', companyName: 'Netflix' },
  // ... more boards
]

const results = await bulkImportSources(greenhouseBoards)
console.log(`Imported ${results.filter(r => r.success).length} sources`)
```

---

## Summary

**Key Points**:

✅ **All sources** submitted via `SOURCE_DISCOVERY` queue type
✅ **Auto-detection** for known types (Greenhouse, Workday, RSS)
✅ **AI discovery** for generic HTML scrapers
✅ **Validation** before enabling sources
✅ **Confidence levels** guide auto-enable decisions
✅ **Type hints** for faster/more accurate detection
✅ **Monitor queue items** for success/failure status

**For detailed implementation**, see:
- [SOURCE_SUBMISSION_DESIGN.md](SOURCE_SUBMISSION_DESIGN.md) - Architecture
- [CLAUDE.md](../CLAUDE.md) - Source discovery system overview
- `src/job_finder/queue/processor.py:_process_source_discovery()` - Implementation
