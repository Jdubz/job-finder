# Portainer Deployment Guide

Complete guide for deploying job-finder in Portainer with separate staging and production environments.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Portainer Server                          │
├──────────────────────────┬──────────────────────────────────┤
│   STAGING STACK          │   PRODUCTION STACK               │
├──────────────────────────┼──────────────────────────────────┤
│ job-finder-staging       │ job-finder-production            │
│ └─ portfolio-staging DB  │ └─ portfolio DB                  │
│ └─ logs-staging/         │ └─ logs/                         │
│ └─ data-staging/         │ └─ data/                         │
│                          │                                  │
│ watchtower-staging       │ watchtower-production            │
│ └─ 3min poll interval    │ └─ 5min poll interval            │
└──────────────────────────┴──────────────────────────────────┘
```

**Key Differences:**
- **Staging**: Lower resources, aggressive updates, `portfolio-staging` database
- **Production**: Higher resources, stable updates, `portfolio` database

---

## Prerequisites

Before deploying to Portainer:

1. ✅ Docker image published to GitHub Container Registry: `ghcr.io/jdubz/job-finder:latest`
2. ✅ Firebase service account credentials file
3. ✅ API keys (Anthropic, OpenAI)
4. ✅ Portainer instance running and accessible

---

## Deployment Steps

### Step 1: Prepare Repository Files

On your server where Portainer runs, create directory structure:

```bash
# On your server
cd /path/to/deployments
mkdir -p job-finder-staging
mkdir -p job-finder-production

# Copy required files to each directory
# For staging:
cd job-finder-staging
mkdir -p credentials config logs-staging data-staging

# For production:
cd ../job-finder-production
mkdir -p credentials config logs data
```

### Step 2: Upload Credentials

Upload your Firebase service account JSON to both environments:

```bash
# Copy credentials to both staging and production
cp /path/to/serviceAccountKey.json job-finder-staging/credentials/
cp /path/to/serviceAccountKey.json job-finder-production/credentials/
```

### Step 3: Upload Configuration Files

```bash
# Staging uses config.yaml
cp config/config.yaml job-finder-staging/config/

# Production uses config.production.yaml
cp config/config.production.yaml job-finder-production/config/
```

### Step 4: Create Portainer Stacks

#### Option A: Using Portainer UI (Recommended)

1. **Navigate to Portainer** → Stacks → Add Stack

2. **For STAGING Stack:**
   - **Name:** `job-finder-staging`
   - **Build method:** Repository
   - **Repository URL:** `https://github.com/Jdubz/job-finder`
   - **Repository reference:** `refs/heads/develop` (or `main`)
   - **Compose path:** `docker-compose.staging.yml`
   - **Environment variables:** (see below)
   - Click **Deploy the stack**

3. **For PRODUCTION Stack:**
   - **Name:** `job-finder-production`
   - **Build method:** Repository
   - **Repository URL:** `https://github.com/Jdubz/job-finder`
   - **Repository reference:** `refs/heads/main`
   - **Compose path:** `docker-compose.production.yml`
   - **Environment variables:** (see below)
   - Click **Deploy the stack**

#### Option B: Using Git Repository (Automated Updates)

**Best Practice:** Use Git repository deployment for automatic updates when you push changes.

1. Go to Portainer → Stacks → Add Stack
2. Select **Repository** as build method
3. Enter your GitHub repository URL
4. Set **Automatic updates:** `true` (enables GitOps)
5. **Fetch interval:** 5 minutes
6. This auto-deploys when you push to the specified branch

---

## Environment Variables Configuration

### Staging Environment Variables

Copy these into Portainer Stack Environment Variables section:

```env
# API Keys (REQUIRED - set your actual keys)
ANTHROPIC_API_KEY=sk-ant-...your-key...
OPENAI_API_KEY=sk-...your-key...

# Optional Watchtower notifications
WATCHTOWER_NOTIFICATION_URL=discord://webhook_token@webhook_id
```

### Production Environment Variables

```env
# API Keys (REQUIRED - set your actual keys)
ANTHROPIC_API_KEY=sk-ant-...your-key...
OPENAI_API_KEY=sk-...your-key...

# Optional Watchtower notifications
WATCHTOWER_NOTIFICATION_URL=discord://webhook_token@webhook_id
```

**Important:** Environment variables for database names are **already set in docker-compose files** and should NOT be overridden in Portainer unless you have a specific reason.

---

## Volume Mapping Strategy

### Staging Volumes

```yaml
volumes:
  - ./credentials:/app/credentials:ro           # Shared credentials
  - ./config:/app/config:ro                     # Staging config
  - ./logs-staging:/app/logs                    # Separate logs
  - ./data-staging:/app/data                    # Separate data
```

**Path on server:** `/path/to/job-finder-staging/`

### Production Volumes

```yaml
volumes:
  - ./credentials:/app/credentials:ro           # Shared credentials
  - ./config:/app/config:ro                     # Production config
  - ./logs:/app/logs                            # Separate logs
  - ./data:/app/data                            # Separate data
```

