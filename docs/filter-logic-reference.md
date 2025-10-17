# Filter Logic Reference

Quick reference for all filter rules in JobFilterEngine.

## Current Default Configuration

```python
{
    # Exclusions
    "excludedCompanies": [],
    "excludedDomains": [],
    "excludedKeywordsUrl": [],
    "excludedKeywordsTitle": ["senior", "lead", "principal", "intern", "junior"],
    "excludedKeywordsDescription": ["clearance required", "relocation required"],

    # Location & Remote
    "remotePolicy": "remote_only",  # Options: remote_only, hybrid_ok, on_site_ok, any
    "allowedLocations": ["Portland, OR", "Remote"],

    # Job Type
    "employmentType": "full_time",  # Options: full_time, contract, part_time, any

    # Experience
    "minYearsExperience": 3,
    "maxYearsExperience": 10,
    "allowedSeniority": ["mid", "senior"],  # Options: junior, mid, senior, staff, principal, lead

    # Salary
    "minSalary": 100000,  # Null = no minimum

    # Tech Stack
    "requiredTech": ["Python", "TypeScript", "React", "Node.js", "AWS"],
    "excludedTech": ["PHP", "WordPress", "Java"],

    # Quality
    "minDescriptionLength": 200,
    "rejectCommissionOnly": True,

    # Meta
    "enabled": True
}
```

## Filter Order (First rejection wins)

1. ✅ **Excluded Companies** - Substring match (case-insensitive)
2. ✅ **Excluded Domains** - URL contains domain
3. ✅ **Excluded Keywords (URL)** - URL contains keyword
4. ✅ **Excluded Keywords (Title)** - Title contains keyword
5. ✅ **Excluded Keywords (Description)** - Description contains keyword
6. ✅ **Remote Policy** - Job must match remote requirements
7. ✅ **Tech Stack (Excluded)** - Job cannot require excluded tech (word boundaries)
8. ✅ **Tech Stack (Required)** - Job must mention at least one required tech
9. ✅ **Experience Level** - Years of experience in acceptable range
10. ✅ **Seniority Level** - Title seniority must be in allowed list
11. ✅ **Salary** - Salary must meet minimum (if listed)
12. ✅ **Employment Type** - Must match required type
13. ✅ **Description Length** - Must be at least minimum length
14. ✅ **Commission Only** - Reject MLM/commission-only jobs

## Filter Details

### 1. Excluded Companies
**Logic:** Case-insensitive substring match in company name
**Example:** `"Meta"` matches `"Meta Platforms, Inc."`
**Rejects:** Any job at excluded companies

### 2. Excluded Domains
**Logic:** Substring match in URL
**Example:** `"indeed.com"` matches `"https://www.indeed.com/job/123"`
**Rejects:** Jobs from excluded job boards

### 3. Excluded Keywords (URL)
**Logic:** Substring match in URL
**Example:** `"apply-now"` matches URLs with `/apply-now/`
**Rejects:** URLs with excluded patterns

### 4. Excluded Keywords (Title)
**Logic:** Substring match in job title
**Default:** `["senior", "lead", "principal", "intern", "junior"]`
**Example:** `"senior"` matches `"Senior Software Engineer"`
**Rejects:** Jobs with seniority levels you don't want

### 5. Excluded Keywords (Description)
**Logic:** Substring match in job description
**Default:** `["clearance required", "relocation required"]`
**Example:** Rejects jobs requiring security clearance
**Rejects:** Jobs with deal-breaker requirements

### 6. Remote Policy
**Logic:** Detect remote/hybrid/onsite indicators in description + location

**Indicators:**
- **Remote:** "fully remote", "100% remote", "work from home", "wfh", "remote-first"
- **Hybrid:** "hybrid", "flexible work", "remote with occasional", "days in office"
- **Onsite:** "on-site", "onsite", "in-office", "office-based"

**Policies:**
- `remote_only`: ONLY fully remote (no hybrid, no onsite)
- `hybrid_ok`: Remote OR hybrid (no onsite)
- `on_site_ok`: Any (remote, hybrid, or onsite)
- `any`: No filtering

