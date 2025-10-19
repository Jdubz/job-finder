# Scheduler Configuration - Upgrade Guide

## For Existing Deployments

This guide helps you add scheduler configuration to an existing job-finder deployment.

## Prerequisites

- Existing job-finder deployment running with cron scheduler
- Access to Firebase Console or Firestore API
- Access to deploy updated code

## Upgrade Steps

### Step 1: Pull Latest Code

```bash
cd /path/to/job-finder
git pull origin main  # or staging
```

### Step 2: Verify Files Changed

Check that these files were updated:

```bash
git log --oneline --name-only -5
```

Should include:
- `src/job_finder/queue/config_loader.py`
- `scripts/setup_firestore_config.py`
- `scripts/workers/hourly_scheduler.py`

### Step 3: Run Setup Script

This creates the `scheduler-settings` document in Firestore:

```bash
# For staging
export STORAGE_DATABASE_NAME=portfolio-staging
python3 scripts/setup_firestore_config.py

# For production
export STORAGE_DATABASE_NAME=portfolio
python3 scripts/setup_firestore_config.py
```

Expected output:
```
Setting up Firestore configuration in database: portfolio-staging
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

======================================================================
CONFIGURATION SUMMARY
======================================================================

⏰ Scheduler Settings:
  Enabled: ✓ YES
  Cron Schedule: 0 */6 * * *
  Daytime Hours: 6:00 - 22:00 America/Los_Angeles
  Target Matches: 5 per run
  Max Sources: 10 per run
```

### Step 4: Verify in Firestore

1. Open Firebase Console
2. Navigate to Firestore Database
3. Go to `job-finder-config` collection
4. Verify `scheduler-settings` document exists

Should contain:
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
  "updatedAt": "2025-10-19T...",
  "updatedBy": "setup_script",
  "description": "Controls automated job scraping via cron. Set enabled=false to disable."
}
```

### Step 5: Deploy Updated Code

**For Docker deployments:**

```bash
# Stop current container
docker-compose down

# Rebuild with new code
docker-compose build

# Start with updated code
docker-compose up -d

# Verify deployment
docker logs -f job-finder-app
```

**For direct Python deployments:**

```bash
# Pull latest requirements (if any changed)
pip install -r requirements.txt

# Restart scheduler service
sudo systemctl restart job-finder-scheduler
```

### Step 6: Verify Scheduler Loads Config

Wait for next cron trigger or run manually:

```bash
# Manual test
python3 scripts/workers/hourly_scheduler.py
```

Check logs for:
```
⚙️  Loading scheduler settings from Firestore...
✓ Scheduler is enabled
  Target matches: 5
  Max sources: 10
  Min match score: 80
```

If you see this, upgrade successful! ✅

## Rollback Procedure

If issues occur:

### Quick Rollback (Keep Code, Disable Feature)

```
Firestore → scheduler-settings → enabled = false
```

Scheduler will skip configuration loading and use defaults.

### Full Rollback (Revert Code)

```bash
# Revert to previous version
git revert <commit-hash>

