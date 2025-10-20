# Job Listing Data Structure Cleanup Plan

## Executive Summary

This document outlines a plan to clean up deprecated, legacy, and confusing fields in the job listing data structures across the job-finder codebase.

## Current Issues Identified

### 1. **Naming Inconsistencies**

**Problem**: Python code uses `snake_case` while Firestore uses `camelCase`, requiring constant transformations.

**Examples**:
- `company_website` (Python) → `companyWebsite` (Firestore)
- `company_info` (Python) → `companyInfo` (Firestore)
- `posted_date` (Python) → `postedDate` (Firestore)
- `match_score` (Python) → `matchScore` (Firestore)

**Impact**:
- Error-prone manual transformations in [firestore_storage.py](../src/job_finder/storage/firestore_storage.py)
- Confusion when reading code (which convention applies where?)
- TypeScript types in job-finder-FE must match Firestore (camelCase)

---

### 2. **Confusing `keywords` Field**

**Problem**: The `keywords` field has multiple conflicting purposes and is populated differently by different parts of the system.

**Current behavior**:
- **Scrapers**: Populate with job metadata (department names from Greenhouse, requisition IDs from Workday)
- **AI Matcher**: Overwrites with ATS keywords from `resume_intake_data["keywords_to_include"]`
- **Documentation**: Says "populated by AI analysis" but scrapers also populate it
- **job-finder-FE**: Reads from `resumeIntakeData.ats_keywords` for resume generation (ignores job-level `keywords`)

