# Deployment Architecture

## Production Environment

**IMPORTANT: Production job-finder runs on a NAS Docker host, NOT in Google Cloud Run.**

### Infrastructure Overview

- **Location**: Docker host on NAS (Network Attached Storage)
- **Container Management**: Portainer web interface
- **Image Registry**: GitHub Container Registry (ghcr.io/jdubz/job-finder:latest)
- **Database**: Google Cloud Firestore (portfolio database)
- **Logging**: Google Cloud Logging (not local logs)

### Key Points

1. **Docker Host Location**
   - Production containers run on a NAS device
   - Managed through Portainer web interface
   - NOT running in Cloud Run
   - NOT running on local development machine

2. **Container Updates**
   - Images are built locally and pushed to GHCR
   - Portainer pulls latest images from GHCR
   - Use Portainer's "Recreate" with "Pull latest image" to update
   - Watchtower auto-updates enabled (checks every 5 minutes)

3. **Logging Configuration**
   - Logs sent to Google Cloud Logging (not local files)
   - View logs in Cloud Console: https://console.cloud.google.com/logs/query?project=static-sites-257923
   - Filter: `logName="projects/static-sites-257923/logs/job-finder"`
   - Requires `ENABLE_CLOUD_LOGGING=true` environment variable

4. **Environment Variables**
   - Set in Portainer web interface
   - Must include:
     - `ENABLE_CLOUD_LOGGING=true`
     - `ANTHROPIC_API_KEY`
     - `GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/serviceAccountKey.json`
     - `PROFILE_DATABASE_NAME=portfolio` (production) or `portfolio-staging` (staging)
     - `STORAGE_DATABASE_NAME=portfolio` (production) or `portfolio-staging` (staging)

## Staging Environment

Same architecture as production:
- Docker host on NAS
- Managed through Portainer
- Uses `portfolio-staging` Firestore database
- Separate container: `job-finder-staging`

## Deployment Process

### 1. Build and Push Image

```bash
# Build Docker image locally
make docker-build

# Authenticate with GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u jdubz --password-stdin

# Push to registry
make docker-push
```

### 2. Update Container in Portainer

1. Access Portainer web interface on NAS
2. Navigate to Containers
3. Find job-finder container
4. Click "Recreate" with "Pull latest image" checked
5. Container will automatically pull new image and restart

**Or use Watchtower:**
- Watchtower auto-updates are enabled
- Checks for new images every 5 minutes
- Automatically pulls and restarts containers with new images

### 3. Verify Logs

Check Google Cloud Logging:
```
https://console.cloud.google.com/logs/query?project=static-sites-257923
```

Filter:
```
resource.type="global"
logName="projects/static-sites-257923/logs/job-finder"
```

## Common Mistakes to Avoid

❌ **DO NOT** look for containers using `docker ps` on local machine
❌ **DO NOT** try to deploy to Cloud Run (not used)
❌ **DO NOT** expect local log files (logs go to Cloud Logging)
❌ **DO NOT** look for logs in Cloud Run (not running there)

✅ **DO** use Portainer on NAS to manage containers
✅ **DO** check Google Cloud Logging for logs
✅ **DO** push images to GHCR for deployment
✅ **DO** set environment variables in Portainer

## Troubleshooting

### Container Not Logging

1. Check Portainer environment variables include `ENABLE_CLOUD_LOGGING=true`
2. Verify `GOOGLE_APPLICATION_CREDENTIALS` is set correctly
3. Check credentials volume is mounted: `./credentials:/app/credentials:ro`
4. Restart container in Portainer

### Can't Find Container

1. Access Portainer web interface on NAS (not local machine)
2. Check "Containers" section
3. Look for `job-finder-staging` or `job-finder-production`

### Image Not Updating

1. Verify image pushed to GHCR successfully
2. Check Watchtower is running
3. Manually recreate container in Portainer with "Pull latest image"

## Related Documentation

- [Cloud Logging Configuration](./cloud-logging.md) (if exists)
- [Firestore Indexes Deployment](./firestore-indexes-deployment.md)
- [Queue System](../queue-system.md) (if exists)
