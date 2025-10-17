# Production Migration Complete

**Date:** 2025-10-16
**Status:** ✅ Complete

## Issue Resolved

The production job-finder scheduler was finding 0 sources to scrape because the `job-sources` collection didn't exist yet.

## What Was Done

### 1. Diagnosed the Problem
- Scheduled search ran but found 0 sources
- Created `scripts/database/check_job_sources.py` to diagnose
- Confirmed: `job-sources` collection was empty in production

### 2. Ran Migration
```bash
python scripts/migrate_listings_to_sources.py \
  --source-db portfolio \
  --target-db portfolio
```

### 3. Migration Results
- **Listings read:** 25
- **Companies created:** 19
- **Sources created:** 25
- **Errors:** 0

### 4. Current State

**Job Sources in Production (`portfolio` database):**
- **Total:** 25 sources
- **Enabled:** 15 sources
- **Disabled:** 10 sources

**Enabled Sources:**
1. We Work Remotely - Full Stack (RSS)
2. We Work Remotely - Programming (RSS)
3. Remotive - Software Development (RSS)
4. RemoteOK API
5. Coinbase Careers (Greenhouse)
6. Databricks Careers (Greenhouse)
7. Datadog Careers (Greenhouse)
8. Cloudflare Careers (Greenhouse)
9. Scale AI Careers (Greenhouse)
10. MongoDB Careers (Greenhouse)
11. Redis Careers (Greenhouse)
12. GitLab Careers (Greenhouse)
13. HashiCorp Careers (Greenhouse)
14. Twilio Careers (Greenhouse)
15. Netflix Careers (Company Page)

**Disabled Sources:**
- Deepgram, Brex, Shopify, Waymo, Stripe, Adzuna, Atlassian, PagerDuty, New Relic, Grammarly

## What Happens Next

### Scheduler Behavior
The scheduler runs every 6 hours (cron: `0 */6 * * *`):
- 00:00 (midnight)
- 06:00 (6 AM)
- 12:00 (noon)
- 18:00 (6 PM)

**Next scheduled run:** 18:00 (6 PM) today

### Expected Results
The next run should:
1. Load 15 enabled sources
2. Scrape jobs from each source
3. Add unique jobs to the queue
4. Queue worker will process them (AI matching, company info, etc.)
5. Matched jobs appear in Firestore `job-matches` collection

## Verification Commands

### Check Job Sources
```bash
source venv/bin/activate
export GOOGLE_APPLICATION_CREDENTIALS=.firebase/static-sites-257923-firebase-adminsdk.json
python scripts/database/check_job_sources.py
```

### Check Queue
```python
from job_finder.storage.firestore_client import FirestoreClient
from job_finder.queue.manager import QueueManager

db = FirestoreClient.get_client("portfolio")
queue_manager = QueueManager(database_name="portfolio")

# Check queue stats
stats = queue_manager.get_queue_stats()
print(f"Pending: {stats['pending']}")
print(f"Processing: {stats['processing']}")
print(f"Success: {stats['success']}")
```

### Check Job Matches
```python
from job_finder.storage.firestore_client import FirestoreClient

db = FirestoreClient.get_client("portfolio")
matches = db.collection("job-matches").stream()
count = len(list(matches))
print(f"Job matches in Firestore: {count}")
```

## Architecture Notes

### Database Structure
**Production (`portfolio` database):**
- `companies` - 19 companies with metadata
- `job-sources` - 25 sources (15 enabled)
- `job-queue` - Queue items for processing
- `job-matches` - AI-analyzed matched jobs
- `job-listings` - ⚠️ **DEPRECATED** (kept for reference, not used by scheduler)

### Data Flow
```
Scheduler (every 6h)
  ↓
SearchOrchestrator
  ↓
JobSourcesManager.get_active_sources()
  ↓
[Scrapes 15 enabled sources]
  ↓
ScraperIntake.submit_jobs()
  ↓
job-queue collection
  ↓
QueueWorker (continuous)
  ↓
QueueItemProcessor
  ↓
[AI Matching, Company Info]
  ↓
job-matches collection
  ↓
Portfolio UI
```

## Troubleshooting

### If scheduler still shows 0 sources:

1. **Check Docker container is running:**
   ```bash
   docker ps | grep job-finder
   ```

2. **Check logs:**
   ```bash
   docker logs job-finder-production
   ```

3. **Verify config file:**
   ```bash
   # Via SMB or direct:
   cat /srv/.../storage/jobscraper/production/config/config.yaml
   ```

4. **Manually trigger search (for testing):**
   ```bash
   docker exec -it job-finder-production python -m job_finder.main
   ```

### If sources are disabled:

Use Firestore console to enable:
1. Go to Firebase Console → Firestore
2. Navigate to `job-sources` collection
3. Find source document
4. Edit `enabled` field to `true`

## Related Documentation

- **Migration Script:** `scripts/migrate_listings_to_sources.py`
- **Check Script:** `scripts/database/check_job_sources.py`
- **Queue System:** `docs/queue-system.md`
- **Architecture:** `docs/architecture.md`

---

**✅ Migration successful! Next scheduler run will scrape jobs from 15 enabled sources.**
