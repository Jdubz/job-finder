# Portainer Deployment Guide

This guide walks you through deploying the job-finder application to Portainer.

## Prerequisites

- Portainer installed and accessible at http://bignasty.local:9000/
- GitHub Personal Access Token (PAT) with `read:packages` permission
- Firebase service account JSON file
- Anthropic API key (for Claude)

## Step 1: Prepare Portainer Host

SSH into your Portainer host machine (`bignasty.local`):

```bash
ssh user@bignasty.local
```

Run the setup script to create necessary directories:

```bash
# Download and run the setup script
curl -O https://raw.githubusercontent.com/Jdubz/job-finder/main/portainer-setup.sh
chmod +x portainer-setup.sh
./portainer-setup.sh
```

Or create directories manually:

```bash
# Staging
sudo mkdir -p /opt/job-finder-staging/{credentials,config,logs,data}
sudo chown -R $USER:$USER /opt/job-finder-staging
chmod 700 /opt/job-finder-staging/credentials

# Production
sudo mkdir -p /opt/job-finder-production/{credentials,config,logs,data}
sudo chown -R $USER:$USER /opt/job-finder-production
chmod 700 /opt/job-finder-production/credentials
```

## Step 2: Upload Firebase Credentials

Upload your Firebase service account JSON to the Portainer host:

```bash
# Option A: SCP from local machine
scp /path/to/serviceAccountKey.json user@bignasty.local:/opt/job-finder-staging/credentials/

# Option B: Create file directly on host
nano /opt/job-finder-staging/credentials/serviceAccountKey.json
# Paste JSON content, save with Ctrl+O, exit with Ctrl+X

# Set correct permissions
chmod 600 /opt/job-finder-staging/credentials/serviceAccountKey.json
```

Repeat for production if needed:

```bash
cp /opt/job-finder-staging/credentials/serviceAccountKey.json \
   /opt/job-finder-production/credentials/
chmod 600 /opt/job-finder-production/credentials/serviceAccountKey.json
```

## Step 3: Add GitHub Container Registry to Portainer

1. **Create GitHub Personal Access Token:**
   - Go to: https://github.com/settings/tokens/new
   - Note: "Portainer GHCR Access"
   - Scopes: Select `read:packages`
   - Click "Generate token" and **copy it**

2. **Add Registry in Portainer:**
   - Navigate to: http://bignasty.local:9000/
   - Go to: **Registries** → **Add registry**
   - Registry provider: **Custom registry**
   - Name: `GitHub Container Registry`
   - Registry URL: `ghcr.io`
   - Authentication: ✅ **Enable**
   - Username: `Jdubz` (your GitHub username)
   - Password: Paste your PAT token
   - Click **Add registry**

## Step 4: Deploy Staging Stack

1. **Navigate to Stacks:**
   - Go to: http://bignasty.local:9000/
   - Click: **Stacks** → **Add stack**

2. **Configure Stack:**
   - Name: `job-finder-staging`
   - Build method: **Web editor**
   - Paste content from: `docker-compose.portainer-staging.yml`

3. **Set Environment Variables:**
   Scroll down to **Environment variables** and add:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-api-key-here
   OPENAI_API_KEY=  (optional, leave empty if not using)
   ```

4. **Deploy:**
   - Click **Deploy the stack**
   - Wait for containers to start

5. **Verify:**
   - Go to: **Containers**
   - Check `job-finder-staging` is running (green status)
   - Check logs: Click container → **Logs**

## Step 5: Deploy Production Stack (Optional)

Repeat Step 4 with these changes:
- Name: `job-finder-production`
- Use: `docker-compose.portainer-production.yml`
- Environment variables: Use production API keys
- Credentials: `/opt/job-finder-production/credentials/`

## Step 6: Verify Deployment

### Check Container Logs

1. In Portainer, go to **Containers**
2. Click on `job-finder-staging`
3. Click **Logs** tab
4. You should see:
   ```
   Connected to Firestore database: portfolio-staging
   Profile loaded successfully
   Starting job search...
   ```

### Check Mounted Files

SSH into the Portainer host and verify:

```bash
# Check credentials are mounted
ls -la /opt/job-finder-staging/credentials/
# Should show: serviceAccountKey.json