**Impact**:
- Misleading field name (what kind of keywords?)
- Data loss (scraper metadata overwritten by AI)
- Unused field (job-finder-FE doesn't read it)

---

### 3. **Legacy Pipeline Support**

**Problem**: Codebase maintains both monolithic and granular pipeline code paths.

**Current state**:
- **Jobs**: Both monolithic (`sub_task=None`) and granular (`sub_task=JOB_SCRAPE/FILTER/ANALYZE/SAVE`) supported
- **Companies**: Granular only (REQUIRED to have `company_sub_task`)
- **Code**: `_process_job()` checks `if not sub_task` to route to legacy path

**Impact**:
- Increased complexity in [processor.py](../src/job_finder/queue/processor.py)
- Two code paths to maintain and test
- No clear migration timeline documented

---

### 4. **Deprecated Filter System**

**Problem**: Old `JobFilter` class still exists alongside new `StrikeFilterEngine`.

**Current state**:
- **Old**: [job_filter.py](../src/job_finder/filters/job_filter.py) - Traditional boolean filtering
- **New**: [strike_filter_engine.py](../src/job_finder/filters/strike_filter_engine.py) - Two-tier strike system
- **Status**: Legacy filter maintained but not used in granular pipeline

**Impact**:
- Dead code in codebase
- Confusion about which filter to use
- Extra maintenance burden

---

### 5. **Ambiguous Optional Fields**

**Problem**: Several fields are marked "optional" but have unclear semantics about when they're present.

**Examples**:
- `company_info` - "Optional" but actually ALWAYS populated during processing (via `CompanyInfoFetcher`)
- `companyId` - "Optional" but ALWAYS added during JOB_ANALYZE step
- `posted_date` - Optional and truly may be missing, but no handling of missing dates in UI
- `salary` - Optional and truly may be missing, but unclear if absence means "not listed" or "scraping failed"

**Impact**:
- Unclear contracts between systems
- Potential null reference errors in job-finder-FE
- No way to distinguish "not scraped" from "not available"

---

### 6. **Resume Intake Data Inconsistencies**

**Problem**: Resume intake data structure has inconsistent field names and unclear nesting.

**Issues**:
- Field `keywords_to_include` in resume intake is mapped to job-level `keywords` field
- But job-finder-FE reads `resumeIntakeData.ats_keywords` instead
- Documentation mentions `keywords_to_include` but code uses various names
- Unclear if `ats_keywords` and `keywords_to_include` are the same thing

**Impact**:
- Data duplication (keywords stored twice?)
- Confusion about which field to use
- Possible desync between job.keywords and resumeIntakeData.ats_keywords

---

### 7. **Unused/Incomplete Features**

**Problem**: Several TODOs and unimplemented features cluttering the codebase.

**Examples**:
- `src/job_finder/storage.py:8` - "TODO: Implement database storage using SQLAlchemy" (likely won't implement)
- `src/job_finder/profile/firestore_loader.py` - Education and projects collection TODOs (not needed?)
- `src/job_finder/main.py` - Scraper initialization TODO (granular pipeline replaced this)

**Impact**:
- Misleading TODOs suggesting features that won't be built
- Dead code paths that will never execute
- Confusion about system capabilities

---

## Proposed Cleanup Actions

### Phase 1: Documentation & Standardization (Low Risk)

#### Action 1.1: Standardize Python Field Names
**Goal**: Use consistent `snake_case` in Python, document the Firestore camelCase mapping clearly.

**Changes**:
1. Create a `FieldMapping` constant in [firestore_storage.py](../src/job_finder/storage/firestore_storage.py):
```python
# Standard field name mappings: Python snake_case → Firestore camelCase
FIELD_MAPPING = {
    "company_website": "companyWebsite",
    "company_info": "companyInfo",
    "company_id": "companyId",
    "posted_date": "postedDate",
    "match_score": "matchScore",
    "matched_skills": "matchedSkills",
    "missing_skills": "missingSkills",
    "experience_match": "experienceMatch",
    "key_strengths": "keyStrengths",
    "potential_concerns": "potentialConcerns",
    "application_priority": "applicationPriority",
    "customization_recommendations": "customizationRecommendations",
    "resume_intake_data": "resumeIntakeData",
    # ... complete mapping
}
```

2. Create helper functions:
```python
def to_firestore_fields(job_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Python snake_case fields to Firestore camelCase."""
    return {FIELD_MAPPING.get(k, k): v for k, v in job_dict.items()}

def from_firestore_fields(firestore_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Firestore camelCase fields to Python snake_case."""
    reverse_mapping = {v: k for k, v in FIELD_MAPPING.items()}
    return {reverse_mapping.get(k, k): v for k, v in firestore_doc.items()}
```

3. Update all direct field assignments to use helper functions.

**Impact**: Clear, centralized mapping; easier to maintain; self-documenting.

---

#### Action 1.2: Clarify `keywords` Field Purpose
**Goal**: Rename or split the `keywords` field to make its purpose clear.

**Option A - Rename Field**:
- Rename `keywords` → `ats_keywords` everywhere to match `resumeIntakeData.ats_keywords`
- Update scraper documentation to NOT populate this field (or use different field like `source_metadata`)

**Option B - Split Fields**:
- Keep `keywords` for scraper metadata (department, req ID, etc.)
- Add new `ats_keywords` field populated by AI
- job-finder-FE reads `ats_keywords` field directly (not from resumeIntakeData)

**Recommendation**: **Option A** - Rename to `ats_keywords` and deprecate scraper population.

**Changes**:
1. Rename field in standard job dictionary (base.py documentation)
2. Update AI matcher to populate `ats_keywords` from `resume_intake_data["keywords_to_include"]`
3. Remove keyword population from scrapers (or move to separate `source_metadata` field)
4. Update Firestore schema to use `atsKeywords` (camelCase)
5. Update job-finder-FE to read `job.atsKeywords` instead of `job.resumeIntakeData.ats_keywords`

**Impact**: Clear purpose, no confusion, single source of truth.

---

#### Action 1.3: Document Optional Field Semantics
**Goal**: Clarify when optional fields are present and what `null` means.

**Changes**:
1. Add detailed field documentation to [base.py](../src/job_finder/scrapers/base.py):
```python
{
    "title": str,              # REQUIRED: Job title/role
    "company": str,            # REQUIRED: Company name
    "company_website": str,    # REQUIRED: Company website URL
    "location": str,           # REQUIRED: Job location
    "description": str,        # REQUIRED: Full job description
    "url": str,                # REQUIRED: Job posting URL

    "company_info": str,       # ALWAYS PRESENT (after processing): Company about/culture info
    "company_id": str,         # ALWAYS PRESENT (after processing): Firestore company document ID
    "ats_keywords": List[str], # ALWAYS PRESENT (after AI analysis): ATS optimization keywords

    "posted_date": str,        # MAY BE ABSENT: Job posting date (if not found on page)
    "salary": str,             # MAY BE ABSENT: Salary range (if not listed in posting)
}
```

2. Add TypeScript types in job-finder-FE with explicit optional markers:
```typescript
interface JobListing {
  // Required fields
  title: string;
  company: string;
  companyWebsite: string;
  location: string;
  description: string;
  url: string;

  // Always present after processing
  companyInfo: string;
  companyId: string;
  atsKeywords: string[];

  // Truly optional (may be null/undefined)
  postedDate?: string | null;
  salary?: string | null;
}
```

**Impact**: Clear contracts, better null handling in job-finder-FE, fewer bugs.

---

### Phase 2: Code Removal (Medium Risk)

#### Action 2.1: Remove Legacy Pipeline Support for Jobs
**Goal**: Jobs must use granular pipeline exclusively (like companies already do).

**Changes**:
1. Remove `if not sub_task` branch from `_process_job()` in [processor.py](../src/job_finder/queue/processor.py)
2. Update `ScraperIntake.submit_job()` to ALWAYS create granular pipeline items (with `sub_task=JOB_SCRAPE`)
3. Add migration script to convert any pending monolithic job items to granular
4. Remove legacy tests

**Migration Strategy**:
```python
# One-time migration script
def migrate_monolithic_job_items():
    """Convert pending monolithic job items to granular pipeline."""
    items = db.collection('job-queue').where('type', '==', 'job').where('sub_task', '==', None).where('status', '==', 'pending').get()

    for item in items:
        # Create new JOB_SCRAPE item with same data
        new_item = {
            **item.to_dict(),
            'sub_task': 'JOB_SCRAPE',
            'pipeline_state': {}
        }
        db.collection('job-queue').add(new_item)

        # Mark old item as migrated
        item.reference.update({'status': 'migrated', 'result_message': 'Converted to granular pipeline'})
```

**Impact**: Simpler code, one code path, easier maintenance.

---

#### Action 2.2: Remove Legacy Filter System
**Goal**: Delete old `JobFilter` class entirely.

**Changes**:
1. Delete [job_filter.py](../src/job_finder/filters/job_filter.py)
2. Remove imports of `JobFilter` from any remaining files
3. Update tests to only test `StrikeFilterEngine`
4. Update CLAUDE.md references to remove legacy filter mentions

**Verification**:
```bash
# Check for any remaining JobFilter usage
grep -r "JobFilter" src/ tests/
grep -r "from job_finder.filters.job_filter" src/ tests/
```

**Impact**: Less code to maintain, no confusion about which filter to use.

---

#### Action 2.3: Remove Incomplete TODOs
**Goal**: Delete TODO comments for features that won't be implemented.

**Changes**:
1. Remove SQLAlchemy TODO from [storage.py](../src/job_finder/storage.py) (Firestore is the only storage)
2. Remove education/projects TODOs from [firestore_loader.py](../src/job_finder/profile/firestore_loader.py) (not needed)
3. Remove scraper initialization TODO from [main.py](../src/job_finder/main.py) (granular pipeline handles this)
4. Add comment explaining why feature isn't needed (if relevant)

**Example**:
```python
# OLD:
# TODO: Implement database storage using SQLAlchemy

# NEW:
# Note: This tool uses Firestore exclusively for storage.
# SQLAlchemy/SQL storage is not planned as it doesn't align with
# the Firebase-based architecture shared with the job-finder-FE project.
```

**Impact**: Clearer codebase, no misleading TODOs.

---

### Phase 3: Structural Changes (High Risk)

#### Action 3.1: Consolidate Resume Intake Data
**Goal**: Single source of truth for keywords and other resume customization data.

**Current Duplication**:
- `job.keywords` (job-level field)
- `job.resumeIntakeData.keywords_to_include` (in AI output)
- `job.resumeIntakeData.ats_keywords` (also in AI output?)

**Proposed Structure**:
```python
# Job dictionary (Python)
{
    "title": "Senior Software Engineer",
    "company": "Netflix",
    # ... other required fields ...

    # NO job-level ats_keywords field anymore

    "resume_intake_data": {
        "target_summary": "...",
        "skills_priority": ["Python", "React", ...],
        "experience_highlights": {...},
        "projects_to_include": [...],
        "achievement_angles": [...],
        "ats_keywords": ["python", "microservices", ...],  # SINGLE source of truth
        "gap_mitigation": {...}
    }
}
```

**Changes**:
1. Remove `keywords`/`ats_keywords` from job-level fields
2. Rename `keywords_to_include` → `ats_keywords` in resume intake structure
3. Update AI prompts to only output `ats_keywords` in resume intake
4. Update job-finder-FE to read `job.resumeIntakeData.atsKeywords` only
5. Update Firestore writes to not include job-level keywords field

**Impact**: No duplication, single source of truth, clearer data flow.

---

#### Action 3.2: Standardize Optional Field Handling
**Goal**: Use `null` consistently to mean "not available" vs. "not scraped yet".

**Changes**:
1. Scrapers return `None` for truly unavailable fields (`posted_date`, `salary`)
2. Processing NEVER adds these fields if scraper didn't populate them
3. Firestore writes preserve `None` as missing field (don't write field at all)
4. job-finder-FE TypeScript types mark as optional: `postedDate?: string`
5. job-finder-FE UI handles missing fields gracefully (show "Not listed" instead of error)

**Example Scraper Code**:
```python
# GOOD: Only populate if actually found
job = {
    "title": title_elem.text,
    "company": company_name,
    # ...
}

# Only add posted_date if found
if posted_date_elem:
    job["posted_date"] = posted_date_elem.text

# AVOID: Don't use empty strings or placeholder values
# job["posted_date"] = ""  # BAD
# job["salary"] = "Not listed"  # BAD
```

**Impact**: Clear semantics, better null handling, fewer bugs.

---

## Implementation Timeline

### Week 1: Documentation & Low-Risk Changes
- [ ] Action 1.1: Standardize field name mapping
- [ ] Action 1.2: Clarify keywords field (rename to ats_keywords)
- [ ] Action 1.3: Document optional field semantics
- [ ] Action 2.3: Remove incomplete TODOs

### Week 2: Code Removal
- [ ] Action 2.1: Remove legacy pipeline support (with migration)
- [ ] Action 2.2: Remove legacy filter system
- [ ] Comprehensive testing of granular pipeline

### Week 3: Structural Changes
- [ ] Action 3.1: Consolidate resume intake data (remove job-level keywords)
- [ ] Action 3.2: Standardize optional field handling
- [ ] Update job-finder-FE project to match new data structures

### Week 4: Verification & Documentation
- [ ] End-to-end testing (job submission → scraping → analysis → job-finder-FE display)
- [ ] Update CLAUDE.md with final data structure documentation
- [ ] Update shared-types.md with authoritative type definitions
- [ ] Create migration guide for any manual data updates needed

---

## Testing Strategy

### Unit Tests
- [ ] Test field mapping functions (to_firestore_fields, from_firestore_fields)
- [ ] Test granular pipeline steps with new field structure
- [ ] Test optional field handling (null vs. missing)

### Integration Tests
- [ ] Test full job pipeline (scrape → filter → analyze → save)
- [ ] Test Firestore write/read with new field structure
- [ ] Test job-finder-FE reading new data structure

### E2E Tests
- [ ] Submit job via job-finder-FE → verify appears in job-matches with correct fields
- [ ] Verify resume generation uses resumeIntakeData.atsKeywords correctly
- [ ] Verify missing optional fields don't cause errors

---

## Rollback Plan

If any phase causes issues:

1. **Phase 1 (Documentation)**: No rollback needed (docs only)
2. **Phase 2 (Code Removal)**:
   - Restore legacy code from git
   - Re-enable legacy pipeline for pending items
3. **Phase 3 (Structural Changes)**:
   - Revert Firestore field structure changes
   - Restore job-level keywords field
   - Revert job-finder-FE to read old structure

**Mitigation**: Use feature flags to gradually enable new structure:
```python
USE_NEW_FIELD_STRUCTURE = os.getenv("USE_NEW_FIELD_STRUCTURE", "false") == "true"

if USE_NEW_FIELD_STRUCTURE:
    # Use new consolidated structure
else:
    # Use legacy structure
```

---

## Success Criteria

### Code Quality
- [ ] Zero references to legacy `JobFilter` class
- [ ] Zero monolithic pipeline code paths
- [ ] All TODOs represent real planned work
- [ ] Field mappings centralized and documented

### Data Quality
- [ ] No duplicate keyword storage
- [ ] Clear semantics for all optional fields
- [ ] Consistent field naming (snake_case Python, camelCase Firestore)

### System Reliability
- [ ] All E2E tests pass
- [ ] job-finder-FE displays jobs correctly with new structure
- [ ] Resume generation works with consolidated atsKeywords

### Documentation
- [ ] CLAUDE.md accurately reflects current data structures
- [ ] shared-types.md matches implementation
- [ ] No misleading or outdated comments in code

---

## Questions for Review

1. **Keywords Consolidation (Action 3.1)**: Should we remove job-level keywords entirely, or keep it for scraper metadata and add separate `ats_keywords`?

2. **Legacy Pipeline (Action 2.1)**: Are there any production job items still using monolithic pipeline that need migration?

3. **Optional Fields (Action 3.2)**: Should we add explicit "reason missing" metadata (e.g., `{"posted_date": null, "posted_date_reason": "not_listed"}`) or just use `null`?

4. **Timeline**: Is 4 weeks reasonable, or should we prioritize certain actions?

5. **Feature Flags**: Should we use feature flags for gradual rollout, or do a full cutover?

---

## References

- [CLAUDE.md](../CLAUDE.md) - Project overview and architecture
- [shared-types.md](shared-types.md) - TypeScript/Python type mappings
- [base.py](../src/job_finder/scrapers/base.py) - Standard job dictionary definition
- [firestore_storage.py](../src/job_finder/storage/firestore_storage.py) - Firestore persistence
- [processor.py](../src/job_finder/queue/processor.py) - Pipeline processing logic
