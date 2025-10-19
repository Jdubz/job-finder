# Scheduler Configuration - Quick Start

## What Is This?

A Firestore-based configuration system that lets you control the automated job scraping scheduler without touching code or redeploying.

## Quick Actions

### Stop Scraping Immediately

1. Open Firebase Console
2. Navigate to: `job-finder-config/scheduler-settings`
3. Set `enabled` to `false`
4. Save

✅ Done! Next cron trigger will skip scraping.

### Resume Scraping

Set `enabled` back to `true` in the same location.

### Adjust How Many Jobs to Find

Change `target_matches`:
- `3` = Conservative (fewer jobs)
- `5` = Default
- `10` = Aggressive (more jobs)

### Change Active Hours

Edit `daytime_hours`:
```json
{
  "start": 8,    // 8am
  "end": 20      // 8pm
}
```

## Where Are Settings?

**Firestore Location:**
```
Collection: job-finder-config
Document: scheduler-settings
```

**Fields:**
- `enabled` - Turn scheduler on/off
- `target_matches` - Jobs to find per run
- `max_sources` - Job boards to check
- `min_match_score` - AI match threshold
- `daytime_hours` - When to run
- `timezone` - Timezone for hours

## Documentation

📖 **Full Guide:** [SCHEDULER_CONFIG.md](SCHEDULER_CONFIG.md)  
⚡ **Quick Reference:** [SCHEDULER_CONFIG_QUICKREF.md](SCHEDULER_CONFIG_QUICKREF.md)  
🔧 **Implementation:** [SCHEDULER_CONFIG_IMPLEMENTATION.md](SCHEDULER_CONFIG_IMPLEMENTATION.md)  
📊 **Flow Diagrams:** [SCHEDULER_CONFIG_FLOW.md](SCHEDULER_CONFIG_FLOW.md)

## Setup

Run once to create the configuration:

```bash
python scripts/setup_firestore_config.py
```

This creates `scheduler-settings` with defaults:
- Enabled: `true`
- Schedule: Every 6 hours
- Hours: 6am-10pm Pacific
- Target: 5 matches per run
- Max sources: 10 per run

## Monitoring

Check if scheduler is active:

```bash
docker logs job-finder-app | grep "Scheduler is"
```

Expected when enabled:
```
✓ Scheduler is enabled
  Target matches: 5
  Max sources: 10
  Min match score: 80
```

When disabled:
```
🚫 Scheduler is DISABLED in Firestore config
```

## Common Scenarios

### 🚨 Emergency: Stop All Scraping

```
Firestore → scheduler-settings → enabled = false
```

### 💼 Active Job Search: More Jobs

```json
{
  "target_matches": 10,
  "max_sources": 20,
  "min_match_score": 70
}
```

### 💰 Save Costs: Be Selective

```json
{
  "target_matches": 3,
  "max_sources": 5,
  "min_match_score": 85
}
```

### 🛠️ Maintenance: Pause for 1 Day

```
Set enabled = false
(Remember to re-enable later!)
```

## Key Benefits

✅ No code changes needed  
✅ No redeployment required  
✅ Changes apply on next cron run  
✅ Different settings per environment  
✅ Easy to test in staging first

## Files Modified

```
src/job_finder/queue/config_loader.py          (Added get_scheduler_settings)
scripts/setup_firestore_config.py               (Added scheduler config)
scripts/workers/hourly_scheduler.py             (Uses Firestore settings)
```

## Related Settings

This works alongside:
- `ai-settings` - AI model and scoring
- `job-filters` - Pre-AI filtering rules
- `technology-ranks` - Tech stack preferences
- `queue-settings` - Queue processing

All in `job-finder-config` collection!

## Need Help?

1. Check [SCHEDULER_CONFIG.md](SCHEDULER_CONFIG.md) for detailed docs
2. View [SCHEDULER_CONFIG_FLOW.md](SCHEDULER_CONFIG_FLOW.md) for diagrams
3. See logs: `docker logs job-finder-app`

---

**Implemented:** October 19, 2025  
**Status:** ✅ Production Ready
