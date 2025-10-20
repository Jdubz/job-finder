# Scheduler Configuration Implementation Summary

## Overview

Implemented a complete Firestore-based configuration system for controlling the automated job scraping cron scheduler. This allows enabling/disabling scraping and adjusting settings without code changes or redeployment.

## Implementation Date

October 19, 2025

## What Was Changed

### 1. ConfigLoader Enhancement (`src/job_finder/queue/config_loader.py`)

**Added:**
- `get_scheduler_settings()` method to load scheduler configuration from Firestore
- Returns `None` if configuration document doesn't exist (fail-safe behavior)
- No default fallback - scheduler must have explicit configuration

**Configuration Schema:**
```python
{
    "enabled": bool,                      # Enable/disable scheduler
    "cron_schedule": str,                 # Reference cron schedule
    "daytime_hours": {                    # Active hours window
        "start": int,                     # Hour (0-23)
        "end": int,                       # Hour (0-23)
    },
    "timezone": str,                      # Timezone for daytime check
    "target_matches": int,                # Stop after N potential matches
    "max_sources": int,                   # Max job boards to scrape
    "min_match_score": int,               # Minimum AI score threshold
}
```

### 2. Scheduler Settings Generator (`scripts/setup_firestore_config.py`)

**Added:**
- `get_scheduler_settings_config()` function to generate default configuration
- Updated `setup_firestore_config()` to include `scheduler-settings` document
- Enhanced summary output to show scheduler configuration

**Default Settings:**
```json
{
  "enabled": true,
  "cron_schedule": "0 */6 * * *",
  "daytime_hours": {"start": 6, "end": 22},
  "timezone": "America/Los_Angeles",
  "target_matches": 5,
  "max_sources": 10,
  "min_match_score": 80
}
```

### 3. Hourly Scheduler Updates (`scripts/workers/hourly_scheduler.py`)

**Modified:**
- `is_daytime_hours()` now accepts optional `scheduler_settings` parameter
  - Uses Firestore settings for timezone and hours if provided
  - Falls back to defaults if not provided
  
- `run_hourly_scrape()` function:
  - Loads scheduler settings from Firestore at startup
  - **Exits immediately if settings are None (not found)**
  - Checks if `enabled=true`, exits if disabled
  - Uses Firestore settings for all scraping parameters
  - Logs clear messages when disabled, missing, or outside hours

**Flow:**
1. Load scheduler settings from Firestore
2. Check if `enabled=true`, exit if disabled
3. Check daytime hours using Firestore timezone/hours
4. Use `target_matches`, `max_sources`, `min_match_score` from Firestore
5. Optional: Override AI matcher's min_match_score if specified

### 4. Documentation

Created comprehensive documentation:

**Main Documentation (`docs/SCHEDULER_CONFIG.md`):**
- Complete configuration schema
- Setup instructions
- Use cases and examples
- Troubleshooting guide
- Security considerations
- Best practices
- API/programmatic access examples

**Quick Reference (`docs/SCHEDULER_CONFIG_QUICKREF.md`):**
- Quick commands for common tasks
- Setting profiles (conservative, balanced, aggressive)
- Impact guide (cost vs volume)
- Testing workflow

**Updated (`docs/README.md`):**
- Added links to new scheduler documentation

## Features

### 1. Enable/Disable Scraping

**Instantly stop scraping** without touching cron or code:
```
Firestore: job-finder-config/scheduler-settings
Field: enabled = false
```

**Re-enable just as easily:**
```
Field: enabled = true
```

### 2. Configurable Daytime Hours

Control when scraping runs, respecting different timezones:
```json
{
  "daytime_hours": {"start": 8, "end": 20},
  "timezone": "America/New_York"
}
```

### 3. Adjustable Scraping Aggressiveness

Fine-tune how many jobs to find per run:
```json
{
  "target_matches": 10,      // More jobs per run
  "max_sources": 20,         // Check more job boards
  "min_match_score": 70      // Lower threshold
}
```

### 4. Real-time Configuration

Changes take effect on next cron trigger - no redeployment needed!

### 5. Environment-Specific Settings

Different configs for staging vs production databases:
- `portfolio-staging` - testing configuration
- `portfolio` - production configuration

## Log Messages

### Scheduler Enabled
```
⚙️  Loading scheduler settings from Firestore...
✓ Scheduler is enabled
  Target matches: 5
  Max sources: 10
  Min match score: 80
```

### Scheduler Disabled
```
🚫 Scheduler is DISABLED in Firestore config (scheduler-settings.enabled=false)
   To enable: Update job-finder-config/scheduler-settings in Firestore
```

### Outside Daytime Hours
```
⏸️  Outside daytime hours (6:00-22:00 America/Los_Angeles), skipping scrape
```

