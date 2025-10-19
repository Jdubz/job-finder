# Scheduler Configuration

The automated job scraping scheduler can be fully controlled via Firestore configuration, allowing you to enable/disable scraping and adjust settings without code changes or redeployment.

## Overview

The hourly scheduler (`scripts/workers/hourly_scheduler.py`) runs via cron and checks Firestore for configuration before executing. This allows dynamic control over:

- **Enable/Disable**: Turn automated scraping on/off instantly
- **Frequency**: Reference for cron schedule (actual schedule in crontab)
- **Daytime Hours**: Control when scraping actually runs
- **Scrape Settings**: Target matches, max sources, minimum match score

## Configuration Location

All scheduler settings are stored in Firestore:

```
Collection: job-finder-config
Document: scheduler-settings
```

## Configuration Schema

```typescript
{
  // Enable/disable the scheduler
  enabled: boolean,                    // true = scraping enabled, false = disabled
  
  // Cron schedule (for reference - actual cron is set in docker/crontab)
  // Examples:
  //   "0 */6 * * *"     = Every 6 hours
  //   "0 8,14,20 * * *" = At 8am, 2pm, 8pm
  //   "0 * * * *"       = Every hour
  cron_schedule: string,
  
  // Daytime hours when scraping should actually run (24-hour format)
  // Even if cron triggers, scraping only happens within these hours
  daytime_hours: {
    start: number,    // Hour (0-23), e.g., 6 for 6am
    end: number,      // Hour (0-23), e.g., 22 for 10pm
  },
  
  // Timezone for daytime hours check
  timezone: string,   // e.g., "America/Los_Angeles", "America/New_York"
  
  // Scrape settings
  target_matches: number,     // Stop after finding this many potential matches
  max_sources: number,        // Maximum sources to scrape per run
  min_match_score: number,    // Minimum AI match score (overrides AI settings)
  
  // Metadata
  updatedAt: string,          // ISO timestamp
  updatedBy: string,          // Who made the change
  description: string,        // Help text
}
```

## Default Configuration

```json
{
  "enabled": true,
  "cron_schedule": "0 */6 * * *",
  "daytime_hours": {
    "start": 6,
    "end": 22
  },
  "timezone": "America/Los_Angeles",
  "target_matches": 5,
  "max_sources": 10,
  "min_match_score": 80,
  "updatedAt": "2025-10-19T00:00:00Z",
  "updatedBy": "setup_script",
  "description": "Controls automated job scraping via cron. Set enabled=false to disable."
}
```

## Setup

### 1. Initialize Configuration

**IMPORTANT**: The scheduler requires the `scheduler-settings` document to exist in Firestore. Without it, the scheduler will not run.

Run the setup script to create the scheduler-settings document:

```bash
python scripts/setup_firestore_config.py
```

This will create all configuration documents including `scheduler-settings`.

### 2. Verify in Firebase Console

Navigate to:
```
Firebase Console → Firestore Database → job-finder-config → scheduler-settings
```

## Common Use Cases

### Disable Automated Scraping

To stop all automated scraping without touching cron or code:

1. Open Firestore Console
2. Navigate to `job-finder-config/scheduler-settings`
3. Set `enabled` to `false`
4. Click Save

The next cron trigger will see this and skip scraping with log message:
```
🚫 Scheduler is DISABLED in Firestore config (scheduler-settings.enabled=false)
   To enable: Update job-finder-config/scheduler-settings in Firestore
```

### Re-enable Scraping

Set `enabled` back to `true` in Firestore.

### Change Scraping Frequency

**Note**: The actual cron schedule is defined in `docker/crontab`. The `cron_schedule` field in Firestore is for reference only.

To change frequency:

1. Edit `docker/crontab`:
   ```cron
   # Every 4 hours
   0 */4 * * * root cd /app && /usr/local/bin/python scheduler.py >> /var/log/cron.log 2>&1
   ```

2. Update Firestore `scheduler-settings.cron_schedule` to match (for documentation)

3. Rebuild and redeploy:
   ```bash
   docker-compose up --build -d
   ```

### Adjust Daytime Hours

Change when scraping is allowed:

```json
{
  "daytime_hours": {
    "start": 8,   // 8am
    "end": 20     // 8pm
  },
  "timezone": "America/New_York"
}
```

Now scraping only happens 8am-8pm EST, even if cron triggers outside those hours.

### Change Scrape Aggressiveness

**More aggressive** (find more jobs per run):
```json
{
  "target_matches": 10,
  "max_sources": 20,
  "min_match_score": 70
}
```

**Less aggressive** (be more selective):
```json
{
  "target_matches": 3,
  "max_sources": 5,
  "min_match_score": 85
}
```

## Integration with Other Settings

The scheduler respects these related configurations:

### AI Settings (`job-finder-config/ai-settings`)
- Default `minMatchScore` (can be overridden by scheduler settings)
- AI provider and model selection
- Cost budget tracking

### Job Filters (`job-finder-config/job-filters`)
- Pre-AI filtering rules
- Remote policy, excluded companies, etc.

### Technology Ranks (`job-finder-config/technology-ranks`)
- Required and strike technologies
- Used in job filtering before AI analysis

## Monitoring

### Check Scheduler Status

**View logs**:
```bash
# Docker
docker logs -f job-finder-app

# Local
tail -f /var/log/job-finder-scheduler.log
```

**Look for these messages**:

✅ **Scheduler enabled and running**:
```
⚙️  Loading scheduler settings from Firestore...
✓ Scheduler is enabled
  Target matches: 5
  Max sources: 10
  Min match score: 80
```

