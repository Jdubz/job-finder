# Queue System Deployment Guide

## Prerequisites

1. **Firestore Index Deployed**
   ```bash
   firebase deploy --only firestore:indexes --project static-sites-257923
   ```

2. **Environment Variables Set** (in Portainer or `.env`)
   - `ANTHROPIC_API_KEY`
   - `GOOGLE_APPLICATION_CREDENTIALS`

3. **Firebase Credentials** mounted at `/app/credentials/serviceAccountKey.json`

## Deployment Steps

### 1. Build and Push Docker Image

```bash
# Build the image
docker build -t ghcr.io/jdubz/job-finder:latest .

# Push to registry
docker push ghcr.io/jdubz/job-finder:latest
```

### 2. Deploy with Docker Compose

```bash
# Pull latest image
docker-compose pull

# Start services
docker-compose up -d

# View logs
docker-compose logs -f job-finder
```

### 3. Verify Queue Worker is Running

Check the logs for these startup messages:

```
========================================
Starting Queue Worker Daemon
========================================
Queue worker will process jobs from Firestore queue

✓ Queue worker started successfully (PID: XXXX)

Container is running in DUAL-PROCESS mode:
  1. Cron (every 6h) - Scrapes sources and adds to queue
  2. Queue Worker (continuous) - Processes queue items
========================================
```

### 4. Monitor Queue Processing

```bash
# View queue worker logs
docker exec job-finder-staging tail -f /app/logs/queue_worker.log

# View cron logs
docker exec job-finder-staging tail -f /var/log/cron.log

# Check queue stats
docker exec job-finder-staging python -c "
from job_finder.queue.manager import QueueManager
manager = QueueManager(database_name='portfolio-staging')
print(manager.get_queue_stats())
"
```

## How It Works

### Dual-Process Mode

When `ENABLE_QUEUE_MODE=true`, the container runs **two processes**:

1. **Cron Job** (every 6 hours)
   - Runs `search_orchestrator_queue.py`
   - Scrapes job sources
   - Adds jobs to Firestore queue
   - Does NOT process jobs

2. **Queue Worker** (continuous daemon)
   - Runs `queue_worker.py`
   - Polls queue every 60 seconds
   - Processes up to 10 items per batch
   - Fetches company info
   - Runs AI matching
   - Saves matches to Firestore

### Process Flow

```
Time 00:00 (Cron runs)
  └─> Scraper finds 50 jobs
  └─> Adds 50 items to job-queue
  └─> Exits

Time 00:00:10 (Queue worker polls)
  └─> Finds 50 pending items
  └─> Processes 10 items (batch limit)
  └─> 40 remain pending

Time 00:01:10 (Queue worker polls)
  └─> Finds 40 pending items
  └─> Processes 10 items
  └─> 30 remain pending

... continues until queue is empty
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENABLE_QUEUE_MODE` | Enable queue worker | `false` | No |
| `ANTHROPIC_API_KEY` | Claude API key | - | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Firebase credentials path | - | Yes |
| `PROFILE_DATABASE_NAME` | Profile database | `portfolio-staging` | No |
| `STORAGE_DATABASE_NAME` | Storage database | `portfolio-staging` | No |
| `TZ` | Container timezone | `America/Los_Angeles` | No |

### Queue Settings (Optional)

Create `job-finder-config/queue-settings` in Firestore:

```json
{
  "maxRetries": 3,
  "retryDelaySeconds": 60,
  "processingTimeout": 300
}
```

### Stop List (Optional)

Create `job-finder-config/stop-list` in Firestore:

```json
{
  "excludedCompanies": ["Company A", "Company B"],
  "excludedKeywords": ["commission only", "unpaid"],
  "excludedDomains": ["spam.com"]
}
```

## Troubleshooting

### Queue Worker Not Starting

**Symptom**: No queue worker log file created

**Check**:
```bash
# Verify environment variable
docker exec job-finder-staging env | grep ENABLE_QUEUE_MODE

# Check entrypoint logs
docker logs job-finder-staging
```