### Configuration Missing
```
❌ Scheduler settings not found in Firestore!
   The scheduler requires configuration to run.
   Please run: python scripts/setup_firestore_config.py
   Database: portfolio-staging
   Expected document: job-finder-config/scheduler-settings
```

## Usage Examples

### Disable Scraping for Maintenance

```python
from job_finder.storage.firestore_client import FirestoreClient

db = FirestoreClient.get_client("portfolio-staging")
doc_ref = db.collection("job-finder-config").document("scheduler-settings")
doc_ref.update({"enabled": False})
```

### Increase Aggressiveness During Active Job Search

```python
doc_ref.update({
    "target_matches": 15,
    "max_sources": 25,
    "min_match_score": 70
})
```

### Change Active Hours for Different Timezone

```python
doc_ref.update({
    "daytime_hours": {"start": 7, "end": 21},
    "timezone": "America/Chicago"
})
```

## Testing

### Manual Test

```bash
# Set STORAGE_DATABASE_NAME to test database
export STORAGE_DATABASE_NAME=portfolio-staging

# Run scheduler once
python scripts/workers/hourly_scheduler.py

# Check logs for scheduler settings load
```

### Verify Configuration Load

```python
from job_finder.queue import ConfigLoader

config_loader = ConfigLoader(database_name="portfolio-staging")
settings = config_loader.get_scheduler_settings()

print(f"Enabled: {settings['enabled']}")
print(f"Target matches: {settings['target_matches']}")
```

## Backward Compatibility

- **Breaking Change**: Scheduler now requires `scheduler-settings` document to exist
- If document doesn't exist, scheduler will log error and exit gracefully
- Deployments must run `setup_firestore_config.py` to initialize settings
- This is intentional - ensures explicit configuration rather than silent defaults

## Future Enhancements

Possible extensions:
1. **Per-source scheduling** - Different frequencies for different job boards
2. **Day-of-week controls** - Don't scrape on weekends
3. **Cost budget enforcement** - Auto-disable if daily budget exceeded
4. **Dynamic frequency** - Adjust based on match success rate
5. **Notification system** - Alert when disabled/errors occur
6. **Web UI** - Manage settings via job-finder-FE web app

## Related Systems

This integrates with:
- **Queue System** - Both use same ConfigLoader pattern
- **AI Settings** - Can override minMatchScore
- **Job Filters** - Pre-AI filtering still applies
- **Technology Ranks** - Strike system still enforced

## Migration Path

To enable this feature:

1. **Run setup script:**
   ```bash
   python scripts/setup_firestore_config.py
   ```

2. **Verify in Firestore:**
   Check that `job-finder-config/scheduler-settings` exists

3. **Deploy updated code:**
   ```bash
   docker-compose up --build -d
   ```

4. **Monitor first run:**
   ```bash
   docker logs -f job-finder-app
   ```
   
   Look for "✓ Scheduler is enabled" message

## Files Changed

```
Modified:
  src/job_finder/queue/config_loader.py
  scripts/setup_firestore_config.py
  scripts/workers/hourly_scheduler.py
  docs/README.md

Created:
  docs/SCHEDULER_CONFIG.md
  docs/SCHEDULER_CONFIG_QUICKREF.md
  docs/SCHEDULER_CONFIG_IMPLEMENTATION.md (this file)
```

## Benefits

✅ **No redeployment** for most configuration changes  
✅ **Instant control** - pause/resume scraping immediately  
✅ **Cost management** - adjust aggressiveness based on budget  
✅ **Flexibility** - different settings for different environments  
✅ **Auditability** - track who changed what and when  
✅ **Safe testing** - test settings in staging before production  

## Limitations

- Cron schedule changes still require Docker rebuild
- Configuration changes apply on next cron trigger (not mid-run)
- Requires Firestore access (won't work if Firestore is down)

## Rollback Plan

If issues arise:

1. **Disable via Firestore:**
   Set `enabled=false` in scheduler-settings

2. **Revert code changes:**
   ```bash
   git revert <commit-hash>
   docker-compose up --build -d
   ```

3. **Use defaults:**
   Delete `scheduler-settings` document - scheduler will use hardcoded defaults

## Support

See documentation:
- [docs/SCHEDULER_CONFIG.md](SCHEDULER_CONFIG.md) - Full guide
- [docs/SCHEDULER_CONFIG_QUICKREF.md](SCHEDULER_CONFIG_QUICKREF.md) - Quick reference

## Conclusion

This implementation provides powerful, flexible control over automated job scraping without sacrificing reliability or requiring constant redeployment. The Firestore-based configuration pattern can be extended to other parts of the system for consistent, centralized control.
