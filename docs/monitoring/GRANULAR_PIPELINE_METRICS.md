# Granular Pipeline Monitoring & Metrics

This document provides comprehensive monitoring strategies for the granular job processing pipeline.

## Overview

The granular pipeline breaks job processing into 4 independent steps, each requiring different monitoring approaches:
1. **JOB_SCRAPE**: Network reliability, selector accuracy, data extraction quality
2. **JOB_FILTER**: Filter effectiveness, rejection rates, strike distribution
3. **JOB_ANALYZE**: AI performance, cost tracking, match quality
4. **JOB_SAVE**: Storage reliability, data integrity

## Key Performance Indicators (KPIs)

### Pipeline Health Metrics

| Metric | Target | Alert Threshold | Description |
|--------|--------|----------------|-------------|
| **Overall Success Rate** | >85% | <80% | % of jobs completing all 4 steps |
| **Step Completion Time** | <20s total | >60s | End-to-end pipeline duration |
| **Error Rate** | <5% | >10% | Failed items / total items |
| **Queue Backlog** | <100 items | >500 | Pending items in queue |
| **Cost per Job** | $0.10-0.30 | >$0.50 | Total AI cost per completed job |

### Step-Specific Metrics

#### JOB_SCRAPE
- **Success Rate**: >90% (Target), <85% (Alert)
- **Average Duration**: 2-5 seconds
- **Selector Failure Rate**: <5%
- **Data Completeness**: >95% (all required fields present)
- **Source Health**: Consecutive failures per source

#### JOB_FILTER
- **Processing Time**: <0.2 seconds
- **Pass Rate**: 30-50% (depends on source quality)
- **Strike Distribution**: Track which filters reject most
- **False Negative Rate**: <2% (good jobs rejected)

#### JOB_ANALYZE
- **Success Rate**: >95%
- **Average Duration**: 5-10 seconds
- **AI Cost per Job**: $0.10-0.30
- **Match Score Distribution**: Track score ranges
- **High Priority Rate**: 20-40% of analyzed jobs

#### JOB_SAVE
- **Success Rate**: >99%
- **Average Duration**: <1 second
- **Storage Errors**: <0.1%

## Monitoring Queries

### Cloud Logging Queries

#### Pipeline Progress Tracking
```
resource.type="cloud_run_revision"
jsonPayload.message=~"Processing.*sub_task"
```

View pipeline flow:
```
resource.type="cloud_run_revision"
(jsonPayload.message=~"Spawning next pipeline step" OR
 jsonPayload.message=~"Pipeline complete")
```

#### Step Performance
```
# SCRAPE performance
resource.type="cloud_run_revision"
jsonPayload.sub_task="scrape"
jsonPayload.duration>5000

# FILTER effectiveness
resource.type="cloud_run_revision"
jsonPayload.sub_task="filter"
jsonPayload.filter_result.passed=true

# ANALYZE costs
resource.type="cloud_run_revision"
jsonPayload.sub_task="analyze"
jsonPayload.ai_cost>0.5

# SAVE failures
resource.type="cloud_run_revision"
jsonPayload.sub_task="save"
severity="ERROR"
```

#### Error Detection
```
# Scraping errors
resource.type="cloud_run_revision"
jsonPayload.sub_task="scrape"
severity="ERROR"

# Selector failures
resource.type="cloud_run_revision"
jsonPayload.message=~"Selector.*failed"

# AI errors
resource.type="cloud_run_revision"
jsonPayload.sub_task="analyze"
jsonPayload.message=~"AI.*error"

# Pipeline orphans (no next step spawned)
resource.type="cloud_run_revision"
jsonPayload.message=~"Pipeline stopped"
severity="WARNING"
```

#### Cost Tracking
```
# Total AI spend
resource.type="cloud_run_revision"
jsonPayload.ai_cost>0
| summarize sum(ai_cost) by sub_task

# Expensive jobs
resource.type="cloud_run_revision"
jsonPayload.total_pipeline_cost>1.0
```

### Firestore Queries

#### Queue Health
```javascript
// Count items by step and status
db.collection('job-queue')
  .where('type', '==', 'job')
  .where('sub_task', '==', 'scrape')
  .where('status', '==', 'pending')
  .count()
  .get()

// Find stuck items (processing > 5 min)
const fiveMinutesAgo = new Date(Date.now() - 5*60*1000);
db.collection('job-queue')
  .where('status', '==', 'processing')
  .where('processed_at', '<', fiveMinutesAgo)
  .get()

// Pipeline completion rate
db.collection('job-queue')
  .where('type', '==', 'job')
  .where('sub_task', '==', 'save')
  .where('status', '==', 'success')
  .count()
  .get()
```

