# Granular Pipeline Deployment Checklist

This checklist provides step-by-step verification procedures for deploying the granular pipeline architecture.

## Pre-Deployment Verification

### 1. Code Readiness ✅

- [ ] All tests passing (554 tests)
  ```bash
  pytest
  # Expected: 554 passed
  ```

- [ ] Type checking clean
  ```bash
  mypy src/
  # Expected: Success: no issues found
  ```

- [ ] Code formatting verified
  ```bash
  black --check src/ tests/
  # Expected: All files formatted correctly
  ```

- [ ] Linting clean
  ```bash
  flake8 src/ tests/
  # Expected: No errors
  ```

### 2. Shared Types Synchronized ✅

- [ ] TypeScript types updated in `job-finder-shared-types`
  - [ ] `JobSubTask` type defined
  - [ ] `QueueItem` includes `sub_task`, `pipeline_state`, `parent_item_id`
  - [ ] Version bumped and published

- [ ] Python models match TypeScript types
  ```python
  # Verify in src/job_finder/queue/models.py
  - JobSubTask enum
  - JobQueueItem Pydantic model
  ```

### 3. Database Compatibility ✅

- [ ] New fields are optional (backwards compatible)
  - [ ] `sub_task: Optional[JobSubTask] = None`
  - [ ] `pipeline_state: Optional[Dict] = None`
  - [ ] `parent_item_id: Optional[str] = None`

- [ ] Firestore indexes created (if needed)
  ```bash
  # Check if composite indexes required
  firebase firestore:indexes
  ```

### 4. Configuration Review

- [ ] AI model selection configured
  ```yaml
  # config/config.yaml
  ai:
    provider: "claude"
    # Models will auto-select based on task
  ```

- [ ] Queue settings appropriate
  ```yaml
  queue:
    max_retries: 3
    processing_timeout: 300
  ```

- [ ] Firestore database name correct
  ```yaml
  firestore:
    database_name: "portfolio"  # or "portfolio-staging" for staging
  ```

### 5. Documentation Complete

- [ ] CLAUDE.md updated with pipeline architecture
- [ ] GRANULAR_PIPELINE_DEPLOYMENT.md created
- [ ] GRANULAR_PIPELINE_METRICS.md created
- [ ] Migration script documented

## Deployment Procedure

### Option A: Gradual Rollout (RECOMMENDED)

#### Phase A1: Deploy Code (No Behavior Change)

- [ ] Create feature branch
  ```bash
  git checkout -b release/granular-pipeline
  ```

- [ ] Verify all changes committed
  ```bash
  git status
  # Expected: nothing to commit, working tree clean
  ```

- [ ] Build Docker image
  ```bash
  docker build -t job-finder:granular .
  ```

- [ ] Tag with version
  ```bash
  docker tag job-finder:granular gcr.io/static-sites-257923/job-finder:v2.0.0-granular
  docker tag job-finder:granular gcr.io/static-sites-257923/job-finder:latest
  ```

- [ ] Push to container registry
  ```bash
  docker push gcr.io/static-sites-257923/job-finder:v2.0.0-granular
  docker push gcr.io/static-sites-257923/job-finder:latest
  ```

- [ ] Deploy to staging (if available)
  ```bash
  gcloud run deploy job-finder-staging \
    --image gcr.io/static-sites-257923/job-finder:v2.0.0-granular \
    --platform managed \
    --region us-west1
  ```

- [ ] Deploy to production
  ```bash
  gcloud run deploy job-finder \
    --image gcr.io/static-sites-257923/job-finder:v2.0.0-granular \
    --platform managed \
    --region us-west1
  ```

- [ ] **Verification Point**: Confirm deployment successful
  ```bash
  gcloud run services list
  # Check READY status
  ```

- [ ] **Verification Point**: Check logs for errors
  ```bash
  gcloud logging read "resource.type=cloud_run_revision" --limit 50
  ```

- [ ] **Verification Point**: Legacy items still processing
  ```bash
  # Submit a test job without sub_task
  # Verify it processes through legacy path
  ```

#### Phase A2: Test with Single Granular Item

- [ ] Create test granular item
  ```python
  from job_finder.queue import QueueManager, JobSubTask

  queue = QueueManager(database_name="portfolio")
  queue.create_pipeline_item(
      url="https://boards.greenhouse.io/stripe/jobs/123456",
      sub_task=JobSubTask.SCRAPE,
      pipeline_state={},
      company_name="Stripe",
      source="user_submission"
  )
  ```

- [ ] **Verification Point**: SCRAPE completes
  ```bash
  # Check logs for "JOB_SCRAPE completed"
  gcloud logging read "jsonPayload.sub_task='scrape'" --limit 10
  ```

