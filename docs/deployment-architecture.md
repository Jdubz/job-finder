# Deployment Architecture

## Overview

The job-finder-worker has three distinct environments:
- **Development**: Local Docker containers managed by dev-monitor
- **Staging**: Docker host on NAS with auto-deployment via GitHub Actions + Watchtower
- **Production**: Docker host on NAS with auto-deployment via GitHub Actions + Watchtower

## Production Environment

**IMPORTANT: Production job-finder runs on a NAS Docker host, NOT in Google Cloud Run.**

### Infrastructure Overview

- **Location**: Docker host on NAS (Network Attached Storage)
- **Container Management**: Portainer web interface
- **Image Registry**: GitHub Container Registry (`ghcr.io/jdubz/job-finder-worker:latest`)
- **Database**: Google Cloud Firestore (`portfolio` database)
- **Logging**: Google Cloud Logging with environment labels

### Key Components

1. **Docker Container**
   - Image: `ghcr.io/jdubz/job-finder-worker:latest`
   - Container: `job-finder-production`
   - Auto-restarts: `unless-stopped`
   - Resources: 1.5 CPU, 1.5GB memory

2. **Watchtower Auto-Deployment**
   - Container: `watchtower-job-finder-production`
   - Poll interval: 5 minutes
   - Automatically pulls and deploys new images from GHCR
   - Cleanup: Removes old images after update

3. **Environment Configuration**
   ```yaml
   ENVIRONMENT: production
   ENABLE_QUEUE_MODE: true
   ENABLE_CRON: true
   ENABLE_CLOUD_LOGGING: true
   PROFILE_DATABASE_NAME: portfolio
   STORAGE_DATABASE_NAME: portfolio
   ```

4. **Logging Configuration**
   - Destination: Google Cloud Logging
   - Log name: `projects/static-sites-257923/logs/job-finder`
   - Environment label: `production`
   - Structured JSON format with categories:
     - `[WORKER]` - Worker lifecycle events
     - `[QUEUE:type]` - Queue item processing
     - `[PIPELINE:stage]` - Pipeline stages
     - `[SCRAPE]` - Web scraping operations
     - `[AI:operation]` - AI model operations
     - `[DB:operation]` - Database operations

## Staging Environment

### Infrastructure Overview

- **Location**: Docker host on NAS (same as production)
- **Container Management**: Portainer web interface
- **Image Registry**: GitHub Container Registry (`ghcr.io/jdubz/job-finder-worker:staging`)
- **Database**: Google Cloud Firestore (`portfolio-staging` database)
- **Logging**: Google Cloud Logging with environment labels

### Key Components

1. **Docker Container**
   - Image: `ghcr.io/jdubz/job-finder-worker:staging`
   - Container: `job-finder-staging`
   - Auto-restarts: `unless-stopped`
   - Resources: 1 CPU, 1GB memory

2. **Watchtower Auto-Deployment**
   - Container: `watchtower-job-finder-staging`
   - Poll interval: 3 minutes (more aggressive for faster iteration)
   - Automatically pulls and deploys new images from GHCR
   - Cleanup: Removes old images after update

3. **Environment Configuration**
   ```yaml
   ENVIRONMENT: staging
   ENABLE_QUEUE_MODE: true
   ENABLE_CRON: false  # Manual queue submissions only
   ENABLE_CLOUD_LOGGING: true
   PROFILE_DATABASE_NAME: portfolio-staging
   STORAGE_DATABASE_NAME: portfolio-staging
   ```

## Development Environment

### Infrastructure Overview

- **Location**: Local development machine
- **Container Management**: dev-monitor (in job-finder-app-manager repo)
- **Image**: Built locally from source
- **Database**: Firebase Emulator (Firestore on `localhost:8080`)
- **Logging**: Local file system (`dev-monitor/logs/queue_worker.log`)

### Key Components

1. **App-Monitor**
   - Location: `job-finder-app-manager/dev-monitor`
   - Manages: Firebase Emulators, Python worker, Frontend, Backend
   - Worker: Docker container built from local source
   - Port: `http://localhost:5174` (web UI)

2. **Environment Configuration**
   ```yaml
   ENVIRONMENT: development
   ENABLE_QUEUE_MODE: true
   ENABLE_CRON: false
   ENABLE_CLOUD_LOGGING: false
   FIRESTORE_EMULATOR_HOST: host.docker.internal:8080
   ```

3. **Local Development Workflow**
   ```bash
   # Start all services including worker
   cd dev-monitor
   make dev-monitor

   # View worker logs
   tail -f logs/queue_worker.log

   # Restart worker after code changes
   make restart-worker

   # Rebuild worker from scratch
   make rebuild-worker
   ```

## CI/CD Pipeline

### GitHub Actions Workflows

#### Staging Deployment (`staging` branch)