# Check logs are being written
ls -la /opt/job-finder-staging/logs/
# Should show: scheduler.log (after first run)

# View logs
tail -f /opt/job-finder-staging/logs/scheduler.log
```

## Watchtower Auto-Updates

The stack includes Watchtower, which automatically updates your container when new images are pushed to GitHub Container Registry.

- **Check interval:** Every 5 minutes
- **Only updates:** Containers with `com.centurylinklabs.watchtower.enable=true` label
- **Cleanup:** Removes old images after update

To manually trigger an update:

```bash
docker exec watchtower-job-finder-staging watchtower --run-once
```

## Troubleshooting

### Container Not Starting

Check logs in Portainer:
1. **Containers** → Click container → **Logs**

Common issues:
- Missing credentials: Check `/opt/job-finder-staging/credentials/serviceAccountKey.json` exists
- Wrong permissions: Run `chmod 600 /opt/job-finder-staging/credentials/serviceAccountKey.json`
- Missing API key: Check environment variables in stack configuration

### Cannot Pull Image

If you see `unauthorized: authentication required`:
1. Verify GitHub Container Registry is added correctly
2. Check PAT token has `read:packages` permission
3. Try pulling manually on host:
   ```bash
   docker login ghcr.io -u Jdubz -p YOUR_PAT_TOKEN
   docker pull ghcr.io/jdubz/job-finder:latest
   ```

### Firestore Connection Failed

Check:
1. Firebase credentials file exists and has correct content
2. File is readable: `cat /opt/job-finder-staging/credentials/serviceAccountKey.json`
3. Container can access file: Check logs for "Credentials file not found" error
4. Database name matches: `portfolio-staging` for staging

### Logs Not Persisting

Ensure log directory permissions:
```bash
sudo chown -R $USER:$USER /opt/job-finder-staging/logs
chmod 755 /opt/job-finder-staging/logs
```

## Updating Configuration

To update config without redeploying:

1. SSH to Portainer host
2. Edit config:
   ```bash
   nano /opt/job-finder-staging/config/config.yaml
   ```
3. Restart container in Portainer:
   - **Containers** → Click container → **Restart**

## Rolling Back

If an update causes issues:

1. In Portainer, go to **Images**
2. Find older `ghcr.io/jdubz/job-finder` image
3. Note the tag (e.g., `main-abc123`)
4. Edit stack, change image to specific tag:
   ```yaml
   image: ghcr.io/jdubz/job-finder:main-abc123
   ```
5. Click **Update the stack**

## Monitoring

### View Real-Time Logs

In Portainer:
- **Containers** → Click container → **Logs**
- Enable "Auto-refresh logs"

On host machine:
```bash
# Container logs
docker logs -f job-finder-staging

# Application logs
tail -f /opt/job-finder-staging/logs/scheduler.log
```

### Resource Usage

In Portainer:
- **Containers** → Click container → **Stats**
- Shows CPU, memory, network usage

### Health Check

Container includes health check that runs every 5 minutes. If unhealthy:
- Portainer will show yellow/red status
- Check logs for errors

## Production Best Practices

1. **Separate environments:** Use different stacks for staging and production
2. **Different databases:** Staging uses `portfolio-staging`, production uses `portfolio`
3. **Resource limits:** Production has higher limits (2GB RAM vs 1GB)
4. **Monitor logs:** Set up log aggregation if running at scale
5. **Backup data:** Regularly backup `/opt/job-finder-production/data/`
6. **API keys:** Use separate API keys for staging and production
7. **Test in staging first:** Always deploy to staging before production

## Getting Help

- **Container logs:** Check Portainer logs first
- **Application logs:** Check `/opt/job-finder-staging/logs/scheduler.log`
- **GitHub Issues:** https://github.com/Jdubz/job-finder/issues
- **Portainer docs:** https://docs.portainer.io/

## Next Steps

After successful deployment:

1. Verify jobs are being collected and stored in Firestore
2. Check job-matches collection in Firebase Console
3. Set up monitoring/alerting if needed
4. Configure cron schedule for automated runs
5. Test the full pipeline end-to-end