**Path on server:** `/path/to/job-finder-production/`

**Why separate logs/data?**
- Prevents staging from overwriting production data
- Makes debugging easier (separate log files)
- Allows independent cleanup/archival

---

## Network Isolation

Each environment has its own isolated network:

- **Staging:** `job-finder-staging-network`
- **Production:** `job-finder-production-network`

**Benefits:**
- Network isolation between environments
- Easier troubleshooting
- Security boundary

**Note:** If you need both environments to access a shared database or service, you can create a shared network:

```yaml
networks:
  job-finder-staging-network:
    external: false
  shared-services:
    external: true  # Connect to external shared network
```

---

## Resource Allocation

### Staging Resources (Lower)

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'      # 1 CPU max
      memory: 1G       # 1GB RAM max
    reservations:
      cpus: '0.25'     # 0.25 CPU guaranteed
      memory: 256M     # 256MB RAM guaranteed
```

**Rationale:**
- Lower cost
- Sufficient for testing
- Prevents staging from consuming production resources

### Production Resources (Higher)

```yaml
deploy:
  resources:
    limits:
      cpus: '1.5'      # 1.5 CPU max
      memory: 1.5G     # 1.5GB RAM max
    reservations:
      cpus: '0.5'      # 0.5 CPU guaranteed
      memory: 512M     # 512MB RAM guaranteed
```

**Rationale:**
- Higher reliability
- Better performance under load
- Room for spikes

---

## Auto-Update Strategy

### Staging: Aggressive Updates

```yaml
watchtower-staging:
  environment:
    - WATCHTOWER_POLL_INTERVAL=180  # 3 minutes
    - WATCHTOWER_SCOPE=staging
```

**Purpose:** Test new changes quickly in staging

### Production: Stable Updates

```yaml
watchtower-production:
  environment:
    - WATCHTOWER_POLL_INTERVAL=300  # 5 minutes
```

**Purpose:** Stable, tested deployments

**Best Practice Workflow:**
1. Push code → automatic staging deployment (3min)
2. Test in staging environment
3. Tag release → production deployment (5min)

---

## Deployment Workflow

### Standard Deployment Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Developer pushes code to 'develop' branch                │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. GitHub Actions builds and pushes Docker image            │
│    → ghcr.io/jdubz/job-finder:latest                        │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Watchtower-staging detects new image (within 3min)       │
│    → Auto-deploys to staging                                │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Test in staging environment                              │
│    → Verify queue processing                                │
│    → Check logs                                             │
│    → Test new features                                      │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Merge to 'main' branch (if tests pass)                   │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Watchtower-production detects new image (within 5min)    │
│    → Auto-deploys to production                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Managing Both Environments in Portainer

### Viewing Container Status

**Portainer UI:**
1. Navigate to **Containers**
2. Filter by name:
   - `job-finder-staging` - Staging worker
   - `job-finder-production` - Production worker
   - `watchtower-*` - Update monitors

### Checking Logs

**Staging logs:**
```bash
# In Portainer
Containers → job-finder-staging → Logs

# Or via CLI
docker logs job-finder-staging -f --tail 100
```

**Production logs:**
```bash
# In Portainer
Containers → job-finder-production → Logs

# Or via CLI
docker logs job-finder-production -f --tail 100
```

### Restarting Containers

**In Portainer UI:**
1. Navigate to Stacks
2. Select `job-finder-staging` or `job-finder-production`
3. Click **Stop** then **Start** (or click **Restart**)

**Via CLI:**
```bash
# Restart staging
docker restart job-finder-staging

# Restart production
docker restart job-finder-production
```

### Updating Configuration

**To update config without rebuilding image:**

1. **Edit config file on server:**
   ```bash
   # Staging
   vim /path/to/job-finder-staging/config/config.yaml

   # Production
   vim /path/to/job-finder-production/config/config.production.yaml
   ```

2. **Restart container in Portainer:**
   - Stacks → select stack → Restart

Configuration changes take effect on container restart.

---

## Monitoring & Troubleshooting

### Health Checks

Both environments have health checks:

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
  interval: 5m
  timeout: 10s
  retries: 3
```

**Check health status in Portainer:**
- Containers → Status column shows health

### Common Issues

#### Issue 1: Container keeps restarting

**Check logs:**
```bash
docker logs job-finder-staging --tail 50
```

**Common causes:**
- Missing credentials file
- Invalid API keys
- Database connection issues

**Solution:**
1. Verify credentials file exists in `/app/credentials/`
2. Check environment variables in Portainer
3. Test database connection

#### Issue 2: Queue items not being processed

**Verify database configuration:**
```bash
# Check environment variables
docker exec job-finder-staging env | grep DATABASE

# Should show:
# PROFILE_DATABASE_NAME=portfolio-staging
# STORAGE_DATABASE_NAME=portfolio-staging
```

**Run diagnostic:**
```bash
# On server
docker exec -it job-finder-staging python scripts/diagnose_production_queue.py --database portfolio-staging
```

