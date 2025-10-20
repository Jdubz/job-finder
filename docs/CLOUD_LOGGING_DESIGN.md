# Cloud Logging Architecture for job-finder-FE Integration

## Overview

This document describes the architecture for sharing structured logs between the job-finder worker and the job-finder-FE UI using **Google Cloud Logging**, enabling real-time monitoring and debugging from the web interface.

**Type Safety:** Log structure is enforced via **@jdubz/job-finder-shared-types** npm package, ensuring consistency between job-finder-FE (TypeScript) and job-finder (Python).

## Why Cloud Logging (Not Firestore)

**Correct Approach:** Use Google Cloud Logging for all application logs
- ✅ Purpose-built for logging (not a database)
- ✅ Automatic log retention and lifecycle management
- ✅ Powerful query language (Logging Query Language)
- ✅ Built-in log sinks, metrics, and alerting
- ✅ Cost-effective at scale (free tier: 50 GB/month)
- ✅ No manual TTL/cleanup needed

**Why Not Firestore:**
- ❌ Firestore is for application data, not logs
- ❌ Requires manual cleanup/TTL management
- ❌ More expensive for high-volume logs
- ❌ Not optimized for time-series data

## Current State

**Already Implemented:**
- Environment labels (staging, production, development)
- Structured log format with categories ([WORKER], [QUEUE:type], [PIPELINE:stage])
- Cloud Logging handler with labels

**What We Have:**
```python
# Logs already go to Cloud Logging with labels
labels = {
    "environment": "staging",
    "service": "job-finder",
    "version": "1.0.0",
}
```

## Enhanced Cloud Logging Structure

### Log Entry Format

**Standard Python Logging (Current):**
```python
logger.info("[WORKER] STARTED | poll_interval=60")
# → textPayload: "[STAGING] 2025-10-18... - [WORKER] STARTED | poll_interval=60"
```

**Enhanced with JSON Structured Logging (Proposed):**
```python
logger.info("Worker started", extra={
    "json_fields": {
        "category": "worker",
        "action": "started",
        "queueItemId": None,
        "pipelineStage": None,
        "details": {"poll_interval": 60}
    }
})
# → jsonPayload: { category: "worker", action: "started", details: {...} }
```

### Structured Fields

All log entries should include these **standardized JSON fields**.

