# Session Context - Companies/Sources Architecture Refactor

**Date:** 2025-10-16
**Branch:** `feature/separate-companies-from-sources`
**Status:** ✅ Complete - All CI Checks Passing - Ready for Production

---

## What Was Accomplished

### ✅ Architecture Refactor Complete
- **Separated companies from job sources** in Firestore schema
- **New collections:**
  - `companies` - Company-specific data (name, website, about, priority, tier, Portland office, tech stack)
  - `job-sources` - Source configuration with optional `companyId` reference
  - `job-matches` - Enhanced with `companyId` field for normalization

### ✅ Code Changes
- **SearchOrchestrator** - Now uses JobSourcesManager with runtime company JOINs
- **FirestoreJobStorage** - Added `companyId` field to job-matches
- **CompaniesManager** - Added `get_company_by_id()` method
- **Deleted** - `JobListingsManager` (replaced by JobSourcesManager)
- **Tests** - All 427 tests passing (47% coverage)

### ✅ Migration Complete
- **Staging migration successful:**
  - 25 job listings → 19 companies + 25 sources
  - 0 errors
- **Migration script ready for production:**
  - `scripts/migrate_listings_to_sources.py`
  - Supports cross-database migration (prod → staging for testing)
  - Safety confirmation for production writes

### ✅ Testing Complete
- Architecture verified end-to-end in staging
- Company data JOINs working correctly
- AI matching working (3 jobs matched, 3 saved, 0 errors)
- Priority-based source ordering verified

### ✅ CI Fixed (2025-10-16 20:30 UTC)
- Fixed black formatting violations in migration script and tests
- Added `.flake8` config (max-line-length=100) to match black settings
- All 427 tests passing
- All CI checks now passing

### ✅ AI Configuration Resolved
- **Issue:** API key was using deprecated model (`claude-3-5-sonnet-20241022`)
- **Resolution:** Updated to `claude-3-5-haiku-20241022`
- **Your API key has access to:**
  - ✅ Claude Haiku 3.5 (currently using - fast & cost-effective)
  - ✅ Claude Sonnet 4 (`claude-sonnet-4-20250514`) - upgrade option
  - ✅ Claude Opus 4 (`claude-opus-4-20250514`) - upgrade option
  - ✅ Claude Sonnet 3.7 (`claude-3-7-sonnet-20250219`)

---

## Current Configuration

**Active Branch:** `feature/separate-companies-from-sources`

**Config File:** `config/config.yaml`
```yaml
ai:
  enabled: true
  provider: "claude"
  model: "claude-3-5-haiku-20241022"  # Fast & cost-effective
  min_match_score: 80
```

**Environment Variables (`.env`):**
```
ANTHROPIC_API_KEY=sk-ant-api03-*********************  # Your API key from Anthropic Console
GOOGLE_APPLICATION_CREDENTIALS=.firebase/static-sites-257923-firebase-adminsdk.json
```

---

## Pull Request

**PR #15:** https://github.com/Jdubz/job-finder/pull/15
**Title:** Complete separation of companies from job sources
**Status:** Ready for review

**Summary:**
- Separates companies from job sources in Firestore
- Runtime company JOINs in SearchOrchestrator
- Migration script with cross-database support
- All tests passing (427/427)
- Verified in staging environment

---

## Next Steps: Production Cutover

### When Ready to Deploy:

**1. Review and Approve PR**
- Review changes at: https://github.com/Jdubz/job-finder/pull/15
- Verify all tests passing
- Approve PR

**2. Run Production Migration**
```bash
cd /home/jdubz/Development/job-finder
source venv/bin/activate

# Activate environment variables
export GOOGLE_APPLICATION_CREDENTIALS=.firebase/static-sites-257923-firebase-adminsdk.json

# Run migration (will prompt for confirmation)
python scripts/migrate_listings_to_sources.py \
  --source-db portfolio \
  --target-db portfolio
```

**Expected Output:**
- ~25 listings migrated
- ~19 companies created
- ~25 sources created
- Should complete with 0 errors

**3. Merge and Deploy**
```bash
# Merge PR (via GitHub UI or CLI)
gh pr merge 15 --squash

# Switch to develop branch
git checkout develop
git pull

# Deploy updated code to production
```

---

## Testing Commands

### Test Staging Environment
```bash
cd /home/jdubz/Development/job-finder
source venv/bin/activate
export GOOGLE_APPLICATION_CREDENTIALS=.firebase/static-sites-257923-firebase-adminsdk.json
while IFS='=' read -r key value; do export "$key=$value"; done < .env

python scripts/test_staging.py
```

### Run Full Test Suite
```bash
source venv/bin/activate
pytest --cov=src/job_finder --cov-report=html
```

