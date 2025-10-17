# Firestore Filter Configuration Schema

Configuration for the strike-based job filtering system.

## Collections

### 1. `job-finder-config/job-filters`

Main filter configuration with hard rejections and strike settings.

```typescript
interface JobFilters {
  // Meta
  enabled: boolean
  strikeThreshold: number  // Default: 5

  // Hard Rejections (immediate fail)
  hardRejections: {
    excludedJobTypes: string[]        // ["sales", "hr", "recruiter", "support"]
    excludedSeniority: string[]       // ["associate", "junior", "intern", "entry-level", "entry level"]
    excludedCompanies: string[]       // [] (managed via company profiles)
    excludedKeywords: string[]        // ["clearance required", "relocation required"]
    minSalaryFloor: number           // 100000 ($100k hard minimum)
    rejectCommissionOnly: boolean    // true
  }

  // Remote Policy (hard rejection if violated)
  remotePolicy: {
    allowRemote: boolean              // true
    allowHybridPortland: boolean      // true (hybrid only if Portland)
    allowOnsite: boolean              // false
  }

  // Strike: Salary
  salaryStrike: {
    enabled: boolean                  // true
    threshold: number                 // 150000 ($150k)
    points: number                    // 2
  }

  // Strike: Experience
  experienceStrike: {
    enabled: boolean                  // true
    minPreferred: number             // 6 years
    points: number                   // 1
  }

  // Strike: Seniority
  seniorityStrikes: {
    "mid-level": number              // 2 points
    "mid level": number              // 2 points
    "principal": number              // 1 point
    "director": number               // 1 point
    "manager": number                // 1 point
    "engineering manager": number    // 1 point
  }

  // Strike: Quality
  qualityStrikes: {
    minDescriptionLength: number     // 200
    shortDescriptionPoints: number   // 1
    buzzwords: string[]              // ["rockstar", "ninja", "guru", "10x engineer"]
    buzzwordPoints: number           // 1
  }

  // Metadata
  lastUpdated: Timestamp
  version: string                    // "2.0-strike-system"
}
```

### 2. `job-finder-config/technology-ranks`

Technology ranking configuration (extracted from job descriptions).

```typescript
interface TechnologyRanks {
  technologies: {
    [techName: string]: {
      rank: "required" | "ok" | "strike" | "fail"
      points: number              // Strike points (0 for required/ok, 2+ for strike, N/A for fail)
      mentions: number            // How often seen in job descriptions (for reference)
    }
  }

  // Strike logic
  strikes: {
    missingAllRequired: number    // 1 point if no required tech found
    perBadTech: number           // 2 points per "strike" tech
    // "fail" tech = immediate hard rejection
  }

  // Metadata
  lastUpdated: Timestamp
  extractedFromJobs: number      // How many jobs were analyzed
  version: string
}
```

#### Technology Rank Meanings:

- **required**: Must have at least ONE of these (Python, TypeScript, JavaScript, React, Angular, Node.js, GCP, Kubernetes, Docker)
  - If NONE found → 1 strike point

- **ok**: Neutral technologies (C++, Go, Rust, etc.)
  - No effect on score

- **strike**: Technologies you'd prefer to avoid (Java, PHP, Ruby/Rails, WordPress, .NET, Perl)
  - 2 points per technology

- **fail**: Technologies that are immediate rejections
  - Hard reject (e.g., if we find any true deal-breakers)

### 3. Example Configuration