**Workflow**: `.github/workflows/docker-build-push-staging.yml`

**Trigger**: Push to `staging` branch

**Steps**:
1. Checkout code
2. Build Docker image for `linux/amd64` and `linux/arm64`
3. Push to GHCR with tags:
   - `ghcr.io/jdubz/job-finder-worker:staging`
   - `ghcr.io/jdubz/job-finder-worker:staging-<sha>`
4. Watchtower detects new image within 3 minutes
5. Watchtower automatically pulls and deploys to staging

**Image Tags**:
- `staging` - Latest staging build (used by Portainer)
- `staging-<sha>` - Git commit SHA for traceability

#### Production Deployment (`main` branch)

**Workflow**: `.github/workflows/docker-build-push.yml`

**Trigger**: Push to `main` branch

**Steps**:
1. Checkout code
2. Build Docker image for `linux/amd64` and `linux/arm64`
3. Push to GHCR with tags:
   - `ghcr.io/jdubz/job-finder-worker:latest`
   - `ghcr.io/jdubz/job-finder-worker:production`
4. Watchtower detects new image within 5 minutes
5. Watchtower automatically pulls and deploys to production

**Image Tags**:
- `latest` - Latest production build (used by Portainer)
- `production` - Alias for latest production
- Git SHA tags for traceability

### Deployment Timeline

**Staging**:
- Code push to `staging` → GitHub Actions build (1-2 min) → Watchtower detect (0-3 min) → Total: 1-5 minutes

**Production**:
- Code push to `main` → GitHub Actions build (1-2 min) → Watchtower detect (0-5 min) → Total: 1-7 minutes

## Portainer Configuration

### Stack Configuration

Both staging and production use docker-compose stacks in Portainer.

**CRITICAL**: Ensure Portainer stacks reference the correct image names:
- Staging: `ghcr.io/jdubz/job-finder-worker:staging`
- Production: `ghcr.io/jdubz/job-finder-worker:latest`

**Note**: Early deployments may have used `ghcr.io/jdubz/job-finder` (without `-worker`). This prevents Watchtower from detecting new builds. Update stack configurations if needed.

### Watchtower Labels

Containers must have these labels for Watchtower to manage them:
```yaml
labels:
  - "com.centurylinklabs.watchtower.enable=true"
  - "environment=staging"  # or "production"
```

### Volume Mounts

**Required**:
- `/srv/.../credentials:/app/credentials:ro` - Service account key
- `/srv/.../config:/app/config:ro` - Configuration files
- `/srv/.../logs:/app/logs` - Log file output (optional, Cloud Logging is primary)

## Monitoring and Logging

### Google Cloud Logging

All environments (staging and production) send structured logs to Google Cloud Logging.

**Access Logs**:
```bash
# Staging logs
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" \
  AND labels.environment="staging"' \
  --limit 20 --freshness 1h

# Production logs
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" \
  AND labels.environment="production"' \
  --limit 20 --freshness 1h

# Filter by category
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder" \
  AND labels.environment="staging" \
  AND textPayload:"[WORKER]"' \
  --limit 10

# Tail real-time logs
gcloud logging tail 'logName="projects/static-sites-257923/logs/job-finder" \
  AND labels.environment="staging"'
```

**Log Categories**:
- `[WORKER]` - Worker status (started, idle, stopped, found_pending_items, no_pending_items, batch_completed)
- `[QUEUE:COMPANY]` - Company pipeline processing
- `[QUEUE:JOB]` - Job pipeline processing
- `[QUEUE:SOURCE_DISCOVERY]` - Job source discovery
- `[PIPELINE:FETCH]` - Fetch stage (company/job)
- `[PIPELINE:EXTRACT]` - Extract stage (company)
- `[PIPELINE:ANALYZE]` - Analyze stage (company/job)
- `[PIPELINE:SAVE]` - Save stage (company/job)
- `[SCRAPE]` - Web scraping operations
- `[AI:MATCH]` - AI job matching
- `[AI:EXTRACT]` - AI data extraction
- `[DB:CREATE]` - Database create operations
- `[DB:UPDATE]` - Database update operations
- `[DB:QUERY]` - Database query operations

### Enhanced Queue Worker Logging (2025-10-22)

The queue worker now logs detailed information on **every queue check** (every 60 seconds):

**When items are found**:
```json
{
  "action": "found_pending_items",
  "details": {
    "iteration": 5,
    "items_count": 3,
    "total_processed": 12
  }
}
```

**Each item details**:
```
[QUEUE] Item 1/3: {
  "position": 1,
  "item_id": "abc123",
  "type": "COMPANY",
  "url": "https://example.com...",
  "company": "Example Corp",
  "sub_task": "FETCH"
}
```

**When queue is empty**:
```json
{
  "action": "no_pending_items",
  "details": {
    "iteration": 6,
    "total_processed": 15
  }
}
```