**Default:** `remote_only`

### 7. Tech Stack (Excluded)
**Logic:** Word boundary regex match (prevents false positives)
**Example:** `"Java"` matches `"Java required"` but NOT `"JavaScript"`
**Rejects:** Jobs requiring technologies you don't want to use

### 8. Tech Stack (Required)
**Logic:** At least ONE required tech must be found (word boundaries)
**Default:** `["Python", "TypeScript", "React", "Node.js", "AWS"]`
**Example:** Job must mention Python OR TypeScript OR React, etc.
**Rejects:** Jobs with NO matching tech

### 9. Experience Level (Years)
**Logic:** Parse description for experience patterns, use highest number found

**Patterns Detected:**
- `"5+ years"` → 5 years
- `"3-5 years"` → 5 years (max of range)
- `"minimum 7 years"` → 7 years
- `"at least 5 years"` → 5 years

**Default Range:** 3-10 years
**Rejects:** Too little experience (< 3 years) or too much (> 10 years)
**Allows:** No experience mentioned (assumes flexible)

### 10. Seniority Level
**Logic:** Detect seniority in title, default to "mid" if not specified

**Detection Patterns:**
- **Junior:** "junior", "jr.", "entry level"
- **Mid:** "mid-level", "intermediate"
- **Senior:** "senior", "sr."
- **Staff:** "staff"
- **Principal:** "principal"
- **Lead:** "lead", "team lead"

**Default Allowed:** `["mid", "senior"]`
**Example:** "Software Engineer" (no level) → defaults to "mid" → PASSES
**Example:** "Junior Engineer" → "junior" → REJECTS

### 11. Salary
**Logic:** Parse salary, use max of range, skip if not listed

**Parsing:**
- `"$120k-$150k"` → $150,000
- `"$100,000+"` → $100,000
- `"100-120K"` → $120,000

**Default Minimum:** $100,000
**Rejects:** Salary below minimum
**Allows:** No salary listed (doesn't reject)

### 12. Employment Type
**Logic:** Detect contract/part-time indicators

**Indicators:**
- **Contract:** "contract", "contractor", "c2c", "1099", "freelance", "temporary"
- **Part-time:** "part-time", "part time"

**Default:** `full_time`
**Rejects:** Contract or part-time when full_time required

### 13. Description Length
**Logic:** Character count of description
**Default Minimum:** 200 characters
**Rejects:** Very short/low-effort postings

### 14. Commission Only
**Logic:** Detect MLM/commission-only indicators

**Indicators:**
- "commission only"
- "commission-only"
- "performance-based pay"
- "unlimited earning potential"
- "be your own boss"
- "mlm"
- "multi-level marketing"

**Default:** Reject commission-only
**Rejects:** MLM schemes and commission-only sales jobs

## Questions to Clarify

1. **Remote Policy**: Do you want `remote_only` or `hybrid_ok`?
2. **Excluded Keywords (Title)**: Should we exclude "senior", "lead", etc.?
3. **Seniority**: Should we allow "mid" and "senior", or just "mid"?
4. **Experience Range**: Is 3-10 years correct?
5. **Required Tech**: Is the list `["Python", "TypeScript", "React", "Node.js", "AWS"]` correct?
6. **Excluded Tech**: Should we exclude Java? (Might filter out JavaScript/TypeScript jobs)
7. **Minimum Salary**: Is $100k the right floor?
8. **Description Length**: Is 200 characters enough to filter spam?

## Edge Cases to Discuss

1. **"JavaScript" matching "Java"**: Currently uses word boundaries, so `"Java"` won't match `"JavaScript"`
2. **No experience mentioned**: Currently ALLOWS jobs with no experience requirement
3. **No salary listed**: Currently ALLOWS jobs without salary info
4. **Seniority in description vs title**: Currently only checks title for seniority
5. **Remote with quarterly onsite**: Currently would be marked as remote (not hybrid)
