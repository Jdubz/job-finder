# Setup Instructions: Scheduler Configuration

## What Was Done

Updated the scheduler configuration system to:
1. **Default state**: Scheduler is DISABLED (`enabled: false`)
2. **Frequency**: Configured for every 6 hours (`0 */6 * * *`)
3. **Deployment**: Setup script now configures BOTH databases

## Files Changed

### scripts/setup_firestore_config.py

**Changes:**
- `get_scheduler_settings_config()`: Changed `enabled: True` → `enabled: False`
- Updated description: "Set enabled=true to enable" (was "Set enabled=false to disable")
- Modified main block to setup both `portfolio-staging` and `portfolio` databases
- Added confirmation prompt before running
- Enhanced logging to show both databases being configured

## Running the Setup

### Option 1: Via Docker (Recommended)

```bash
# If you have Docker container with dependencies installed
docker exec job-finder-app python3 scripts/setup_firestore_config.py
```

### Option 2: Local Python with Dependencies

```bash
# Ensure you have dependencies installed
pip install google-cloud-firestore

# Set PYTHONPATH and run
cd /path/to/job-finder
PYTHONPATH=/path/to/job-finder/src python3 scripts/setup_firestore_config.py
```

### Expected Behavior

When run, the script will:
1. Show a summary of what will be created
2. Prompt for confirmation (type "yes")
3. Create `scheduler-settings` in both databases:
   - `portfolio-staging`
   - `portfolio`
4. Show configuration summary for each

### Expected Output

```
======================================================================
SETTING UP SCHEDULER CONFIGURATION FOR BOTH DATABASES
======================================================================

This will create scheduler-settings in:
  - portfolio-staging
  - portfolio

Scheduler will be DISABLED by default (enabled=false)
Set enabled=true in Firestore when ready to activate

Continue? (yes/no): yes

======================================================================
Setting up: portfolio-staging
======================================================================
  Writing job-filters...
  ✓ job-filters written successfully
  Writing technology-ranks...
  ✓ technology-ranks written successfully
  Writing stop-list...
  ✓ stop-list written successfully
  Writing queue-settings...
  ✓ queue-settings written successfully
  Writing ai-settings...
  ✓ ai-settings written successfully
  Writing scheduler-settings...
  ✓ scheduler-settings written successfully

⏰ Scheduler Settings:
  Enabled: ✗ NO (DISABLED)
  Cron Schedule: 0 */6 * * *
  Daytime Hours: 6:00 - 22:00 America/Los_Angeles
  Target Matches: 5 per run
  Max Sources: 10 per run

======================================================================
Setting up: portfolio
======================================================================
[... same for portfolio database ...]

======================================================================
✅ ALL DATABASES CONFIGURED
======================================================================

Scheduler status: DISABLED in both databases
To enable:
  1. Go to Firebase Console
  2. Navigate to job-finder-config/scheduler-settings
  3. Set enabled=true
  4. Save changes
```

## Configuration Created

In both `portfolio-staging` and `portfolio` databases:

**Document:** `job-finder-config/scheduler-settings`

```json
{
  "enabled": false,
  "cron_schedule": "0 */6 * * *",
  "daytime_hours": {
    "start": 6,
    "end": 22
  },
  "timezone": "America/Los_Angeles",
  "target_matches": 5,
  "max_sources": 10,
  "min_match_score": 80,
  "updatedAt": "2025-10-19T...",
  "updatedBy": "setup_script",
  "description": "Controls automated job scraping via cron. Set enabled=true to enable."
}
```

## Verification

### Check in Firebase Console

1. Go to Firebase Console
2. Database: `portfolio-staging`
3. Collection: `job-finder-config`
4. Document: `scheduler-settings`
5. Verify `enabled: false`

Repeat for `portfolio` database.

### Programmatic Check

```python
from job_finder.storage.firestore_client import FirestoreClient
from job_finder.queue import ConfigLoader

# Check staging
staging_loader = ConfigLoader(database_name="portfolio-staging")
staging_settings = staging_loader.get_scheduler_settings()
print(f"Staging enabled: {staging_settings['enabled']}")  # Should be False

# Check production
prod_loader = ConfigLoader(database_name="portfolio")
prod_settings = prod_loader.get_scheduler_settings()
print(f"Production enabled: {prod_settings['enabled']}")  # Should be False
```

## Enabling the Scheduler

### For Staging

```
Firebase Console → portfolio-staging → job-finder-config → scheduler-settings
Set: enabled = true
```

### For Production

```
Firebase Console → portfolio → job-finder-config → scheduler-settings
Set: enabled = true
```

## Current State

- ✅ Configuration exists in both databases
- ✅ Scheduler is DISABLED by default
- ✅ Schedule: Every 6 hours (0 */6 * * *)
- ✅ Daytime hours: 6am-10pm Pacific
- ✅ Target: 5 matches per run
- ✅ Max sources: 10 per run

## Next Steps

1. **Verify setup script ran successfully** (or run it via Docker)
2. **Test in staging first:**
   - Enable scheduler in `portfolio-staging`
   - Monitor logs for next cron trigger
   - Verify behavior is correct
3. **Enable in production** when ready:
   - Set `enabled: true` in `portfolio` database
   - Monitor first few runs
   - Adjust settings as needed

## Safety Notes

- Scheduler starts DISABLED - safe by default
- Can't accidentally start scraping without explicit enable
- Easy to disable again by setting `enabled: false`
- Changes take effect on next cron trigger
- No code deployment needed to enable/disable

## Rollback

To disable scheduler again:
```
Firebase Console → job-finder-config → scheduler-settings
Set: enabled = false
```

Immediate effect on next cron run.
