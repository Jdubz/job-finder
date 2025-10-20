# Scrape Triggers - Queue-Based On-Demand Scraping

## Overview

Job scraping is now a queue-based operation. Instead of running scrapers directly, you trigger scraping by creating SCRAPE queue items. The queue worker processes these items alongside job and company queue items.

**Key Benefits:**
- ✅ **Unified processing** - Single worker handles all operations
- ✅ **On-demand scraping** - Trigger custom scrapes anytime
- ✅ **Configurable** - Each scrape can have unique settings
- ✅ **Audit trail** - All scrapes logged in queue with results
- ✅ **No duplicate scrapes** - Prevents multiple pending scrapes
- ✅ **Works everywhere** - CLI, job-finder-FE UI (future), cron jobs

## Architecture

### SCRAPE Queue Items

SCRAPE is a new queue item type (alongside JOB and COMPANY):

```typescript
{
  type: "scrape",
  status: "pending" | "processing" | "success" | "failed",
  scrape_config: {
    target_matches: 5,        // Stop after N matches (null = unlimited, scrape all sources)
    max_sources: 20,          // Max sources to check (null = unlimited)
    source_ids: [...],        // Specific sources (null = all sources with rotation)
    min_match_score: 75       // Override AI threshold (null = use default)
  },
  source: "user_submission" | "automated_scan",
  result_message: "Scrape completed: 3 jobs saved, 5 sources scraped",
  scraped_data: { /* stats */ }
}
```

### How It Works

```
┌─────────────────┐
│  Hourly Cron    │  Runs every hour (6am-10pm PT)
│  (automated)    │  Creates SCRAPE queue items
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CLI Tool       │  User-triggered anytime
│  (manual)       │  Creates SCRAPE queue items
└────────┬────────┘
         │
         ▼
    ┌─────────────────────┐
    │   job-queue         │  Firestore collection
    │   ┌───────────────┐ │
    │   │ SCRAPE items  │ │  Pending scrape requests
    │   │ JOB items     │ │  Mixed with other queue items
    │   │ COMPANY items │ │
    │   └───────────────┘ │
    └──────────┬──────────┘
               │
               ▼
    ┌──────────────────────┐
    │   Queue Worker       │  Polls queue every 60s
    │   ┌────────────────┐ │
    │   │ Process SCRAPE │ │  → ScrapeRunner.run_scrape()
    │   │ Process JOB    │ │  → Analyze & save
    │   │ Process COMPANY│ │  → Fetch info
    │   └────────────────┘ │
    └──────────────────────┘
```

## Triggering Scrapes

### 1. Hourly Automated Scrapes

**Setup cron:**
```bash
./scripts/setup_hourly_cron.sh
```

This installs a cron job that runs every hour and:
- Checks if it's daytime (6am-10pm PT)
- Checks if a pending SCRAPE already exists
- Creates a new SCRAPE queue item with default settings

**Configuration** (`config/config.yaml`):
```yaml
scheduler:
  target_matches: 5      # Stop after 5 potential matches
  max_sources_per_run: 20  # Check up to 20 sources
```

### 2. Manual On-Demand Scrapes

**CLI Tool**: `scripts/trigger_scrape.py`

```bash
# Default scrape (5 matches, 20 sources max, rotation)
python scripts/trigger_scrape.py

# Find 10 potential matches
python scripts/trigger_scrape.py --target-matches 10

# Scrape ALL sources until exhausted (no limits)
python scripts/trigger_scrape.py --no-target-limit --no-source-limit

# Scrape specific sources only (all jobs from these sources)
python scripts/trigger_scrape.py --sources source-id-1 source-id-2 --no-target-limit

# Scrape up to 50 sources
python scripts/trigger_scrape.py --max-sources 50

# Override minimum match score
python scripts/trigger_scrape.py --min-score 70

# Production database
python scripts/trigger_scrape.py --database portfolio

# Force create even if pending scrape exists
python scripts/trigger_scrape.py --force
```

**Full options:**
```
--target-matches, -t    Stop after N potential matches (default: 5)
--no-target-limit       No limit - scrape all allowed sources
--max-sources, -m       Maximum sources to scrape (default: 20)
--no-source-limit       No limit - scrape all available sources
--sources, -s           Specific source IDs (space-separated, default: all with rotation)
--min-score            Override AI match threshold (0-100)
--database, -d          Database name (default: portfolio-staging)
--force, -f             Force trigger even if pending scrape exists
```

**Behavior Rules:**
- `source_ids` omitted → scrape all sources (with rotation, oldest first)
- `source_ids` specified → scrape only those specific sources
- `target_matches` omitted → default to 5
- `--no-target-limit` → scrape all allowed sources (no early exit)
- `max_sources` omitted → default to 20
- `--no-source-limit` → unlimited sources (until target_matches or all sources done)

### 3. From job-finder-FE UI (Future)

The job-finder-FE web app will have a "Run Custom Scrape" button that:
1. Shows form with scrape settings
2. Creates SCRAPE queue item in Firestore
3. Displays real-time status as queue worker processes it

## Configuration

### Scrape Settings

**In `config/config.yaml`:**
```yaml
scheduler:
  target_matches: 5          # Default potential matches goal
  max_sources_per_run: 20    # Default max sources per scrape

ai:
  min_match_score: 80        # Default AI threshold (can be overridden per-scrape)
```