### Test Migration (Dry Run)
```bash
source venv/bin/activate
export GOOGLE_APPLICATION_CREDENTIALS=.firebase/static-sites-257923-firebase-adminsdk.json

python scripts/migrate_listings_to_sources.py \
  --source-db portfolio \
  --target-db portfolio-staging \
  --dry-run
```

---

## Important Files

**Architecture:**
- `src/job_finder/search_orchestrator.py` - Main pipeline orchestrator
- `src/job_finder/storage/companies_manager.py` - Company data management
- `src/job_finder/storage/job_sources_manager.py` - Source data management
- `src/job_finder/storage/firestore_storage.py` - Job matches storage

**Migration:**
- `scripts/migrate_listings_to_sources.py` - Database migration script
- `scripts/test_staging.py` - Staging environment test script

**Configuration:**
- `config/config.yaml` - Application configuration
- `.env` - Environment variables (API keys, credentials)

**Tests:**
- `tests/test_search_orchestrator.py` - Orchestrator tests (includes company JOIN tests)
- `tests/test_placeholder.py` - Basic import tests

---

## Key Technical Details

### Database Schema

**companies collection:**
```javascript
{
  "id": "auto-generated-id",
  "name": "Company Name",
  "website": "https://company.com",
  "about": "Company description...",
  "hasPortlandOffice": true,
  "techStack": ["Python", "React"],
  "tier": "S",  // S/A/B/C/D
  "priorityScore": 150,  // 0-200+
  "company_size_category": "large",  // large/medium/small
  "headquarters_location": "San Francisco, CA"
}
```

**job-sources collection:**
```javascript
{
  "id": "auto-generated-id",
  "name": "Source Name",
  "sourceType": "greenhouse",  // greenhouse/company-page/rss/etc
  "config": {
    "board_token": "token",
    // source-specific config
  },
  "enabled": true,
  "companyId": "company-doc-id",  // Optional: reference to companies collection
  "companyName": "Company Name"   // Denormalized for convenience
}
```

**job-matches collection:**
```javascript
{
  "title": "Job Title",
  "company": "Company Name",
  "companyId": "company-doc-id",  // NEW: Link to companies collection
  "companyWebsite": "https://...",
  // ... rest of job match fields
}
```

### Runtime Company JOINs

SearchOrchestrator performs JOINs at runtime:
1. Load active sources from `job-sources` collection
2. For sources with `companyId`:
   - Look up company data using `get_company_by_id()`
   - Enrich source with: `priorityScore`, `tier`, `hasPortlandOffice`, `techStack`
3. Sort sources by priority (highest first)
4. Scrape in priority order

### Priority Scoring System

**Company Scoring (0-200+ points):**
- Portland office: +50 points
- Tech stack alignment: up to +100 points (based on user's expert/advanced skills)
- Company size preference: ±10 points
- Timezone compatibility: ±15 points

**Tier Classification:**
- S tier: 150+ points (highest priority)
- A tier: 100-149 points
- B tier: 70-99 points
- C tier: 50-69 points
- D tier: 0-49 points (default for RSS feeds)

---

## Troubleshooting

### Issue: AI Model 404 Errors

**Symptom:** `NotFoundError: model: claude-3-5-sonnet-20241022`

**Cause:** Old model ID is deprecated

**Fix:** Update config to use current models:
- Haiku: `claude-3-5-haiku-20241022` (fast & cheap)
- Sonnet 4: `claude-sonnet-4-20250514` (best quality)
- Opus 4: `claude-opus-4-20250514` (most powerful)

### Issue: Firebase Authentication Errors

**Symptom:** `ValueError: Firebase credentials not found`

**Fix:** Set credentials environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=.firebase/static-sites-257923-firebase-adminsdk.json
```

### Issue: Environment Variables Not Loading

**Symptom:** API key not found or empty

**Fix:** Load `.env` properly:
```bash
while IFS='=' read -r key value; do export "$key=$value"; done < .env
```

---

## Contact & Resources

**GitHub Repository:** https://github.com/Jdubz/job-finder
**Pull Request:** https://github.com/Jdubz/job-finder/pull/15
**Anthropic Console:** https://console.anthropic.com/
**Firebase Console:** https://console.firebase.google.com/

---

## Session Outcome

✅ **Architecture refactor complete and production-ready**
✅ **All tests passing (427/427)**
✅ **Staging migration successful**
✅ **AI configuration resolved**
✅ **Pull request ready for review**

**Next action:** Review PR #15 and run production migration when ready.

---

*Generated: 2025-10-16*
*Session ID: Companies/Sources Separation Refactor*
