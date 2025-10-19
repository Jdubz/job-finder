# Scheduler Configuration - Deployment Summary

## What Was Changed

### Code Changes

1. **scripts/setup_firestore_config.py**
   - Changed default `enabled` from `True` to `False`
   - Updated to deploy to BOTH databases automatically
   - Added confirmation prompt
   - Enhanced logging

### Configuration State

**Both `portfolio-staging` AND `portfolio` databases will have:**

```json
{
  "enabled": false,           // ← DISABLED by default
  "cron_schedule": "0 */6 * * *",  // Every 6 hours
  "daytime_hours": {"start": 6, "end": 22},
  "timezone": "America/Los_Angeles",
  "target_matches": 5,
  "max_sources": 10,
  "min_match_score": 80
}
```

## Action Required

### Run Setup Script

The setup script needs to be executed to create the configuration in Firestore.

**Via Docker (if available):**
```bash
docker exec job-finder-app python3 scripts/setup_firestore_config.py
```

**Or manually in Firebase Console:**

Create document in both databases:
- Location: `job-finder-config/scheduler-settings`
- Copy the JSON configuration above

## Current Status

✅ Code updated and ready  
⏳ **Needs deployment**: Run setup script to create Firestore documents  
🔒 **Safe state**: Scheduler will be DISABLED by default  

## Enabling Later

When ready to activate automated scraping:

1. Firebase Console → `job-finder-config/scheduler-settings`
2. Set `enabled: true`
3. Save

Scheduler will start on next cron trigger.

## Safety Features

- Starts disabled - can't accidentally run
- Explicit enable required
- Can disable instantly by setting `enabled: false`
- No redeployment needed to enable/disable
- Changes apply on next cron run

## Files Modified

```
scripts/setup_firestore_config.py - Updated scheduler config creation
SETUP_SCHEDULER_INSTRUCTIONS.md   - Detailed setup instructions (NEW)
```

---

**Ready to deploy!** Run the setup script when dependencies are available.
