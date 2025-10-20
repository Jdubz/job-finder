# Source Submission Design

## Overview

This document outlines the design for allowing the job-finder-FE project to submit new job scraping sources for discovery and ingestion.

## Use Cases

### 1. User Submits Company Career Page
**Scenario**: User finds an interesting company and wants to track their job postings.

**Flow**:
1. User enters company name + career page URL in job-finder-FE UI
2. job-finder-FE creates SOURCE_DISCOVERY queue item
3. Job-finder fetches page, uses AI to discover selectors
4. Job-finder validates selectors and creates job-source
5. Source is ready for automated scraping
6. job-finder-FE notifies user of success/failure

### 2. User Submits Specific Job Board
**Scenario**: User wants to track a specific Greenhouse/Workday board.

**Flow**:
1. User enters job board URL (e.g., `https://boards.greenhouse.io/stripe`)
2. job-finder-FE detects board type (Greenhouse) and creates SOURCE_DISCOVERY item
3. Job-finder validates the board exists and is scrapable
4. Job-finder creates job-source with appropriate config
5. Source is ready for automated scraping

### 3. User Submits RSS Feed
**Scenario**: User finds a job board RSS feed they want to track.

**Flow**:
1. User enters RSS feed URL
2. job-finder-FE creates SOURCE_DISCOVERY item with type hint "rss"
3. Job-finder validates feed format
4. Job-finder creates job-source with RSS config
5. Source is ready for automated scraping

## Architecture

### Queue Item Type: SOURCE_DISCOVERY

**New queue item type** to handle source submission and discovery:

```typescript
// In shared-types
type QueueItemType = "job" | "company" | "scrape" | "source_discovery"

interface SourceDiscoveryConfig {
  url: string                          // URL to analyze
  type_hint?: SourceTypeHint          // Optional hint about source type
  company_id?: string                 // Optional company reference
  company_name?: string               // Optional company name
  auto_enable?: boolean               // Auto-enable if discovery succeeds (default: true)
  validation_required?: boolean       // Require manual validation (default: false)
}

type SourceTypeHint = "auto" | "greenhouse" | "workday" | "rss" | "generic"

interface QueueItem {
  // ... existing fields
  source_discovery_config?: SourceDiscoveryConfig
}
```

### Processing Pipeline

**SOURCE_DISCOVERY items follow this pipeline:**

```
┌─────────────────────────────────────────────────────────────────┐
│                      SOURCE_DISCOVERY                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Type Detection  │
                    │  (greenhouse,    │
                    │   workday, rss,  │
                    │   generic HTML)  │
                    └──────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
       ┌────────────────┐         ┌────────────────┐
       │  Known Type    │         │  Generic HTML  │
       │  (GH, WD, RSS) │         │   Scraping     │
       └────────────────┘         └────────────────┘
                │                           │
                │                           ▼
                │                  ┌────────────────┐
                │                  │  AI Selector   │
                │                  │   Discovery    │
                │                  └────────────────┘
                │                           │
                └─────────────┬─────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Validate Config │
                    │  (test scrape)   │
                    └──────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
         ┌───────────┐              ┌─────────────┐
         │  Success  │              │   Failed    │
         │  Create   │              │   Update    │
         │  Source   │              │   Queue     │
         └───────────┘              └─────────────┘
                │                           │
                ▼                           ▼
      ┌──────────────────┐        ┌──────────────────┐
      │ Notify job-finder-FE │        │ Notify job-finder-FE │
      │ (source_id)      │        │ (error details)  │
      └──────────────────┘        └──────────────────┘
```

### Source Discovery Processor

**New processor method**: `_process_source_discovery()`

```python
def _process_source_discovery(self, item: JobQueueItem) -> None:
    """
    Process SOURCE_DISCOVERY queue item.

    Steps:
    1. Fetch URL and detect source type
    2. For known types (GH/WD/RSS): validate and create config
    3. For generic HTML: use AI selector discovery
    4. Test scrape to validate configuration
    5. Create job-source document if successful
    6. Update queue item with result
    """
```

### Source Type Detection

**Auto-detect source type from URL patterns:**