**Type Definitions:** See [@jdubz/job-finder-shared-types](https://github.com/Jdubz/job-finder-shared-types/blob/main/src/logging.types.ts) for complete TypeScript definitions.

**job-finder-FE Usage:**
```typescript
import {
  StructuredLogEntry,
  LogCategory,
  LogAction,
  CloudLogEntry
} from '@jdubz/job-finder-shared-types';
```

**Structure:**
```json
{
  "severity": "INFO",
  "timestamp": "2025-10-18T09:15:00.123Z",
  "labels": {
    "environment": "staging",  // CloudLoggingLabels.environment
    "service": "job-finder",
    "version": "1.0.0"
  },
  "jsonPayload": {  // StructuredLogEntry type
    // Standard fields (always present)
    "category": "worker|queue|pipeline|scrape|ai|database",  // LogCategory
    "action": "started|processing|completed|failed|skipped",  // LogAction
    "message": "Human-readable message",

    // Context fields (optional)
    "queueItemId": "abc123",
    "queueItemType": "job|company|scrape|source_discovery",
    "pipelineStage": "scrape|filter|analyze|save|fetch|extract",  // PipelineStage

    // Metadata (optional)
    "details": {
      // Any additional key-value data
      "url": "https://...",
      "duration": 1250,
      "method": "greenhouse"
    },

    // Error fields (optional)
    "error": {
      "type": "ValueError",
      "message": "Invalid URL",
      "stack": "Traceback..."
    }
  }
}
```

### Log Categories

**Consistent categories for filtering** (enforced by `LogCategory` type):
- `worker` - Worker lifecycle (started, idle, processing, stopped)
- `queue` - Queue item processing (job, company, scrape, source_discovery)
- `pipeline` - Pipeline stages (scrape, filter, analyze, save, fetch, extract)
- `scrape` - Web scraping operations
- `ai` - AI model operations (match, analyze, extract)
- `database` - Firestore operations (create, update, query)

## Querying Logs from job-finder-FE

### Cloud Logging API (Backend)

**Option 1: Cloud Functions Proxy**
```typescript
// Deploy Cloud Function that job-finder-FE calls
// functions/getLogs.ts
import { Logging } from '@google-cloud/logging';

export const getLogs = async (req, res) => {
  const { queueItemId, environment, category, limit } = req.body;

  const logging = new Logging();

  let filter = `
    logName="projects/static-sites-257923/logs/job-finder"
    labels.environment="${environment}"
  `;

  if (queueItemId) {
    filter += ` jsonPayload.queueItemId="${queueItemId}"`;
  }
  if (category) {
    filter += ` jsonPayload.category="${category}"`;
  }

  const [entries] = await logging.getEntries({
    filter,
    orderBy: 'timestamp desc',
    pageSize: limit || 100,
  });

  res.json({ logs: entries });
};
```

**Option 2: Direct API from Next.js Server Actions**
```typescript
// app/actions/getLogs.ts
'use server';

import { Logging } from '@google-cloud/logging';

export async function getWorkerLogs(options: {
  queueItemId?: string;
  environment?: string;
  category?: string;
  limit?: number;
}) {
  const logging = new Logging();

  const filter = buildFilter(options);

  const [entries] = await logging.getEntries({
    filter,
    orderBy: 'timestamp desc',
    pageSize: options.limit || 100,
  });

  return entries.map(entry => ({
    timestamp: entry.metadata.timestamp,
    severity: entry.metadata.severity,
    message: entry.data.message,
    category: entry.data.category,
    queueItemId: entry.data.queueItemId,
    pipelineStage: entry.data.pipelineStage,
    details: entry.data.details,
  }));
}
```

### Real-time Logs (Polling)

Since Cloud Logging doesn't support real-time websockets, use **polling**:

```typescript
// hooks/useWorkerLogs.ts
export function useWorkerLogs(options: LogOptions) {
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    async function fetchLogs() {
      const entries = await getWorkerLogs(options);
      setLogs(entries);
    }

    // Poll every 5 seconds for near-real-time
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);

    return () => clearInterval(interval);
  }, [options]);

  return { logs };
}
```

### Example Queries

**Get all logs for a queue item:**
```
logName="projects/static-sites-257923/logs/job-finder"
labels.environment="staging"
jsonPayload.queueItemId="abc123"
```

**Get worker status logs:**
```
logName="projects/static-sites-257923/logs/job-finder"
labels.environment="staging"
jsonPayload.category="worker"
```

**Get pipeline errors:**
```
logName="projects/static-sites-257923/logs/job-finder"
labels.environment="production"
jsonPayload.category="pipeline"
severity>=ERROR
```

**Get recent activity (last 1 hour):**
```
logName="projects/static-sites-257923/logs/job-finder"
labels.environment="staging"
timestamp>="2025-10-18T08:00:00Z"
```

## Implementation Changes

### Enhanced StructuredLogger

Update `StructuredLogger` to write **JSON structured logs** instead of text:

```python
class StructuredLogger:
    def queue_item_processing(
        self, item_id: str, item_type: str, action: str, details: Optional[Dict] = None
    ):
        # Old: Text log with parsing needed
        # message = f"[QUEUE:{item_type.upper()}] {action} - ID:{item_id}"

        # New: JSON structured log
        self.logger.info(
            f"Queue item {action}",
            extra={
                "json_fields": {
                    "category": "queue",
                    "action": action,
                    "queueItemId": item_id,
                    "queueItemType": item_type,
                    "details": details or {}
                }
            }
        )
```

### Cloud Logging Handler Configuration

Ensure Cloud Logging handler uses **structured logging**:

```python
# In setup_logging()
cloud_handler = CloudLoggingHandler(
    client,
    name="job-finder",
    labels=labels,
    # Enable JSON structured logging
    resource=Resource(type="generic_task", labels={
        "project_id": client.project,
        "location": "us-central1",
        "namespace": "job-finder",
        "job": "queue-worker",
        "task_id": os.getenv("HOSTNAME", "unknown"),
    })
)
```

## job-finder-FE UI Components

### 1. Worker Status Dashboard

Shows current worker state:
```typescript
function WorkerStatusDashboard() {
  const { logs } = useWorkerLogs({
    environment: 'staging',
    category: 'worker',
    limit: 10
  });

  const latestStatus = logs[0];

  return (
    <div>
      <StatusBadge status={latestStatus?.action} />
      <div>Last activity: {latestStatus?.timestamp}</div>
      {latestStatus?.details && (
        <Details data={latestStatus.details} />
      )}
    </div>
  );
}
```

### 2. Queue Item Logs Viewer

Shows complete pipeline execution for a job:
```typescript
function QueueItemLogs({ itemId }: { itemId: string }) {
  const { logs } = useWorkerLogs({
    queueItemId: itemId,
    limit: 100
  });

  // Group by pipeline stage
  const pipelineStages = groupByStage(logs);

  return (
    <PipelineVisualization>
      {pipelineStages.map(stage => (
        <StageCard
          key={stage.name}
          stage={stage}
          logs={stage.logs}
        />
      ))}
    </PipelineVisualization>
  );
}
```

### 3. Live Activity Feed

Recent worker activity:
```typescript
function LiveActivityFeed() {
  const { logs } = useWorkerLogs({
    environment: 'staging',
    limit: 50
  });

  return (
    <div className="activity-feed">
      {logs.map(log => (
        <LogEntry
          key={log.timestamp}
          log={log}
          category={log.category}
          severity={log.severity}
        />
      ))}
    </div>
  );
}
```

## Log Retention & Costs

**Cloud Logging Pricing:**
- First 50 GB/month: **Free**
- Additional storage: $0.50/GB/month
- Default retention: **30 days**
- Extended retention: Up to 3650 days (configurable)

**Estimated Usage:**
- Avg log entry: ~500 bytes
- 1000 logs/day = 500 KB/day = 15 MB/month
- Well within free tier

**Log Sinks (Optional):**
- Export logs to BigQuery for long-term analysis
- Export to Cloud Storage for archival
- Stream to Pub/Sub for real-time processing

## Security

**IAM Permissions:**
```yaml
# job-finder-FE service account needs:
roles/logging.viewer  # Read logs
roles/logging.privateLogViewer  # Access all log data

# Job-finder worker needs:
roles/logging.logWriter  # Write logs
```

**Log-Based Metrics (Optional):**
Create metrics from logs for dashboards:
```
# Count errors per hour
resource.type="generic_task"
jsonPayload.category="pipeline"
severity>=ERROR
```

## Migration from Firestore Approach

1. **Remove** `ActivityLogManager` class
2. **Keep** `StructuredLogger` but enhance with JSON fields
3. **Update** log methods to use `json_fields` extra parameter
4. **Create** Cloud Function or Server Action for job-finder-FE log access
5. **Build** job-finder-FE UI components using Cloud Logging API

## Next Steps

1. ✅ Environment labels already implemented
2. ⬜ Enhance StructuredLogger to use JSON structured logging
3. ⬜ Create Cloud Function/Server Action for job-finder-FE log access
4. ⬜ Build job-finder-FE UI components for worker monitoring
5. ⬜ Set up log-based metrics for dashboard
6. ⬜ Configure alerting policies for errors

## Example Log Queries

**Debug why job failed:**
```
logName="projects/static-sites-257923/logs/job-finder"
jsonPayload.queueItemId="abc123"
severity>=WARNING
```

**Monitor worker health:**
```
logName="projects/static-sites-257923/logs/job-finder"
jsonPayload.category="worker"
timestamp>="2025-10-18T00:00:00Z"
```

**Track AI usage:**
```
logName="projects/static-sites-257923/logs/job-finder"
jsonPayload.category="ai"
jsonPayload.details.model="claude-3-5-sonnet"
```

**Performance analysis:**
```
logName="projects/static-sites-257923/logs/job-finder"
jsonPayload.category="pipeline"
jsonPayload.details.duration>5000
```

This approach leverages Google Cloud Logging's strengths while avoiding the complexity and costs of storing logs in Firestore.