#### Source Health
```javascript
// Sources with high failure rates
db.collection('job-sources')
  .where('consecutiveFailures', '>=', 3)
  .where('enabled', '==', true)
  .get()

// Disabled sources
db.collection('job-sources')
  .where('enabled', '==', false)
  .get()
```

#### Match Quality
```javascript
// Recent matches
db.collection('job-matches')
  .orderBy('created_at', 'desc')
  .limit(50)
  .get()

// High priority matches
db.collection('job-matches')
  .where('application_priority', '==', 'High')
  .where('created_at', '>', yesterdayTimestamp)
  .get()

// Score distribution
db.collection('job-matches')
  .where('match_score', '>=', 85)
  .count()
  .get()
```

## Alerting Rules

### Critical Alerts (Immediate Action Required)

#### Pipeline Stopped
```
Condition: No SAVE completions in 15 minutes
Query:
  resource.type="cloud_run_revision"
  jsonPayload.sub_task="save"
  jsonPayload.status="success"
  timestamp < (now - 15m)
Action: Check worker health, queue backlog
```

#### High Error Rate
```
Condition: >20% error rate in any step over 10 minutes
Query:
  resource.type="cloud_run_revision"
  severity="ERROR"
  jsonPayload.sub_task IN ["scrape","filter","analyze","save"]
  | rate(10m) > 0.2
Action: Check logs for error patterns, disable failing sources
```

#### Source Failure Spike
```
Condition: >5 sources disabled in 1 hour
Query:
  db.collection('job-sources')
    .where('enabled', '==', false)
    .where('updatedAt', '>', oneHourAgo)
    .count()
Action: Review selector configurations, check for website changes
```

#### Cost Overrun
```
Condition: Daily AI cost >$50
Query:
  resource.type="cloud_run_revision"
  jsonPayload.ai_cost>0
  timestamp > startOfDay
  | sum(ai_cost) > 50
Action: Check for retry loops, verify model selection
```

### Warning Alerts (Review Within Hours)

#### Low Pass Rate
```
Condition: FILTER pass rate <20% over 1 hour
Action: Review filter configuration, check job quality
```

#### Slow Processing
```
Condition: Average step duration >2x expected
Action: Check Cloud Run performance, review logs
```

#### Queue Backlog Growing
```
Condition: Pending items increasing >100 in 30 minutes
Action: Scale workers, check processing rate
```

## Dashboards

### Main Pipeline Dashboard

**Panels:**
1. **Pipeline Funnel** - Items at each step (SCRAPE → FILTER → ANALYZE → SAVE)
2. **Success Rate by Step** - Time series of completion rates
3. **Processing Time** - Average duration per step
4. **Error Rate** - Errors by step and type
5. **Cost Tracking** - AI spend by step and total
6. **Queue Depth** - Pending items by step

**Refresh**: Real-time (30 seconds)

### Source Health Dashboard

**Panels:**
1. **Active Sources** - Count by type (greenhouse, workday, etc.)
2. **Failure Rate by Source** - Top failing sources
3. **Jobs per Source** - Scraping volume
4. **Disabled Sources** - Recently disabled, reason
5. **Selector Success** - Which fields failing most

**Refresh**: 5 minutes

### Match Quality Dashboard

**Panels:**
1. **Match Score Distribution** - Histogram of scores
2. **Priority Breakdown** - High/Medium/Low counts
3. **Top Companies** - Most matches by company
4. **Skills Matched** - Most common matched skills
5. **Time to Match** - End-to-end pipeline duration

**Refresh**: 5 minutes

### Cost Dashboard

**Panels:**
1. **Daily AI Spend** - Total cost by day
2. **Cost by Step** - SCRAPE vs ANALYZE
3. **Cost per Job** - Average and trend
4. **Token Usage** - Input/output tokens by model
5. **Estimated Monthly Cost** - Projection based on current rate

**Refresh**: 1 hour

## Health Check Procedures

### Daily Health Check (5 minutes)
1. ✅ Check main dashboard for red alerts
2. ✅ Verify pipeline funnel looks normal (30-50% pass filter)
3. ✅ Check cost is within budget ($0.10-0.30 per job)
4. ✅ Review any disabled sources
5. ✅ Scan recent errors in logs

### Weekly Deep Dive (30 minutes)
1. 📊 Analyze match quality distribution
2. 📊 Review filter effectiveness (strike patterns)
3. 📊 Check source health trends
4. 📊 Optimize underperforming sources
5. 📊 Review cost trends and optimization opportunities
6. 📊 Update filter/scoring configurations if needed

