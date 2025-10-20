# Portainer Quick Start Guide

5-minute guide to deploying job-finder staging and production in Portainer.

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Portainer running and accessible
- [ ] Firebase service account JSON file
- [ ] Anthropic API key
- [ ] GitHub repository access
- [ ] Server with Docker installed

---

## Step 1: Prepare Server Directories (2 minutes)

SSH into your server and create directory structure:

```bash
# Create staging directory
mkdir -p ~/job-finder-staging/{credentials,config,logs-staging,data-staging}

# Create production directory
mkdir -p ~/job-finder-production/{credentials,config,logs,data}

# Upload Firebase credentials
# Replace with your actual service account file
scp serviceAccountKey.json user@server:~/job-finder-staging/credentials/
scp serviceAccountKey.json user@server:~/job-finder-production/credentials/

# Set proper permissions
chmod 600 ~/job-finder-*/credentials/serviceAccountKey.json
```

---

## Step 2: Deploy Staging Stack (2 minutes)

1. **Open Portainer** → Navigate to **Stacks** → Click **Add stack**

2. **Stack Configuration:**
   - **Name:** `job-finder-staging`
   - **Build method:** Select **Repository**

3. **Repository Settings:**
   - **Authentication:** (if private repo)
   - **Repository URL:** `https://github.com/Jdubz/job-finder`
   - **Repository reference:** `refs/heads/develop`
   - **Compose path:** `docker-compose.staging.yml`
   - **Enable Automatic updates:** ✅ (optional)
   - **Fetch interval:** 300 seconds

4. **Environment Variables:**
   Click "Add an environment variable" for each:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-...your-key...
   OPENAI_API_KEY=sk-...your-key...
   ```

5. **Click "Deploy the stack"**

6. **Verify Deployment:**
   - Navigate to **Containers**
   - Look for `job-finder-staging` (should be green/running)
   - Click container → **Logs** → Check for errors

---

## Step 3: Deploy Production Stack (2 minutes)

1. **Open Portainer** → Navigate to **Stacks** → Click **Add stack**

2. **Stack Configuration:**
   - **Name:** `job-finder-production`
   - **Build method:** Select **Repository**

3. **Repository Settings:**
   - **Authentication:** (if private repo)
   - **Repository URL:** `https://github.com/Jdubz/job-finder`
   - **Repository reference:** `refs/heads/main`
   - **Compose path:** `docker-compose.production.yml`
   - **Enable Automatic updates:** ✅ (optional)
   - **Fetch interval:** 300 seconds

4. **Environment Variables:**
   Click "Add an environment variable" for each:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-...your-production-key...
   OPENAI_API_KEY=sk-...your-production-key...
   ```

5. **Click "Deploy the stack"**

6. **Verify Deployment:**
   - Navigate to **Containers**
   - Look for `job-finder-production` (should be green/running)
   - Click container → **Logs** → Check for errors

---

## Step 4: Verify Both Environments (1 minute)

### Check Staging

```bash
# SSH into server
docker logs job-finder-staging --tail 20
docker exec job-finder-staging env | grep DATABASE
```

**Expected output:**
```
PROFILE_DATABASE_NAME=portfolio-staging
STORAGE_DATABASE_NAME=portfolio-staging
```

### Check Production

```bash
docker logs job-finder-production --tail 20
docker exec job-finder-production env | grep DATABASE
```

**Expected output:**
```
PROFILE_DATABASE_NAME=portfolio
STORAGE_DATABASE_NAME=portfolio
```

---

## Step 5: Test Queue Processing (Optional)

### Test Staging Queue

```bash
# Run diagnostic
docker exec -it job-finder-staging python scripts/diagnose_production_queue.py --database portfolio-staging
```

### Test Production Queue

```bash
# Run diagnostic
docker exec -it job-finder-production python scripts/diagnose_production_queue.py --database portfolio
```

---

## Common Issues & Fixes

### Issue: Container Not Starting

**Check logs:**
```bash
docker logs job-finder-staging
```

**Common causes:**
- Missing credentials file
- Invalid API key
- Wrong volume paths

**Fix:**
1. Verify credentials file exists: `ls ~/job-finder-staging/credentials/`
2. Check API keys in Portainer environment variables
3. Verify volume paths match directory structure

### Issue: "No such file or directory" Error

**Fix volume paths in Portainer:**
1. Navigate to **Stacks** → Select stack → **Editor**
2. Update volume paths to match your server:
   ```yaml
   volumes:
     - /home/youruser/job-finder-staging/credentials:/app/credentials:ro
     - /home/youruser/job-finder-staging/config:/app/config:ro
     - /home/youruser/job-finder-staging/logs-staging:/app/logs
     - /home/youruser/job-finder-staging/data-staging:/app/data
   ```
3. Click **Update the stack**

### Issue: Database Connection Errors

**Verify database names:**
```bash
docker exec job-finder-staging env | grep DATABASE
```

**Should show:**
- Staging: `portfolio-staging`
- Production: `portfolio`

**If wrong, update in Portainer:**
1. Stacks → Select stack → Editor
2. Fix environment variables in docker-compose file
3. Update the stack

---

## Quick Commands Reference

```bash
# View logs
docker logs -f job-finder-staging
docker logs -f job-finder-production

# Restart containers
docker restart job-finder-staging
docker restart job-finder-production

# Check resource usage
docker stats job-finder-staging job-finder-production

# Run diagnostics
docker exec -it job-finder-staging python scripts/diagnose_production_queue.py --database portfolio-staging
docker exec -it job-finder-production python scripts/diagnose_production_queue.py --database portfolio

# Check environment variables
docker exec job-finder-staging env
docker exec job-finder-production env
```

---

## What's Next?

After successful deployment:

1. ✅ **Configure job-finder-FE Frontend** - See `docs/FRONTEND_CONFIG.md`
2. ✅ **Test Queue Processing** - Submit test job from job-finder-FE UI
3. ✅ **Set Up Monitoring** - Configure Watchtower notifications (optional)
4. ✅ **Review Logs Regularly** - Check for errors daily

---

## Getting Help

If you encounter issues:

1. **Check logs first:**
   ```bash
   docker logs job-finder-staging --tail 100
   ```

2. **Review detailed guides:**
   - `docs/PORTAINER_DEPLOYMENT_GUIDE.md` - Complete deployment guide
   - `docs/STAGING_VS_PRODUCTION.md` - Environment differences
   - `docs/PRODUCTION_QUEUE_TROUBLESHOOTING.md` - Queue issues

3. **Run diagnostics:**
   ```bash
   docker exec -it job-finder-staging python scripts/diagnose_production_queue.py --database portfolio-staging
   ```

---

## Summary

You should now have:

✅ **Staging environment** running on `portfolio-staging` database
✅ **Production environment** running on `portfolio` database
✅ **Both containers** healthy and processing queue items
✅ **Auto-updates** configured via Watchtower

**Total setup time:** ~5 minutes 🚀

Next step: Configure your job-finder-FE frontend to submit queue items to the correct database!