**Fix**: Ensure `ENABLE_QUEUE_MODE=true` in docker-compose.yml or Portainer

### Jobs Not Being Processed

**Symptom**: Queue items stay in "pending" status

**Check**:
```bash
# Is worker running?
docker exec job-finder-staging ps aux | grep queue_worker

# Check for errors
docker exec job-finder-staging tail -50 /app/logs/queue_worker.log
```

**Common Issues**:
1. **Missing Firestore index** → Deploy indexes: `firebase deploy --only firestore:indexes`
2. **No API key** → Check `ANTHROPIC_API_KEY` is set
3. **Worker crashed** → Check logs for Python errors, restart container

### Items Failing with "Below Threshold"

**Symptom**: Jobs marked as "skipped" with "score below threshold"

**This is normal!** The AI matcher filters jobs below the minimum score (default 80).

To adjust:
1. Edit `config/config.yaml`: `ai.min_match_score: 70`
2. Or create `job-finder-config/ai-settings` in Firestore

### High API Costs

**Symptom**: Unexpected AI API charges

**Solutions**:
1. **Enable Stop List** - Filter out unwanted jobs before AI
2. **Reduce Sources** - Scrape fewer job boards
3. **Increase Score Threshold** - Only process high-quality matches
4. **Set Daily Budget** - Create `ai-settings` with `costBudgetDaily`

## Maintenance

### Update Stop List

```bash
# Add company to exclusion list
firebase firestore:set job-finder-config/stop-list \
  --project static-sites-257923 \
  --database portfolio-staging \
  --merge \
  '{"excludedCompanies": ["BadCorp", "ScamInc"]}'
```

### Clean Old Queue Items

```python
from job_finder.queue.manager import QueueManager

manager = QueueManager(database_name="portfolio-staging")

# Delete completed items older than 7 days
deleted = manager.clean_old_completed(days_old=7)
print(f"Cleaned up {deleted} old items")
```

### Reset Stuck Items

If items are stuck in "processing" (worker crashed):

```python
from job_finder.queue.manager import QueueManager
from job_finder.queue.models import QueueStatus

manager = QueueManager(database_name="portfolio-staging")

# Manually query and update in Firestore Console
# Or use Firebase Admin SDK to reset status to "pending"
```

## Performance Tuning

### Batch Size

Edit `queue_worker.py`:
```python
# Process more items per batch (uses more API calls)
pending_items = queue_manager.get_pending_items(limit=20)  # Default: 10
```

### Poll Interval

Edit `queue_worker.py`:
```python
# Poll more/less frequently
time.sleep(30)  # Default: 60 seconds
```

### Resource Limits

Edit `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # More CPU for faster processing
      memory: 2G       # More memory for caching
```

## Monitoring

### Key Metrics to Track

1. **Queue Length** - `pending` count should not grow unbounded
2. **Success Rate** - `success / total` should be > 50%
3. **Failed Items** - Review and fix recurring failures
4. **Processing Time** - Should average < 15s per job

### Alerts to Set Up

1. **Queue Backlog** - Alert if pending > 100
2. **High Failure Rate** - Alert if failed > 20%
3. **Worker Down** - Alert if no processing for 10 minutes
4. **API Budget** - Alert at 80% of daily budget

## Rollback

If queue mode causes issues:

```yaml
# docker-compose.yml
environment:
  - ENABLE_QUEUE_MODE=false  # Disable queue worker
```

```bash
# Redeploy
docker-compose up -d

# System reverts to legacy direct processing mode
```

## Next Steps

1. ✅ Deploy Firestore indexes
2. ✅ Enable `ENABLE_QUEUE_MODE=true`
3. ✅ Deploy container
4. ✅ Monitor queue worker logs
5. ⏳ Configure stop list (optional)
6. ⏳ Set up monitoring/alerts
7. ⏳ Tune batch size and thresholds

## Support

- **Documentation**: See `QUEUE_SYSTEM_GUIDE.md`
- **Tests**: Run `pytest tests/queue/ -v`
- **E2E Test**: Run `python test_e2e_queue.py`
