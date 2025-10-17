# Hourly Job Scraping with Source Rotation

## Overview

The job finder now uses an intelligent hourly scraping strategy that:

1. **Runs every hour** during daytime hours (6am-10pm Pacific Time)
2. **Rotates through sources** by scraping the least-recently-scraped sources first
3. **Stops early** after finding 5 potential job matches or scraping all sources
4. **Tracks scraping history** in Firestore for each source

This approach provides:
- ✅ Consistent discovery of new jobs throughout the day
- ✅ Fair rotation ensuring all sources are eventually scraped
- ✅ Cost efficiency by stopping after finding enough matches
- ✅ Better job variety by not always scraping the same sources

## Architecture

### Hourly Scheduler

**File**: [scripts/workers/hourly_scheduler.py](../scripts/workers/hourly_scheduler.py)

The hourly scheduler is a standalone script designed to run via cron every hour. It:

1. **Checks daytime hours** (6am-10pm PT) - skips if outside this window
2. **Loads configuration** from Firestore and config.yaml
3. **Initializes AI matcher** with user profile
4. **Gets next sources** to scrape, ordered by `lastScrapedAt` (oldest first)
5. **Scrapes each source** until reaching 5 potential matches or exhausting sources
6. **Updates tracking** - records `lastScrapedAt`, jobs found, matches, and errors

### Source Rotation Logic

Sources are retrieved from the `job-sources` collection in Firestore and sorted by:

```python
def get_next_sources(sources_manager, limit=10):
    sources = sources_manager.get_active_sources()

    # Sort by lastScrapedAt (None = never scraped = highest priority)
    def sort_key(source):
        last_scraped = source.get("lastScrapedAt")
        if last_scraped is None:
            return datetime(1970, 1, 1, tzinfo=timezone.utc)  # Epoch = first
        return last_scraped

    return sorted(sources, key=sort_key)[:limit]
```

**Priority order:**
1. Sources never scraped (`lastScrapedAt = None`) - highest priority
2. Sources scraped longest ago - sorted oldest to newest
3. Recently scraped sources - lowest priority

### Early Exit Strategy

The scheduler tracks **potential matches** = jobs that pass filters and go to AI analysis.

```python
target_matches = 5
potential_matches = 0

for source in sources:
    if potential_matches >= target_matches:
        logger.info(f"Found {potential_matches} potential matches, stopping early")
        break

    source_stats = scrape_source(source, ...)
    potential_matches += source_stats["jobs_analyzed"]
```

**Why "potential" matches?**
- A potential match is any job that passes basic filters (remote, role fit) and is sent to AI
- Some potential matches may not meet the AI score threshold, but we count them anyway
- This ensures we give the AI enough jobs to analyze in each hourly run
- Typically finding 5 potential matches yields 2-3 actual saved matches

### Daytime Hours

Scraping only runs during **6am-10pm Pacific Time** (17 hours daily):

```python
def is_daytime_hours() -> bool:
    now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
    hour = now_pt.hour
    return 6 <= hour < 22  # 6am to 10pm
```

**Why these hours?**
- Most companies post jobs during business hours
- Reduces API costs by not scraping during quiet hours
- Aligns with when you're likely reviewing new matches

## Setup

### 1. Install Cron Job

Run the setup script to install the hourly cron job:

```bash
./scripts/setup_hourly_cron.sh
```

This creates a crontab entry that runs every hour:

```cron
0 * * * * cd /path/to/job-finder && source venv/bin/activate && python scripts/workers/hourly_scheduler.py
```

### 2. Manual Testing

Test the scheduler manually:

```bash
# Activate virtual environment
source venv/bin/activate

# Run scheduler once
python scripts/workers/hourly_scheduler.py

# Check logs
tail -f /var/log/job-finder-scheduler.log
```

### 3. Environment Variables

The scheduler respects these environment variables:

