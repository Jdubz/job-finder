# Development Workflow

This document describes the complete development workflow for the job-finder-worker project, from local development to production deployment.

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Development Cycle](#development-cycle)
3. [Testing](#testing)
4. [Code Quality](#code-quality)
5. [Deployment Workflow](#deployment-workflow)
6. [Troubleshooting](#troubleshooting)

## Local Development Setup

### Prerequisites

```bash
# Required software
- Python 3.12+
- Docker & Docker Compose
- Node.js 18+ (for dev-monitor)
- Git
- gcloud CLI (for viewing staging/production logs)
```

### Using App-Monitor (Recommended)

The dev-monitor is the **primary method** for local development. It manages all services including the Python worker via Docker.

**Location**: `job-finder-app-manager/dev-monitor`

**Services Managed**:
- Firebase Emulators (Firestore, Functions, Auth)
- Python Worker (Docker container)
- Frontend development server (React)
- Backend Firebase Functions (TypeScript)

#### Starting App-Monitor

```bash
# Navigate to dev-monitor directory
cd ../dev-monitor

# Start all services
make dev-monitor

# Or start specific services
make start-emulators  # Firebase only
make start-worker     # Worker only
make start-frontend   # Frontend only
make start-backend    # Backend only
```

#### Accessing Services

- **App-Monitor UI**: http://localhost:5174
- **Firebase Emulator UI**: http://localhost:4000
- **Firestore Emulator**: localhost:8080
- **Frontend**: http://localhost:3000
- **Backend Functions**: http://localhost:5001

#### Worker Logs

```bash
# View worker logs in real-time
tail -f dev-monitor/logs/queue_worker.log

# Or via the dev-monitor web UI
open http://localhost:5174
```

#### Restarting After Code Changes

```bash
# Rebuild and restart worker after Python changes
make restart-worker

# Rebuild from scratch (if dependencies changed)
make rebuild-worker

# Restart frontend after React changes (auto-reload usually handles this)
make restart-frontend

# Restart backend after TypeScript changes
make restart-backend
```

### Manual Python Development (Alternative)

For running tests or scripts outside of dev-monitor:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Set environment variables
export GOOGLE_APPLICATION_CREDENTIALS="credentials/serviceAccountKey.json"
export STORAGE_DATABASE_NAME="portfolio-staging"
export ENVIRONMENT="development"

# Run tests
pytest

# Run specific test
pytest tests/test_filters.py -v

# Run with coverage
pytest --cov=src/job_finder --cov-report=html
```

## Development Cycle

### 1. Create Feature Branch

```bash
# Ensure you're on staging
git checkout staging
git pull origin staging

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Develop Locally

```bash
# Start dev-monitor
cd ../dev-monitor
make dev-monitor

# Make changes in job-finder-worker repo
cd ../job-finder-worker

# Test changes by restarting worker
cd ../dev-monitor
make restart-worker

# View logs
tail -f logs/queue_worker.log
```

### 3. Write Tests

```bash
# Write tests for new functionality
# Location: tests/

# Run tests
pytest tests/

# Run specific test file
pytest tests/queue/test_processor.py -v

# Run with coverage
pytest --cov=src/job_finder --cov-report=html
```

### 4. Code Quality Checks

```bash
# Format code with black
black src/ tests/

# Check formatting without changes
black --check src/ tests/

# Type checking
mypy src/

# Run linter
flake8 src/ tests/
```

### 5. Commit Changes

```bash
# Stage changes
git add .

# Commit (pre-commit hook runs black)
git commit -m "feat: add new feature"

# Push to feature branch
git push origin feature/your-feature-name
```

## Testing

### Unit Tests

```bash
# Run all unit tests
pytest

# Run specific test module
pytest tests/queue/test_processor.py

# Run specific test function
pytest tests/queue/test_processor.py::test_process_company_fetch -v

# Run tests matching pattern
pytest -k "company" -v

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src/job_finder --cov-report=term-missing
```

### Integration Tests

```bash
# Run integration tests
pytest tests/queue/test_integration.py -v

# Run smoke tests
pytest tests/smoke/ -v
```

### Testing Against Staging Data

```bash
# Use staging database for testing
export STORAGE_DATABASE_NAME="portfolio-staging"

# Run tests
pytest tests/
```

## Code Quality

### Pre-Commit Hooks

Pre-commit hooks automatically run when you commit:

```bash
# Hooks run automatically on commit
git commit -m "your message"

# Manually run pre-commit checks
.husky/pre-commit

# Black formatting
black src/ tests/
```

### Pre-Push Hooks

Pre-push hooks run before pushing to remote:

```bash
# Hooks run automatically on push
git push origin feature-branch

# Manually run pre-push checks
.husky/pre-push

# Checks performed:
# - mypy type checking
# - pytest (all tests must pass)
```

### Manual Quality Checks

```bash
# Format code
black src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/

# Run all checks
black src/ tests/ && mypy src/ && pytest
```

## Deployment Workflow

### Development → Staging → Production

```
Local Dev (dev-monitor)
  ↓ PR to staging
Staging (auto-deploy via Watchtower in 3 min)
  ↓ Verify + PR to main
Production (auto-deploy via Watchtower in 5 min)
```

### 1. Deploy to Staging

```bash
# Ensure all tests pass
pytest

# Push to staging branch (triggers GitHub Actions)
git checkout staging
git merge feature/your-feature-name
git push origin staging

# GitHub Actions automatically:
# 1. Runs tests
# 2. Runs code quality checks
# 3. Builds Docker image
# 4. Pushes to ghcr.io/jdubz/job-finder-worker:staging
# 5. Watchtower detects and deploys within 3 minutes
```

### 2. Verify in Staging

```bash
# View staging logs
gcloud logging tail 'logName="projects/static-sites-257923/logs/job-finder" \
  AND labels.environment="staging"'

# Or read recent logs
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" \
  AND labels.environment="staging"' \
  --limit 20 --freshness 10m

# Check worker status
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" \
  AND labels.environment="staging" \
  AND textPayload:"[WORKER]"' \
  --limit 5
```

### 3. Deploy to Production

```bash
# After verifying staging works correctly
git checkout main
git merge staging
git push origin main

# GitHub Actions automatically:
# 1. Runs tests
# 2. Runs code quality checks
# 3. Builds Docker image
# 4. Pushes to ghcr.io/jdubz/job-finder-worker:latest
# 5. Watchtower detects and deploys within 5 minutes
```

### 4. Verify in Production

```bash
# View production logs
gcloud logging tail 'logName="projects/static-sites-257923/logs/job-finder" \
  AND labels.environment="production"'

# Check worker status
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" \
  AND labels.environment="production" \
  AND textPayload:"[WORKER]"' \
  --limit 5
```

## Monitoring Queue Activity

### Enhanced Logging (Added 2025-10-22)

The queue worker now logs detailed information on **every queue check** (every 60 seconds).

**Monitor staging queue**:
```bash
# Watch for queue activity
gcloud logging tail 'logName="projects/static-sites-257923/logs/job-finder" \
  AND labels.environment="staging" \
  AND (textPayload:"found_pending_items" OR textPayload:"no_pending_items")'

# View queue items being processed
gcloud logging tail 'logName="projects/static-sites-257923/logs/job-finder" \
  AND labels.environment="staging" \
  AND textPayload:"[QUEUE] Item"'
```

**Monitor local queue** (dev-monitor):
```bash
# Watch worker log
tail -f dev-monitor/logs/queue_worker.log

# Filter for queue activity
tail -f dev-monitor/logs/queue_worker.log | grep -E "(found_pending_items|no_pending_items|\[QUEUE\])"
```

## Troubleshooting

### App-Monitor Won't Start

**Symptoms**: `make dev-monitor` fails or services don't start

**Solutions**:
```bash
# Check if ports are in use
lsof -i :4000  # Firebase Emulator UI
lsof -i :8080  # Firestore Emulator
lsof -i :3000  # Frontend
lsof -i :5001  # Backend Functions
lsof -i :5174  # App-Monitor UI

# Stop conflicting processes
make stop-all

# Restart from scratch
make clean
make dev-monitor
```

### Worker Not Connecting to Emulator

**Symptoms**: Worker shows connection errors or "ALTS creds" warnings

**Solutions**:
```bash
# Check Firestore emulator is running
curl http://localhost:8080

# Check worker environment
# Should have: FIRESTORE_EMULATOR_HOST=host.docker.internal:8080

# Restart worker
make restart-worker

# Check worker logs
tail -f dev-monitor/logs/queue_worker.log
```

### Tests Failing in CI but Passing Locally

**Symptoms**: GitHub Actions tests fail, but `pytest` passes locally

**Solutions**:
```bash
# Run tests with same Python version as CI
python3.12 -m pytest

# Run tests in clean environment
deactivate  # Exit venv
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
pytest

# Check for missing dependencies
pip list
```

### Staging Deployment Not Working

**Symptoms**: Push to staging doesn't trigger deployment or Watchtower doesn't update

**Checks**:
```bash
# 1. Verify GitHub Actions completed
gh run list --repo Jdubz/job-finder-worker --branch staging --limit 3

# 2. Check if image was pushed
# Visit: https://github.com/Jdubz/job-finder-worker/pkgs/container/job-finder-worker

# 3. Verify Portainer stack has correct image name
# Should be: ghcr.io/jdubz/job-finder-worker:staging
# NOT: ghcr.io/jdubz/job-finder:staging

# 4. Check Watchtower is running
# In Portainer: Containers → watchtower-job-finder-staging

# 5. Manually trigger update if needed
# In Portainer: Containers → job-finder-staging → Recreate (with "Pull latest image")
```

### Loop Prevention Bug (Fixed 2025-10-22)

**Symptoms**: Company pipeline stuck after FETCH, logs show "Circular dependency detected"

**Cause**: Loop prevention incorrectly blocked granular pipeline progression (same URL with different sub-tasks)

**Fix Applied**: Disabled Check 2 (circular dependency) in `src/job_finder/queue/manager.py:683-687`

**Verification**:
```bash
# Check if company pipelines are progressing
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" \
  AND labels.environment="staging" \
  AND (textPayload:"COMPANY_FETCH" OR textPayload:"COMPANY_EXTRACT")' \
  --limit 10
```

## Best Practices

### 1. Always Use App-Monitor for Local Development

❌ **Don't**: Start worker manually with `python scripts/workers/queue_worker.py`
✅ **Do**: Use `make dev-monitor` to start all services together

### 2. Test Before Pushing

❌ **Don't**: Push untested code to staging
✅ **Do**: Run `pytest` locally first, verify in dev-monitor

### 3. Monitor Staging Before Production

❌ **Don't**: Deploy to production immediately after merging to staging
✅ **Do**: Wait 3-5 minutes, verify staging logs, then deploy to production

### 4. Use Structured Logging

❌ **Don't**: Use print() statements
✅ **Do**: Use slogger with appropriate categories:
```python
from job_finder.logging_config import get_structured_logger
slogger = get_structured_logger(__name__)

# Worker status
slogger.worker_status("started", {"poll_interval": 60})

# Database activity
slogger.database_activity("query", "job-queue", "fetching pending items")

# Pipeline activity
slogger.pipeline_activity("FETCH", "company", "success", {"pages": 3})
```

### 5. Clean Up Feature Branches

```bash
# After PR merged to staging
git checkout staging
git pull origin staging
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

## Related Documentation

- [Deployment Architecture](../deployment-architecture.md) - Infrastructure and CI/CD details
- [Local Testing Guide](../guides/local-testing.md) - Testing strategies
- [Cloud Logging Design](../CLOUD_LOGGING_DESIGN.md) - Logging architecture
- [Loop Prevention](../LOOP_PREVENTION_SUMMARY.md) - Queue safety mechanisms