### Source Rotation

Sources are scraped in priority order:
1. **Never scraped** (`lastScrapedAt = null`) - highest priority
2. **Oldest scraped** - sorted by `lastScrapedAt` ascending
3. **Recently scraped** - lowest priority

**Specific sources override rotation:**
```bash
# Only scrape Netflix and Google
python scripts/trigger_scrape.py --sources netflix-greenhouse google-greenhouse
```

### Early Exit Logic

The scraper tracks **potential matches** = jobs sent to AI for analysis.

- Scrapes sources one-by-one
- Counts jobs that pass basic filters (remote, role fit)
- Stops after reaching `target_matches` potential matches
- Saves only jobs that meet AI threshold

**Example:**
- `target_matches: 5` configured
- Source 1: 2 jobs analyzed, 1 saved
- Source 2: 3 jobs analyzed, 2 saved
- **Stops** (5 potential matches found)
- Total saved: 3 jobs

## Deduplication

**Only one pending SCRAPE allowed** in the queue at a time.

```bash
# First trigger succeeds
$ python scripts/trigger_scrape.py
✅ Scrape request added to queue!

# Second trigger blocked
$ python scripts/trigger_scrape.py
⚠️  WARNING: There is already a pending SCRAPE in the queue.
   Use --force to create another one anyway.

# Force override
$ python scripts/trigger_scrape.py --force
✅ Scrape request added to queue!
```

**Why?**
- Prevents queue flooding
- Ensures scrapers don't compete for same sources
- Cleaner logs and status tracking

## Monitoring

### View Queue Status

**Check for pending scrapes:**
```python
from job_finder.queue import QueueManager

manager = QueueManager(database_name="portfolio")
has_pending = manager.has_pending_scrape()
print(f"Pending scrape: {has_pending}")
```

**View queue stats:**
```python
stats = manager.get_queue_stats()
print(stats)
# {'pending': 3, 'processing': 1, 'success': 42, ...}
```

### View Scrape Results

**In Firestore Console:**
- Go to `job-queue` collection
- Filter by `type == "scrape"`
- Check `status`, `result_message`, `scraped_data`

**Scrape results include:**
```json
{
  "sources_scraped": 5,
  "total_jobs_found": 47,
  "remote_jobs": 28,
  "jobs_filtered_by_role": 12,
  "duplicates_skipped": 8,
  "jobs_analyzed": 5,
  "jobs_matched": 2,
  "jobs_saved": 2,
  "errors": []
}
```

### Logs

**Hourly cron logs:**
```bash
tail -f /var/log/job-finder-scheduler.log
```

**Queue worker logs:**
```bash
# Docker
docker logs -f job-finder-worker

# Local
tail -f logs/queue_worker.log
```

## Examples

### High-Volume Scrape

Find as many matches as possible:
```bash
python scripts/trigger_scrape.py \
  --target-matches 20 \
  --max-sources 50 \
  --min-score 70
```

### Specific Company Scrape

Only check specific companies:
```bash
python scripts/trigger_scrape.py \
  --sources netflix-greenhouse stripe-greenhouse airbnb-greenhouse \
  --target-matches 3
```

### Weekly Deep Scrape

Run a thorough weekly scrape (via cron):
```cron
# Every Sunday at 8am
0 8 * * 0 cd /path/to/job-finder && python scripts/trigger_scrape.py --target-matches 30 --max-sources 100
```

## Comparison: Before vs After

### Before (Direct Scraping)

```
Hourly Scheduler
    ↓
Directly runs scraping logic
    ↓
No way to trigger custom scrapes
```

**Limitations:**
- ❌ No on-demand scraping
- ❌ Can't customize per-scrape
- ❌ No audit trail
- ❌ Hard to test/debug

### After (Queue-Based)

```
Hourly Cron OR CLI Tool
    ↓
Creates SCRAPE queue item
    ↓
Queue Worker processes it
    ↓
Full audit trail in Firestore
```

**Benefits:**
- ✅ On-demand with custom settings
- ✅ Single worker handles everything
- ✅ Full audit trail
- ✅ Easy to monitor
- ✅ job-finder-FE UI integration ready

## Troubleshooting

### Scrape Not Starting

1. **Check queue for pending SCRAPE:**
   ```bash
   python scripts/trigger_scrape.py  # Will show if one exists
   ```

2. **Check queue worker is running:**
   ```bash
   docker ps | grep job-finder-worker
   ```

3. **View worker logs:**
   ```bash
   docker logs job-finder-worker
   ```

### No Jobs Found

1. **Check scrape results** in queue item's `scraped_data`
2. **Review source status** in `job-sources` collection
3. **Check `lastScrapedStatus` and `lastScrapedError`** for each source

### Too Many/Few Jobs

**Adjust settings:**
```bash
# More jobs
python scripts/trigger_scrape.py --target-matches 10 --max-sources 30

# Fewer jobs
python scripts/trigger_scrape.py --target-matches 3 --max-sources 10

# Lower threshold
python scripts/trigger_scrape.py --min-score 65
```

## Related Documentation

- [Queue System](./queue-system.md)
- [Job Sources Management](../FIRESTORE_INDEXES.md#job-sources-collection)
- [Hourly Scraping](./hourly-scraping.md)
