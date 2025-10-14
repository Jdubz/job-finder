# Job Finder - Docker Deployment Guide

Complete guide for deploying Job Finder as a Docker container in Portainer on OpenMediaVault.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Setup Steps](#setup-steps)
- [Configuration](#configuration)
- [Deployment in Portainer](#deployment-in-portainer)
- [Auto-Updates](#auto-updates)
- [Monitoring & Logs](#monitoring--logs)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

1. **OpenMediaVault** with Docker and Portainer installed
2. **Firebase Service Account JSON** for Firestore access
3. **Anthropic API Key** (for Claude AI)
4. **GitHub Account** with repository access

### Optional

- OpenAI API Key (if using GPT-4 instead of Claude)
- Adzuna API credentials (for additional job sources)

---

## Setup Steps

### 1. Prepare Credentials

On your OpenMediaVault server, create a directory structure:

```bash
mkdir -p /path/to/job-finder/{credentials,config,logs,data}
```

**Place your Firebase service account JSON:**
```bash
# Copy your serviceAccountKey.json to credentials folder
cp serviceAccountKey.json /path/to/job-finder/credentials/
```

**Create environment variables file:**
```bash
cat > /path/to/job-finder/.env << 'EOF'
ANTHROPIC_API_KEY=your-anthropic-api-key-here
OPENAI_API_KEY=your-openai-key-here
TZ=America/Los_Angeles
EOF
```

### 2. Configure Job Search Settings

Copy the configuration file:

```bash
cp config/config.yaml /path/to/job-finder/config/
```

**Edit the configuration:**
```bash
nano /path/to/job-finder/config/config.yaml
```

Key settings to review:
- `profile.firestore.database_name` - Use `portfolio-staging` for testing, `portfolio` for production
- `profile.firestore.name` - Your name
- `profile.firestore.email` - Your email
- `storage.database_name` - Where to save job matches
- `search.max_jobs` - Maximum jobs to save per run
- `ai.min_match_score` - Minimum match threshold (0-100)

### 3. Set Up GitHub Container Registry

The Docker image is automatically built and pushed to GitHub Container Registry (ghcr.io) on merges to `main`.

**To pull the image:**
```bash
docker pull ghcr.io/jdubz/job-finder:latest
```

**For private repositories, create a GitHub Personal Access Token:**
1. Go to GitHub Settings → Developer Settings → Personal Access Tokens → Tokens (classic)
2. Generate new token with `read:packages` scope
3. Save the token securely

---

## Configuration

### Scheduler Configuration

The container runs a cron job that executes job searches periodically.

**Default schedule:** Every 6 hours at minute 0 (12am, 6am, 12pm, 6pm)

**To customize the schedule:**

Edit `docker/crontab` before building:
```cron
# Run every 4 hours
0 */4 * * * root cd /app && /usr/local/bin/python scheduler.py >> /var/log/cron.log 2>&1

# Run at specific times (6am, 2pm, 10pm)
0 6,14,22 * * * root cd /app && /usr/local/bin/python scheduler.py >> /var/log/cron.log 2>&1

# Run daily at 8am
0 8 * * * root cd /app && /usr/local/bin/python scheduler.py >> /var/log/cron.log 2>&1
```

Then rebuild the Docker image.

### Job Sources Configuration

Job sources are stored in Firestore (`job-listings` collection).

**To add/modify sources:**

Run the setup script (one-time):
```bash
docker exec -it job-finder python setup_job_listings.py
```

Or add sources directly in Firestore:
- Database: `portfolio-staging`
- Collection: `job-listings`

---

## Deployment in Portainer

### Method 1: Using Portainer Stacks (Recommended)

1. **Login to Portainer**
2. **Navigate to Stacks** → Add Stack
3. **Name:** `job-finder`
4. **Web editor:** Paste the contents of `docker-compose.yml`
5. **Environment variables:**
   - Click "+ Add an environment variable"
   - Add:
     ```
     ANTHROPIC_API_KEY=your-key-here
     OPENAI_API_KEY=your-key-here
     ```

6. **Advanced settings:**
   - Enable "Auto-update"
   - Enable "Re-pull image"

7. **Click "Deploy the stack"**

### Method 2: Using Portainer Containers

1. **Navigate to Containers** → Add Container
2. **Name:** `job-finder`
3. **Image:** `ghcr.io/jdubz/job-finder:latest`
4. **Network:** Bridge (or custom network)

5. **Volume Mappings:**
   ```
   Container: /app/credentials  → Host: /path/to/job-finder/credentials (Read-only)
   Container: /app/config       → Host: /path/to/job-finder/config (Read-only)
   Container: /app/logs         → Host: /path/to/job-finder/logs
   Container: /app/data         → Host: /path/to/job-finder/data
   ```

6. **Environment Variables:**
   ```
   ANTHROPIC_API_KEY=your-key-here
   GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/serviceAccountKey.json
   TZ=America/Los_Angeles
   ```

7. **Restart Policy:** Unless stopped

8. **Deploy Container**

### Method 3: Docker CLI (on OMV)

```bash
docker run -d \
  --name job-finder \
  --restart unless-stopped \
  -e ANTHROPIC_API_KEY=your-key-here \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/serviceAccountKey.json \
  -e TZ=America/Los_Angeles \
  -v /path/to/job-finder/credentials:/app/credentials:ro \
  -v /path/to/job-finder/config:/app/config:ro \
  -v /path/to/job-finder/logs:/app/logs \
  -v /path/to/job-finder/data:/app/data \
  --label com.centurylinklabs.watchtower.enable=true \
  ghcr.io/jdubz/job-finder:latest
```

---

## Auto-Updates

The deployment uses **Watchtower** to automatically update the container when a new image is pushed.

### How it Works

1. **GitHub Actions:** On merge to `main`, builds and pushes new image to `ghcr.io`
2. **Watchtower:** Polls the registry every 5 minutes for new images
3. **Auto-Update:** When detected, pulls new image and restarts container
4. **Cleanup:** Removes old image to save space

### Watchtower Configuration

Watchtower is included in `docker-compose.yml`. It:
- Checks every 5 minutes (`WATCHTOWER_POLL_INTERVAL=300`)
- Only updates containers with the label `com.centurylinklabs.watchtower.enable=true`
- Cleans up old images (`WATCHTOWER_CLEANUP=true`)

### Manual Update

If not using Watchtower:

**Via Portainer:**
1. Navigate to Containers
2. Select `job-finder`
3. Click "Recreate" → Enable "Pull latest image"

**Via CLI:**
```bash
docker pull ghcr.io/jdubz/job-finder:latest
docker stop job-finder
docker rm job-finder
# Re-run docker run command from above
```

---

## Monitoring & Logs

### View Logs

**Via Portainer:**
1. Containers → job-finder → Logs
2. Select number of lines (e.g., 100, 500, all)
3. Enable "Auto-refresh"

**Via CLI:**
```bash
# Follow live logs
docker logs -f job-finder

# Last 100 lines
docker logs --tail 100 job-finder

# Logs since 1 hour ago
docker logs --since 1h job-finder
```

### Log Files

Logs are persisted in mounted volumes:

```bash
# Scheduler logs
tail -f /path/to/job-finder/logs/scheduler.log

# Cron logs
docker exec job-finder tail -f /var/log/cron.log
```

### Check Job Matches in Firestore

1. Open Firebase Console
2. Navigate to Firestore Database
3. Select database: `portfolio-staging` (or `portfolio`)
4. View collection: `job-matches`

Each document includes:
- Job details (title, company, description, URL)
- AI match analysis (score, skills, priorities)
- Resume intake data
- Tracking fields (documentGenerated, applied, status)

### Healthcheck

The container includes a healthcheck that runs every 5 minutes:

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' job-finder
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker logs job-finder
```

**Common issues:**
- Missing environment variables
- Invalid credentials path
- Configuration file errors
- Firestore connection issues

### No Jobs Being Found

**Check scheduler logs:**
```bash
docker exec job-finder tail -f /var/log/cron.log
```

**Verify cron is running:**
```bash
docker exec job-finder ps aux | grep cron
```

**Manually trigger a search:**
```bash
docker exec job-finder python run_job_search.py
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

### Duplicate Jobs Being Saved

This shouldn't happen - the system checks for duplicates before saving.

**To verify:**
```bash
# Check Firestore job-matches collection
# Look for duplicate URLs
```

**To clear duplicates (if needed):**
- Manually delete duplicate documents in Firestore
- The system will skip them on future runs

### Auto-Update Not Working

**Check Watchtower logs:**
```bash
docker logs watchtower-job-finder
```

**Verify label is set:**
```bash
docker inspect job-finder | grep watchtower
```

**Manually trigger Watchtower:**
```bash
docker exec watchtower-job-finder watchtower --run-once
```

### Performance Issues

**Resource limits:**

Edit `docker-compose.yml` to adjust:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Increase CPU limit
      memory: 2G       # Increase memory limit
```

**Check resource usage:**
```bash
docker stats job-finder
```

---

## Advanced Configuration

### Custom Cron Schedule

**Option 1: Environment Variable**

Add to `docker-compose.yml`:
```yaml
environment:
  - CRON_SCHEDULE=0 */4 * * *  # Every 4 hours
```

Then modify `Dockerfile` to use this variable.

**Option 2: Override Crontab**

Mount custom crontab:
```yaml
volumes:
  - ./custom-crontab:/etc/cron.d/job-finder-cron:ro
```

### Multiple Profiles

To run searches for multiple users:

1. Create separate containers per user
2. Mount different config files
3. Use different Firestore user IDs

### Email Notifications

Add email notifications for new matches:

1. Install `sendmail` in Dockerfile
2. Add notification script
3. Call from scheduler after successful search

---

## Security Best Practices

1. **Never commit credentials:**
   - `.env` files are in `.gitignore`
   - Service account JSON is in `.gitignore`
   - API keys should be Portainer secrets or environment variables

2. **Use read-only mounts:**
   - Credentials volume is mounted `:ro`
   - Config volume is mounted `:ro`

3. **Restrict permissions:**
   ```bash
   chmod 600 /path/to/job-finder/credentials/serviceAccountKey.json
   chmod 600 /path/to/job-finder/.env
   ```

4. **Firestore security rules:**
   - Ensure service account has minimal required permissions
   - Use staging database for testing

5. **Regular updates:**
   - Watchtower keeps container updated
   - Monitor GitHub security advisories

---

## Support

For issues or questions:
1. Check logs first (container, scheduler, cron)
2. Review Firestore data in Firebase Console
3. Open an issue on GitHub: https://github.com/Jdubz/job-finder/issues

---

## Quick Reference

### Essential Commands

```bash
# View logs
docker logs -f job-finder

# Manual search
docker exec job-finder python run_job_search.py

# Access shell
docker exec -it job-finder /bin/bash

# Restart container
docker restart job-finder

# Update container
docker pull ghcr.io/jdubz/job-finder:latest && docker restart job-finder

# View Firestore matches
# → Open Firebase Console → portfolio-staging → job-matches
```

### File Locations

```
/path/to/job-finder/
├── credentials/
│   └── serviceAccountKey.json
├── config/
│   └── config.yaml
├── logs/
│   └── scheduler.log
└── data/
    └── (any local exports)
```

---

**Last Updated:** {{ current_date }}
**Version:** 1.0.0
