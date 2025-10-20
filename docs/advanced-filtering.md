# Advanced Job Filtering System

## Overview

Comprehensive filtering system to evaluate jobs **before** AI analysis, ensuring only high-quality candidates progress through the pipeline. This reduces AI costs and improves match quality.

## Architecture

### Current Flow (Simple)
```
Scraper → Queue → Stop List Check → AI Analysis → job-matches
```

### New Flow (Advanced)
```
Scraper → Queue → Advanced Filter Engine → AI Analysis (only best jobs) → job-matches
                         ↓
                   Filtered Jobs (with detailed rejection reasons)
```

## Filter Categories

### 1. **Exclusion Filters** (Block jobs that don't meet requirements)

#### Company Filters
- ✅ **Excluded Companies** (existing)
  - Example: "Meta", "Amazon" (if you don't want FAANG)
  - Match: Substring in company name (case-insensitive)

#### Domain Filters
- ✅ **Excluded Domains** (existing)
  - Example: "indeed.com", "ziprecruiter.com"
  - Match: Substring in URL

#### Keyword Filters (Enhanced)
- ✅ **Excluded Keywords in URL** (existing)
- 🆕 **Excluded Keywords in Title**
  - Example: "senior", "lead", "principal", "staff" (if too senior)
  - Example: "intern", "junior" (if too junior)
- 🆕 **Excluded Keywords in Description**
  - Example: "clearance required", "relocation required", "travel 50%"
  - Example: "C++", "Java", ".NET" (if you only want Python/JS)

### 2. **Requirement Filters** (Must-have criteria)

#### Location & Remote
- 🆕 **Remote Work Policy**
  - Options: `remote_only`, `hybrid_ok`, `on_site_ok`, `any`
  - Parse job description for: "remote", "hybrid", "on-site", "in-office"
  - Reject if doesn't match preference

- 🆕 **Location Preferences**
  - Allowed locations: ["Portland, OR", "Seattle, WA", "Remote"]
  - Reject if location doesn't match AND not remote

#### Job Type
- 🆕 **Employment Type**
  - Options: `full_time`, `contract`, `part_time`, `any`
  - Parse for: "full-time", "FTE", "contractor", "C2H", "part-time"

#### Experience Level
- 🆕 **Years of Experience Range**
  - Min: 3, Max: 8 (example)
  - Parse job description for: "5+ years", "3-5 years experience"
  - Use regex: `(\d+)[\+\-]?\s*years?`

- 🆕 **Seniority Level**
  - Options: `junior`, `mid`, `senior`, `staff`, `principal`
  - Parse title for level indicators
  - Example: Reject "Senior" if you want "Mid-level"

#### Salary
- 🆕 **Minimum Salary**
  - Example: $120,000
  - Parse for salary ranges: "$120k-$150k", "$100,000+"
  - Skip if salary not listed (don't reject)

#### Tech Stack (Positive Filters)
- 🆕 **Required Technologies** (at least one must be present)
  - Example: ["Python", "TypeScript", "React", "Node.js"]
  - Match in job description or title

- 🆕 **Excluded Technologies** (none can be present)
  - Example: ["PHP", "WordPress", "Ruby on Rails"]
  - Match in job description

### 3. **Quality Filters** (Job posting quality indicators)

- 🆕 **Minimum Description Length**
  - Example: 200 characters
  - Reject very short/low-effort postings

- 🆕 **Spam Detection**
  - Keywords indicating spam: "earn $10k/month", "work from home opportunity"
  - Excessive caps lock, excessive exclamation marks

- 🆕 **Commission-Only Rejection**
  - Keywords: "commission only", "performance-based pay", "1099"
  - Reject unless explicitly allowed

## Filter Configuration

### Firestore Schema

**Collection:** `job-finder-config`
**Document:** `job-filters`

```typescript
interface JobFilters {
  // Exclusions (existing + enhanced)
  excludedCompanies: string[]
  excludedDomains: string[]
  excludedKeywordsUrl: string[]
  excludedKeywordsTitle: string[]        // NEW
  excludedKeywordsDescription: string[]  // NEW

  // Location & Remote
  remotePolicy: 'remote_only' | 'hybrid_ok' | 'on_site_ok' | 'any'
  allowedLocations: string[]  // e.g., ["Portland, OR", "Remote"]

  // Job Type
  employmentType: 'full_time' | 'contract' | 'part_time' | 'any'

  // Experience
  minYearsExperience: number | null  // null = no minimum
  maxYearsExperience: number | null  // null = no maximum
  allowedSeniority: ('junior' | 'mid' | 'senior' | 'staff' | 'principal')[]

  // Salary
  minSalary: number | null  // null = no minimum

  // Tech Stack
  requiredTech: string[]  // At least one must be present
  excludedTech: string[]  // None can be present

  // Quality
  minDescriptionLength: number
  rejectCommissionOnly: boolean

  // Meta
  enabled: boolean
  lastUpdated: Timestamp
}
```

### Default Configuration

```python
DEFAULT_FILTERS = {
    # Exclusions
    "excludedCompanies": [],
    "excludedDomains": [],
    "excludedKeywordsUrl": [],
    "excludedKeywordsTitle": ["senior", "lead", "principal", "intern", "junior"],
    "excludedKeywordsDescription": ["clearance required", "relocation required"],

    # Location & Remote
    "remotePolicy": "remote_only",
    "allowedLocations": ["Portland, OR", "Remote"],

    # Job Type
    "employmentType": "full_time",

    # Experience
    "minYearsExperience": 3,
    "maxYearsExperience": 10,
    "allowedSeniority": ["mid", "senior"],

    # Salary
    "minSalary": 100000,

    # Tech Stack
    "requiredTech": ["Python", "TypeScript", "React", "Node.js", "AWS"],
    "excludedTech": ["PHP", "WordPress", "Java"],

    # Quality
    "minDescriptionLength": 200,
    "rejectCommissionOnly": True,

    # Meta
    "enabled": True,
}
```

## Filter Results

### New Queue Status: `filtered`

Add to `QueueStatus` enum:
- `pending` - In queue, not processed yet
- `processing` - Currently being processed
- `filtered` - **NEW** - Rejected by filter engine (not AI worthy)
- `skipped` - Duplicate or stop list blocked
- `success` - Passed filters, AI analyzed, saved to job-matches
- `failed` - Processing error

### Rejection Reason Structure

```python
@dataclass
class FilterRejection:
    """Detailed rejection reason from filter engine."""

    filter_category: str  # "location", "experience", "tech_stack", etc.
    filter_name: str      # "remote_policy", "min_years_experience", etc.
    reason: str           # Human-readable reason
    detail: str           # Specific detail (e.g., "Job requires 10+ years")

class FilterResult:
    """Result of running filter engine on a job."""

    passed: bool
    rejections: List[FilterRejection]

    def get_rejection_summary(self) -> str:
        """Get comma-separated list of rejection reasons."""
        return ", ".join([r.reason for r in self.rejections])
```

### Example Rejection Reasons

```python
# Location rejection
FilterRejection(
    filter_category="location",
    filter_name="remote_policy",
    reason="Requires on-site work",
    detail="Job description mentions 'in-office 5 days/week'"
)

# Experience rejection
FilterRejection(
    filter_category="experience",
    filter_name="years_experience",
    reason="Requires too much experience",
    detail="Job requires 10+ years, your max is 8"
)

# Tech stack rejection
FilterRejection(
    filter_category="tech_stack",
    filter_name="required_tech",
    reason="Missing required technologies",
    detail="None of your required tech found: Python, TypeScript, React"
)

# Seniority rejection
FilterRejection(
    filter_category="experience",
    filter_name="seniority_level",
    reason="Seniority level mismatch",
    detail="Job title contains 'Principal' (not in allowed list)"
)
```

## Implementation Plan

### Phase 1: Core Filter Engine (This PR)
1. Create `JobFilterEngine` class in `src/job_finder/filters/filter_engine.py`
2. Create filter configuration loader in `config_loader.py`
3. Add `filtered` status to `QueueStatus` enum (update shared-types)
4. Implement basic filters:
   - Enhanced keyword filtering (title + description)
   - Remote work policy
   - Tech stack requirements
5. Update `QueueItemProcessor` to call filter engine before AI analysis
6. Add comprehensive tests

### Phase 2: Advanced Filters
1. Experience level detection
2. Salary parsing and filtering
3. Location matching
4. Job type filtering
5. Quality filters (spam detection, minimum length)

### Phase 3: UI Integration (job-finder-FE)
1. Create `JobFiltersTab.tsx` for configuration UI
2. Add filter statistics to queue dashboard
3. Display rejection reasons in queue management
4. Add "View Filtered Jobs" section

### Phase 4: Analytics & Optimization
1. Track filter performance (which filters reject most jobs)
2. A/B testing different filter thresholds
3. Machine learning for spam detection
4. Automatic tech stack extraction from job descriptions

## Benefits

### Cost Savings
- **Before:** AI analyzes 1000 jobs/day at $0.01 each = $10/day = $300/month
- **After:** Filters reduce to 100 jobs/day = $1/day = $30/month
- **Savings:** 90% reduction in AI costs

### Quality Improvement
- Only analyze jobs that meet basic requirements
- Higher match rate from AI (better quality input)
- Fewer false positives in job-matches

### User Experience
- Detailed rejection reasons help understand why jobs didn't make the cut
- Can fine-tune filters based on rejection patterns
- Transparency in the pipeline

## Edge Cases & Considerations

1. **Missing Job Data**
   - If description is missing, should we reject or allow?
   - Decision: Allow if description missing, but flag for manual review

2. **Ambiguous Tech Stack**
   - Job mentions "JavaScript" but you want "TypeScript"
   - Decision: Treat as separate technologies, be explicit in requirements

3. **Salary Ranges**
   - Job says "$80k-$150k" and your min is $120k
   - Decision: Use the max of the range if provided

4. **Remote Hybrid Confusion**
   - Job says "remote with quarterly on-sites"
   - Decision: Treat as remote, not hybrid (occasional travel OK)

5. **Seniority in Body vs Title**
   - Title says "Engineer" but description wants "10+ years"
   - Decision: Check both title and parsed experience years

## Testing Strategy

1. **Unit Tests**
   - Each filter function tested independently
   - Edge cases for parsing (experience, salary, tech stack)
   - Regex pattern matching

2. **Integration Tests**
   - Full filter engine with real job descriptions
   - Test rejection reason accuracy
   - Performance testing (1000 jobs in <1 second)

3. **Regression Tests**
   - Ensure existing stop list functionality still works
   - Verify queue status flow with new `filtered` status

## Migration Strategy

1. **Gradual Rollout**
   - Start with `enabled: false` in config
   - Test in staging with real data
   - Enable filters one category at a time

2. **Backwards Compatibility**
   - Keep existing stop list system working
   - New filters are additive, not breaking changes
   - Can disable advanced filters via config

3. **Data Migration**
   - No schema changes to existing queue items
   - New fields added to config collection only

---

**Ready to implement?** Let's start with Phase 1: Core Filter Engine.