### Monthly Review (2 hours)
1. 📈 Compare metrics month-over-month
2. 📈 Review all disabled sources, re-enable if fixed
3. 📈 Analyze cost per quality match
4. 📈 Identify new sources to add
5. 📈 Update AI prompts based on match feedback
6. 📈 Review and update alerting thresholds

## Troubleshooting Runbooks

### Runbook 1: High SCRAPE Failure Rate

**Symptoms**: >20% SCRAPE errors, specific source

**Diagnosis Steps**:
1. Check Cloud Logging for selector failures
2. Visit the job board website manually
3. Compare current HTML to stored selectors
4. Check for rate limiting (429 errors)

**Resolution**:
- If selectors outdated: Re-discover with AI selector discovery
- If rate limited: Increase delay, rotate IPs
- If website down: Temporarily disable source
- If major redesign: Update source configuration

### Runbook 2: FILTER Passing Too Many/Few Jobs

**Symptoms**: Pass rate <20% or >80%

**Diagnosis Steps**:
1. Query Firestore for recent filter results
2. Check strike distribution
3. Review sample rejected jobs
4. Compare to user expectations

**Resolution**:
- Adjust strike thresholds in config
- Update keyword exclusions
- Refine location filtering
- Review job type preferences

### Runbook 3: High AI Costs

**Symptoms**: Cost per job >$0.50

**Diagnosis Steps**:
1. Check model selection (should use Haiku for SCRAPE)
2. Look for retry loops in logs
3. Check average token counts
4. Review job descriptions being analyzed

**Resolution**:
- Verify AITask.SCRAPE uses Haiku
- Add retry limits to prevent loops
- Filter more aggressively before ANALYZE
- Truncate excessively long job descriptions

### Runbook 4: Pipeline Orphans (Stuck Items)

**Symptoms**: Items stuck in processing, no next step spawned

**Diagnosis Steps**:
1. Find stuck items in Firestore
2. Check logs for processing errors
3. Review pipeline_state data
4. Check for crashes during processing

**Resolution**:
- Reset stuck items to pending
- Fix underlying error (scraping, AI, etc.)
- Manually spawn next step if data exists
- Add retry with exponential backoff

## Metrics Collection

### Structured Logging Format

All pipeline steps should log in this format:

```python
logger.info(
    "Pipeline step completed",
    extra={
        "sub_task": "scrape",
        "item_id": item.id,
        "duration": duration_ms,
        "status": "success",
        "pipeline_state_size": len(json.dumps(pipeline_state)),
        "next_step": "filter",
        # Step-specific fields
        "selectors_used": ["title", "company", "description"],
        "data_completeness": 0.95,
    }
)
```

### Custom Metrics to Export

If using Prometheus/Cloud Monitoring:

**Counters**:
- `pipeline_items_total{step, status}` - Total items processed
- `pipeline_errors_total{step, error_type}` - Errors by type
- `ai_requests_total{task, model}` - AI API calls

**Histograms**:
- `pipeline_step_duration_seconds{step}` - Processing time distribution
- `ai_cost_dollars{step}` - Cost distribution
- `match_score{priority}` - Score distribution

**Gauges**:
- `queue_depth{step, status}` - Current queue size
- `active_sources` - Enabled sources count
- `pipeline_success_rate{step}` - Rolling success rate

## Performance Baselines

Based on initial testing, these are expected performance baselines:

### Processing Time (p50/p95/p99)
- **SCRAPE**: 3s / 8s / 15s
- **FILTER**: 0.05s / 0.1s / 0.2s
- **ANALYZE**: 6s / 12s / 20s
- **SAVE**: 0.3s / 0.8s / 2s
- **Total**: 10s / 25s / 40s

### Success Rates
- **SCRAPE**: 92% success, 5% selector failures, 3% network errors
- **FILTER**: 95% processed, 5% data validation errors
- **ANALYZE**: 98% success, 2% AI errors
- **SAVE**: 99.5% success, 0.5% storage errors

### Cost per Job
- **SCRAPE (Haiku)**: $0.002 average (1-3K tokens)
- **FILTER**: $0
- **ANALYZE (Sonnet)**: $0.15 average (3-6K tokens)
- **SAVE**: $0
- **Total**: $0.152 average, $0.10-0.30 typical range

### Resource Usage
- **Memory per Step**: 50-200KB (avg 100KB)
- **CPU per Step**: <0.5 vCPU-seconds
- **Network**: ~50KB download per scrape

## Related Documentation

- [GRANULAR_PIPELINE_DEPLOYMENT.md](../GRANULAR_PIPELINE_DEPLOYMENT.md) - Deployment procedures
- [CLAUDE.md](../../CLAUDE.md) - Architecture overview
- [Queue System](../queue-system.md) - Queue processing details
