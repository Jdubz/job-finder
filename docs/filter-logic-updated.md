# Updated Filter Logic - Strike-Based System

## Two-Tier Filtering System

### Tier 1: Hard Rejections (Immediate Fail)
These are absolute deal-breakers - job is immediately marked as FILTERED.

### Tier 2: Strike System (Accumulate Points)
Jobs accumulate strikes. If strikes >= threshold (e.g., 3), job is FILTERED.
Each strike has a severity (1-3 points).

---

## Hard Rejections (Immediate FILTERED)

### 1. Job Type - Sales/HR/Non-Engineering
**Logic:** Detect non-engineering role types in title/description
**Patterns:**
- Sales: "sales engineer", "account executive", "business development", "sales representative"
- HR: "recruiter", "talent acquisition", "human resources"
- Support: "customer support", "help desk", "technical support"
- Management: "engineering manager", "director of engineering" (unless you want these?)

**Action:** REJECT immediately

### 2. Seniority - Too Junior
**Logic:** Detect junior-level indicators in title
**Patterns:**
- "associate"
- "junior"
- "intern"
- "entry-level"
- "entry level"
- "co-op"
- "trainee"

**Action:** REJECT immediately

### 3. Salary - Below Minimum Floor
**Logic:** Parse salary, reject if max < $100k
**Examples:**
- "$80k-$95k" → REJECT
- "$90k-$110k" → ALLOW (max is $110k)
- No salary listed → ALLOW (no data)

**Action:** REJECT if salary < $100k

### 4. Commission Only / MLM
**Logic:** Detect commission-only indicators
**Patterns:** (same as before)
- "commission only"
- "unlimited earning potential"
- "mlm"
- "be your own boss"

**Action:** REJECT immediately

### 5. Required Clearance / Relocation
**Logic:** Detect deal-breaker requirements
**Patterns:**
- "security clearance required"
- "clearance required"
- "relocation required"
- "must relocate"

**Action:** REJECT immediately

### 6. Remote Policy Violations
**Logic:**
- If remote → ALLOW
- If hybrid + Portland → ALLOW
- If hybrid + NOT Portland → REJECT
- If onsite → REJECT

**Detection:**
- Remote: "fully remote", "100% remote", "remote position", "work from home", "wfh"
- Hybrid: "hybrid", "flexible work", "X days in office"
- Portland: "portland" in location or description
- Onsite: "on-site", "in-office", "office-based" (and NOT remote/hybrid)

**Action:** REJECT if not (remote OR (hybrid AND portland))

### 7. Excluded Companies
**Logic:** Company name substring match
**Examples:** TBD - any companies you never want to work for?

**Action:** REJECT immediately

---

## Strike System (Accumulate to 3+ = FILTERED)

### Strike Severity Levels
- **1 point:** Minor concern
- **2 points:** Moderate concern
- **3 points:** Major concern (almost a hard reject)

### Strikes List

#### Technology Stack Strikes

**Bad Tech (2 points each):**
- Java (NOT JavaScript/TypeScript)
- PHP
- Ruby / Rails
- WordPress
- .NET / C#
- Perl

**Missing Good Tech (1 point if NONE found):**
- Python
- TypeScript
- JavaScript
- React
- Angular
- Node.js
- GCP (Google Cloud Platform)
- Kubernetes
- Docker

**Logic:**
- If job has 2+ bad tech → 4+ points (likely filtered)
- If job has 0 good tech → 1 point
- If job has 1 good tech + 1 bad tech → 2 points (still passes)
- If job has 2+ good tech + 1 bad tech → 2 points (still passes)

#### Salary Strikes

**Low Salary (2 points):**
- Salary listed and max < $150k

**Examples:**
- $120k-$140k → 2 points (below $150k)
- $140k-$160k → 0 points (max >= $150k)
- No salary → 0 points (no data)

#### Experience Strikes

**Too Little Experience (1 point):**
- Job requires < 6 years experience

**Examples:**
- "2-4 years" → 1 point
- "5+ years" → 1 point (< 6)
- "7+ years" → 0 points
- No experience mentioned → 0 points

#### Seniority Strikes

**Seniority Too Low (2 points):**
- Title contains "mid-level" or "mid level"

**Seniority Too High (1 point):**
- Title contains "principal" or "director"

**Allowed Levels (0 points):**
- Senior
- Staff
- Lead
- (No level specified - defaults to mid-senior)

**Examples:**
- "Mid-Level Engineer" → 2 points
- "Principal Engineer" → 1 point
- "Director of Engineering" → 1 point
- "Senior Engineer" → 0 points
- "Staff Engineer" → 0 points
- "Software Engineer" → 0 points (no level = assume senior)

#### Location/Remote Strikes

**Weak Remote Language (1 point):**
- "Remote possible" (not "fully remote")
- "Occasional remote work"
- "Remote considered"

**Examples:**
- "Fully remote" → 0 points
- "Remote possible for right candidate" → 1 point

#### Description Quality Strikes

**Too Short (1 point):**
- Description < 200 characters

**Too Generic (1 point):**
- Description contains excessive buzzwords:
  - "rockstar", "ninja", "guru", "10x engineer"
  - "fast-paced environment" (without substance)