- [ ] **Verification Point**: FILTER spawned
  ```bash
  # Check Firestore for FILTER item with same parent_item_id
  # Check logs for "Spawning next pipeline step: filter"
  ```

- [ ] **Verification Point**: ANALYZE spawned (if filter passed)
  ```bash
  # Check Firestore for ANALYZE item
  # Verify pipeline_state includes job_data and filter_result
  ```

- [ ] **Verification Point**: SAVE completed
  ```bash
  # Check job-matches collection for new match
  # Verify all 4 steps completed successfully
  ```

- [ ] **Verification Point**: Cost within expected range
  ```bash
  # Check logs for AI cost tracking
  # Expected: SCRAPE ~$0.002, ANALYZE ~$0.10-0.30
  ```

#### Phase A3: Monitor Initial Processing

- [ ] Set up monitoring dashboard
  - [ ] Pipeline funnel (SCRAPE → FILTER → ANALYZE → SAVE)
  - [ ] Success rates by step
  - [ ] Cost tracking
  - [ ] Error rates

- [ ] Monitor for 24 hours with single test item
  - [ ] No unexpected errors
  - [ ] Cost within budget
  - [ ] All steps completing

- [ ] Review logs for anomalies
  ```bash
  # Check for errors
  gcloud logging read "severity=ERROR" --limit 50

  # Check for warnings
  gcloud logging read "severity=WARNING" --limit 50
  ```

#### Phase A4: Migrate Existing Queue (Optional)

**Note**: Only migrate if you want existing pending items to use granular pipeline.

- [ ] Analyze current queue composition
  ```bash
  python scripts/migrate_to_granular_pipeline.py --analyze-only
  ```

- [ ] Review migration plan
  ```bash
  python scripts/migrate_to_granular_pipeline.py --dry-run
  ```

- [ ] Migrate pending items only
  ```bash
  python scripts/migrate_to_granular_pipeline.py --status pending --confirm
  ```

- [ ] **Verification Point**: Migrated items processing
  ```bash
  # Check Firestore for items with sub_task="scrape"
  # Verify they're progressing through pipeline
  ```

- [ ] Monitor migrated items for 1 hour
  - [ ] All migrated items processing
  - [ ] No increase in error rate
  - [ ] Cost per job as expected

#### Phase A5: Update job-finder-FE Integration

- [ ] Update portfolio job submission code
  ```typescript
  // In portfolio project's job submission
  const queueItem: QueueItem = {
    type: "job",
    url: jobUrl,
    company_name: companyName,
    sub_task: "scrape",  // NEW: Start with SCRAPE step
    pipeline_state: {},   // NEW: Empty initial state
    source: "user_submission",
    // ... other fields
  }
  ```

- [ ] Deploy portfolio changes

- [ ] **Verification Point**: New submissions use granular pipeline
  ```bash
  # Submit job through portfolio
  # Verify it has sub_task="scrape"
  # Verify it progresses through all steps
  ```

### Option B: Big Bang Deployment

**⚠️ Warning**: Higher risk, only use if confident in testing.

- [ ] Complete all Pre-Deployment Verification steps above

- [ ] Deploy code (same as Option A, Phase A1)

- [ ] Immediately migrate all pending items
  ```bash
  python scripts/migrate_to_granular_pipeline.py --status pending --confirm
  ```

- [ ] Update portfolio integration immediately

- [ ] **Critical Monitoring**: Watch for 2 hours continuously
  - [ ] All items processing
  - [ ] Error rate <10%
  - [ ] Cost within budget

## Post-Deployment Verification

### Immediate Checks (Within 1 Hour)

- [ ] **Pipeline Health**: All 4 steps processing
  ```javascript
  // Firestore query for each step
  db.collection('job-queue')
    .where('sub_task', '==', 'scrape')
    .where('status', '==', 'success')
    .limit(10)
    .get()
  // Repeat for filter, analyze, save
  ```

- [ ] **Error Rate**: <10% overall
  ```bash
  gcloud logging read "severity=ERROR" --limit 100 --format json \
    | jq 'length'
  ```

- [ ] **Cost Tracking**: Within $0.10-0.30 per job
  ```bash
  # Check logs for AI cost entries
  gcloud logging read "jsonPayload.ai_cost>0" --limit 50
  ```

- [ ] **Queue Not Backing Up**: Pending items processing
  ```javascript
  db.collection('job-queue')
    .where('status', '==', 'pending')
    .count()
    .get()
  // Should not be growing rapidly
  ```

### Daily Checks (First Week)

- [ ] **Day 1**: Review all metrics
  - [ ] Success rate by step
  - [ ] Average processing time
  - [ ] Total cost
  - [ ] Error patterns

