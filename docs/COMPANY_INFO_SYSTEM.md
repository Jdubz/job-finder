# Company Information Fetching System

This document explains how the company information fetching and caching system works in the job search pipeline.

## Overview

The system automatically fetches company information (about, culture, mission) from company websites and caches it in Firestore. This information is then included in AI job analysis to provide better context for matching.

## Components

### 1. CompanyInfoFetcher (`src/job_finder/company_info_fetcher.py`)

Fetches company information from websites using web scraping and AI extraction.

**Features:**
- Tries multiple URLs: `/about`, `/about-us`, `/company`, `/careers`, homepage
- Uses BeautifulSoup for HTML parsing
- Cleans content (removes scripts, styles, nav, footer, header)
- Extracts information using AI (Claude/GPT-4) for intelligent parsing
- Falls back to heuristics (pattern matching) if AI unavailable
- Handles errors gracefully

**AI Extraction:**
The AI extracts structured information:
- `about`: 2-3 sentence summary of what the company does
- `culture`: Company culture, values, or work environment
- `mission`: Company mission statement
- `size`: Company size/employees
- `industry`: Industry/sector
- `founded`: Year founded

**Heuristics Fallback:**
Looks for common patterns:
- "our mission", "mission statement"
- "our culture", "company culture"
- "about us", "who we are"

### 2. CompaniesManager (`src/job_finder/storage/companies_manager.py`)

Manages company data in Firestore with intelligent caching.

**Features:**
- Stores companies in `companies` collection
- Case-insensitive company lookup (uses `name_lower` field)
- Smart updates: only updates if new info is better (longer/more complete)
- `get_or_create_company()`: Intelligently decides when to fetch fresh data

**Caching Logic:**
```python
# Check if existing info is "good enough"
has_about = len(company.get('about', '')) > 100
has_culture = len(company.get('culture', '')) > 50

if has_about or has_culture:
    # Use cached - no need to re-fetch
    return cached_company
else:
    # Fetch fresh info
    fetch_from_website()
```

**Update Logic:**
Only updates cached data if new information is better:
```python
# Update if new value is longer/better
if new_value and len(new_value) > len(existing_value):
    should_update = True
```

### 3. Integration in Search Orchestrator

The system is integrated into the job search pipeline in `search_orchestrator.py`.

**Initialization:**
```python
# In _initialize_storage()
self.companies_manager = CompaniesManager(database_name=database_name)
self.company_info_fetcher = CompanyInfoFetcher(
    ai_provider=self.ai_matcher.provider  # Shares AI provider
)
```

**Processing Flow:**
```python
# In _process_listing() - after scraping jobs
1. Fetch/cache company info
2. Combine about/culture/mission fields
3. Update all jobs with company_info string
4. Continue with remote filtering and AI analysis
```

**Company Info in Jobs:**
```python
job = {
    'title': 'Senior Engineer',
    'company': 'Coinbase',
    'company_website': 'https://coinbase.com',
    'company_info': 'About: Coinbase is a...\n\nCulture: We value...\n\nMission: To...',
    # ... other fields
}
```

### 4. AI Prompt Integration

Company information is included in AI job analysis prompts (`src/job_finder/ai/prompts.py`).

**Job Analysis Prompt:**
```
**Title:** Senior Python Engineer
**Company:** Coinbase
**Location:** Remote
**Description:** ...

**Company Information:**
About: Coinbase is a cryptocurrency exchange platform...

Culture: We value transparency, innovation, and customer focus...

Mission: To create an open financial system for the world.
```

The AI uses this context to better assess cultural fit and company alignment.

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Search Orchestrator gets job listing                    │
│    (company_name, company_website)                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CompaniesManager.get_or_create_company()                 │
│    - Check Firestore cache                                  │
│    - Is cached info good enough?                            │
└─────────────────┬───────────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │ Cached & Good?    │
        ├─────────┬─────────┤
       YES       NO
        │         │
        │         ▼
        │  ┌────────────────────────────────────────────────┐
        │  │ 3. CompanyInfoFetcher.fetch_company_info()     │
        │  │    - Try /about, /about-us, etc.               │
        │  │    - Parse HTML with BeautifulSoup             │
        │  │    - Extract with AI or heuristics             │
        │  └────────┬───────────────────────────────────────┘
        │           │
        │           ▼
        │  ┌────────────────────────────────────────────────┐
        │  │ 4. Save/update company in Firestore            │
        │  └────────┬───────────────────────────────────────┘
        │           │
        └───────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Return company data (about, culture, mission)            │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Update all jobs with company_info string                 │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. AI analyzes jobs with company context                    │
