# Scheduler Configuration Quick Reference

Quick guide for enabling/disabling and configuring the automated job scraper.

## TL;DR

**Disable scraping immediately:**
1. Go to Firebase Console → Firestore → `job-finder-config/scheduler-settings`
2. Set `enabled` to `false`
3. Save

**Re-enable:** Set `enabled` back to `true`

## Common Tasks

### ✋ Stop All Automated Scraping

```
Location: job-finder-config/scheduler-settings
Field: enabled
Value: false
```

### ▶️ Resume Automated Scraping

```
Location: job-finder-config/scheduler-settings
Field: enabled
Value: true
```

### 🎯 Change Target Matches (How many jobs to find per run)

```
Field: target_matches
Default: 5
Low: 3        # More selective, fewer API calls
High: 10-15   # More aggressive, more API calls
```

### 📊 Change Max Sources (How many job boards to check)

```
Field: max_sources
Default: 10
Low: 5       # Faster, fewer sources
High: 20-30  # Slower, more comprehensive
```

### 🎚️ Change Match Score Threshold

```
Field: min_match_score
Default: 80
Stricter: 85-90   # Only excellent matches
Looser: 70-75     # More potential matches
```

### ⏰ Change Active Hours

```json
{
  "daytime_hours": {
    "start": 8,    // 8am
    "end": 20      // 8pm
  },
  "timezone": "America/Los_Angeles"
}
```

### 📅 Change Cron Frequency

**Note:** Requires Docker rebuild

1. Edit `docker/crontab`:
   ```cron
   0 */4 * * *  # Every 4 hours
   0 8,14,20 * * *  # 8am, 2pm, 8pm
   0 * * * *  # Every hour
   ```

2. Update Firestore `cron_schedule` field to match (for reference)

3. Rebuild:
   ```bash
   docker-compose up --build -d
   ```

## Setting Profiles

### 🐌 Conservative (Low cost, high quality)

```json
{
  "enabled": true,
  "target_matches": 3,
  "max_sources": 5,
  "min_match_score": 85,
  "daytime_hours": {
    "start": 9,
    "end": 18
  }
}
```

### ⚖️ Balanced (Default)

```json
{
  "enabled": true,
  "target_matches": 5,
  "max_sources": 10,
  "min_match_score": 80,
  "daytime_hours": {
    "start": 6,
    "end": 22
  }
}
```

### 🚀 Aggressive (High volume, more cost)

```json
{
  "enabled": true,
  "target_matches": 10,
  "max_sources": 20,
  "min_match_score": 70,
  "daytime_hours": {
    "start": 6,
    "end": 23
  }
}
```

### 💤 Paused (Disabled)

```json
{
  "enabled": false
}
```

## Quick Checks

### Is scraping enabled?

```
Firestore → job-finder-config/scheduler-settings → enabled
```

### When does it run?

```
Firestore → job-finder-config/scheduler-settings → daytime_hours
```

### What are current settings?

```bash
# View logs
docker logs job-finder-app | grep -A 5 "Scheduler is enabled"
```

Expected output:
```
✓ Scheduler is enabled
  Target matches: 5
  Max sources: 10
  Min match score: 80
```

### Why isn't scraping running?

Check logs for one of these:

```
🚫 Scheduler is DISABLED in Firestore config
⏸️  Outside daytime hours (6:00-22:00 America/Los_Angeles)
```

## Impact Guide

| Setting | Impact on... | Impact on... |
|---------|-------------|--------------|
| | **Job Volume** | **API Cost** |
| ↑ target_matches | More jobs | Higher cost |
| ↑ max_sources | More jobs | Higher cost |
| ↓ min_match_score | More jobs | Higher cost |
| ↑ daytime window | More runs | Higher cost |
| enabled=false | No jobs | No cost |

## Testing Changes

**Before production:**

1. Update `portfolio-staging` database
2. Run manually:
   ```bash
   python scripts/workers/hourly_scheduler.py
   ```
3. Check results
4. Apply to production (`portfolio` database)

## Access

### Firebase Console

```
https://console.firebase.google.com/project/static-sites-257923/firestore/databases/portfolio-staging/data/~2Fjob-finder-config~2Fscheduler-settings
```

### Update Programmatically

```python
from job_finder.storage.firestore_client import FirestoreClient

db = FirestoreClient.get_client("portfolio-staging")
doc_ref = db.collection("job-finder-config").document("scheduler-settings")

# Disable
doc_ref.update({"enabled": False})

# Change settings
doc_ref.update({
    "target_matches": 10,
    "max_sources": 20
})
```

## Full Documentation

See [SCHEDULER_CONFIG.md](SCHEDULER_CONFIG.md) for complete documentation.
