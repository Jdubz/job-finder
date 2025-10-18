# Real-Time Log Streaming for E2E Tests

## Overview

Google Cloud Logging provides **TailLogEntries API** for real-time log streaming. This guide shows how to integrate real-time log monitoring with your E2E test suite running against staging.

### What is TailLogEntries?

- **Native GCP API** for streaming logs in real-time
- **No polling** - true push-based streaming  
- **Built-in buffering** - batches logs for efficiency
- **Efficient** - minimal latency (typically <1 second)
- **Scalable** - designed for high-volume logging

## Quick Start

### Basic Usage

```python
from tests.e2e.helpers import LogStreamer

# Create streamer
streamer = LogStreamer(
    project_id="your-gcp-project",
    database_name="portfolio-staging"
)

# Stream logs during test execution
with streamer.stream_logs(test_run_id="e2e_test_123"):
    # Run your E2E tests here
    run_e2e_tests()
    
# Logs are automatically displayed to console in real-time
# with colors and formatting
```

## Advanced Features

### Custom Filters

```python
# Filter by specific stages
with streamer.stream_logs(
    filter_string='resource.type="gce_instance" AND jsonPayload.stage="scrape"'
):
    run_tests()

# Filter by severity
streamer = LogStreamer(project_id)
with streamer.stream_logs(
    test_run_id="e2e_test_123",
):
    # Built-in support for severity filtering
    pass
```

### Log Callbacks

Process each log entry programmatically:

```python
def my_callback(entry):
    """Called for each log entry."""
    severity = entry.get("severity")
    message = entry.get("textPayload", "")
    
    if severity == "ERROR":
        print(f"ERROR DETECTED: {message}")
        # Could send alert, update metrics, etc.

with streamer.stream_logs(
    test_run_id="e2e_test_123",
    callback=my_callback
):
    run_tests()
```

### Search Logs

Non-streaming search of log history:

```python
# Find specific logs
entries = streamer.search_logs(
    test_run_id="e2e_test_123",
    limit=100
)

for entry in entries:
    print(f"[{entry['severity']}] {entry['textPayload']}")
```

### Get Log Summary

Get statistics after test run:

```python
summary = streamer.get_log_summary("e2e_test_123")

print(f"Total log entries: {summary['total_entries']}")
print(f"By severity: {summary['by_severity']}")
print(f"Test duration: {summary['duration']}s")
print(f"Errors: {len(summary['errors'])}")
print(f"Warnings: {len(summary['warnings'])}")
```

## Integration with E2E Tests

### Example: Enhance test runner

File: `tests/e2e/run_all_scenarios.py`

```python
from tests.e2e.helpers import stream_test_logs, get_test_logs_summary

def run_scenarios(test_run_id=None, stream_logs=True, **kwargs):
    """Run all scenarios with optional log streaming."""
    
    if test_run_id is None:
        test_run_id = f"e2e_test_{uuid.uuid4().hex[:8]}"
    
    results = []
    
    # Stream logs during test execution
    log_context = (
        stream_test_logs(project_id, test_run_id)
        if stream_logs
        else nullcontext()
    )
    
    with log_context:
        # Run all scenarios
        for scenario_class in [JobSubmissionScenario, ...]:
            scenario = scenario_class(test_run_id=test_run_id)
            result = scenario.run()
            results.append(result)
    
    # Get log summary after tests
    if stream_logs:
        summary = get_test_logs_summary(project_id, test_run_id)
        print_log_summary(summary)
    
    return results
```

### Example: Scenario with logging

```python
from tests.e2e.helpers import LogStreamer

class MyScenario(BaseE2EScenario):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.log_streamer = LogStreamer(
            project_id=os.getenv("GCP_PROJECT_ID"),
            database_name=self.db_name
        )
    
    def run(self):
        """Run scenario with log streaming."""
        with self.log_streamer.stream_logs(test_run_id=self.test_run_id):
            self.setup()
            self.execute()
            self.verify()
            self.cleanup()
```