│    - Better cultural fit assessment                         │
│    - More informed matching decisions                       │
└─────────────────────────────────────────────────────────────┘
```

## Benefits

### 1. Better AI Matching
The AI has context about company values, culture, and mission when analyzing job fit.

**Example:**
```
Job: "Senior Engineer" at "Anthropic"
Company Info: "Anthropic is an AI safety company building reliable,
interpretable, and steerable AI systems..."

→ AI can assess fit based on AI safety interest, research background, etc.
```

### 2. Efficient Caching
Companies are only fetched once, then cached in Firestore.

**Performance:**
- First fetch: 2-5 seconds (web scraping + AI)
- Subsequent fetches: <100ms (Firestore cache)
- Smart updates: Only re-fetch if cached data is sparse

### 3. Graceful Degradation
System continues working even if company info fetch fails.

**Fallback Behavior:**
```python
try:
    company_info = fetch_company_info()
except Exception:
    # Continue without company info
    job['company_info'] = ''
```

### 4. Multi-Source Support
Works for all job source types:
- ✅ Greenhouse scrapers (direct company scraping)
- ✅ RSS job boards (investigates company for each job)
- ✅ API sources
- ✅ Company page scrapers

## Example Output

### Successful Fetch
```
🏢 Fetching company info for Anthropic...
✓ Company info cached (523 chars)

Company info stored:
{
  "name": "Anthropic",
  "website": "https://anthropic.com",
  "about": "Anthropic is an AI safety company building reliable, interpretable, and steerable AI systems.",
  "culture": "We value scientific rigor, safety-first thinking, and collaborative research.",
  "mission": "To ensure AI systems are safe, beneficial, and aligned with human values.",
  "size": "100-500 employees",
  "industry": "AI Research",
  "founded": "2021"
}
```

### Cached Fetch (Subsequent)
```
🏢 Fetching company info for Anthropic...
✓ Using cached company info for Anthropic
✓ Company info cached (523 chars)
```

### Failed Fetch (Graceful)
```
🏢 Fetching company info for Unknown Startup...
⚠️  Failed to fetch company info: Connection timeout
(Continues without company info)
```

## Configuration

No configuration needed - the system works automatically!

**Optional customization:**
```python
# In search_orchestrator.py
company_info_fetcher = CompanyInfoFetcher(
    ai_provider=None  # Disable AI extraction, use heuristics only
)
```

## Database Schema

### Firestore `companies` Collection

```javascript
{
  "name": "Coinbase",                    // Company name
  "name_lower": "coinbase",              // For case-insensitive search
  "website": "https://coinbase.com",     // Company website
  "about": "Coinbase is a...",           // About/description
  "culture": "We value...",              // Culture/values
  "mission": "To create...",             // Mission statement
  "size": "1000-5000 employees",         // Company size
  "industry": "Cryptocurrency/Fintech",  // Industry/sector
  "founded": "2012",                     // Year founded
  "createdAt": Timestamp,                // When first cached
  "updatedAt": Timestamp                 // Last update
}
```

## Testing

The system was tested with:
- Coinbase Careers (Greenhouse scraper)
- Successfully cached company in Firestore
- Company info passed to AI analysis
- Graceful handling when website scraping fails

**Test Command:**
```bash
source .env && export GOOGLE_APPLICATION_CREDENTIALS && export ANTHROPIC_API_KEY && \
source venv/bin/activate && \
STORAGE_DATABASE_NAME=portfolio-staging python3 -m job_finder.main
```

## Future Enhancements

### 1. Manual Company Data Entry
Allow adding/editing company info manually for companies where web scraping fails.

### 2. Multiple Sources
Try multiple information sources:
- Crunchbase API
- LinkedIn Company Pages
- AngelList

### 3. Freshness Check
Re-fetch company info after a certain period (e.g., 30 days).

### 4. Company Scoring Enhancement
Use company info to boost/reduce company priority scores:
- Mission alignment → +10 points
- Culture fit → +5 points
- Values match → +5 points

## Files Modified

- `src/job_finder/company_info_fetcher.py` - **NEW**: Company info fetcher
- `src/job_finder/storage/companies_manager.py` - **NEW**: Firestore caching
- `src/job_finder/search_orchestrator.py` - Integrated fetcher/manager
- `src/job_finder/ai/prompts.py` - Added company info to AI prompts
- `src/job_finder/scrapers/greenhouse_scraper.py` - Already had `company_info` field

## Summary

The company information fetching system provides rich context for AI job matching by automatically scraping and caching company data. It works seamlessly across all job sources, handles errors gracefully, and significantly improves match quality by giving the AI insight into company culture, mission, and values.
