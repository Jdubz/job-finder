# Portfolio UI for Job Scraping - Design & Implementation Plan

## Overview

This document outlines the UI features and implementation requirements for adding job scraping controls to the Portfolio web application. The UI will allow users to trigger on-demand scraping, monitor scraping status, and review scraping history.

## Core Principles

1. **Simple by Default** - Most users should trigger scrapes with one click
2. **Powerful When Needed** - Advanced users can customize every parameter
3. **Transparent** - Always show what's happening and what happened
4. **Safe** - Prevent accidental expensive operations
5. **Responsive** - Works on mobile and desktop

---

## UI Features

### 1. Quick Scrape Button (Main CTA)

**Location:** Job matches dashboard, prominent position (header or sidebar)

**Appearance:**
- Primary button: "Find New Jobs" or "Run Job Search"
- Icon: magnifying glass or refresh icon
- Disabled state when scrape already pending

**Behavior:**
- Single click triggers default scrape (5 matches, 20 sources)
- Shows confirmation if scrape is currently running
- Displays success toast notification with queue item ID
- Opens status panel automatically

**States:**
- Ready: Green/primary color, "Find New Jobs"
- Pending Scrape Exists: Orange, "Scrape Running..." (disabled)
- Success: Brief success animation, then return to ready
- Error: Red border, show error message

---

### 2. Advanced Scrape Configuration (Modal/Drawer)

**Trigger:** Secondary button or gear icon next to Quick Scrape button

**Modal Title:** "Custom Job Search"

**Configuration Sections:**

#### Section A: Search Scope
```
┌─────────────────────────────────────────┐
│ What to Search                          │
├─────────────────────────────────────────┤
│ ○ All Sources (default)                 │
│   Searches all job boards in rotation   │
│                                          │
│ ○ Specific Companies                    │
│   [Dropdown: Select companies...]       │
│   Selected: Netflix, Google, Stripe     │
│   (multi-select with checkboxes)        │
└─────────────────────────────────────────┘
```

**Requirements:**
- Fetch active sources from Firestore `job-sources` collection
- Display source name and type (Greenhouse, RSS, etc.)
- Group by company if multiple sources per company
- Search/filter capability for large source lists

#### Section B: Search Limits
```
┌─────────────────────────────────────────┐
│ When to Stop                            │
├─────────────────────────────────────────┤
│ Target Matches (jobs to analyze)        │
│ ○ Smart (5 matches) - recommended       │
│ ○ Quick (3 matches)                     │
│ ○ Thorough (10 matches)                 │
│ ○ Custom: [___] matches                 │
│ ☑ No limit (exhaust all sources)       │
│                                          │
│ Max Sources to Check                    │
│ ○ Standard (20 sources)                 │
│ ○ Fast (10 sources)                     │
│ ○ Deep (50 sources)                     │
│ ○ Custom: [___] sources                 │
│ ☑ No limit (check all sources)         │
└─────────────────────────────────────────┘
```

**Requirements:**
- Preset buttons for common configurations
- Custom input with validation (1-999)
- Checkboxes for "no limit" that disable number inputs
- Warning message if both limits unchecked (potentially expensive)

#### Section C: Match Quality
```
┌─────────────────────────────────────────┐
│ Match Threshold                         │
├─────────────────────────────────────────┤
│ Minimum Match Score: [___] / 100       │
│ (slider: 0 ──●────────── 100)          │
│                                          │
│ Current default: 80                     │
│ Lower = more jobs, potentially less fit │
│ Higher = fewer jobs, better fit         │
└─────────────────────────────────────────┘
```

**Requirements:**
- Slider with numeric input
- Display current default from AI config
- Show estimate of expected results based on history
- Warning if significantly different from default

#### Section D: Cost Estimate & Confirmation
```
┌─────────────────────────────────────────┐
│ Estimated Cost & Time                   │
├─────────────────────────────────────────┤
│ 🤖 AI Credits: ~$0.15 - $0.30          │
│ ⏱️  Duration: 5-10 minutes              │
│ 📊 Expected Jobs: 2-5 matches          │
│                                          │
│ [Cancel]  [Start Custom Search]         │
└─────────────────────────────────────────┘
```

**Requirements:**
- Calculate estimates based on historical data
- Show cost in user's currency preference
- Update estimates in real-time as settings change
- Show warning for expensive configurations (>$1)

---

### 3. Scrape Status Panel