```bash
# Database configuration
export STORAGE_DATABASE_NAME=portfolio-staging  # or portfolio
export PROFILE_DATABASE_NAME=portfolio

# Logging
export SCHEDULER_LOG_FILE=/var/log/job-finder-scheduler.log

# Config file
export CONFIG_PATH=config/config.yaml
```

## Monitoring

### View Cron Jobs

```bash
# List all cron jobs
crontab -l

# Edit cron jobs
crontab -e
```

### View Logs

```bash
# Real-time logs
tail -f /var/log/job-finder-scheduler.log

# Last 100 lines
tail -n 100 /var/log/job-finder-scheduler.log

# Search for errors
grep ERROR /var/log/job-finder-scheduler.log
```

### Check Source Status

Use the Firestore console or query to check source scraping history:

```python
from job_finder.storage.job_sources_manager import JobSourcesManager

manager = JobSourcesManager(database_name="portfolio")
sources = manager.get_active_sources()

for source in sources:
    print(f"{source['name']}")
    print(f"  Last scraped: {source.get('lastScrapedAt')}")
    print(f"  Status: {source.get('lastScrapedStatus')}")
    print(f"  Jobs found: {source.get('totalJobsFound', 0)}")
    print(f"  Jobs matched: {source.get('totalJobsMatched', 0)}")
```

## Statistics

Each hourly run logs comprehensive statistics:

```
📊 STATISTICS:
  Sources scraped: 3
  Total jobs found: 47
  Remote jobs: 28
  Filtered by role: 12
  Duplicates skipped: 8
  Jobs analyzed (potential matches): 5
  Jobs matched: 2
  Jobs saved: 2
```

**Key metrics:**
- **Sources scraped**: How many sources were checked in this run
- **Jobs analyzed**: Potential matches sent to AI (target: 5)
- **Jobs matched**: Jobs that met AI score threshold
- **Jobs saved**: New matches stored in Firestore

## Troubleshooting

### Scheduler Not Running

1. **Check cron is running:**
   ```bash
   sudo systemctl status cron  # Linux
   ```

2. **Verify crontab entry:**
   ```bash
   crontab -l | grep hourly_scheduler
   ```

3. **Check script permissions:**
   ```bash
   ls -la scripts/workers/hourly_scheduler.py
   # Should be executable
   ```

### Outside Daytime Hours

If the scheduler runs but skips scraping:

```
⏸️  Outside daytime hours (6am-10pm PT), skipping scrape
```

This is expected behavior. The scheduler runs every hour but only scrapes during 6am-10pm Pacific.

### No Sources Found

If no sources are scraped:

1. **Check job-sources collection** has active sources:
   ```python
   manager = JobSourcesManager(database_name="portfolio")
   sources = manager.get_active_sources()
   print(f"Active sources: {len(sources)}")
   ```

2. **Verify source configuration** - ensure `enabled: true` and valid config

3. **Check logs** for source-specific errors

### Errors During Scraping

The scheduler continues running even if individual sources fail. Check logs for:

```
⚠️  Errors: 1
  - Error processing Netflix Greenhouse: [error details]
```

Common issues:
- **Network timeouts**: Temporary, usually resolves on next run
- **Invalid board_token**: Check source config in Firestore
- **Rate limiting**: Source may need cooldown period

## Comparison with Previous Approach

### Old Scheduler (scheduler.py)

- ✗ Scraped all sources every run
- ✗ No rotation or fairness
- ✗ No early exit (wasted API costs)
- ✗ No tracking of source history
- ✗ Fixed max_jobs limit across all sources

### New Hourly Scheduler (hourly_scheduler.py)

- ✅ Scrapes only oldest sources first (rotation)
- ✅ Fair distribution ensures all sources get scraped
- ✅ Stops after 5 potential matches (cost efficient)
- ✅ Tracks lastScrapedAt for each source
- ✅ Runs more frequently (hourly vs daily/manual)
- ✅ Better job discovery throughout the day

## Related Documentation

- [Job Sources Management](../FIRESTORE_INDEXES.md#job-sources-collection)
- [Queue System](./queue-system.md)
- [Deployment](./deployment.md)