```json
{
  "job-filters": {
    "enabled": true,
    "strikeThreshold": 5,

    "hardRejections": {
      "excludedJobTypes": ["sales", "hr", "recruiter", "support", "customer success"],
      "excludedSeniority": ["associate", "junior", "intern", "entry-level", "entry level", "co-op"],
      "excludedCompanies": [],
      "excludedKeywords": ["clearance required", "security clearance", "relocation required", "must relocate"],
      "minSalaryFloor": 100000,
      "rejectCommissionOnly": true
    },

    "remotePolicy": {
      "allowRemote": true,
      "allowHybridPortland": true,
      "allowOnsite": false
    },

    "salaryStrike": {
      "enabled": true,
      "threshold": 150000,
      "points": 2
    },

    "experienceStrike": {
      "enabled": true,
      "minPreferred": 6,
      "points": 1
    },

    "seniorityStrikes": {
      "mid-level": 2,
      "mid level": 2,
      "principal": 1,
      "director": 1,
      "manager": 1,
      "engineering manager": 1
    },

    "qualityStrikes": {
      "minDescriptionLength": 200,
      "shortDescriptionPoints": 1,
      "buzzwords": ["rockstar", "ninja", "guru", "10x engineer", "code wizard"],
      "buzzwordPoints": 1
    },

    "lastUpdated": "2025-10-16T19:00:00Z",
    "version": "2.0-strike-system"
  },

  "technology-ranks": {
    "technologies": {
      "Python": { "rank": "required", "points": 0, "mentions": 45 },
      "TypeScript": { "rank": "required", "points": 0, "mentions": 38 },
      "JavaScript": { "rank": "required", "points": 0, "mentions": 52 },
      "React": { "rank": "required", "points": 0, "mentions": 41 },
      "Angular": { "rank": "required", "points": 0, "mentions": 15 },
      "Node.js": { "rank": "required", "points": 0, "mentions": 33 },
      "GCP": { "rank": "required", "points": 0, "mentions": 12 },
      "Kubernetes": { "rank": "required", "points": 0, "mentions": 28 },
      "Docker": { "rank": "required", "points": 0, "mentions": 31 },

      "C++": { "rank": "ok", "points": 0, "mentions": 8 },
      "Go": { "rank": "ok", "points": 0, "mentions": 14 },
      "Rust": { "rank": "ok", "points": 0, "mentions": 6 },
      "PostgreSQL": { "rank": "ok", "points": 0, "mentions": 22 },
      "Redis": { "rank": "ok", "points": 0, "mentions": 18 },

      "Java": { "rank": "strike", "points": 2, "mentions": 29 },
      "PHP": { "rank": "strike", "points": 2, "mentions": 11 },
      "Ruby": { "rank": "strike", "points": 2, "mentions": 9 },
      "Rails": { "rank": "strike", "points": 2, "mentions": 8 },
      "Ruby on Rails": { "rank": "strike", "points": 2, "mentions": 7 },
      "WordPress": { "rank": "strike", "points": 2, "mentions": 5 },
      ".NET": { "rank": "strike", "points": 2, "mentions": 12 },
      "C#": { "rank": "strike", "points": 2, "mentions": 10 },
      "Perl": { "rank": "strike", "points": 2, "mentions": 2 }
    },

    "strikes": {
      "missingAllRequired": 1,
      "perBadTech": 2
    },

    "lastUpdated": "2025-10-16T19:00:00Z",
    "extractedFromJobs": 78,
    "version": "1.0"
  }
}
```

## Usage Flow

1. **Extract Technologies**: Run `scripts/extract_technologies.py` to scan existing jobs
2. **Review & Adjust**: Manually adjust technology ranks in Firestore
3. **Configure Filters**: Set strike thresholds and hard rejection rules
4. **Test**: Process a few jobs and review strike accumulation
5. **Tune**: Adjust strike points and threshold based on results

## Strike Examples

### Example 1: Pass (2 points)
- **Tech**: Python, React, GCP → 0 required tech found
- **Salary**: $140k → 2 points (< $150k)
- **Seniority**: Senior → 0 points
- **Total**: 2 points → **PASSES** (< 5)

### Example 2: Fail (6 points)
- **Tech**: Java, PHP → 4 points (2 bad tech × 2 points)
- **Salary**: $130k → 2 points (< $150k)
- **Experience**: 4 years → 0 points (>= 3)
- **Total**: 6 points → **FILTERED** (>= 5)

### Example 3: Border (4 points)
- **Tech**: TypeScript, Ruby on Rails → 2 points (1 bad tech)
- **Salary**: $145k → 2 points (< $150k)
- **Seniority**: Mid-level → 2 points
- **Total**: 6 points → **FILTERED** (>= 5)

### Example 4: Excellent (0 points)
- **Tech**: Python, TypeScript, React, GCP → 0 points (all good)
- **Salary**: $180k → 0 points (>= $150k)
- **Experience**: 8 years → 0 points (>= 6)
- **Seniority**: Staff → 0 points
- **Total**: 0 points → **PASSES** (< 5)
