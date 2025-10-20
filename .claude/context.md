# Job Finder Project Context

## Overview
AI-powered Python web scraper that finds and analyzes job postings matching your profile. Uses LLMs (Claude/GPT-4) for intelligent matching and generates structured data for tailored applications.

## Related Projects

### job-finder-FE
**Location:** `/home/jdubz/Development/portfolio`
**Purpose:** Professional portfolio website with AI resume generation and job management UI
**Language:** TypeScript/React (Gatsby + Firebase)
**Integration:** Provides web interface for viewing job matches and managing applications

**Key Integration Points:**
- **Shared Database:** Both projects use the same Firestore instance (`portfolio` database)
- **Shared Types:** Both projects reference `@jdubz/shared-types` for type definitions
- **Profile Source:** Reads profile data from portfolio's `experience-entries` and `experience-blurbs` collections
- **Job Queue:** Processes jobs submitted via portfolio's web interface
- **Job Storage:** Writes analyzed matches to `job-matches` collection for portfolio UI display
- **Configuration:** Reads settings from `job-finder-config` collection (managed via portfolio UI)

**Data Flow:**
```
portfolio (profile data) → job-finder (scrape + analyze) → portfolio (display results)
                    ↓                                           ↓
           shared-types (TypeScript definitions - source of truth)
```

### Shared Types
**Repository:** https://github.com/Jdubz/job-finder-shared-types
**Purpose:** Single source of truth for TypeScript type definitions shared across projects
**Language:** TypeScript
**Package:** `@jdubz/job-finder-shared-types`

**Why Shared Types Matter:**
- **Type Safety:** Ensures Python models match TypeScript interfaces exactly
- **Documentation:** TypeScript types serve as authoritative schema reference
- **Change Management:** Single place to update types that affect both projects
- **Cross-Language Consistency:** Python models must mirror TypeScript definitions

**Integration in Job-finder:**
- Python models in `src/job_finder/queue/models.py` are **derived from** TypeScript types in `@jdubz/job-finder-shared-types`
- When modifying queue schemas, **update TypeScript first** in the shared-types repo, then update Python to match
- TypeScript types are the **source of truth** - Python follows TypeScript

## Shared Firestore Collections

### Read by Job-finder
- `experience-entries`: Your work experience (source: portfolio)
- `experience-blurbs`: Your skills and highlights (source: portfolio)
- `job-queue`: Jobs to process (written by portfolio or scrapers)
- `job-finder-config`: Stop lists, AI settings, queue settings (configured via portfolio)

### Written by Job-finder
- `job-matches`: Analyzed job matches with AI scores and recommendations
- `job-queue`: Status updates as jobs are processed
- `companies`: Company info and metadata
- `job-sources`: Job board source prioritization data

## Type System Architecture

### Source of Truth: @jdubz/job-finder-shared-types
All queue-related types are defined in the shared-types GitHub repository and must be kept in sync between TypeScript and Python.

**TypeScript (Authoritative):**
- Repository: https://github.com/Jdubz/job-finder-shared-types
- Package: `@jdubz/job-finder-shared-types`
- Used by: job-finder-FE (TypeScript imports directly from npm package)
- Purpose: Single source of truth for all type definitions

**Python (Derived):**
- Location: `/home/jdubz/Development/job-finder/src/job_finder/queue/models.py`
- Used by: Job-finder (Python models mirror TypeScript types)
- Purpose: Runtime validation and Firestore serialization

### Type Mapping Reference

| TypeScript Type | Python Equivalent | Notes |
|-----------------|-------------------|-------|
| `QueueStatus` | `QueueStatus` | String enum with identical values |
| `QueueItemType` | `QueueItemType` | String enum: "job", "company" |
| `QueueSource` | `str` | Literal type in Python (see shared-types for valid values) |
| `QueueItem` | `JobQueueItem` | Pydantic model matching TS interface exactly |
| `Date \| any` | `Optional[datetime]` | Firestore timestamps converted automatically |