**Location:** Sidebar or bottom drawer, expandable/collapsible

**Always Visible (Collapsed):**
```
┌──────────────────────────────────────────┐
│ 🔄 Job Search Status                     │
│ Currently checking: Netflix Greenhouse   │
│ Found: 2 jobs • Analyzed: 1 • Saved: 1  │
│                              [Expand ▼]  │
└──────────────────────────────────────────┘
```

**Expanded View:**
```
┌──────────────────────────────────────────┐
│ 🔄 Job Search Running                [✕] │
├──────────────────────────────────────────┤
│ Started: 2 minutes ago                   │
│ Queue ID: scrape-2025-10-17-abc123       │
│                                           │
│ Progress                                  │
│ ▓▓▓▓▓▓▓▓░░░░░░░░░░░░  8/20 sources      │
│                                           │
│ Current Source: Netflix Greenhouse       │
│ Status: Scraping jobs...                 │
│                                           │
│ Results So Far                            │
│ • Jobs found: 47                         │
│ • Passed filters: 12                     │
│ • Analyzed by AI: 3                      │
│ • Matched & saved: 1                     │
│                                           │
│ Recent Sources                            │
│ ✓ Stripe Greenhouse (2 matches)         │
│ ✓ Google Jobs RSS (0 matches)           │
│ ✓ Airbnb Greenhouse (1 match)           │
│ ⏳ Netflix Greenhouse (in progress...)   │
│                                           │
│ [View Full History]  [Cancel Scrape]     │
└──────────────────────────────────────────┘
```

**Requirements:**
- Real-time updates via Firestore listener on queue item
- Progress bar based on sources_scraped / max_sources (or estimated)
- Live updates every 5-10 seconds
- Show current source being scraped
- Ability to cancel (update queue item status to cancelled)
- Auto-close on completion with success message

---

### 4. Scrape History View

**Location:** Dedicated page or tab in Jobs section

**List View:**
```
┌──────────────────────────────────────────────────────────────┐
│ Job Search History                              [New Search] │
├──────────────────────────────────────────────────────────────┤
│ Filters: [All] [Success] [Failed] [Cancelled]               │
│ Time Range: [Last 7 Days ▼]                                 │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ ✓ Today, 2:30 PM                                    3 mins   │
│   Standard Search • 5 sources • 2 jobs matched               │
│   [View Details]                                             │
│                                                               │
│ ✓ Today, 10:15 AM                                   8 mins   │
│   Custom: Netflix, Stripe • 2 sources • 1 job matched       │
│   [View Details]                                             │
│                                                               │
│ ✓ Yesterday, 3:00 PM                                12 mins  │
│   Deep Search • 15 sources • 5 jobs matched                  │
│   [View Details]                                             │
│                                                               │
│ ✗ Yesterday, 9:00 AM                                Failed   │
│   Standard Search • Error: Rate limit exceeded               │
│   [View Error] [Retry]                                       │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Detail View (Modal):**
```
┌──────────────────────────────────────────────────────────────┐
│ Job Search Details - October 17, 2:30 PM               [✕]  │
├──────────────────────────────────────────────────────────────┤
│ Configuration                                                 │
│ • Target matches: 5                                          │
│ • Max sources: 20                                            │
│ • Min score: 80                                              │
│ • Source filter: All (rotation)                              │
│                                                               │
│ Duration: 3 minutes 24 seconds                               │
│ Queue ID: scrape-2025-10-17-abc123                           │
│                                                               │
│ Results                                                       │
│ • Sources scraped: 5                                         │
│ • Total jobs found: 47                                       │
│ • Remote jobs: 28                                            │
│ • Filtered by role: 12                                       │
│ • Duplicates skipped: 8                                      │
│ • Jobs analyzed: 5                                           │
│ • Jobs matched: 2                                            │
│ • Jobs saved: 2                                              │
│                                                               │
│ Sources Checked                                               │
│ ✓ Netflix Greenhouse - 15 jobs, 1 matched                   │
│ ✓ Stripe Greenhouse - 12 jobs, 1 matched                    │
│ ✓ Google Jobs RSS - 8 jobs, 0 matched                       │
│ ✓ Airbnb Greenhouse - 7 jobs, 0 matched                     │
│ ✓ Adobe Greenhouse - 5 jobs, 0 matched                      │
│                                                               │
│ Matched Jobs                                                  │
│ • Senior Software Engineer at Netflix (Score: 87)           │
│ • Backend Engineer at Stripe (Score: 82)                    │
│                                                               │
│ [Close]  [Retry with Same Settings]                          │
└──────────────────────────────────────────────────────────────┘
```

**Requirements:**
- Query `job-queue` collection for SCRAPE type items
- Filter by status, date range, user
- Pagination for large result sets
- Export history to CSV
- Link to matched jobs in main jobs view

---

### 5. Source Management (Admin View)

**Location:** Settings or Admin section

**Purpose:** View and manage job sources, see which are active/inactive

```
┌──────────────────────────────────────────────────────────────┐
│ Job Sources                                  [Add Source +]   │
├──────────────────────────────────────────────────────────────┤
│ Active Sources (42)          [Grid View] [List View]         │
│                                                               │
│ Company         Type         Last Scraped      Status         │
│ ──────────────────────────────────────────────────────────── │
│ Netflix         Greenhouse   5 mins ago       ✓ Active       │
│                 47 jobs      1 match          [Edit]         │
│                                                               │
│ Stripe          Greenhouse   1 hour ago       ✓ Active       │
│                 12 jobs      1 match          [Edit]         │
│                                                               │
│ Google          RSS Feed     3 hours ago      ⚠ Error        │
│                 Error: Feed unavailable       [Fix]          │
│                                                               │
│ Adobe           Greenhouse   Never            ⏸ Disabled     │
│                 -            -                [Enable]       │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Requirements:**
- Display all sources from `job-sources` collection
- Show status indicators (active, error, disabled)
- Last scraped timestamp with relative time
- Basic stats (jobs found, matches)
- Enable/disable sources
- Edit source configuration (advanced users only)
- Add new sources (requires technical knowledge)

