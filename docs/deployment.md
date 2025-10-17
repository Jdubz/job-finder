# Deployment Guide

Complete guide for deploying Job Finder in production using Docker and Portainer.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Portainer Deployment](#portainer-deployment)
- [Environment Configuration](#environment-configuration)
- [Auto-Updates with Watchtower](#auto-updates-with-watchtower)
- [Monitoring & Logs](#monitoring--logs)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

Get Job Finder running in 5 minutes:

### 1. Prepare Directories

```bash
# On your Docker host (e.g., bignasty.local)
mkdir -p /path/to/job-finder/{credentials,config,logs,data}
cd /path/to/job-finder
```

### 2. Add Credentials

```bash
# Copy Firebase service account key
cp /path/to/serviceAccountKey.json credentials/
chmod 600 credentials/serviceAccountKey.json

# Create .env file with API keys
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/serviceAccountKey.json
TZ=America/Los_Angeles
EOF
```

### 3. Deploy

**Option A: Docker Compose (CLI)**
```bash
# Download compose file
wget https://raw.githubusercontent.com/Jdubz/job-finder/main/docker-compose.yml

# Start containers
docker-compose up -d
```

**Option B: Portainer (Web UI)**
- See [Portainer Deployment](#portainer-deployment) section below

### 4. Verify

```bash
# Check logs
docker logs -f job-finder

# Or in Portainer: Containers → job-finder → Logs
```

---

## Prerequisites

### Required

1. **Docker Host** with Docker and Docker Compose installed
2. **Firebase Service Account JSON** for Firestore access
   - Download from [Firebase Console](https://console.firebase.google.com/) → Project Settings → Service Accounts
3. **Anthropic API Key** for Claude AI
   - Get from [Anthropic Console](https://console.anthropic.com/)
4. **Portainer** (optional but recommended for easier management)
   - Install: https://docs.portainer.io/start/install

### Optional

- OpenAI API Key (for GPT-4 instead of Claude)
- Adzuna API credentials (for additional job sources)

---

## Portainer Deployment

Detailed walkthrough for deploying via Portainer web interface.

### Step 1: Set Up Directory Structure

SSH into your Docker host:

```bash
ssh user@your-docker-host

# Create directory structure
sudo mkdir -p /opt/job-finder-staging/{credentials,config,logs,data}
sudo mkdir -p /opt/job-finder-production/{credentials,config,logs,data}

# Set ownership
sudo chown -R $USER:$USER /opt/job-finder-staging /opt/job-finder-production

# Secure credentials directories
chmod 700 /opt/job-finder-staging/credentials /opt/job-finder-production/credentials
chmod 755 /opt/job-finder-staging/{config,logs,data} /opt/job-finder-production/{config,logs,data}
```

### Step 2: Upload Credentials

```bash
# Copy Firebase service account JSON
scp /path/to/serviceAccountKey.json user@your-docker-host:/opt/job-finder-staging/credentials/
ssh user@your-docker-host "chmod 600 /opt/job-finder-staging/credentials/serviceAccountKey.json"

# Copy to production if deploying both environments
ssh user@your-docker-host "cp /opt/job-finder-staging/credentials/serviceAccountKey.json /opt/job-finder-production/credentials/ && chmod 600 /opt/job-finder-production/credentials/serviceAccountKey.json"
```

### Step 3: Add GitHub Container Registry

1. **Create GitHub Personal Access Token:**
   - Go to: https://github.com/settings/tokens/new
   - Note: "Portainer GHCR Access"
   - Scopes: Select `read:packages`
   - Generate token and copy it

2. **Add Registry in Portainer:**
   - Navigate to: **Registries** → **Add registry**
   - Provider: **Custom registry**
   - Name: `GitHub Container Registry`
   - Registry URL: `ghcr.io`
   - Authentication: ✅ Enable
   - Username: Your GitHub username
   - Password: Paste your PAT token
   - Click **Add registry**

### Step 4: Deploy Stack

1. **Navigate to Stacks:**
   - Portainer → **Stacks** → **Add stack**

2. **Configure Stack:**
   - Name: `job-finder-staging` (or `job-finder-production`)
   - Build method: **Web editor**
   - Paste the appropriate docker-compose content (see below)

3. **Set Environment Variables:**
   Scroll to **Environment variables** and add:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-api-key-here
   OPENAI_API_KEY=  (optional)
   ```

4. **Deploy:**
   - Click **Deploy the stack**
   - Wait for containers to start (1-2 minutes)

#### Staging Docker Compose

```yaml
services:
  job-finder:
    image: ghcr.io/jdubz/job-finder:latest
    container_name: job-finder-staging
    restart: unless-stopped

    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/serviceAccountKey.json
      - ENVIRONMENT=staging
      - PROFILE_DATABASE_NAME=portfolio-staging
      - STORAGE_DATABASE_NAME=portfolio-staging
      - CONFIG_PATH=/app/config/config.yaml
      - LOG_FILE=/app/logs/scheduler.log
      - TZ=America/Los_Angeles

    volumes:
      - /opt/job-finder-staging/credentials:/app/credentials:ro
      - /opt/job-finder-staging/config:/app/config:ro
      - /opt/job-finder-staging/logs:/app/logs
      - /opt/job-finder-staging/data:/app/data

    labels:
      - "com.centurylinklabs.watchtower.enable=true"
      - "environment=staging"

    networks:
      - job-finder-network

    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 5m
      timeout: 10s
      retries: 3
      start_period: 30s

  watchtower:
    image: containrrr/watchtower:latest
    container_name: watchtower-job-finder-staging
    restart: unless-stopped

    environment:
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_POLL_INTERVAL=300
      - WATCHTOWER_LABEL_ENABLE=true
      - TZ=America/Los_Angeles

    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

    networks:
      - job-finder-network

networks:
  job-finder-network:
    driver: bridge
```

#### Production Docker Compose

For production, change:
- `container_name: job-finder-production`
- `ENVIRONMENT=production`
- `PROFILE_DATABASE_NAME=portfolio`
- `STORAGE_DATABASE_NAME=portfolio`
- `CONFIG_PATH=/app/config/config.production.yaml`
- Volume paths: `/opt/job-finder-production/...`
- Resource limits: `cpus: '2.0'`, `memory: 2G`

### Step 5: Verify Deployment

**Check Container Status:**
1. Portainer → **Containers**
2. Verify `job-finder-staging` shows **running** (green status)

**Check Logs:**
1. Click container → **Logs** tab
2. Look for:
   ```
   ✅ Connected to Firestore database: portfolio-staging
   ✅ Profile loaded successfully
   ✅ Starting job search...
   ```

**Check Firestore:**
1. Open [Firebase Console](https://console.firebase.google.com/)
2. Navigate to Firestore Database → `portfolio-staging`
3. View collection: `job-matches`
4. Verify documents are being created

---

## Environment Configuration

Job Finder supports separate staging and production environments.

### Staging Environment

- **Purpose:** Testing and development
- **Database:** `portfolio-staging`
- **Config:** `config/config.yaml`
- **Safe for:** Experimentation, testing changes
- **Container:** `job-finder-staging`

### Production Environment

- **Purpose:** Live job searches
- **Database:** `portfolio`
- **Config:** `config/config.production.yaml`
- **Container:** `job-finder-production`

### Configuration Methods

Environment variables override config file settings (in order of precedence):

1. **Environment Variables** (highest priority)
   ```yaml
   environment:
     - PROFILE_DATABASE_NAME=portfolio-staging
     - STORAGE_DATABASE_NAME=portfolio-staging
   ```

2. **Config File**
   ```yaml
   profile:
     firestore:
       database_name: "portfolio-staging"
   storage:
     database_name: "portfolio-staging"
   ```

3. **Code Defaults** (fallback)

**See [environments.md](./environments.md) for detailed configuration guide.**

---

## Auto-Updates with Watchtower

Watchtower automatically updates your container when new images are pushed to GitHub Container Registry.

### How It Works

1. **GitHub Actions:** On merge to `main`, builds and pushes new image
2. **Watchtower:** Polls registry every 5 minutes for new images
3. **Auto-Update:** Pulls new image and restarts container
4. **Cleanup:** Removes old images to save space

### Configuration

Watchtower is included in the stack and configured to:
- Check every 5 minutes (`WATCHTOWER_POLL_INTERVAL=300`)
- Only update containers with label `com.centurylinklabs.watchtower.enable=true`
- Clean up old images (`WATCHTOWER_CLEANUP=true`)

### Manual Update

If not using Watchtower or want to force update:

**Via Portainer:**
1. Containers → Select container → **Recreate**
2. Enable **Pull latest image**

**Via CLI:**
```bash
docker pull ghcr.io/jdubz/job-finder:latest
docker restart job-finder-staging
```

---

## Monitoring & Logs

### View Logs in Portainer

1. **Containers** → Click container → **Logs**
2. Select number of lines (100, 500, all)
3. Enable **Auto-refresh** for real-time viewing

### View Logs via CLI

```bash
# Follow live logs
docker logs -f job-finder-staging

# Last 100 lines
docker logs --tail 100 job-finder-staging

# Logs since 1 hour ago
docker logs --since 1h job-finder-staging
```

### Log Files

Logs are persisted in mounted volumes:

```bash
# Scheduler logs
tail -f /opt/job-finder-staging/logs/scheduler.log

# Cron logs (inside container)
docker exec job-finder-staging tail -f /var/log/cron.log
```

### Google Cloud Logging (Optional)

Enable Cloud Logging to view logs in Google Cloud Console:

```yaml
environment:
  - ENABLE_CLOUD_LOGGING=true
```

**See [cloud-logging.md](./cloud-logging.md) for setup and usage.**

### Check Firestore Job Matches

1. Open [Firebase Console](https://console.firebase.google.com/)
2. Firestore Database → Select database (`portfolio-staging` or `portfolio`)
3. View collection: `job-matches`

Each document includes:
- Job details (title, company, description, URL)
- AI match analysis (score, skills, priorities)
- Resume intake data
- Tracking fields (applied, status)

### Container Health Check

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' job-finder-staging
```

---

## Troubleshooting

### Container Logs are Empty

**Problem:** Container appears running but logs are empty in Portainer

**Cause:** Container is running cron in background, waiting for next scheduled run (every 6 hours at 00:00, 06:00, 12:00, 18:00). Between runs, there's no output.

**Solution:** Check the detailed startup logs that show:
- Container start time and timezone
- Cron schedule
- Next scheduled run time
- Cron daemon status

**Manual trigger for testing:**
```bash
docker exec job-finder-staging /app/docker/run-now.sh
```

This runs a job search immediately and shows output in the logs.

### Container Won't Start

**Check logs:**
```bash
docker logs job-finder-staging
```

**Common issues:**
- Missing environment variables (check `ANTHROPIC_API_KEY`)
- Invalid credentials path
- Configuration file errors
- Firestore connection issues

**Fix:**
1. Verify environment variables in Portainer stack
2. Check credentials file exists and is readable
3. Verify config file is valid YAML

### Cannot Pull Image

**Error:** `unauthorized: authentication required`

**Fix:**
1. Verify GitHub Container Registry is added in Portainer
2. Check PAT token has `read:packages` permission
3. Test manually:
   ```bash
   docker login ghcr.io -u YOUR_USERNAME -p YOUR_PAT
   docker pull ghcr.io/jdubz/job-finder:latest
   ```

### No Jobs Being Found

**Check scheduler logs:**
```bash
docker exec job-finder-staging tail -f /var/log/cron.log
```

**Verify cron is running:**
```bash
docker exec job-finder-staging ps aux | grep cron
```

**Manually trigger search:**
```bash
docker exec job-finder-staging python run_job_search.py
```

### Authentication Errors

**Firebase/Firestore:**
- Verify `GOOGLE_APPLICATION_CREDENTIALS` path is correct
- Check service account JSON is valid
- Ensure service account has Firestore permissions

**Anthropic API:**
- Verify `ANTHROPIC_API_KEY` is set
- Check API key is valid and has credits
- Review rate limits

### Firestore Connection Failed

**Check environment:**
```bash
docker exec job-finder-staging env | grep -E 'GOOGLE|ANTHROPIC'
```

**Check credentials mounted:**
```bash
docker exec job-finder-staging ls -la /app/credentials/
docker exec job-finder-staging cat /app/credentials/serviceAccountKey.json | head -5
```

**Verify service account permissions:**
1. Go to [IAM & Admin](https://console.cloud.google.com/iam-admin/iam)
2. Find service account
3. Ensure roles include: **Cloud Datastore User** or **Firebase Admin**

### Auto-Update Not Working

**Check Watchtower logs:**
```bash
docker logs watchtower-job-finder-staging
```

**Verify label is set:**
```bash
docker inspect job-finder-staging | grep watchtower
```

**Manually trigger Watchtower:**
```bash
docker exec watchtower-job-finder-staging watchtower --run-once
```

### Performance Issues

**Check resource usage:**
```bash
docker stats job-finder-staging
```

**Adjust resource limits:**
Edit stack and increase limits:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Increase CPU
      memory: 2G       # Increase memory
```

---

## Advanced Configuration

### Custom Cron Schedule

Default: Every 6 hours at minute 0 (12am, 6am, 12pm, 6pm)

**To customize:**

1. Edit `docker/crontab` in repository
2. Rebuild Docker image
3. Push to trigger auto-update

Example schedules:
```cron
# Every 4 hours
0 */4 * * * root cd /app && /usr/local/bin/python scripts/workers/scripts/workers/scheduler.py >> /var/log/cron.log 2>&1

# Specific times (6am, 2pm, 10pm)
0 6,14,22 * * * root cd /app && /usr/local/bin/python scripts/workers/scripts/workers/scheduler.py >> /var/log/cron.log 2>&1

# Daily at 8am
0 8 * * * root cd /app && /usr/local/bin/python scripts/workers/scripts/workers/scheduler.py >> /var/log/cron.log 2>&1
```

### Multiple Users/Profiles

To run searches for multiple users:

1. Create separate stacks per user
2. Mount different config files
3. Use different Firestore user IDs in config

### Resource Limits

Adjust based on your needs:

**Light usage** (1-2 searches/day):
```yaml
limits:
  cpus: '0.5'
  memory: 512M
```

**Heavy usage** (hourly searches):
```yaml
limits:
  cpus: '2.0'
  memory: 2G
```

---

## Security Best Practices

1. **Never commit credentials:**
   - `.env` files are in `.gitignore`
   - Service account JSON is in `.gitignore`
   - Use Portainer secrets or environment variables

2. **Use read-only mounts:**
   - Credentials: `:ro`
   - Config: `:ro`

3. **Restrict permissions:**
   ```bash
   chmod 600 /opt/job-finder-staging/credentials/serviceAccountKey.json
   chmod 600 /opt/job-finder-staging/.env
   ```

4. **Firestore security:**
   - Use separate staging/production databases
   - Grant minimal required permissions
   - Review service account roles regularly

5. **Regular updates:**
   - Watchtower keeps container updated
   - Monitor GitHub security advisories
   - Review dependency vulnerabilities

---

## Quick Reference

### Essential Commands

```bash
# View logs
docker logs -f job-finder-staging
docker logs --tail 100 job-finder-staging

# Manual search (immediate trigger)
docker exec job-finder-staging /app/docker/run-now.sh

# Check container status
docker ps -a | grep job-finder

# Check cron is running
docker exec job-finder-staging ps aux | grep cron

# View cron schedule
docker exec job-finder-staging cat /etc/cron.d/job-finder-cron

# View cron log
docker exec job-finder-staging cat /var/log/cron.log

# Check environment variables
docker exec job-finder-staging printenv | grep -E "ANTHROPIC|STORAGE|PROFILE|ENVIRONMENT"

# Access shell
docker exec -it job-finder-staging /bin/bash

# Restart container
docker restart job-finder-staging

# Update container
docker pull ghcr.io/jdubz/job-finder:latest && docker restart job-finder-staging
```

### File Locations

```
/opt/job-finder-staging/
├── credentials/
│   └── serviceAccountKey.json
├── config/
│   └── config.yaml
├── logs/
│   └── scheduler.log
└── data/
    └── (local exports)
```

### Useful Links

- [Local Testing Guide](./local-testing.md)
- [Environment Configuration](./environments.md)
- [Cloud Logging Setup](./cloud-logging.md)
- [Development Workflow](./development.md)
- [GitHub Repository](https://github.com/Jdubz/job-finder)
- [GitHub Issues](https://github.com/Jdubz/job-finder/issues)

---

## Support

For issues or questions:
1. Check logs first (container, scheduler, cron)
2. Review Firestore data in Firebase Console
3. Consult troubleshooting section above
4. Search existing [GitHub Issues](https://github.com/Jdubz/job-finder/issues)
5. Create new issue with logs and context

---

**Last Updated:** 2025-10-14
