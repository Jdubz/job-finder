# Portainer Deployment - Step-by-Step Walkthrough

Complete walkthrough for deploying job-finder to Portainer on bignasty.local.

---

## STEP 1: Set Up Directory Structure on OMV

**What we're doing:** Creating the directory structure on your OMV server to store credentials, config, logs, and data.

### 1.1 SSH into OMV

```bash
ssh root@bignasty.local
# Password: dub2tack
```

### 1.2 Navigate to your storage directory

```bash
cd /srv/dev-disk-by-uuid-45e47416-96ad-41be-9fc0-582e15241cbd/storage/jobscraper
```

### 1.3 Create directory structure

```bash
# Create staging directories
mkdir -p staging/credentials
mkdir -p staging/config
mkdir -p staging/logs
mkdir -p staging/data

# Create production directories
mkdir -p production/credentials
mkdir -p production/config
mkdir -p production/logs
mkdir -p production/data
```

### 1.4 Set correct permissions

```bash
# Secure credentials directories (only owner can read)
chmod 700 staging/credentials
chmod 700 production/credentials

# Make other directories readable
chmod 755 staging/config staging/logs staging/data
chmod 755 production/config production/logs production/data
```

### 1.5 Copy Firebase credentials

If you already have `serviceAccountKey.json` in the current directory:

```bash
# Copy to staging
cp serviceAccountKey.json staging/credentials/
chmod 600 staging/credentials/serviceAccountKey.json

# Copy to production
cp serviceAccountKey.json production/credentials/
chmod 600 production/credentials/serviceAccountKey.json
```

If you don't have it yet:

```bash
# Create the file and paste the JSON content
nano staging/credentials/serviceAccountKey.json
# Paste your Firebase service account JSON, then:
# Press Ctrl+O to save
# Press Ctrl+X to exit

# Set permissions
chmod 600 staging/credentials/serviceAccountKey.json

# Copy to production
cp staging/credentials/serviceAccountKey.json production/credentials/
chmod 600 production/credentials/serviceAccountKey.json
```

### 1.6 Verify structure

```bash
# Check directories were created
ls -la staging/
ls -la production/

# Should see:
# drwx------ credentials
# drwxr-xr-x config
# drwxr-xr-x logs
# drwxr-xr-x data
```

✅ **Directory setup complete!** You can exit SSH now (`exit` or Ctrl+D).

---

## STEP 2: Create GitHub Personal Access Token (PAT)

**What we're doing:** Creating a token that allows Portainer to pull images from GitHub Container Registry.

### 2.1 Open GitHub Token Creation Page

1. Go to: https://github.com/settings/tokens/new
2. Or navigate: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)

### 2.2 Configure Token

- **Note:** `Portainer GHCR Access`
- **Expiration:** Choose your preference (recommend: 90 days or 1 year)
- **Select scopes:**
  - ✅ Check **`read:packages`** (required to pull images)
  - ✅ Optional: **`write:packages`** (if you want Portainer to push images)

### 2.3 Generate and Copy Token