---

## Technical Requirements

### Firestore Integration

**Collections to Access:**

1. **`job-queue`** (Read/Write)
   - Create SCRAPE items
   - Listen for real-time status updates
   - Query history by user

2. **`job-sources`** (Read)
   - Fetch active sources for dropdown
   - Display source metadata
   - Show last scraped status

3. **`ai-settings`** (Read)
   - Get current min_match_score default
   - Show model configuration

**Security Rules Needed:**
```javascript
// Users can create SCRAPE queue items
allow create: if request.auth != null
  && request.resource.data.type == 'scrape'
  && request.resource.data.source == 'user_submission';

// Users can read their own SCRAPE items
allow read: if request.auth != null
  && resource.data.type == 'scrape'
  && resource.data.submitted_by == request.auth.uid;

// Users can read job-sources (but not modify)
allow read: if request.auth != null;
```

### Real-Time Updates

**Firestore Listener:**
- Subscribe to queue item document when scrape triggered
- Update UI every time document changes
- Unsubscribe when scrape completes or component unmounts
- Handle listener errors gracefully

**Update Frequency:**
- Queue item updates every 10-30 seconds during processing
- More frequent updates during active scraping
- Final update on completion with full stats

### Client-Side Validation

**Before Submitting Scrape:**
1. Check if pending scrape exists (call has_pending_scrape equivalent)
2. Validate numeric inputs (1-999 range)
3. Warn if both limits disabled (expensive operation)
4. Estimate cost and get user confirmation for >$1 operations
5. Ensure at least one source exists and is active

### Error Handling

**Possible Errors:**
- Pending scrape already exists → Show status of existing scrape
- No active sources → Prompt to enable sources or contact admin
- Rate limit exceeded → Show retry time
- Firestore permission denied → Check authentication
- Network timeout → Retry with exponential backoff

**User-Friendly Messages:**
- "Another search is running. View status?"
- "No job sources available. Please contact support."
- "Search failed due to rate limiting. Try again in 5 minutes."
- "Connection lost. Reconnecting..."

---

## Implementation Plan

### Phase 1: Basic Scrape Trigger (MVP)
**Goal:** Allow users to trigger default scrapes

**Tasks:**
1. Add Quick Scrape button to dashboard
2. Create Firestore queue item on click
3. Show success/error toast notifications
4. Add basic permission check (prevent if pending)

**Deliverables:**
- Functional button that creates SCRAPE queue items
- Basic error handling and user feedback
- Security rules for queue item creation

**Estimated Effort:** 4-6 hours

---

### Phase 2: Real-Time Status Display
**Goal:** Show scraping progress in real-time

**Tasks:**
1. Create status panel component (collapsible)
2. Implement Firestore listener for queue item
3. Parse and display progress data
4. Add cancel functionality
5. Show completion notification