```python
def detect_source_type(url: str) -> str:
    """
    Detect source type from URL patterns.

    Examples:
    - boards.greenhouse.io/* → "greenhouse"
    - *.myworkdayjobs.com/* → "workday"
    - */feed or */rss or *.xml → "rss"
    - everything else → "generic"
    """
```

**Detection logic:**

| URL Pattern | Source Type | Config Generation |
|------------|-------------|-------------------|
| `boards.greenhouse.io/{token}` | greenhouse | Extract board_token |
| `*.wd*.myworkdayjobs.com/{company}` | workday | Extract company_id, base_url |
| `*.xml`, `*/feed`, `*/rss` | rss | Test feed parsing |
| Other | generic | AI selector discovery |

### Validation Strategy

**Test scrape to validate configuration:**

1. **Greenhouse/Workday**: Fetch API, verify jobs returned
2. **RSS**: Parse feed, verify items exist
3. **Generic**: Scrape with discovered selectors, verify data extracted

**Validation requirements:**
- At least 1 job found
- Required fields present (title, company OR url)
- Selectors work on current page

**Confidence levels:**
- **High**: Known type (GH/WD) with working API
- **Medium**: RSS feed with valid format, or AI selectors validated
- **Low**: AI selectors discovered but not validated

### Job Source Document Structure

**Created in `job-sources` collection:**

```javascript
{
  // Identity
  id: string                          // Auto-generated
  name: string                        // Display name
  source_type: string                 // "greenhouse" | "workday" | "rss" | "scraper"

  // Configuration
  config: {
    // Type-specific config (see job_sources_manager.py)
  }

  // Discovery metadata
  discovered_via: "user_submission" | "automated_scan"
  discovered_at: Timestamp
  discovered_by?: string              // User ID if submitted by user
  discovery_confidence: "high" | "medium" | "low"
  discovery_queue_item_id?: string    // Reference to SOURCE_DISCOVERY item

  // Company relationship (optional)
  company_id?: string
  company_name?: string

  // Status
  enabled: boolean
  validation_required: boolean        // Requires manual review before enabling

  // Health tracking (existing fields)
  lastScraped?: Timestamp
  consecutiveFailures: number
  totalJobsFound: number

  // Metadata
  tags?: string[]
  notes?: string
  created_at: Timestamp
  updated_at: Timestamp
}
```

## Implementation Plan

### Phase 1: Core Infrastructure

1. **Update shared-types** ✅
   - Add `source_discovery` to QueueItemType
   - Add SourceDiscoveryConfig interface
   - Add source_discovery_config to QueueItem

2. **Update Python models** ✅
   - Add SOURCE_DISCOVERY to QueueItemType enum
   - Add SourceDiscoveryConfig Pydantic model
   - Add source_discovery_config to JobQueueItem

3. **Implement source type detection** ✅
   - Create `src/job_finder/utils/source_type_detector.py`
   - Pattern matching for GH/WD/RSS
   - URL parsing and validation

### Phase 2: Discovery Processor

4. **Implement processor** ✅
   - Add `_process_source_discovery()` to processor.py
   - Integrate with selector_discovery.py
   - Validation logic

5. **Enhance selector discovery** ✅
   - Improve AI prompts for better selector extraction
   - Add test scraping to validation
   - Return confidence scores

### Phase 3: Integration & Testing

6. **Update JobSourcesManager** ✅
   - Add `create_from_discovery()` method
   - Add discovery metadata fields
   - Track submission source

7. **Write tests** ✅
   - Test source type detection
   - Test discovery processor
   - Test validation logic
   - Integration tests

8. **Documentation** ✅
   - API documentation for portfolio integration
   - Examples of source submission
   - Troubleshooting guide

## job-finder-FE Integration

### Submitting a Source

**From job-finder-FE (TypeScript):**

```typescript
import { QueueItem } from '@jdubz/job-finder-shared-types'

async function submitJobSource(
  url: string,
  companyId?: string,
  companyName?: string,
  typeHint?: SourceTypeHint
) {
  const queueItem: QueueItem = {
    type: 'source_discovery',
    url: '',  // Not used for source_discovery
    company_name: companyName || '',
    company_id: companyId,
    source: 'user_submission',
    submitted_by: currentUser.uid,
    status: 'pending',
    source_discovery_config: {
      url: url,
      type_hint: typeHint || 'auto',
      company_id: companyId,
      company_name: companyName,
      auto_enable: true,
      validation_required: false,
    },
    created_at: new Date(),
  }

  // Add to Firestore
  const docRef = await db.collection('job-queue').add(queueItem)

  return docRef.id
}
```

