# Google Cloud Logging Integration

This document explains how to use Google Cloud Logging to view application logs in the Google Cloud Console instead of shelling into containers.

## Overview

When enabled, all application logs are automatically sent to Google Cloud Logging, where you can:
- View logs in real-time from the Google Cloud Console
- Filter and search logs with powerful query syntax
- Set up log-based alerts and metrics
- Export logs to BigQuery, Cloud Storage, or Pub/Sub
- View logs across multiple containers in one place

## Setup

### 1. Enable Cloud Logging

Cloud Logging is enabled via an environment variable in your docker-compose configuration.

**In Portainer:**

1. Go to **Stacks** → Click your stack → **Editor**
2. Find the `ENABLE_CLOUD_LOGGING` environment variable
3. Set it to `true`:
   ```yaml
   environment:
     - ENABLE_CLOUD_LOGGING=true
   ```
4. Click **Update the stack**

**The same Firebase service account credentials used for Firestore are automatically used for Cloud Logging - no additional configuration needed!**

### 2. Verify Cloud Logging

After updating the stack, check the container logs in Portainer:

```
✅ Google Cloud Logging enabled - logs will appear in Google Cloud Console
   Project: your-project-id
   Log name: job-finder
```

If you see this message, Cloud Logging is working!

## Viewing Logs in Google Cloud Console

### Access Logs

1. Open Google Cloud Console: https://console.cloud.google.com/
2. Select your Firebase project
3. Go to **Logging** → **Logs Explorer** (left sidebar)

### Filter Logs

**View all job-finder logs:**
```
logName="projects/YOUR_PROJECT_ID/logs/job-finder"
```

**Filter by severity:**
```
logName="projects/YOUR_PROJECT_ID/logs/job-finder"
severity>=ERROR
```

**Filter by time range:**
- Use the time picker at the top to select a time range

**Search log content:**
```
logName="projects/YOUR_PROJECT_ID/logs/job-finder"
textPayload=~"Firestore"
```

### Common Queries

**View errors only:**
```
logName="projects/YOUR_PROJECT_ID/logs/job-finder"
severity>=ERROR
```

**View job scraping activity:**
```
logName="projects/YOUR_PROJECT_ID/logs/job-finder"
textPayload=~"Analyzing"
```

**View AI matching results:**
```
logName="projects/YOUR_PROJECT_ID/logs/job-finder"
textPayload=~"Matched! Score"
```

**View all logs from the last hour:**
```
logName="projects/YOUR_PROJECT_ID/logs/job-finder"
timestamp>="2024-01-01T12:00:00Z"
```

## Log Levels

Control log verbosity with the `LOG_LEVEL` environment variable:

```yaml
environment:
  - LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

**Log Levels:**
- **DEBUG**: Very detailed, useful for troubleshooting
- **INFO**: General informational messages (default)
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical errors only

## Advanced Features

### Log-Based Metrics

Create metrics from log entries:

1. In Logs Explorer, build your query
2. Click **Actions** → **Create metric**
3. Define metric details
4. Use metric in dashboards and alerts

### Log-Based Alerts

Set up alerts for specific log patterns:

1. In Logs Explorer, build your query for the condition you want to alert on
2. Click **Create alert**
3. Configure notification channels (email, Slack, etc.)

Example: Alert on errors
```
logName="projects/YOUR_PROJECT_ID/logs/job-finder"
severity>=ERROR
```

### Log Export

Export logs for long-term storage or analysis:

1. Go to **Logging** → **Log Router**
2. Click **Create Sink**
3. Choose destination:
   - **BigQuery**: For SQL analysis
   - **Cloud Storage**: For archival
   - **Pub/Sub**: For streaming to other systems

## Troubleshooting

### Logs Not Appearing in Cloud Console

**Check environment variable:**
```bash
docker exec job-finder-production env | grep ENABLE_CLOUD_LOGGING
# Should show: ENABLE_CLOUD_LOGGING=true
```

**Check container logs for initialization:**
```bash
docker logs job-finder-production | grep "Cloud Logging"
# Should show: "✅ Google Cloud Logging enabled"
```

**Verify credentials:**
```bash
docker exec job-finder-production env | grep GOOGLE_APPLICATION_CREDENTIALS
# Should show: GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/serviceAccountKey.json
```

**Check service account permissions:**

Your Firebase service account needs the **Logs Writer** role:
1. Go to **IAM & Admin** → **IAM**
2. Find your service account (ends with `@static-sites-257923.iam.gserviceaccount.com`)
3. Click **Edit**
4. Add role: **Logs Writer** (`roles/logging.logWriter`)
5. Click **Save**

### Cloud Logging Library Not Found

If you see this error:
```
⚠️  google-cloud-logging not installed
```

The Docker image needs to be rebuilt with the updated requirements.txt:
1. Push your code changes to GitHub
2. Wait for GitHub Actions to build the new image
3. Watchtower will auto-update your container (or restart manually)

### Performance Impact

Cloud Logging adds minimal overhead:
- Logs are sent asynchronously (non-blocking)
- Local file logging still works as backup
- Typical latency: < 100ms per log entry

To disable if needed:
```yaml
environment:
  - ENABLE_CLOUD_LOGGING=false
```

## Cost Considerations

**Free Tier (per month):**
- First 50 GB: Free
- After 50 GB: $0.50 per GB

**Typical Usage:**
- ~10,000 log entries per job search run
- ~1 MB per run
- Running hourly: ~720 MB/month (well within free tier)

**Best Practices:**
- Use appropriate log levels (avoid DEBUG in production)
- Set up log exclusion filters for noisy logs
- Configure log retention policies (default: 30 days)

## Benefits Over File Logs

**Why use Cloud Logging?**

✅ **No SSH required** - View logs from anywhere
✅ **Powerful search** - Filter, query, and analyze
✅ **Real-time** - See logs as they happen
✅ **Persistent** - Logs survive container restarts
✅ **Centralized** - Multiple containers in one place
✅ **Alerting** - Get notified of errors automatically
✅ **Integration** - Export to BigQuery, dashboards, etc.

**Local file logs still work!**
- Files in `/app/logs/` are still written
- View via Portainer console or SSH if needed
- Useful for quick debugging

## Example Workflow

**Daily monitoring workflow:**

1. Open Logs Explorer in the morning
2. Check for errors overnight:
   ```
   logName="projects/YOUR_PROJECT_ID/logs/job-finder"
   severity>=ERROR
   timestamp>="2024-01-15T00:00:00Z"
   ```
3. Review job matching statistics:
   ```
   logName="projects/YOUR_PROJECT_ID/logs/job-finder"
   textPayload=~"JOB SEARCH COMPLETE"
   ```
4. Investigate any issues by expanding log entries for full stack traces

**No SSH needed! Everything in the cloud console.**

## Documentation

- [Cloud Logging Overview](https://cloud.google.com/logging/docs)
- [Logs Explorer](https://cloud.google.com/logging/docs/view/logs-explorer-interface)
- [Query Language](https://cloud.google.com/logging/docs/view/logging-query-language)
- [Python Client Library](https://cloud.google.com/logging/docs/setup/python)

## Next Steps

After enabling Cloud Logging:

1. ✅ View logs in Google Cloud Console
2. ✅ Set up error alerts
3. ✅ Create dashboard with log-based metrics
4. ✅ Configure log retention policy
5. ✅ Set up log exports (optional)

---

**Questions? Check the logs!** 😄
