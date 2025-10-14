## OMV (OpenMediaVault) Deployment Guide

Quick deployment guide for job-finder on OpenMediaVault with Portainer.

**Your Setup:**
- Host: bignasty.local
- Portainer: http://bignasty.local:9000/
- Storage: `/srv/dev-disk-by-uuid-45e47416-96ad-41be-9fc0-582e15241cbd/storage/jobscraper`

---

## Step 1: Set Up Directory Structure on OMV

SSH into your OMV server:

```bash
ssh root@bignasty.local
```

Run the setup script:

```bash
# Navigate to your storage directory
cd /srv/dev-disk-by-uuid-45e47416-96ad-41be-9fc0-582e15241cbd/storage/jobscraper

# Create directory structure
mkdir -p staging/{credentials,config,logs,data}
mkdir -p production/{credentials,config,logs,data}

# Set permissions
chmod 700 staging/credentials production/credentials
chmod 755 staging/{config,logs,data} production/{config,logs,data}

# Copy Firebase credentials (if serviceAccountKey.json is in current directory)
cp serviceAccountKey.json staging/credentials/
cp serviceAccountKey.json production/credentials/
chmod 600 staging/credentials/serviceAccountKey.json
chmod 600 production/credentials/serviceAccountKey.json

# Verify structure
ls -la staging/ production/
```

---

## Step 2: Add GitHub Container Registry to Portainer

1. Open Portainer: http://bignasty.local:9000/
2. Go to: **Registries** → **Add registry**
3. Configure:
   - **Provider:** Custom registry
   - **Name:** GitHub Container Registry
   - **URL:** `ghcr.io`
   - **Authentication:** ✅ Enable
   - **Username:** `Jdubz`
   - **Password:** [Your GitHub PAT with read:packages scope]
4. Click **Add registry**

**Create GitHub PAT:** https://github.com/settings/tokens/new
- Scopes: `read:packages`

---

## Step 3: Deploy Staging Stack

1. In Portainer, go to: **Stacks** → **Add stack**
2. **Name:** `job-finder-staging`
3. **Build method:** Web editor
4. **Paste content from:** `docker-compose.omv-staging.yml`
5. **Environment variables** (scroll down):
   ```
   ANTHROPIC_API_KEY=sk-ant-your-actual-api-key-here
   OPENAI_API_KEY=  (optional)
   ```
6. Click **Deploy the stack**

---

## Step 4: Verify Deployment

Check container logs in Portainer:
- **Containers** → `job-finder-staging` → **Logs**

You should see:
```
Connected to Firestore database: portfolio-staging
Profile loaded successfully
```

Check files on OMV:
```bash
# SSH to bignasty.local
ls -la /srv/dev-disk-by-uuid-45e47416-96ad-41be-9fc0-582e15241cbd/storage/jobscraper/staging/logs/
tail -f /srv/dev-disk-by-uuid-45e47416-96ad-41be-9fc0-582e15241cbd/storage/jobscraper/staging/logs/scheduler.log
```

---

## Step 5: Deploy Production (Optional)

Repeat Step 3 with:
- **Name:** `job-finder-production`
- **File:** `docker-compose.omv-production.yml`
- **Environment:** Use production API keys

---

## Quick Reference

### File Locations on OMV

```
/srv/dev-disk-by-uuid-45e47416-96ad-41be-9fc0-582e15241cbd/storage/jobscraper/
├── staging/
│   ├── credentials/
│   │   └── serviceAccountKey.json  (required)
│   ├── config/
│   │   └── config.yaml  (optional)
│   ├── logs/
│   │   └── scheduler.log
│   └── data/
│       └── (output files)
└── production/
    ├── credentials/
    ├── config/
    ├── logs/
    └── data/
```

### Docker Images

- Staging: `ghcr.io/jdubz/job-finder:latest`
- Production: `ghcr.io/jdubz/job-finder:latest`

Auto-updates via Watchtower (checks every 5 minutes)

### Useful Commands

```bash
# SSH to OMV
ssh root@bignasty.local

# View logs
tail -f /srv/.../jobscraper/staging/logs/scheduler.log

# Check container status
docker ps | grep job-finder

# Restart container
docker restart job-finder-staging

# View container logs
docker logs -f job-finder-staging

# Pull latest image manually
docker pull ghcr.io/jdubz/job-finder:latest
```

---

## Troubleshooting

### Container Won't Start

Check Portainer logs first, then:

```bash
# Verify credentials exist
ls -la /srv/.../jobscraper/staging/credentials/

# Check permissions
stat /srv/.../jobscraper/staging/credentials/serviceAccountKey.json
# Should show: 0600

# Test credentials are valid JSON
cat /srv/.../jobscraper/staging/credentials/serviceAccountKey.json | python3 -m json.tool
```

### Can't Pull Image

1. Verify GitHub Container Registry is added in Portainer
2. Test manually on OMV:
   ```bash
   docker login ghcr.io -u Jdubz -p YOUR_PAT
   docker pull ghcr.io/jdubz/job-finder:latest
   ```

### Firestore Connection Failed

Check environment variables in Portainer stack:
- `ANTHROPIC_API_KEY` should be set
- `GOOGLE_APPLICATION_CREDENTIALS` should be `/app/credentials/serviceAccountKey.json`

---

## Next Steps

1. ✅ Set up directory structure
2. ✅ Deploy staging stack
3. ✅ Verify logs and Firestore connection
4. Configure cron schedule (if needed)
5. Test end-to-end job scraping pipeline
6. Deploy production when ready

For detailed instructions, see [PORTAINER_DEPLOYMENT.md](./PORTAINER_DEPLOYMENT.md)
