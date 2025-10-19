# Scheduler Configuration Behavior Update

## Change Summary

**Date:** October 19, 2025

The scheduler configuration system has been updated to **require** explicit configuration in Firestore. The scheduler will no longer run with default/fallback values if the configuration is missing.

## What Changed

### Before
```python
# If scheduler-settings document missing:
# - Used hardcoded defaults
# - Scheduler would run anyway
# - Silent fallback behavior
```

### After
```python
# If scheduler-settings document missing:
# - Returns None from get_scheduler_settings()
# - Scheduler exits with clear error message
# - Requires explicit setup
```

## Why This Change?

**Fail-Safe Design Principle:**
- Explicit configuration is safer than silent defaults
- Prevents unexpected behavior in production
- Forces conscious decision about scheduler settings
- Makes misconfiguration obvious immediately

**Better Operational Control:**
- Clear indication when setup is incomplete
- Prevents scheduler from running without proper oversight
- Easier to debug configuration issues

## Error Messages

When configuration is missing, you'll see:

```
❌ Scheduler settings not found in Firestore!
   The scheduler requires configuration to run.
   Please run: python scripts/setup_firestore_config.py
   Database: portfolio-staging
   Expected document: job-finder-config/scheduler-settings
```

## Migration Required

### For New Deployments

**MUST** run setup script before scheduler will work:

```bash
python scripts/setup_firestore_config.py
```

### For Existing Deployments

If you already have `scheduler-settings` document:
- ✅ **No action needed** - continues working as before

If you don't have `scheduler-settings` document:
- ❌ **Action required** - run setup script
- Scheduler will not run until configured

## How to Check

### Verify Configuration Exists

**In Firebase Console:**
1. Go to Firestore Database
2. Navigate to `job-finder-config` collection
3. Look for `scheduler-settings` document
4. If missing, run setup script

**Programmatically:**
```python
from job_finder.queue import ConfigLoader

config_loader = ConfigLoader(database_name="portfolio-staging")
settings = config_loader.get_scheduler_settings()

if settings is None:
    print("❌ Configuration missing - run setup script")
else:
    print(f"✅ Configuration exists - enabled: {settings['enabled']}")
```

## Setup Process

### Step 1: Run Setup Script

```bash
# For staging
export STORAGE_DATABASE_NAME=portfolio-staging
python scripts/setup_firestore_config.py

# For production
export STORAGE_DATABASE_NAME=portfolio
python scripts/setup_firestore_config.py
```

### Step 2: Verify Creation

Check Firebase Console for `job-finder-config/scheduler-settings`

Should contain:
```json
{
  "enabled": true,
  "cron_schedule": "0 */6 * * *",
  "daytime_hours": {"start": 6, "end": 22},
  "timezone": "America/Los_Angeles",
  "target_matches": 5,
  "max_sources": 10,
  "min_match_score": 80,
  "updatedAt": "2025-10-19T...",
  "updatedBy": "setup_script"
}
```

### Step 3: Test Scheduler

```bash
# Run manually to test
python scripts/workers/hourly_scheduler.py
```

Expected output:
```
⚙️  Loading scheduler settings from Firestore...
✓ Scheduler is enabled
  Target matches: 5
  Max sources: 10
  Min match score: 80
```

## Troubleshooting

### Issue: Scheduler not running after update

**Check:**
1. Does `scheduler-settings` document exist in Firestore?
2. Are you using the correct database name?
3. Did you run the setup script?

**Fix:**
```bash
python scripts/setup_firestore_config.py
```

### Issue: Error says configuration missing but it exists

**Check:**
1. Verify database name matches (staging vs production)
2. Check environment variable: `STORAGE_DATABASE_NAME`
3. Verify service account has read permissions

**Debug:**
```bash
# Check what database scheduler is using
docker logs job-finder-app | grep "Storage database"

# Should show:
# Storage database: portfolio-staging (or portfolio)
```

## Benefits of This Change

✅ **Explicit is better than implicit**
- No hidden defaults
- Clear setup requirements
- Obvious configuration state

✅ **Easier debugging**
- Missing config is immediately obvious
- Clear error messages with remediation steps
- No mysterious behavior

✅ **Safer operations**
- Can't accidentally run with wrong settings
- Forces review of configuration
- Prevents silent failures

✅ **Better documentation**
- Setup process is mandatory and documented
- Configuration requirements are clear
- Reduces support questions

## Rollback

If you need to revert this behavior:

### Option 1: Create Configuration (Recommended)
```bash
python scripts/setup_firestore_config.py
```

### Option 2: Code Rollback (If needed)
```bash
git revert <commit-hash>
docker-compose up --build -d
```

## Impact Assessment

### Low Risk
- Only affects deployments without configuration
- Existing configured deployments unaffected
- Clear error messages guide remediation

### Required Action
- New deployments: Run setup script
- Existing deployments: Verify config exists

### Timeline
- Immediate: Error messages appear if config missing
- Resolution: ~5 minutes to run setup script

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| Missing config | Uses defaults | Returns error |
| Behavior | Silent fallback | Explicit failure |
| Setup required | Optional | Mandatory |
| Error clarity | None | Clear message |
| Safety | Lower | Higher |

## Related Documentation

- [SCHEDULER_CONFIG.md](SCHEDULER_CONFIG.md) - Full configuration guide
- [SCHEDULER_CONFIG_UPGRADE.md](SCHEDULER_CONFIG_UPGRADE.md) - Migration guide
- [SCHEDULER_CONFIG_IMPLEMENTATION.md](SCHEDULER_CONFIG_IMPLEMENTATION.md) - Technical details

---

**TL;DR**: Scheduler now requires `scheduler-settings` document in Firestore. Run `python scripts/setup_firestore_config.py` to create it. This is safer and more explicit than using hidden defaults.