---

## Strike Threshold

**Threshold:** 3 points
- 0-2 points → Job PASSES filters → Sent to AI
- 3+ points → Job FILTERED → Status = filtered, reasons listed

---

## Examples

### Example 1: Good Job (0 points)
```
Title: Senior Software Engineer
Company: Google
Salary: $160k-$200k
Stack: Python, GCP, Kubernetes
Experience: 5+ years
Remote: Fully remote
```
**Strikes:** 0 points → PASSES

### Example 2: Marginal Job (2 points)
```
Title: Software Engineer
Company: Startup
Salary: $130k-$145k
Stack: Python, Ruby on Rails
Experience: 3+ years
Remote: Fully remote
```
**Strikes:**
- Low salary (< $150k): 2 points
- Bad tech (Ruby/Rails): 2 points
- Total: 4 points → FILTERED

### Example 3: Borderline (2 points)
```
Title: Staff Engineer
Company: Microsoft
Salary: $140k-$165k
Stack: TypeScript, React, Node.js
Experience: 5+ years
Remote: Fully remote
```
**Strikes:**
- Experience < 6 years: 1 point
- Low salary (< $150k min): 0 points (max is $165k)
- Total: 1 point → PASSES

### Example 4: Hard Reject
```
Title: Junior Software Engineer
Company: Amazon
Salary: $95k-$115k
Stack: Java, Spring Boot
Experience: 2+ years
Remote: Hybrid (Seattle)
```
**Hard Rejections:**
- Junior in title → REJECT
- Salary < $100k (min) → REJECT
- Not remote AND not (hybrid + Portland) → REJECT
**Result:** FILTERED (hard rejection)

---

## Implementation Notes

### Data Model Update Needed

```python
@dataclass
class FilterRejection:
    filter_category: str
    filter_name: str
    reason: str
    detail: str
    severity: str  # NEW: "hard_reject" or "strike"
    points: int    # NEW: Strike points (0 for hard rejects)

@dataclass
class FilterResult:
    passed: bool
    rejections: List[FilterRejection]
    total_strikes: int  # NEW: Total strike points
    strike_threshold: int  # NEW: Threshold for filtering (default 3)
```

### Filter Engine Changes

```python
class JobFilterEngine:
    def __init__(self, config: dict):
        # ...
        self.strike_threshold = config.get("strikeThreshold", 3)

    def evaluate_job(self, job_data: dict) -> FilterResult:
        result = FilterResult(passed=True, total_strikes=0, strike_threshold=self.strike_threshold)

        # Phase 1: Check hard rejections
        if self._check_hard_rejections(job_data, result):
            return result  # Failed hard reject

        # Phase 2: Accumulate strikes
        self._accumulate_strikes(job_data, result)

        # Phase 3: Check if strikes exceed threshold
        if result.total_strikes >= self.strike_threshold:
            result.passed = False

        return result
```

### Configuration Schema

```python
{
    # Hard Rejections
    "excludedJobTypes": ["sales", "hr", "recruiter", "support"],
    "excludedSeniority": ["associate", "junior", "intern", "entry-level"],
    "minSalaryHardFloor": 100000,
    "remotePolicy": "remote_or_portland_hybrid",
    "rejectCommissionOnly": True,
    "excludedKeywordsDescription": ["clearance required", "relocation required"],
    "excludedCompanies": [],

    # Strike System
    "strikeThreshold": 3,

    # Tech Stack Strikes
    "badTech": {
        "Java": 2,      # 2 points per bad tech
        "PHP": 2,
        "Ruby": 2,
        "Rails": 2,
        "WordPress": 2,
        ".NET": 2,
        "C#": 2,
        "Perl": 2
    },
    "goodTech": ["Python", "TypeScript", "JavaScript", "React", "Angular", "Node.js", "GCP", "Kubernetes", "Docker"],
    "missingGoodTechStrike": 1,  # 1 point if no good tech found

    # Salary Strikes
    "salaryStrikeThreshold": 150000,  # < $150k = 2 points
    "salaryStrikePoints": 2,

    # Experience Strikes
    "minExperiencePreferred": 6,  # < 6 years = 1 point
    "lowExperienceStrikePoints": 1,

    # Seniority Strikes
    "seniorityStrikes": {
        "mid-level": 2,
        "mid level": 2,
        "principal": 1,
        "director": 1
    },

    # Quality Strikes
    "minDescriptionLength": 200,
    "shortDescriptionStrike": 1,
    "buzzwordStrike": 1,
    "buzzwords": ["rockstar", "ninja", "guru", "10x engineer"]
}
```

---

## Questions

1. **Engineering Manager / Director roles:** Hard reject or allow with strikes?
2. **Excluded companies:** Any specific companies to always reject?
3. **Tech stack clarifications:**
   - Is C++ on the bad list?
   - Is Go on the good list?
   - Is Rust on the good list?
4. **Seniority:** Should we add "Engineering Manager" to hard rejects or allow with strikes?
5. **Strike threshold:** Is 3 points the right threshold, or should it be higher (4-5)?