- [ ] **Day 2-7**: Monitor trends
  - [ ] Success rates stable or improving
  - [ ] No cost spikes
  - [ ] Error rate declining
  - [ ] Queue depth stable

- [ ] **Weekly Summary**:
  - [ ] Document metrics
  - [ ] Compare to baselines (see GRANULAR_PIPELINE_METRICS.md)
  - [ ] Identify optimization opportunities

## Rollback Procedure

### Trigger Rollback If:
- Error rate >20% for >30 minutes
- Cost per job >$1.00 consistently
- Pipeline completely stuck (no completions for >15 minutes)
- Data integrity issues detected

### Rollback Steps

1. **Stop Processing Granular Items**
   ```python
   # Quick code fix in processor.py
   def process_item(self, item):
       if item.sub_task:
           logger.warning(f"Skipping granular item (rollback mode): {item.id}")
           self.queue_manager.update_status(
               item.id, QueueStatus.FAILED,
               result_message="Granular pipeline disabled during rollback"
           )
           return
       # Continue with legacy processing
   ```

2. **Deploy Previous Version**
   ```bash
   # Find previous working version
   gcloud run services describe job-finder --format="value(status.latestReadyRevisionName)"

   # Rollback to previous revision
   gcloud run services update-traffic job-finder \
     --to-revisions=PREVIOUS_REVISION=100
   ```

3. **Clean Up Granular Items** (if necessary)
   ```python
   # Only if data corrupted or causing issues
   db = firestore.Client(database="portfolio")
   query = db.collection('job-queue').where('sub_task', '!=', None)
   for doc in query.stream():
       doc.reference.delete()
   ```

4. **Revert job-finder-FE Changes**
   ```bash
   # In portfolio project
   git revert <commit-with-granular-changes>
   # Deploy reverted version
   ```

5. **Post-Rollback Verification**
   - [ ] Legacy processing working
   - [ ] No new granular items created
   - [ ] Error rate back to normal
   - [ ] Cost back to normal

## Success Criteria

Deployment is successful when ALL criteria met:

### Technical Success
- [ ] ✅ All 4 pipeline steps processing correctly
- [ ] ✅ SCRAPE → FILTER → ANALYZE → SAVE chain working
- [ ] ✅ Error rate <5% (same as legacy or better)
- [ ] ✅ No increase in stuck items
- [ ] ✅ Legacy items (if any) still processing correctly

### Performance Success
- [ ] ✅ Average processing time <25 seconds (p50)
- [ ] ✅ Memory usage per step ~100KB (67% reduction)
- [ ] ✅ Queue not backing up (depth stable)

### Cost Success
- [ ] ✅ Cost per job $0.10-0.30 (70% reduction from legacy)
- [ ] ✅ SCRAPE using Haiku (~$0.002 per job)
- [ ] ✅ ANALYZE using Sonnet (~$0.10-0.30 per job)

### Quality Success
- [ ] ✅ Match quality maintained (score distribution similar)
- [ ] ✅ job-finder-FE project receiving matches normally
- [ ] ✅ No complaints from portfolio users
- [ ] ✅ Data integrity verified (no missing fields)

## Monitoring Schedule

### First 24 Hours
- **Every 30 minutes**: Check main dashboard
- **Every 2 hours**: Review error logs
- **Every 4 hours**: Verify cost tracking

### First Week
- **Daily**: Review all KPIs (see GRANULAR_PIPELINE_METRICS.md)
- **Daily**: Check for new error patterns
- **Daily**: Verify cost within budget

### Ongoing
- **Daily**: 5-minute health check (see monitoring docs)
- **Weekly**: 30-minute deep dive
- **Monthly**: 2-hour comprehensive review

## Troubleshooting Contact

For issues during deployment:

1. **Check monitoring dashboard** - Most issues visible here
2. **Review logs** - Cloud Logging has detailed traces
3. **Check Firestore** - View queue items directly
4. **Consult runbooks** - See GRANULAR_PIPELINE_METRICS.md

If rollback needed:
1. Execute rollback procedure above
2. Document issue for post-mortem
3. Plan remediation before re-attempting deployment

## Sign-Off

Deployment completed by: _______________
Date: _______________
Version deployed: _______________

All success criteria met: [ ] Yes [ ] No

Notes:
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

## Related Documentation

- [GRANULAR_PIPELINE_DEPLOYMENT.md](GRANULAR_PIPELINE_DEPLOYMENT.md) - Detailed deployment guide
- [GRANULAR_PIPELINE_METRICS.md](monitoring/GRANULAR_PIPELINE_METRICS.md) - Monitoring and metrics
- [CLAUDE.md](../CLAUDE.md) - Architecture overview
- [Migration Script](../scripts/migrate_to_granular_pipeline.py) - Migrate legacy items