This provides real-time visibility into queue activity without needing to wait for processing events.

### Development Logs

Local development logs to file system instead of Cloud Logging:

```bash
# View worker logs
tail -f dev-monitor/logs/queue_worker.log

# Or via dev-monitor web UI
open http://localhost:5174
```

## Deployment Process

### Automated Deployment (Recommended)

**Staging**:
1. Commit changes to feature branch
2. Create PR to `staging` branch
3. Merge PR (triggers GitHub Actions)
4. Wait 1-5 minutes for auto-deployment
5. Verify in Google Cloud Logging

**Production**:
1. Test thoroughly in staging
2. Create PR from `staging` to `main`
3. Merge PR (triggers GitHub Actions)
4. Wait 1-7 minutes for auto-deployment
5. Verify in Google Cloud Logging

### Manual Deployment (Emergency)

If Watchtower fails or immediate deployment needed:

```bash
# Via Portainer UI
1. Navigate to Containers
2. Select job-finder-staging or job-finder-production
3. Click "Recreate" with "Pull latest image" enabled
4. Confirm

# Via SSH to NAS
ssh user@nas
docker pull ghcr.io/jdubz/job-finder-worker:staging
docker restart job-finder-staging
```

## Troubleshooting

### Watchtower Not Auto-Deploying

**Symptoms**: New images pushed but container not updating

**Checks**:
1. Verify Watchtower container is running in Portainer
2. Check Portainer stack references correct image name:
   - ❌ `ghcr.io/jdubz/job-finder:staging` (wrong)
   - ✅ `ghcr.io/jdubz/job-finder-worker:staging` (correct)
3. Verify container has Watchtower labels:
   ```yaml
   labels:
     - "com.centurylinklabs.watchtower.enable=true"
   ```
4. Check Watchtower logs in Portainer
5. Manually recreate container to pull latest image

**Fix**: Update Portainer stack configuration with correct image name and recreate stack.

### Container Not Logging to Cloud Logging

**Symptoms**: No logs appearing in Google Cloud Logging console

**Checks**:
1. Verify `ENABLE_CLOUD_LOGGING=true` in Portainer environment
2. Check `GOOGLE_APPLICATION_CREDENTIALS` points to valid file
3. Verify credentials volume mounted: `./credentials:/app/credentials:ro`
4. Check service account has `roles/logging.logWriter` permission
5. View container stdout/stderr in Portainer logs

### Development Worker Not Starting

**Symptoms**: Worker fails to start in dev-monitor

**Checks**:
1. Verify Firebase Emulators running (`http://localhost:4000`)
2. Check Firestore emulator on port 8080
3. Verify `FIRESTORE_EMULATOR_HOST` set correctly
4. Check worker log: `tail -f dev-monitor/logs/queue_worker.log`
5. Rebuild worker: `make rebuild-worker`

### Pipeline Items Not Processing

**Symptoms**: Queue items stuck in pending state

**Checks**:
1. Check worker status in Cloud Logging:
   ```bash
   gcloud logging read 'textPayload:"[WORKER]"' --limit 5
   ```
2. Look for "found_pending_items" or "no_pending_items" logs
3. Check for error messages in pipeline stages
4. Verify database connectivity
5. Check API keys (ANTHROPIC_API_KEY) are set

**Recent Fix (2025-10-22)**: Loop prevention was incorrectly blocking granular pipeline progression (FETCH → EXTRACT). Fixed by disabling circular dependency check (Check 2) since duplicate work is prevented by Check 3 and Check 4.

## Environment Comparison

| Feature | Development | Staging | Production |
|---------|------------|---------|------------|
| **Location** | Local machine | NAS Docker | NAS Docker |
| **Management** | dev-monitor | Portainer | Portainer |
| **Image** | Local build | GHCR staging | GHCR latest |
| **Database** | Emulator | portfolio-staging | portfolio |
| **Logging** | File system | Cloud Logging | Cloud Logging |
| **Auto-deploy** | Manual | Watchtower (3 min) | Watchtower (5 min) |
| **CRON** | Disabled | Disabled | Enabled |
| **CPU** | Varies | 1 CPU | 1.5 CPU |
| **Memory** | Varies | 1GB | 1.5GB |

## Related Documentation

- [Cloud Logging Design](./CLOUD_LOGGING_DESIGN.md) - Detailed logging architecture
- [Staging vs Production](./STAGING_VS_PRODUCTION.md) - Environment differences
- [Portainer Deployment Guide](./PORTAINER_DEPLOYMENT_GUIDE.md) - Step-by-step Portainer setup
- [Development Workflow](./development/DEV_WORKFLOW.md) - Local development guide
- [Loop Prevention](./LOOP_PREVENTION_SUMMARY.md) - Queue loop prevention design