1. Click **"Generate token"** (green button at bottom)
2. **IMMEDIATELY COPY THE TOKEN** - you won't see it again!
3. Save it somewhere temporarily (you'll paste it in Portainer next)

Example token format: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## STEP 3: Add GitHub Container Registry to Portainer

**What we're doing:** Configuring Portainer to authenticate with GitHub Container Registry so it can pull your private images.

### 3.1 Open Portainer

1. Open browser to: http://bignasty.local:9000/
2. Log in to Portainer

### 3.2 Navigate to Registries

1. In the left sidebar, click **"Registries"**
2. Click the blue **"+ Add registry"** button

### 3.3 Configure Registry

Fill in the form:

**Registry provider:**
- Select: **"Custom registry"** (from dropdown)

**Name:**
- Enter: `GitHub Container Registry` (or any name you prefer)

**Registry URL:**
- Enter: `ghcr.io` (exactly this, no https://)

**Authentication:**
- ✅ **Toggle ON** (enable authentication)

**Username:**
- Enter: `Jdubz` (your GitHub username, case-sensitive)

**Password:**
- Paste: Your GitHub PAT token from Step 2 (starts with `ghp_`)

**Example:**
```
Registry provider: Custom registry
Name: GitHub Container Registry
Registry URL: ghcr.io
Authentication: [X] ON
Username: Jdubz
Password: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3.4 Add Registry

1. Click **"Add registry"** (blue button at bottom)
2. You should see a success message
3. The registry should appear in your registries list

✅ **GitHub Container Registry configured!**

---

## STEP 4: Deploy Staging Stack

**What we're doing:** Creating a new stack in Portainer that will run your job-finder application.

### 4.1 Open Stacks

1. In Portainer left sidebar, click **"Stacks"**
2. Click the blue **"+ Add stack"** button

### 4.2 Name Your Stack

**Name:**
- Enter: `job-finder-staging`

### 4.3 Build Method

Select: **"Web editor"** (should be selected by default)

### 4.4 Paste Docker Compose Content

In the large text editor box, paste the entire contents of `docker-compose.omv-staging.yml`:

```yaml
version: '3.8'

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
      - /srv/dev-disk-by-uuid-45e47416-96ad-41be-9fc0-582e15241cbd/storage/jobscraper/staging/credentials:/app/credentials:ro
      - /srv/dev-disk-by-uuid-45e47416-96ad-41be-9fc0-582e15241cbd/storage/jobscraper/staging/config:/app/config:ro
      - /srv/dev-disk-by-uuid-45e47416-96ad-41be-9fc0-582e15241cbd/storage/jobscraper/staging/logs:/app/logs
      - /srv/dev-disk-by-uuid-45e47416-96ad-41be-9fc0-582e15241cbd/storage/jobscraper/staging/data:/app/data

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
        reservations:
          cpus: '0.25'
          memory: 256M

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
      - WATCHTOWER_INCLUDE_RESTARTING=true
      - TZ=America/Los_Angeles

    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

    networks:
      - job-finder-network

networks:
  job-finder-network:
    driver: bridge
```

### 4.5 Set Environment Variables

Scroll down to the **"Environment variables"** section.

Click **"+ add an environment variable"** and add:

**Variable 1:**
- Name: `ANTHROPIC_API_KEY`
- Value: Your Claude API key (starts with `sk-ant-`)

**Example:**
```
Name: ANTHROPIC_API_KEY
Value: sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Variable 2 (optional):**
- Name: `OPENAI_API_KEY`
- Value: Your OpenAI key (if you have one), or leave empty

### 4.6 Deploy the Stack

1. Scroll to the bottom
2. Click the blue **"Deploy the stack"** button
3. Wait for deployment (this may take 1-2 minutes as it pulls the image)

You should see:
- A progress indicator
- Then a success message: "Stack successfully deployed"

✅ **Stack deployed!**

---

## STEP 5: Verify Deployment

**What we're doing:** Checking that the containers are running and the application is working correctly.

### 5.1 Check Container Status

1. In Portainer left sidebar, click **"Containers"**
2. You should see two new containers:
   - `job-finder-staging` - Status: **running** (green)
   - `watchtower-job-finder-staging` - Status: **running** (green)

If either is red/stopped, click on it to see why.

### 5.2 View Container Logs

1. Click on **`job-finder-staging`** container name
2. Click the **"Logs"** tab (near the top)
3. Toggle **"Auto-refresh logs"** ON (if available)

**What to look for:**

✅ **Good signs:**
```
Connected to Firestore database: portfolio-staging
Profile loaded successfully
Starting job search...
```

❌ **Error signs:**
```
Credentials file not found
Failed to initialize Firestore
ANTHROPIC_API_KEY not set
```

### 5.3 Check Logs on OMV (Alternative Method)

SSH back into OMV and check the log file:

```bash
ssh root@bignasty.local

# View real-time logs
tail -f /srv/dev-disk-by-uuid-45e47416-96ad-41be-9fc0-582e15241cbd/storage/jobscraper/staging/logs/scheduler.log

# Or view entire log
cat /srv/dev-disk-by-uuid-45e47416-96ad-41be-9fc0-582e15241cbd/storage/jobscraper/staging/logs/scheduler.log
```

### 5.4 Test Firestore Connection

Check that job-matches are being created:

1. Go to Firebase Console: https://console.firebase.google.com/
2. Select your project
3. Click **Firestore Database** in left sidebar
4. Select database: **portfolio-staging**
5. Look for collection: **job-matches**
6. You should see documents appearing as jobs are scraped

---

## STEP 6: Test the Application (Optional)

**What we're doing:** Manually running the job search to verify everything works.

### 6.1 Execute Job Search Manually

In Portainer:

1. Go to **Containers**
2. Click **`job-finder-staging`**
3. Click **"Console"** tab
4. Click **"Connect"** button
5. In the console, run:

```bash
python -m job_finder.main
```

Watch the output for:
- Firestore connection
- Profile loading
- Job scraping
- AI matching
- Storage to Firestore

### 6.2 View Results

Check Firestore database for new job-matches documents.

---

## Troubleshooting

### Problem: Container keeps restarting

**Check:**
1. View logs in Portainer
2. Common issues:
   - Missing `ANTHROPIC_API_KEY` environment variable
   - Missing credentials file
   - Wrong Firestore database name

**Fix:**
- Edit stack → Update environment variables → Update the stack

### Problem: "Failed to pull image"

**Check:**
1. GitHub Container Registry is added correctly
2. Token has `read:packages` permission
3. Username is `Jdubz` (exact case)

**Fix:**
- Delete and re-add registry with correct credentials

### Problem: "Credentials file not found"

**Check:**
```bash
ssh root@bignasty.local
ls -la /srv/.../jobscraper/staging/credentials/serviceAccountKey.json
```

**Fix:**
- Verify file exists
- Check permissions: `chmod 600 serviceAccountKey.json`
- Verify it's valid JSON: `cat serviceAccountKey.json | python3 -m json.tool`

### Problem: Container can't access mounted files

**Check:**
- Portainer is running with access to host filesystem
- Volume paths are absolute (starting with `/srv/...`)

**Fix:**
- Verify paths in docker-compose exactly match your OMV storage

---

## What's Next?

After successful deployment:

1. ✅ **Monitor**: Watch logs for the first few runs
2. ✅ **Verify**: Check Firestore for job-matches being created
3. ✅ **Schedule**: Set up cron for automated runs (if needed)
4. ✅ **Production**: Deploy production stack when ready
5. ✅ **Auto-updates**: Watchtower will auto-update when you push to GitHub

---

## Quick Reference Commands

```bash
# SSH to OMV
ssh root@bignasty.local

# View logs
tail -f /srv/.../jobscraper/staging/logs/scheduler.log

# Check container
docker ps | grep job-finder

# Restart container
docker restart job-finder-staging

# View container logs
docker logs -f job-finder-staging

# Manual run
docker exec -it job-finder-staging python -m job_finder.main
```

---

**You're all set!** 🎉

The application will now:
- Run in Portainer
- Store logs persistently on OMV
- Auto-update when you push to GitHub (via Watchtower)
- Store job matches in Firestore `portfolio-staging` database