🚫 **Scheduler disabled**:
```
🚫 Scheduler is DISABLED in Firestore config (scheduler-settings.enabled=false)
   To enable: Update job-finder-config/scheduler-settings in Firestore
```

⏸️ **Outside daytime hours**:
```
⏸️  Outside daytime hours (6:00-22:00 America/Los_Angeles), skipping scrape
```

❌ **Configuration missing** (scheduler will not run):
```
❌ Scheduler settings not found in Firestore!
   The scheduler requires configuration to run.
   Please run: python scripts/setup_firestore_config.py
   Database: portfolio-staging
   Expected document: job-finder-config/scheduler-settings
```

### Verify Configuration Load

The scheduler logs configuration when it starts:
```
✓ Scheduler is enabled
  Target matches: 5
  Max sources: 10
  Min match score: 80
```

If settings aren't loading correctly, check:
1. Firestore document exists: `job-finder-config/scheduler-settings`
2. Database name is correct (check `STORAGE_DATABASE_NAME` env var)
3. Service account has read permissions

## Troubleshooting

### Configuration Missing

**Problem**: Scheduler not running, logs show "Scheduler settings not found"

**Solution**: The configuration document is required and doesn't exist.

```bash
# Run setup script to create it
python scripts/setup_firestore_config.py

# Verify it was created
# Go to Firebase Console → job-finder-config → scheduler-settings
```

**Why this happens**:
- Fresh deployment without running setup script
- Accidentally deleted the document
- Using wrong database (staging vs production)

### Scheduler Not Respecting Changes

**Problem**: Changed Firestore config but scheduler still uses old values

**Solution**: The scheduler loads config fresh on each run. Check:
1. Correct database (staging vs production)
2. Config changes were saved in Firestore
3. Wait for next cron trigger (changes apply on next run)

### Scraping Not Running

**Check**:
1. `enabled` is `true` in Firestore
2. Current time is within `daytime_hours`
3. Cron is actually triggering (check cron logs)
4. Docker container is running

**View cron status**:
```bash
docker exec job-finder-app crontab -l
```

### Jobs Not Being Found

**Check**:
1. `target_matches` might be too low
2. `min_match_score` might be too high
3. Job sources might be exhausted or inactive
4. AI filtering might be too aggressive

**Temporarily adjust**:
```json
{
  "target_matches": 15,
  "max_sources": 30,
  "min_match_score": 70
}
```

## Security Considerations

### Firestore Security Rules

Ensure scheduler-settings has appropriate access:

```javascript
match /job-finder-config/{document=**} {
  // Allow reads for authenticated users and service accounts
  allow read: if request.auth != null;
  
  // Allow writes only for admins or service accounts
  allow write: if request.auth.token.admin == true;
}
```

### Production vs Staging

Use different databases:
- **Staging**: `portfolio-staging` (for testing config changes)
- **Production**: `portfolio` (stable configuration)

Set via environment variable:
```bash
export STORAGE_DATABASE_NAME=portfolio  # or portfolio-staging
```

## Best Practices

### 1. Test Config Changes in Staging

Before changing production settings:
1. Update `portfolio-staging` database
2. Trigger scheduler manually to test
3. Verify logs and results
4. Apply to production

### 2. Document Changes

Use the `updatedBy` field:
```json
{
  "enabled": false,
  "updatedAt": "2025-10-19T15:30:00Z",
  "updatedBy": "john@example.com - Disabling for maintenance"
}
```

### 3. Monitor After Changes

After changing settings:
1. Watch next 2-3 scheduler runs
2. Check job match counts
3. Verify no unexpected errors
4. Monitor AI costs (if changed thresholds)

### 4. Balance Aggressiveness vs Cost

More matches = more AI calls = higher cost:
- **High target_matches + low min_match_score** = $$$
- **Low target_matches + high min_match_score** = $

Find your balance based on:
- Daily cost budget
- Job search urgency
- Quality requirements

## API / Programmatic Access

### Load Settings in Code

```python
from job_finder.queue import ConfigLoader

config_loader = ConfigLoader(database_name="portfolio-staging")
scheduler_settings = config_loader.get_scheduler_settings()

if scheduler_settings["enabled"]:
    print(f"Scheduler active: {scheduler_settings['target_matches']} target matches")
```

### Update Settings Programmatically

```python
from job_finder.storage.firestore_client import FirestoreClient
from datetime import datetime

db = FirestoreClient.get_client("portfolio-staging")
doc_ref = db.collection("job-finder-config").document("scheduler-settings")

doc_ref.update({
    "enabled": False,
    "updatedAt": datetime.utcnow().isoformat(),
    "updatedBy": "automated_script"
})
```

## Related Documentation

- [Hourly Scraping System](hourly-scraping.md) - Overall scheduler architecture
- [Queue System](queue-system.md) - Queue-based job processing
- [Scrape Triggers](scrape-triggers.md) - On-demand scraping
- [Firestore Filter Config](firestore-filter-config-schema.md) - Job filtering rules

## Summary

The scheduler configuration system provides flexible, runtime control over automated job scraping:

✅ **Enable/disable** instantly via Firestore  
✅ **Adjust frequency** via cron schedule  
✅ **Control hours** when scraping runs  
✅ **Tune aggressiveness** with target matches and score thresholds  
✅ **No redeployment** needed for most changes  
✅ **Environment-specific** configs (staging vs production)

This makes it easy to:
- Pause scraping during maintenance
- Adjust based on job search urgency
- Control costs by limiting scrape volume
- Test different strategies in staging
- Respond to changing requirements without code changes