**Deliverables:**
- Live progress display
- Source-by-source updates
- Stats dashboard (jobs found, matched, etc.)
- Cancel button

**Estimated Effort:** 6-8 hours

---

### Phase 3: Advanced Configuration
**Goal:** Allow custom scrape parameters

**Tasks:**
1. Design and implement configuration modal
2. Add source selection dropdown (fetch from Firestore)
3. Add limit configuration (target matches, max sources)
4. Add min score slider
5. Calculate and display cost estimates
6. Implement confirmation flow

**Deliverables:**
- Full configuration UI
- Source selection with multi-select
- Presets for common configurations
- Cost estimation

**Estimated Effort:** 10-12 hours

---

### Phase 4: History & Analytics
**Goal:** View past scrapes and their results

**Tasks:**
1. Create scrape history page
2. Query job-queue for SCRAPE items
3. Build detail view modal
4. Add filtering and pagination
5. Link to matched jobs
6. Add retry functionality

**Deliverables:**
- Scrape history list
- Detailed result view
- Filter and search capabilities
- Retry with same configuration

**Estimated Effort:** 8-10 hours

---

### Phase 5: Source Management (Admin)
**Goal:** Manage job sources from UI

**Tasks:**
1. Create sources management page
2. Display all sources with stats
3. Enable/disable sources
4. Edit source configuration
5. Add new sources (form with validation)
6. Show error states and troubleshooting

**Deliverables:**
- Source management dashboard
- CRUD operations for sources
- Admin-only access control

**Estimated Effort:** 12-15 hours

---

## User Flows

### Flow 1: Quick Scrape (Most Common)
1. User clicks "Find New Jobs" button
2. System checks for pending scrape → none exists
3. System creates SCRAPE queue item with defaults
4. Status panel expands automatically
5. User sees real-time progress
6. Scrape completes, success notification shown
7. User reviews new job matches

**Expected Time:** 5-10 minutes total, 30 seconds user interaction

---

### Flow 2: Custom Company Search
1. User clicks gear icon → configuration modal opens
2. User selects "Specific Companies"
3. User checks: Netflix, Stripe, Airbnb
4. User enables "No limit" on target matches
5. System shows estimate: "$0.50, 10-15 mins, ~5 jobs"
6. User confirms → scrape starts
7. Status panel shows progress for 3 sources
8. Scrape completes with 4 matched jobs

**Expected Time:** 10-15 minutes total, 2-3 minutes user interaction

---

### Flow 3: Review History
1. User navigates to Job Search History
2. System shows last 20 scrapes
3. User filters by "Success" only
4. User clicks "View Details" on recent scrape
5. Modal shows full configuration and results
6. User clicks "Senior Engineer at Netflix"
7. Navigates to job detail page

**Expected Time:** 2-5 minutes

---

## Mobile Considerations

**Responsive Design:**
- Stack configuration sections vertically
- Use bottom sheet instead of modal
- Simplify status panel for narrow screens
- Touch-friendly tap targets (min 44px)
- Swipe to dismiss notifications

**Mobile-Specific Features:**
- Push notifications when scrape completes
- Offline queue (create queue item when back online)
- Reduced animation for performance

---

## Accessibility Requirements

**WCAG 2.1 AA Compliance:**
- Keyboard navigation for all controls
- Screen reader announcements for status changes
- High contrast mode support
- Focus indicators on interactive elements
- ARIA labels for icon-only buttons
- Skip links for repetitive content

**Specific Considerations:**
- Announce scrape progress updates to screen readers
- Provide text alternatives for progress bars
- Ensure color is not the only indicator (icons + text)
- Keyboard shortcuts for common actions

---

## Analytics & Monitoring

**Track User Actions:**
- Scrape triggered (default vs custom)
- Configuration used (targets, sources)
- Completion rate
- Error rate by error type
- Average duration
- Cost per scrape

**Business Metrics:**
- Daily active scrapers
- Average jobs matched per scrape
- Most popular sources
- Peak usage times
- Cost per matched job

---

## Future Enhancements

**Phase 6+ Ideas:**

1. **Scheduled Scrapes**
   - Set recurring scrapes (daily, weekly)
   - Custom schedules per user
   - Notification preferences

2. **Smart Recommendations**
   - "Based on your last scrape, try..."
   - Suggest sources based on successful matches
   - Optimize configuration for user's preferences

