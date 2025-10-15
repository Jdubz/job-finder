# Docker Deployment Guide

## Current Production Issue

**Problem**: Container logs are empty in Portainer
**Cause**: Container is running and waiting for the next cron schedule (every 6 hours at 00:00, 06:00, 12:00, 18:00)
**Solution**: Merge PR #8 and redeploy to get better logging and manual trigger capability

## Fix Steps

### 1. Merge and Deploy PR #8

PR #8 adds:
- **Entrypoint script** with detailed startup logging
- Shows next scheduled run time
- **Manual trigger script** for immediate execution
- Better debugging visibility

### 2. Redeploy in Portainer

**Option A: Update Existing Stack**

1. In Portainer, go to **Stacks → job-finder-prod**
2. Click **Editor**
3. Click **Pull and redeploy**
4. Wait for Watchtower to pull the new image (5 minutes max)
5. Check logs - you should now see:
   ```
   =========================================
   Job Finder Container Starting
   =========================================
   Current time: 2025-10-14 18:30:00
   Timezone: America/Los_Angeles
   Environment: production

   Cron schedule:
   0 */6 * * * root cd /app && /usr/local/bin/python scheduler.py >> /var/log/cron.log 2>&1

   Next scheduled run: 00:00

   ✓ Cron daemon started successfully

   Container is ready and waiting for scheduled runs.
   =========================================
   ```

**Option B: Manual Container Restart**

1. In Portainer, go to **Containers**
2. Find `job-finder-staging`
3. Click **Restart**
4. Check logs

### 3. Manually Trigger a Job Search (Testing)

Once the new image is deployed:

```bash
docker exec job-finder-staging /app/docker/run-now.sh
```

This will run immediately and show output in the logs.

## Production Deployment Checklist

### Before Deploying

- [ ] Merge PR #8 (company info + entrypoint fixes)
- [ ] Verify GitHub Actions built and pushed image
- [ ] Check image exists: `ghcr.io/jdubz/job-finder:latest`

### In Portainer

- [ ] Stack exists: `job-finder-prod`
- [ ] Environment variables set:
  - `ANTHROPIC_API_KEY` (REQUIRED)
  - `OPENAI_API_KEY` (optional)
  - `ENVIRONMENT=production`
  - `PROFILE_DATABASE_NAME=portfolio`
  - `STORAGE_DATABASE_NAME=portfolio`
- [ ] Volumes mounted:
  - `./credentials:/app/credentials:ro`
  - `./config:/app/config:ro`
  - `./logs:/app/logs`
  - `./data:/app/data`
- [ ] Credentials file exists: `credentials/serviceAccountKey.json`

### After Deploying

- [ ] Check container logs show startup messages
- [ ] Verify cron schedule is correct
- [ ] Test manual run: `docker exec job-finder-staging /app/docker/run-now.sh`
- [ ] Monitor logs for first scheduled run
- [ ] Check Firestore for saved job matches

## Cron Schedule

Current schedule: **Every 6 hours** at 00:00, 06:00, 12:00, 18:00

To change the schedule:

1. Edit `docker/crontab`
2. Examples:
   ```bash
   # Every 3 hours
   0 */3 * * * root cd /app && /usr/local/bin/python scheduler.py >> /var/log/cron.log 2>&1

   # Twice daily (9 AM and 6 PM)
   0 9,18 * * * root cd /app && /usr/local/bin/python scheduler.py >> /var/log/cron.log 2>&1

   # Daily at 6 AM
   0 6 * * * root cd /app && /usr/local/bin/python scheduler.py >> /var/log/cron.log 2>&1
   ```
3. Rebuild and push image
4. Watchtower will auto-update

## Debugging Commands

### Check Container Status
```bash
docker ps -a | grep job-finder
```

### View Logs
```bash
docker logs job-finder-staging -f
```

### Check Cron is Running
```bash
docker exec job-finder-staging ps aux | grep cron
```

### View Cron Schedule
```bash
docker exec job-finder-staging cat /etc/cron.d/job-finder-cron
```

### Manual Test Run
```bash
docker exec job-finder-staging /app/docker/run-now.sh
```

### Check Environment Variables
```bash
docker exec job-finder-staging printenv | grep -E "ANTHROPIC|STORAGE|PROFILE|ENVIRONMENT"
```

### Restart Container
```bash
docker restart job-finder-staging
```

## Troubleshooting

### Container Logs are Empty

**Before PR #8**: This is expected - container is waiting for cron schedule
**After PR #8**: Should show detailed startup logs

### Cron Jobs Not Running

1. Check cron is running: `docker exec job-finder-staging ps aux | grep cron`
2. Check crontab: `docker exec job-finder-staging crontab -l`
3. Check cron log: `docker exec job-finder-staging cat /var/log/cron.log`

### Environment Variables Not Available

Cron doesn't inherit shell environment. Solution:
- Entrypoint saves env to `/etc/environment`
- Cron jobs can source it if needed

### Permission Errors

Check volume permissions:
```bash
# On bignasty.local
ls -la /path/to/stack/credentials
ls -la /path/to/stack/logs
```

Credentials should be readable, logs should be writable.

## Monitoring

### Watchtower Auto-Updates

Watchtower checks for new images every 5 minutes and auto-deploys:

```bash
# Check Watchtower logs
docker logs watchtower-job-finder-staging
```

### Health Checks

The container has a healthcheck that runs every 5 minutes:
```bash
docker inspect job-finder-staging | grep -A 10 Health
```

## Production vs Staging

### Staging Environment
- Container: `job-finder-staging`
- Stack: `job-finder-staging`
- Databases: `portfolio-staging`
- Used for testing before production

### Production Environment
- Container: `job-finder-prod`
- Stack: `job-finder-prod`
- Databases: `portfolio`
- Real job search results

## Next Steps After PR #8 Merge

1. **Merge PR #8** on GitHub
2. **Wait 2-5 minutes** for GitHub Actions to build and push
3. **Wait 5 more minutes** for Watchtower to pull and restart
4. **Check logs** in Portainer - should show startup messages
5. **Test manual run**: `docker exec job-finder-staging /app/docker/run-now.sh`
6. **Wait for next cron** or change schedule if needed

## Summary

The "empty logs" issue happens because:
1. Container runs cron in background
2. Cron only executes every 6 hours
3. Between runs, there's no output
4. `tail -f /var/log/cron.log` shows nothing because file is empty

**PR #8 fixes this by:**
1. Adding startup logs (shows container is alive)
2. Showing next scheduled run time
3. Adding manual trigger for testing
4. Making debugging much easier
