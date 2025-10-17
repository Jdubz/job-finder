# Development Roadmap & Next Steps

This document tracks completed work, current technical debt, planned features, and future enhancements for the Job Finder project.

**Last Updated:** 2025-10-16

## Table of Contents

- [Recently Completed](#recently-completed)
- [Current Technical Debt](#current-technical-debt)
- [Planned Features](#planned-features)
- [Future Enhancements](#future-enhancements)
- [Known Issues](#known-issues)

---

## Recently Completed

### Sprint 1 (October 2025) - Firestore Client Singleton

**✅ Issue Resolved:** Eliminated Firestore initialization duplication

**What was done:**
- Created `FirestoreClient` singleton class for centralized connection management
- Migrated 4 files: `listings_manager.py`, `companies_manager.py`, `firestore_loader.py`, `firestore_storage.py`
- Added comprehensive tests (11 tests, 94% coverage)
- Eliminated ~195 lines of duplicate code

**Results:**
- Single source of truth for Firestore initialization
- Singleton pattern prevents multiple connections
- All tests passing (13/13)
- Code coverage increased from 14% to 15%

### Sprint 2 (October 2025) - Exception Handling Improvements

**✅ Issue Resolved:** Replaced broad exception handling in critical files

**What was done:**
- **Pipeline files**: Fixed `search_orchestrator.py` (4 instances), `company_info_fetcher.py` (4 instances)
- **Storage files**: Fixed `firestore_storage.py` (6 instances), `listings_manager.py` (5 instances), `companies_manager.py` (4 instances), `firestore_loader.py` (3 instances)
- Added specific exception types: `RuntimeError`, `ValueError`, `KeyError`, `AttributeError`, `requests.RequestException`, `json.JSONDecodeError`
- Improved error messages with exception type names
- Maintained graceful degradation where appropriate

**Results:**
- 26 instances of broad exception handling fixed (46% of total)
- 100% of critical pipeline and storage files improved
- Better debugging capabilities
- No regressions (all tests passing)

**Remaining:**
- ~30 instances in optional scraper files (low priority)

### Queue System Implementation (October 2025)

**✅ Phase 1 Complete:** Queue-based architecture deployed

**What was built:**
- Queue models and manager (CRUD operations, statistics)
- Configuration loader (Firestore-based settings)
- Job processor with retry logic
- Queue worker daemon (continuous polling)
- Scraper integration helpers
- Dual-process Docker mode

**Key features:**
- FIFO queue processing
- Duplicate detection
- Stop list filtering
- Retry mechanism (max 3 attempts)
- Status tracking
- Portfolio integration ready

See **[Queue System Guide](queue-system.md)** for complete details.

### CI/CD Fixes (October 2025)

**✅ Completed:** Code formatting and CI pipeline fixes

**What was done:**
- Fixed all black formatting issues
- Sorted imports with isort
- Resolved flake8 linting warnings
- Updated GitHub Actions workflow
- All quality checks passing

---

## Current Technical Debt

### Medium Priority Issues

#### Issue #3: Long Functions Need Refactoring

**Severity:** Medium
**Impact:** Reduced readability and testability
**Effort:** 3-5 hours

**Files to refactor:**

1. **`search_orchestrator.py:_process_listing()`** - 156 lines
   - Split into smaller methods: `_initialize_scraper()`, `_scrape_jobs()`, `_enrich_company_info()`, `_filter_remote_jobs()`, `_match_jobs_with_ai()`, `_store_matched_jobs()`
   - Each method should have single responsibility
   - Easier to test individual steps

2. **`firestore_loader.py:_load_experiences()`** - 127 lines
   - Split into: `_fetch_experience_documents()`, `_parse_experience_data()`, `_validate_experiences()`
   - Separate data loading, transformation, and validation

3. **`ai/matcher.py:analyze_job()`** - 118 lines
   - Extract prompt building, API calling, and response parsing into separate methods

**Benefits:**
- Better testability
- Improved maintainability
- Clearer code flow
- Easier debugging

#### Issue #4: God Class Anti-Pattern

**Severity:** Medium
**Impact:** Single class doing too much
**Effort:** 6-8 hours

**Problem:**
`JobSearchOrchestrator` has too many responsibilities:
- Profile loading
- Scraper initialization
- Company info fetching
- Job filtering
- AI matching
- Statistics tracking
- Storage management

**Proposed Solution:**
Split into focused classes using composition and pipeline pattern:
- `JobSearchPipeline` - Orchestrates pipeline stages
- `ProfileLoadStage` - Profile loading
- `ScrapingStage` - Job scraping
- `CompanyEnrichmentStage` - Company info fetching
- `FilteringStage` - Job filtering
- `AIMatchingStage` - AI analysis
- `StorageStage` - Data persistence
- `PipelineStatistics` - Statistics tracking

**Benefits:**
- Single Responsibility Principle
- Easier to test individual stages
- Pipeline can be modified (add/remove stages)
- Better separation of concerns

#### Issue #5: Duplicate Company Info Logic

**Severity:** Medium
**Impact:** Potential inconsistency
**Effort:** 1-2 hours

**Problem:**
Company info fetching logic exists in two places:
- `CompanyInfoFetcher` class
- Similar logic in `CompaniesManager`

**Solution:**
Merge into single component:
- `CompaniesManager` handles caching and retrieval
- `CompanyInfoFetcher` does actual fetching
- Clear separation of concerns
- Single source of truth

---

## Planned Features

### Alerting System (Planning Phase)

**Status:** Design phase
**Priority:** High
**Effort:** 2-3 weeks

**Objectives:**
- Real-time notifications for perfect job matches (score >= 90)
- Daily digest emails with job summaries
- Error alerts for system failures
- Budget alerts for AI API costs

**Components to build:**
1. Alert manager service
2. Notification templates
3. User preferences storage
4. Integration with email service (SendGrid/Mailgun)
5. Slack webhook integration (optional)

**See:** `docs/ALERTING_SYSTEM_PLAN.md` (in archive)

### Gmail Integration (Future)

**Status:** Backlog
**Priority:** Medium
**Effort:** 1-2 weeks

**Objectives:**
- Parse job posting emails
- Extract job URL and company info
- Submit to queue for processing
- Auto-categorize recruiting emails

**Technical Requirements:**
- Gmail API integration
- Email parsing logic
- Spam detection
- Duplicate detection

### Perfect Match Notifications (Future)

**Status:** Backlog
**Priority:** High
**Effort:** 1 week

**Objectives:**
- Instant notifications for high-score jobs (>= 90)
- Push notifications to mobile
- SMS alerts (optional)
- Integration with Portfolio project

**Technical Requirements:**
- Real-time Firestore listeners
- Push notification service (FCM)
- SMS service (Twilio) - optional

---

## Future Enhancements

### Phase 1: Quality Improvements (3-4 weeks)

- [ ] Comprehensive test coverage (target: >80%)
- [ ] Refactor long functions (Issue #3)
- [ ] Refactor God class to pipeline pattern (Issue #4)
- [ ] Consolidate company info logic (Issue #5)
- [ ] Add missing docstrings
- [ ] Improve type hint coverage
- [ ] Fix remaining broad exception handling in scrapers

### Phase 2: Feature Additions (4-6 weeks)

- [ ] Application tracking system
  - Status tracking (applied, interview, offer, rejected)
  - Application timeline
  - Follow-up reminders
- [ ] Cover letter generation
  - Use resume intake data
  - Template-based generation
  - AI-powered customization
- [ ] Job recommendation email digest
  - Daily/weekly summaries
  - Personalized recommendations
  - One-click apply links
- [ ] Web UI for reviewing matches
  - Job card interface
  - Filtering and sorting
  - Quick apply buttons
  - Notes and tagging

### Phase 3: Scale & Performance (4-6 weeks)

- [ ] Batch AI analysis
  - Analyze multiple jobs in one API request
  - Reduce API costs
  - Faster processing
- [ ] Parallel scraping
  - Process multiple listings concurrently
  - Worker pool pattern
  - Better resource utilization
- [ ] Redis caching layer
  - Cache company information
  - Cache AI responses
  - Reduce Firestore reads
- [ ] Rate limiting with exponential backoff
  - Prevent API throttling
  - Graceful degradation
  - Retry strategies

### Phase 4: Multi-User Support (8-10 weeks)

- [ ] API layer for multi-user access
  - RESTful API
  - GraphQL (optional)
  - API documentation
- [ ] User authentication and authorization
  - JWT tokens
  - Role-based access control
  - OAuth integration
- [ ] Per-user profiles and preferences
  - User-specific settings
  - Custom filters
  - Saved searches
- [ ] Subscription management
  - Tiered plans
  - Usage tracking
  - Billing integration

---

## Known Issues

### Bug Tracking

#### High Priority

None currently identified.

#### Medium Priority

1. **Duplicate jobs in matches (rare)**
   - Cause: URL already existed before queue system
   - Workaround: Run cleanup script `cleanup_job_matches.py`
   - Fix: Improve duplicate detection in intake

2. **Timezone detection for global companies**
   - Current: Smart detection for small/medium companies
   - Issue: May misidentify HQ timezone for large companies
   - Status: Acceptable, working as designed

#### Low Priority

1. **Long company names truncated in logs**
   - Impact: Cosmetic only
   - Workaround: Check Firestore for full name

2. **Inconsistent naming in some test files**
   - Impact: Minor readability issue
   - Priority: Code cleanup task

### Performance Considerations

**Current Performance:**
- Profile loading: ~2s
- Queue intake: ~0.5s per job
- AI analysis: ~7-10s per job (Claude Haiku)
- Total processing: ~12s per job

**Acceptable for current scale (personal use, 10-50 jobs/day)**

**Future optimization needed for:**
- High volume processing (>100 jobs/day)
- Multiple users
- Real-time requirements

---

## Metrics Tracking

### Current State (October 2025)

- **Lines of Code:** ~3,500 (src/)
- **Test Coverage:** ~15% (improving)
- **Code Duplication:** ~3% (down from 8%)
- **Cyclomatic Complexity:** Moderate
- **Active Technical Debt:** 3 medium-priority issues

### Target State (6 months)

- **Lines of Code:** ~4,000 (with new features)
- **Test Coverage:** >80%
- **Code Duplication:** <2%
- **Cyclomatic Complexity:** Low (all functions <10)
- **Active Technical Debt:** 0 medium+ priority issues

### Quality Metrics

**Resolved Issues:**
- ✅ Firestore initialization duplication (195 lines eliminated)
- ✅ Broad exception handling in critical files (26 instances fixed)
- ✅ CI/CD pipeline (all checks passing)
- ✅ Queue system architecture (production ready)

**In Progress:**
- 🟡 Test coverage improvements
- 🟡 Documentation consolidation

**Upcoming:**
- 🔄 Long function refactoring
- 🔄 God class refactoring
- 🔄 Company info consolidation

---

## Contributing

When working on roadmap items:

1. **Create a branch:** `feature/issue-#-description` or `enhancement/feature-name`
2. **One item per PR:** Don't mix features or refactoring
3. **Add tests first:** Write tests before implementing
4. **Verify no regression:** All existing tests must pass
5. **Update documentation:** Keep docs in sync with code
6. **Mark complete:** Update this document when done

---

## Review Schedule

This roadmap is reviewed and updated:
- **After each sprint** - Mark completed items
- **Monthly** - Re-prioritize based on needs
- **Quarterly** - Major planning and goal setting

**Next Review Date:** 2025-11-16 (1 month)

---

## Related Documentation

- **[Architecture](architecture.md)** - System design and components
- **[Development](development.md)** - Development workflow
- **[Queue System](queue-system.md)** - Queue architecture details
- **[Contributing](../CONTRIBUTING.md)** - Contribution guidelines

---

**Last Updated:** 2025-10-16