# Rebuild and deploy
docker-compose up --build -d
```

## Migration Checklist

- [ ] Pulled latest code
- [ ] Verified changed files
- [ ] Ran setup script for staging
- [ ] Verified Firestore document in staging
- [ ] Deployed to staging
- [ ] Tested staging scheduler (wait for cron or run manually)
- [ ] Verified staging logs show config loading
- [ ] Ran setup script for production
- [ ] Verified Firestore document in production
- [ ] Deployed to production
- [ ] Verified production logs
- [ ] Updated documentation/runbooks if needed

## Testing Recommendations

### Test 1: Disable Scheduler

1. Set `enabled = false` in Firestore
2. Wait for next cron trigger
3. Check logs for: `🚫 Scheduler is DISABLED`
4. Verify no scraping occurred
5. Set `enabled = true`
6. Verify scraping resumes

### Test 2: Change Target Matches

1. Set `target_matches = 3` in Firestore
2. Run scheduler manually or wait for cron
3. Check logs: `Target matches: 3`
4. Verify scraping stops after finding 3 matches

### Test 3: Adjust Daytime Hours

1. Set `daytime_hours = {start: 23, end: 1}` (unrealistic window)
2. Trigger scheduler during day
3. Should see: `⏸️  Outside daytime hours`
4. Reset to normal hours

## Configuration Customization

After upgrade, customize settings for your needs:

### High-Volume Job Search

```json
{
  "enabled": true,
  "target_matches": 10,
  "max_sources": 20,
  "min_match_score": 70
}
```

### Cost-Conscious Search

```json
{
  "enabled": true,
  "target_matches": 3,
  "max_sources": 5,
  "min_match_score": 85
}
```

### Different Timezone

```json
{
  "daytime_hours": {"start": 8, "end": 20},
  "timezone": "America/New_York"
}
```

## Troubleshooting

### Issue: Scheduler not loading settings

**Symptoms:**
- Logs don't show "Loading scheduler settings"
- Old behavior continues

**Check:**
1. Database name is correct: `STORAGE_DATABASE_NAME` env var
2. Firestore document exists: `job-finder-config/scheduler-settings`
3. Service account has read permissions
4. Code was actually deployed (check file timestamps)

**Fix:**
```bash
# Verify code is latest
git log -1 --oneline

# Check Docker container has new code
docker exec job-finder-app cat scripts/workers/hourly_scheduler.py | grep "get_scheduler_settings"

# Rebuild if needed
docker-compose up --build -d
```

### Issue: Settings changes not taking effect

**Symptoms:**
- Changed settings in Firestore
- Scheduler still uses old values

**Remember:**
- Changes apply on **next cron trigger**
- Not mid-run - wait for current run to finish
- Cache may need clear (restart helps)

**Fix:**
```bash
# Trigger manually to test immediately
docker exec job-finder-app python3 scripts/workers/hourly_scheduler.py

# Or restart container to clear any cache
docker-compose restart
```

### Issue: Setup script fails

**Error:** `ModuleNotFoundError: No module named 'job_finder'`

**Fix:**
```bash
# Set PYTHONPATH
export PYTHONPATH=/path/to/job-finder/src

# Or use Docker
docker exec job-finder-app python3 scripts/setup_firestore_config.py
```

### Issue: Firestore permissions

**Error:** `Permission denied` or `403 Forbidden`

**Fix:**
- Verify service account key is valid
- Check Firestore security rules allow reads
- Ensure database name is correct

## Post-Upgrade Monitoring

For first 24-48 hours after upgrade:

### Monitor These Metrics

1. **Scheduler runs** - Are they happening on schedule?
2. **Config loading** - Do logs show settings load?
3. **Job matches** - Are results consistent with settings?
4. **Errors** - Any new errors in logs?
5. **Costs** - AI costs within expected range?

### Check Logs Daily

```bash
# View recent scheduler runs
docker logs --since 24h job-finder-app | grep -A 10 "HOURLY SCRAPE"

# Check for errors
docker logs --since 24h job-finder-app | grep -i error

# Verify config loads
docker logs --since 24h job-finder-app | grep "Scheduler is enabled"
```

## Support

If you encounter issues:

1. Check [SCHEDULER_CONFIG.md](SCHEDULER_CONFIG.md) troubleshooting section
2. Review logs for error messages
3. Try disabling (`enabled=false`) to verify rollback works
4. Check Firestore document structure matches schema

## Next Steps

After successful upgrade:

1. **Document your settings** - Note custom values for your environment
2. **Set up monitoring** - Alert if scheduler stops running
3. **Create runbook** - Document how to disable/enable for your team
4. **Test in staging first** - Before changing production settings

## Summary

✅ **Backward Compatible** - Old deployments work without upgrade  
✅ **Safe to Deploy** - Can disable instantly if issues arise  
✅ **Easy Rollback** - Multiple rollback options available  
✅ **Gradual Adoption** - Test in staging before production

---

**Upgrade Time:** ~15 minutes  
**Downtime Required:** None (rolling update)  
**Risk Level:** Low (can disable immediately)