#### Issue 3: Different behavior between staging and production

**Compare configurations:**
```bash
# Staging config
cat /path/to/job-finder-staging/config/config.yaml

# Production config
cat /path/to/job-finder-production/config/config.production.yaml
```

**Check database:**
- Staging should use `portfolio-staging`
- Production should use `portfolio`

---

## Database Configuration Summary

| Environment | Database Name | Config File | Container Name |
|------------|---------------|-------------|----------------|
| **Staging** | `portfolio-staging` | `config.yaml` | `job-finder-staging` |
| **Production** | `portfolio` | `config.production.yaml` | `job-finder-production` |

**Verification Commands:**

```bash
# Check staging database
docker exec job-finder-staging python -c "
import os
print('PROFILE_DATABASE:', os.getenv('PROFILE_DATABASE_NAME'))
print('STORAGE_DATABASE:', os.getenv('STORAGE_DATABASE_NAME'))
"

# Check production database
docker exec job-finder-production python -c "
import os
print('PROFILE_DATABASE:', os.getenv('PROFILE_DATABASE_NAME'))
print('STORAGE_DATABASE:', os.getenv('STORAGE_DATABASE_NAME'))
"
```

---

## Security Best Practices

### 1. API Key Management

**Don't:**
- ❌ Commit API keys to Git
- ❌ Share keys between staging and production
- ❌ Store keys in config files

**Do:**
- ✅ Store in Portainer environment variables
- ✅ Use separate keys for staging/production (if possible)
- ✅ Rotate keys regularly

### 2. Credentials File

```bash
# Set proper permissions
chmod 600 credentials/serviceAccountKey.json
chown root:root credentials/serviceAccountKey.json
```

### 3. Network Security

- Use Portainer's network isolation
- Don't expose unnecessary ports
- Use firewall rules if needed

### 4. Log Rotation

```bash
# Set up log rotation to prevent disk fill
# Create /etc/logrotate.d/job-finder

/path/to/job-finder-staging/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    missingok
}

/path/to/job-finder-production/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
}
```

---

## Quick Reference Commands

### Portainer CLI Management

```bash
# List all job-finder containers
docker ps | grep job-finder

# Check staging status
docker ps --filter "name=job-finder-staging"

# Check production status
docker ps --filter "name=job-finder-production"

# View staging logs (live)
docker logs -f job-finder-staging

# View production logs (live)
docker logs -f job-finder-production

# Restart staging
docker restart job-finder-staging

# Restart production
docker restart job-finder-production

# Check resource usage
docker stats job-finder-staging job-finder-production
```

### Diagnostic Scripts

```bash
# Run diagnostics in staging
docker exec -it job-finder-staging python scripts/diagnose_production_queue.py --database portfolio-staging

# Run diagnostics in production
docker exec -it job-finder-production python scripts/diagnose_production_queue.py --database portfolio

# Check queue stats in staging
docker exec -it job-finder-staging python -c "
import sys; sys.path.insert(0, 'src')
from job_finder.queue import QueueManager
qm = QueueManager(database_name='portfolio-staging')
print(qm.get_queue_stats())
"

# Check queue stats in production
docker exec -it job-finder-production python -c "
import sys; sys.path.insert(0, 'src')
from job_finder.queue import QueueManager
qm = QueueManager(database_name='portfolio')
print(qm.get_queue_stats())
"
```

---

## Maintenance Schedule

### Daily
- ✅ Check container health status
- ✅ Review error logs

### Weekly
- ✅ Review queue statistics
- ✅ Check disk space usage
- ✅ Verify auto-updates are working

### Monthly
- ✅ Rotate API keys (if required)
- ✅ Clean up old logs
- ✅ Review resource usage and adjust if needed
- ✅ Update dependencies in Dockerfile

---

## Rollback Procedure

If a deployment causes issues:

### Quick Rollback

```bash
# In Portainer UI:
1. Navigate to Stacks
2. Select affected stack (staging or production)
3. Click "Stop"
4. Edit stack → change image tag to previous version
5. Click "Update the stack"
```

### Or via Docker CLI:

```bash
# Pull previous image version
docker pull ghcr.io/jdubz/job-finder:v1.2.3

# Stop current container
docker stop job-finder-production

# Remove current container
docker rm job-finder-production

# Restart stack with previous image
docker-compose -f docker-compose.production.yml up -d
```

---

## Support Checklist

When troubleshooting issues, gather this information:

- [ ] Environment (staging or production)?
- [ ] Container logs (`docker logs job-finder-[env]`)
- [ ] Environment variables (`docker exec job-finder-[env] env`)
- [ ] Database configuration
- [ ] Queue statistics
- [ ] Recent deployments/changes
- [ ] Error messages or stack traces

---

## Next Steps

After deploying both environments:

1. ✅ Verify both containers are running
2. ✅ Check logs for errors
3. ✅ Run diagnostic scripts
4. ✅ Test queue processing in staging
5. ✅ Promote to production once verified
6. ✅ Set up monitoring/alerting (optional)
