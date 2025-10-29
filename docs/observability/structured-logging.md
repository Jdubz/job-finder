# Structured Logging in job-finder-worker

**Formatter:** `src/job_finder/logging/json_formatter.py`  
**Logger:** `src/job_finder/logging/structured_logger.py`

## Local Development
- Local runs emit JSON entries to stdout and configured log files.
- App Monitor tails `logs/worker.log` for real-time viewing.
- Ensure the virtualenv uses the latest worker package (run `pip install -e .` after schema changes).

## Example Output
```json
{
  "severity": "INFO",
  "timestamp": "2025-10-21T10:30:45.123Z",
  "environment": "staging",
  "category": "queue",
  "action": "processing",
  "message": "Queue item processing",
  "queueItemId": "abc123",
  "details": { "duration": 1234 }
}
```

## Configuration Notes
- `StructuredLogger` routes to console, file, and Cloud Logging handlers.
- Labels such as `service`, `environment`, and `queueItemId` are added automatically.
- Update `logging_config.py` if new handlers or sinks are required.

## Verification Checklist
1. Run `pytest tests/logging` to validate log serialization.
2. Tail `logs/worker.log` in App Monitor and confirm queue events appear.
3. In staging, inspect Google Cloud Logging for entries with `service=worker`.