### Monitoring Progress

**Listen for completion:**

```typescript
function monitorSourceDiscovery(queueItemId: string) {
  return db.collection('job-queue')
    .doc(queueItemId)
    .onSnapshot(snapshot => {
      const item = snapshot.data()

      if (item.status === 'success') {
        // Discovery succeeded!
        const sourceId = item.result_message  // Contains source ID
        console.log(`Source created: ${sourceId}`)

        // Navigate to source or show success
        showSuccess(`Job source added successfully!`)
      } else if (item.status === 'failed') {
        // Discovery failed
        console.error(`Discovery failed: ${item.error_details}`)
        showError(item.result_message)
      }
    })
}
```

### Getting Created Source

**After success, fetch the source:**

```typescript
async function getCreatedSource(sourceId: string) {
  const sourceDoc = await db.collection('job-sources')
    .doc(sourceId)
    .get()

  return sourceDoc.data()
}
```

## Example Workflows

### Example 1: User Submits Stripe Greenhouse

**User action**: Enters `https://boards.greenhouse.io/stripe`

**Processing:**
1. Type detection: `greenhouse` (pattern match)
2. Extract board_token: `stripe`
3. Validate: Fetch Greenhouse API
4. Success: Create source with config:
   ```javascript
   {
     name: "Stripe Greenhouse",
     source_type: "greenhouse",
     config: { board_token: "stripe" },
     discovered_via: "user_submission",
     discovery_confidence: "high",
     enabled: true
   }
   ```

### Example 2: User Submits Generic Career Page

**User action**: Enters `https://example.com/careers`

**Processing:**
1. Type detection: `generic` (no pattern match)
2. Fetch HTML
3. AI selector discovery:
   ```javascript
   {
     job_list_container: ".careers-list",
     job_item: ".job-posting",
     title: "h3.title",
     company: null,  // Company page, no company field
     location: ".location",
     description: ".description",
     apply_url: "a.apply-link"
   }
   ```
4. Test scrape: Validate selectors work
5. Success: Create source with config:
   ```javascript
   {
     name: "Example Corp Careers",
     source_type: "scraper",
     config: {
       base_url: "https://example.com/careers",
       selectors: { /* AI-discovered */ },
       pagination: { /* detected or default */ }
     },
     discovered_via: "user_submission",
     discovery_confidence: "medium",
     enabled: true
   }
   ```

### Example 3: Discovery Fails

**User action**: Enters invalid or unsupported URL

**Processing:**
1. Type detection: `generic`
2. Fetch HTML: 404 or access denied
3. Failure: Update queue item:
   ```javascript
   {
     status: "failed",
     result_message: "Could not access URL (404 Not Found)",
     error_details: "HTTP 404: Page not found"
   }
   ```

## Security Considerations

### Rate Limiting
- Limit source submissions per user (5 per day)
- Prevent duplicate submissions (same URL within 24h)

### Validation
- Verify URL is valid and accessible
- Check against blocklist (spam sites, malicious domains)
- Require authentication for submissions

### Auto-Enable Safety
- High confidence sources: Auto-enable
- Medium/low confidence: Require manual validation
- Failed test scrape: Do not enable, flag for review

## Future Enhancements

### Smart Suggestions
- Detect company from URL, suggest linking to existing company
- Suggest similar sources already in system
- Auto-tag based on URL patterns

### Collaborative Improvement
- Track which selectors fail over time
- Allow users to report broken sources
- Crowdsource selector improvements

### Monitoring Dashboard
- Show all user-submitted sources
- Display success/failure rates
- Allow users to see their submission history

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Project overview
- [Job Sources Manager](../src/job_finder/storage/job_sources_manager.py) - Source management
- [Selector Discovery](../src/job_finder/ai/selector_discovery.py) - AI-powered discovery