3. **Collaborative Features**
   - Share scrape configurations with team
   - Compare results with colleagues
   - Leaderboards for most matches

4. **Advanced Filters**
   - Scrape only jobs posted in last N days
   - Filter by salary range before AI analysis
   - Location-based source selection

5. **Cost Optimization**
   - Show cost per matched job over time
   - Suggest cheaper configurations with similar results
   - Budget limits per user/team

---

## Success Metrics

**User Adoption:**
- 80% of active users trigger at least one custom scrape per week
- Average 3-5 scrapes per user per week

**Performance:**
- 95% scrape success rate
- <500ms UI response time for triggering scrape
- <2 second load time for status panel

**User Satisfaction:**
- <5% cancellation rate for started scrapes
- Positive feedback on scraping feature
- Increased job application rate from scraped results

---

## Technical Architecture Decisions

### Frontend Framework
- Use React with TypeScript
- Context API or Redux for scrape state management
- React Query for Firestore queries
- Tailwind CSS for styling

### Component Structure
```
components/
  scraping/
    QuickScrapeButton.tsx
    ScrapeConfigModal.tsx
    ScrapeStatusPanel.tsx
    ScrapeHistory.tsx
    SourceManager.tsx
    hooks/
      useScrapeStatus.ts      // Firestore listener
      useScrapeHistory.ts     // Query hook
      useTriggerScrape.ts     // Mutation hook
    utils/
      costEstimator.ts
      scrapeFormatter.ts
```

### State Management
- Local component state for UI (modal open/close)
- React Query cache for Firestore data
- Context for active scrape status (global)
- Persistent state for user preferences

### Testing Requirements
- Unit tests for all utility functions
- Integration tests for Firestore operations
- E2E tests for critical flows (trigger, monitor, complete)
- Accessibility tests with axe-core
- Performance tests for real-time updates

---

## Dependencies & Prerequisites

**Required:**
- Firestore security rules updated
- Firebase SDK configured in frontend
- Authentication working (user ID available)
- Job-sources collection populated
- Queue worker running in job-finder project

**Optional but Recommended:**
- Sentry for error tracking
- Google Analytics for usage metrics
- Feature flags for gradual rollout
- A/B testing framework

---

## Documentation Requirements

**User Documentation:**
- Help article: "How to Find New Jobs"
- Video tutorial: "Customizing Your Job Search"
- FAQ: Common scraping questions
- Troubleshooting guide

**Developer Documentation:**
- API reference for Firestore collections
- Component API documentation
- State management guide
- Testing guide

---

## Rollout Strategy

### Beta Testing (Week 1-2)
- Enable for 5-10 internal users
- Gather feedback on usability
- Monitor for bugs and performance issues
- Iterate on UI based on feedback

### Limited Release (Week 3-4)
- Enable for 25% of users
- Feature flag to control access
- Continue monitoring metrics
- A/B test different UI variations

### General Availability (Week 5+)
- Enable for all users
- Full documentation published
- Marketing announcement
- Monitor scaling and costs

---

## Risk Mitigation

**Cost Risk:**
- Set per-user daily scrape limits
- Require confirmation for expensive operations
- Monitor and alert on unusual spending

**Performance Risk:**
- Rate limit scrape creation (max 1 per minute per user)
- Queue depth monitoring and alerting
- Automatic scaling for queue worker

**UX Risk:**
- Extensive user testing before launch
- Clear error messages and help text
- Fallback to CLI if UI unavailable

**Security Risk:**
- Strict Firestore security rules
- Audit logs for scrape creation
- No sensitive data in queue items
- Rate limiting to prevent abuse

---

## Open Questions

1. Should users be able to schedule recurring scrapes from UI?
2. What's the appropriate daily scrape limit per user?
3. Should there be team/workspace-level scrape sharing?
4. How to handle scrape costs in billing?
5. Should we show AI token usage in stats?
6. Enable scrape templates (save configurations)?
7. Allow scraping while another scrape is running (queue multiple)?

---

## Conclusion

This UI will transform job scraping from a developer-only CLI tool into a user-friendly feature accessible to all Portfolio users. The phased approach allows for iterative development and validation at each stage.

**Next Steps:**
1. Review and approve this plan
2. Set up project tracking (Jira/Linear/GitHub Projects)
3. Assign phases to sprints
4. Begin Phase 1 implementation
5. Schedule design review for Phase 3+ UI components