### Keeping Types in Sync

**When modifying queue schema:**
1. **Update TypeScript first** in https://github.com/Jdubz/job-finder-shared-types
2. **Create PR and merge** changes to shared-types repo
3. **Publish new version** to npm (automated via GitHub Actions)
4. **Update Python** in `src/job_finder/queue/models.py` to match the TypeScript changes
5. **Test both projects** to verify compatibility
6. **Document changes** in both repositories

**Common Sync Issues:**
- Missing fields in Python model
- Enum values don't match
- Optional vs required fields differ
- Timestamp handling inconsistencies

**See:** https://github.com/Jdubz/job-finder-shared-types for complete type mapping guide

### Profile Types
Python models in `src/job_finder/profile/schema.py`:
- `Profile`: Complete user profile for job matching
- `Experience`: Work history entries (maps to portfolio's experience-entries)
- `Skill`: Individual skills with proficiency levels
- `Project`: Personal/professional projects
- `Preferences`: Job search preferences

**Data Source:** Loaded via `FirestoreProfileLoader` from portfolio database.

## Cross-Repository Workflows

### Profile Data Sync
1. **job-finder-FE:** User updates experience via `/experience` page
2. **job-finder-FE:** Data saved to Firestore `experience-entries` collection
3. **Job-finder:** `FirestoreProfileLoader` automatically reads latest data on next run
4. **Job-finder:** AI uses updated profile for matching

**No manual sync needed** - profile stays current automatically.

### Job Queue Processing
1. **job-finder-FE:** User submits job URL via web form OR scraper finds new job
2. **job-finder-FE/Scraper:** Write entry to `job-queue` collection with status `pending`
3. **Job-finder:** Queue processor (`queue/processor.py`) polls for pending jobs every 60s
4. **Job-finder:** Processes job (scrape, analyze, score) and writes to `job-matches`
5. **Job-finder:** Updates queue item status to `success`/`failed`/`skipped`
6. **job-finder-FE:** UI polls queue status and displays results

### Configuration Updates
1. **job-finder-FE:** Admin updates stop list or AI settings via `/admin/config` page
2. **job-finder-FE:** Settings saved to `job-finder-config` collection
3. **Job-finder:** Reads latest config on each processing cycle
4. **Job-finder:** Immediately applies new exclusions and thresholds

## Environment Configuration

### Firebase Connection
Connects to portfolio's Firebase project using service account:

```bash
# Required environment variable
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/serviceAccountKey.json"
```

**Database Selection:**
- Local: Firebase emulator (default database)
- Staging: `portfolio-staging`
- Production: `portfolio`

Configure in `config/config.yaml`:
```yaml
profile:
  source: "firestore"
  firestore:
    database_name: "portfolio"  # or "portfolio-staging"
```

### Getting Service Account Key
1. Open [Firebase Console](https://console.firebase.google.com/)
2. Go to Project Settings → Service Accounts
3. Click "Generate New Private Key"
4. Save to secure location (e.g., `~/.firebase/portfolio-key.json`)
5. Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

## Development Tips

### When Modifying Queue System
- **ALWAYS update shared-types TypeScript definitions first**
- Update Python models in `src/job_finder/queue/models.py` to match TypeScript
- Rebuild shared-types: `cd ../shared-types && npm run build`
- Test with portfolio UI to verify status updates display correctly
- Check timestamp handling (Python datetime vs Firebase Timestamp)
- Verify enum values match exactly between TypeScript and Python

### When Modifying Profile Schema
- Update `src/job_finder/profile/schema.py`
- Check if portfolio's Firestore schema needs updates
- Test `FirestoreProfileLoader` with real portfolio data
- Verify AI prompts still work with schema changes

### When Adding New Job Sources
- Create scraper in `src/job_finder/scrapers/[site].py`
- Add to `JobSourcesManager` for prioritization
- Test that scraped jobs appear in portfolio UI
- Update portfolio's configuration UI if needed

### Testing with job-finder-FE
```bash
# Terminal 1: job-finder-FE Firebase emulators
cd /home/jdubz/Development/portfolio
make firebase-emulators

# Terminal 2: job-finder-FE web server (view results)
cd /home/jdubz/Development/portfolio
make dev

# Terminal 3: Job-finder queue processor
cd /home/jdubz/Development/job-finder
python -m job_finder.queue.processor

# Terminal 4: Run job search
cd /home/jdubz/Development/job-finder
python -m job_finder.main
```

## Documentation

### Job-finder Docs
- Main: `/home/jdubz/Development/job-finder/CLAUDE.md`
- Architecture: `/home/jdubz/Development/job-finder/docs/architecture.md`
- Queue System: `/home/jdubz/Development/job-finder/docs/queue-system.md`
- Setup Guide: `/home/jdubz/Development/job-finder/docs/setup.md`

### job-finder-FE Docs
- Main: `/home/jdubz/Development/portfolio/CLAUDE.md`
- Context: `/home/jdubz/Development/portfolio/.claude/context.md`
- Integration Guide: `/home/jdubz/Development/portfolio/PORTFOLIO_INTEGRATION_GUIDE.md`
- API Docs: `/home/jdubz/Development/portfolio/docs/development/ARCHITECTURE.md`

### Shared Types Docs
- Repository: https://github.com/Jdubz/job-finder-shared-types
- README: https://github.com/Jdubz/job-finder-shared-types#readme
- Queue Types: https://github.com/Jdubz/job-finder-shared-types/blob/main/src/queue.types.ts

### Integration Docs
- job-finder-FE Integration: `/home/jdubz/Development/job-finder/docs/integrations/portfolio.md`
- Queue Implementation: `/home/jdubz/Development/portfolio/PORTFOLIO_INTEGRATION_GUIDE.md`

## Module Purpose

### This is a DATA PIPELINE, not a web app
**Important:** Job-finder has **no UI** and should not have one. All user interaction happens in the portfolio project.

**Job-finder's role:**
- Scrape job boards for relevant postings
- Analyze jobs against your profile using AI
- Generate match scores and recommendations
- Write results to Firestore
- Process queue entries from portfolio

**job-finder-FE's role:**
- Display matched jobs in web interface
- Allow users to submit jobs for analysis
- Manage application tracking
- Generate tailored resumes
- Configure job-finder settings

**When considering improvements:**
- ❌ **DO NOT** build web UI, dashboards, or visualizations here
- ❌ **DO NOT** duplicate functionality that exists in portfolio
- ✅ **DO** improve scraping quality and coverage
- ✅ **DO** enhance AI matching accuracy
- ✅ **DO** optimize queue processing performance
- ✅ **DO** add new job board scrapers

## Testing Cross-Repository Changes

### Firestore Schema Changes
1. Update Python models in job-finder
2. Update corresponding TypeScript types in portfolio
3. Test with emulator data
4. Verify data displays correctly in portfolio UI
5. Update migration scripts if needed

### Queue Processing Changes
1. Update `queue/processor.py` logic
2. Test status updates appear in portfolio UI
3. Verify error handling works in both directions
4. Check retry logic doesn't create duplicates

### AI Analysis Changes
1. Update prompts in `ai/prompts.py`
2. Test with real job descriptions
3. Verify results structure matches portfolio expectations
4. Check resume intake data is usable by portfolio

## Common Pitfalls

- **Type Sync:** Python and TypeScript queue types must match - check both repos
- **Timestamps:** Use Firestore server timestamps, not Python datetime strings
- **Collection Names:** Must exactly match portfolio's expected names
- **Profile Updates:** Remember profile comes from portfolio - don't modify here
- **No UI:** Don't build web interfaces - use portfolio for all user-facing features