## Output Format

Logs are displayed with:

- **Timestamp** - When the log was created
- **Severity** - DEBUG, INFO, WARNING, ERROR, CRITICAL (with colors)
- **Stage** - Pipeline stage (fetch, extract, analyze, save)
- **Document ID** - First 8 chars of queue item ID
- **Status** - Current processing status
- **Message** - Log message or JSON payload

**Example output:**

```
2025-10-18T14:30:45.123Z [INFO    ] [FETCH      ] doc:abc12345 status:pending Scraping URL...
2025-10-18T14:30:46.456Z [DEBUG   ] [EXTRACT    ] doc:abc12345 status:running Processing job data...
2025-10-18T14:30:48.789Z [INFO    ] [ANALYZE    ] doc:abc12345 status:running AI matching analysis...
2025-10-18T14:30:49.012Z [WARNING ] [SAVE       ] doc:abc12345 status:success Below match threshold
2025-10-18T14:30:49.234Z [INFO    ] [COMPLETE   ] doc:abc12345 status:success Job processing finished
```

## Configuration

### Environment Variables

```bash
export GCP_PROJECT_ID="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
```

### Settings

```python
streamer = LogStreamer(
    project_id="my-project",
    database_name="portfolio-staging",
    buffer_duration=1.0,  # Seconds to buffer logs
)
```

## Performance Considerations

### API Quotas

Google Cloud Logging has generous quotas:
- **Reads:** 10,000 entries/second per project
- **Writes:** 1,000 entries/second per service account
- **Streaming:** 1,000 concurrent streams

**E2E tests are well within limits.**

### Network Impact

- Minimal: Only log entries are streamed
- Typical: 5-10 KB/minute during test execution
- No overhead on job processing or Firestore

### Latency

- **Typical:** <1 second from log write to stream
- **99th percentile:** <5 seconds
- **Edge case:** Up to 15 seconds during high volume

## Troubleshooting

### Logs not appearing

1. Check credentials: `echo $GOOGLE_APPLICATION_CREDENTIALS`
2. Verify project ID: `gcloud config get-value project`
3. Check filter: Try searching without stream first
4. Verify logs exist: `gcloud logging read 'resource.type="gce_instance"' --limit 5`

### Too many logs

Filter by:
- `test_run_id` - only your test
- `severity` - ERROR/WARNING only
- `stage` - specific pipeline stage

### Logs stopping mid-test

Usually a transient network issue. The context manager will restart streaming.

## Advanced: Custom API Usage

For direct API access without the wrapper:

```python
from google.cloud import logging as cloud_logging

client = cloud_logging.Client()

# List entries with custom filter
entries = client.list_entries(
    filter_='resource.type="gce_instance" AND severity="ERROR"',
    page_size=50,
)

for entry in entries:
    print(entry)
```

## Security Notes

- Credentials are loaded from `GOOGLE_APPLICATION_CREDENTIALS`
- Service account should have `logging.logEntries.list` permission
- Logs may contain sensitive data - don't share with untrusted parties
- Use filters to limit data exposure

## Cost Implications

Google Cloud Logging includes:
- **5 GB/month free** - covers typical E2E test logging
- **Pay per GB** beyond free tier (~$0.50/GB)
- **E2E tests typically use:** <100 MB/month

**Cost for E2E logs: typically $0**

## Next Steps

1. Add log streaming to your test runner
2. Configure project ID and credentials
3. Run E2E tests with `stream_logs=True`
4. Monitor real-time logs in console
5. Use `get_test_logs_summary()` for post-run analysis

## Reference

- [Google Cloud Logging API](https://cloud.google.com/logging/docs/reference/v2/rpc)
- [TailLogEntries API](https://cloud.google.com/logging/docs/reference/v2/rpc/google.logging.v2#google.logging.v2.LoggingServiceV2)
- [Log Filtering](https://cloud.google.com/logging/docs/view/logging-query-language)
- [Python Client Library](https://cloud.google.com/python/docs/reference/logging/latest)
