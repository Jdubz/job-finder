# Source Submission Quick Reference

Fast code snippets for submitting job sources.

---

## Basic Template

```typescript
import { addDoc, collection, Timestamp } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { auth } from '@/lib/firebase'

// Basic source submission template
const queueItem = {
  type: 'source_discovery',
  url: '',  // Always empty for source_discovery
  company_name: 'Company Name',
  company_id: 'company-doc-id',  // Or null
  source: 'user_submission',
  submitted_by: auth.currentUser?.uid || null,
  source_discovery_config: {
    url: 'https://example.com/url-to-discover',
    type_hint: 'auto',  // or specific type
    company_id: 'company-doc-id',
    company_name: 'Company Name',
    auto_enable: true,
    validation_required: false,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}

const docRef = await addDoc(collection(db, 'job-queue'), queueItem)
console.log('Submitted:', docRef.id)
```

---

## Source Type Snippets

### Greenhouse Board

```typescript
// ✅ Auto-enable safe
{
  type: 'source_discovery',
  url: '',
  company_name: 'Stripe',
  company_id: 'stripe-id',
  source: 'user_submission',
  submitted_by: auth.currentUser?.uid,
  source_discovery_config: {
    url: 'https://boards.greenhouse.io/stripe',
    type_hint: 'greenhouse',  // or 'auto'
    company_id: 'stripe-id',
    company_name: 'Stripe',
    auto_enable: true,  // ✅ Safe for Greenhouse
    validation_required: false,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

### Workday Board

```typescript
// ⚠️ Requires validation
{
  type: 'source_discovery',
  url: '',
  company_name: 'Walmart',
  company_id: 'walmart-id',
  source: 'user_submission',
  submitted_by: auth.currentUser?.uid,
  source_discovery_config: {
    url: 'https://walmart.wd5.myworkdayjobs.com/WalmartExternal',
    type_hint: 'workday',  // or 'auto'
    company_id: 'walmart-id',
    company_name: 'Walmart',
    auto_enable: false,  // ⚠️ Needs manual test
    validation_required: true,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

### RSS Feed

```typescript
// ✅ Auto-enable if valid
{
  type: 'source_discovery',
  url: '',
  company_name: 'Example Corp',
  company_id: 'example-id',
  source: 'user_submission',
  submitted_by: auth.currentUser?.uid,
  source_discovery_config: {
    url: 'https://example.com/jobs/feed',
    type_hint: 'rss',  // or 'auto'
    company_id: 'example-id',
    company_name: 'Example Corp',
    auto_enable: true,  // ✅ Safe if feed is valid
    validation_required: false,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

### Generic Career Page

```typescript
// ⚠️ Requires validation
{
  type: 'source_discovery',
  url: '',
  company_name: 'Example Corp',
  company_id: 'example-id',
  source: 'user_submission',
  submitted_by: auth.currentUser?.uid,
  source_discovery_config: {
    url: 'https://example.com/careers',
    type_hint: 'generic',  // or 'auto'
    company_id: 'example-id',
    company_name: 'Example Corp',
    auto_enable: false,  // ⚠️ AI discovery needs validation
    validation_required: true,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

---

## Helper Functions

### Submit Source Function

```typescript
/**
 * Submit a source for discovery.
 *
 * @param url - URL to discover
 * @param companyId - Company document ID
 * @param companyName - Company name
 * @param typeHint - Optional type hint (auto, greenhouse, workday, rss, generic)
 * @param autoEnable - Auto-enable if validation succeeds
 * @returns Queue item document ID
 */
export async function submitSource(
  url: string,
  companyId: string | null,
  companyName: string,
  typeHint: 'auto' | 'greenhouse' | 'workday' | 'rss' | 'generic' = 'auto',
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

// Usage
const queueItemId = await submitSource(
  'https://boards.greenhouse.io/stripe',
  'stripe-id',
  'Stripe',
  'greenhouse',
  true
)
```

### Monitor Submission Function

```typescript
/**
 * Monitor a source submission.
 *
 * @param queueItemId - Queue item document ID
 * @param onSuccess - Callback when discovery succeeds
 * @param onFailure - Callback when discovery fails
 * @returns Unsubscribe function
 */
export function monitorSubmission(
  queueItemId: string,
  onSuccess: (sourceId: string) => void,
  onFailure: (error: string, details: string | null) => void
) {
  return onSnapshot(
    doc(db, 'job-queue', queueItemId),
    (snapshot) => {
      const item = snapshot.data()

      if (item.status === 'success') {
        // Extract source ID from result_message
        // Format: "Created source: {source_id}"
        const sourceId = item.result_message?.split(': ')[1]
        if (sourceId) {
          onSuccess(sourceId)
        }
      } else if (item.status === 'failed') {
        onFailure(
          item.result_message || 'Unknown error',
          item.error_details || null
        )
      }
    },
    (error) => {
      console.error('Error monitoring submission:', error)
      onFailure('Failed to monitor submission', error.message)
    }
  )
}

// Usage
const unsubscribe = monitorSubmission(
  queueItemId,
  (sourceId) => {
    console.log('Source created:', sourceId)
    showSuccessToast('Source added successfully!')
  },
  (error, details) => {
    console.error('Discovery failed:', error, details)
    showErrorToast(`Failed: ${error}`)
  }
)
```

### Complete Flow Example

```typescript
/**
 * Submit a source and monitor its discovery.
 */
export async function addAndMonitorSource(
  url: string,
  companyId: string | null,
  companyName: string,
  typeHint: 'auto' | 'greenhouse' | 'workday' | 'rss' | 'generic' = 'auto'
): Promise<{sourceId: string} | {error: string}> {
  return new Promise((resolve, reject) => {
    // Submit source
    submitSource(url, companyId, companyName, typeHint, true)
      .then((queueItemId) => {
        console.log('Submitted source, monitoring...')

        // Monitor result
        const unsubscribe = monitorSubmission(
          queueItemId,
          (sourceId) => {
            unsubscribe()
            resolve({ sourceId })
          },
          (error, details) => {
            unsubscribe()
            resolve({ error: `${error}${details ? `: ${details}` : ''}` })
          }
        )
      })
      .catch((error) => {
        reject(error)
      })
  })
}

// Usage
try {
  const result = await addAndMonitorSource(
    'https://boards.greenhouse.io/stripe',
    'stripe-id',
    'Stripe',
    'greenhouse'
  )

  if ('sourceId' in result) {
    console.log('Success! Source ID:', result.sourceId)
  } else {
    console.error('Failed:', result.error)
  }
} catch (error) {
  console.error('Submission error:', error)
}
```

---

## React Component Example

```typescript
import { useState } from 'react'
import { addDoc, collection, Timestamp, onSnapshot, doc } from 'firebase/firestore'
import { db, auth } from '@/lib/firebase'

export function AddSourceForm() {
  const [url, setUrl] = useState('')
  const [companyId, setCompanyId] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [typeHint, setTypeHint] = useState<'auto' | 'greenhouse' | 'workday' | 'rss' | 'generic'>('auto')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setStatus('Submitting...')

    try {
      // Create queue item
      const queueItem = {
        type: 'source_discovery' as const,
        url: '',
        company_name: companyName,
        company_id: companyId || null,
        source: 'user_submission' as const,
        submitted_by: auth.currentUser?.uid || null,
        source_discovery_config: {
          url,
          type_hint: typeHint,
          company_id: companyId || null,
          company_name: companyName,
          auto_enable: typeHint === 'greenhouse' || typeHint === 'rss',
          validation_required: typeHint !== 'greenhouse' && typeHint !== 'rss',
        },
        status: 'pending' as const,
        created_at: Timestamp.now(),
      }

      const docRef = await addDoc(collection(db, 'job-queue'), queueItem)
      setStatus('Processing...')

      // Monitor result
      const unsubscribe = onSnapshot(
        doc(db, 'job-queue', docRef.id),
        (snapshot) => {
          const item = snapshot.data()

          if (item?.status === 'success') {
            setStatus(`Success! ${item.result_message}`)
            setLoading(false)
            unsubscribe()
          } else if (item?.status === 'failed') {
            setStatus(`Failed: ${item.result_message}`)
            setLoading(false)
            unsubscribe()
          }
        }
      )
    } catch (error) {
      setStatus(`Error: ${error.message}`)
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="url"
        placeholder="Source URL"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        required
      />

      <input
        type="text"
        placeholder="Company Name"
        value={companyName}
        onChange={(e) => setCompanyName(e.target.value)}
        required
      />

      <input
        type="text"
        placeholder="Company ID (optional)"
        value={companyId}
        onChange={(e) => setCompanyId(e.target.value)}
      />

      <select value={typeHint} onChange={(e) => setTypeHint(e.target.value as any)}>
        <option value="auto">Auto-detect</option>
        <option value="greenhouse">Greenhouse</option>
        <option value="workday">Workday</option>
        <option value="rss">RSS Feed</option>
        <option value="generic">Generic Scraper</option>
      </select>

      <button type="submit" disabled={loading}>
        {loading ? 'Processing...' : 'Add Source'}
      </button>

      {status && <p>{status}</p>}
    </form>
  )
}
```

---

## URL Detection Examples

```typescript
/**
 * Detect source type from URL.
 */
export function detectSourceType(url: string): 'greenhouse' | 'workday' | 'rss' | 'generic' {
  // Greenhouse
  if (url.includes('boards.greenhouse.io')) {
    return 'greenhouse'
  }

  // Workday
  if (url.includes('.myworkdayjobs.com')) {
    return 'workday'
  }

  // RSS
  if (url.endsWith('.xml') || url.includes('/feed') || url.includes('/rss') || url.endsWith('.rss')) {
    return 'rss'
  }

  // Generic
  return 'generic'
}

// Usage
const sourceType = detectSourceType('https://boards.greenhouse.io/stripe')
// → 'greenhouse'

const autoEnable = sourceType === 'greenhouse' || sourceType === 'rss'
// → true (safe to auto-enable)
```

---

## Common Patterns

### Pattern: Auto-detect and Submit

```typescript
async function smartSubmitSource(url: string, companyId: string, companyName: string) {
  // Auto-detect type
  const type = detectSourceType(url)

  // Determine if safe to auto-enable
  const autoEnable = type === 'greenhouse' || type === 'rss'

  // Submit with detected settings
  return submitSource(url, companyId, companyName, type, autoEnable)
}
```

### Pattern: Batch Import

```typescript
async function batchImportSources(
  sources: Array<{url: string, companyId: string, companyName: string}>
) {
  const results = await Promise.allSettled(
    sources.map(source =>
      smartSubmitSource(source.url, source.companyId, source.companyName)
    )
  )

  const succeeded = results.filter(r => r.status === 'fulfilled').length
  const failed = results.filter(r => r.status === 'rejected').length

  return { succeeded, failed, results }
}
```

### Pattern: Retry Failed Submission

```typescript
async function retryFailedSubmission(failedQueueItemId: string) {
  // Get failed item
  const failedDoc = await getDoc(doc(db, 'job-queue', failedQueueItemId))
  const failedItem = failedDoc.data()

  if (!failedItem?.source_discovery_config) {
    throw new Error('Not a source discovery item')
  }

  // Resubmit with same config
  const { url, company_id, company_name, type_hint } = failedItem.source_discovery_config

  return submitSource(url, company_id, company_name, type_hint, true)
}
```

---

## Quick Reference Table

| Source Type | Type Hint | Auto Enable | Validation Required | Confidence |
|-------------|-----------|-------------|---------------------|------------|
| Greenhouse | `greenhouse` | ✅ Yes | ❌ No | High |
| Workday | `workday` | ❌ No | ✅ Yes | Medium |
| RSS | `rss` | ✅ Yes | ❌ No | High |
| Generic | `generic` | ❌ No | ✅ Yes | Variable |
| Auto-detect | `auto` | Depends | Depends | Depends |

---

## Status Lifecycle

```
pending → processing → success
                     ↘ failed
```

**Monitoring code**:
```typescript
onSnapshot(doc(db, 'job-queue', queueItemId), (snap) => {
  const { status, result_message, error_details } = snap.data()

  switch (status) {
    case 'pending':
      // Waiting in queue
      break
    case 'processing':
      // Being processed
      break
    case 'success':
      // Discovery succeeded
      const sourceId = result_message.split(': ')[1]
      break
    case 'failed':
      // Discovery failed
      console.error(result_message, error_details)
      break
  }
})
```

---

## Type Safety

```typescript
// Type-safe queue item
import type { QueueItem, SourceDiscoveryConfig } from '@jdubz/job-finder-shared-types'

const queueItem: QueueItem = {
  type: 'source_discovery',
  url: '',
  company_name: 'Stripe',
  company_id: 'stripe-id',
  source: 'user_submission',
  submitted_by: auth.currentUser?.uid || null,
  source_discovery_config: {
    url: 'https://boards.greenhouse.io/stripe',
    type_hint: 'greenhouse',
    company_id: 'stripe-id',
    company_name: 'Stripe',
    auto_enable: true,
    validation_required: false,
  },
  status: 'pending',
  created_at: Timestamp.now(),
}
```

---

## See Also

- [SOURCE_SUBMISSION_API.md](SOURCE_SUBMISSION_API.md) - Complete API reference
- [SOURCE_SUBMISSION_DESIGN.md](SOURCE_SUBMISSION_DESIGN.md) - Architecture design
- [shared-types.md](shared-types.md) - Type definitions
