# Docker Quick Start Guide

Get Job Finder running in Docker in 5 minutes.

## Prerequisites

- Docker installed
- Portainer installed (for web UI management)
- Firebase service account JSON
- Anthropic API key

## Quick Setup

### 1. Create Directory Structure

```bash
mkdir -p ~/job-finder/{credentials,config,logs,data}
cd ~/job-finder
```

### 2. Add Credentials

```bash
# Copy your Firebase service account JSON
cp /path/to/your/serviceAccountKey.json credentials/

# Create .env file
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/serviceAccountKey.json
TZ=America/Los_Angeles
EOF
```

### 3. Download Configuration

```bash
# Download example config from GitHub
wget https://raw.githubusercontent.com/Jdubz/job-finder/main/config/config.yaml -O config/config.yaml

# Edit configuration
nano config/config.yaml
```

**Minimum required changes:**
- `profile.firestore.name` - Your name
- `profile.firestore.email` - Your email
- `storage.database_name` - Use `portfolio-staging` for testing

### 4. Deploy with Docker Compose

```bash
# Download docker-compose.yml
wget https://raw.githubusercontent.com/Jdubz/job-finder/main/docker-compose.yml

# Start containers
docker-compose up -d
```

### 5. Initialize Job Sources

```bash
# One-time setup of job source listings
docker exec job-finder python setup_job_listings.py
```

### 6. Verify

```bash
# Check logs
docker logs -f job-finder

# Manual test run
docker exec job-finder python run_job_search.py
```

## Using Portainer

### Import Stack

1. **Login to Portainer** (usually `http://your-server:9000`)
2. **Go to:** Stacks → Add Stack
3. **Name:** `job-finder`
4. **Build method:** Web editor
5. **Paste:** Contents of `docker-compose.yml`
6. **Environment variables:**
   - Click "+ add an environment variable"
   - Add: `ANTHROPIC_API_KEY` = `your-key-here`
7. **Deploy the stack**

### View Logs

Portainer → Containers → job-finder → Logs

## Default Schedule

Job searches run automatically every 6 hours:
- 12:00 AM
- 6:00 AM
- 12:00 PM
- 6:00 PM

## What Happens Automatically

1. **Scheduled Searches:** Cron runs job search every 6 hours
2. **Auto-Updates:** Watchtower checks for new images every 5 minutes
3. **Duplicate Prevention:** Already-saved jobs are skipped
4. **Firestore Storage:** All matches saved to `portfolio-staging` database

## Viewing Results

**Option 1: Firebase Console**
1. Open Firebase Console
2. Navigate to Firestore Database
3. Select: `portfolio-staging`
4. View collection: `job-matches`

**Option 2: Export to JSON** (future feature)
```bash
docker exec job-finder python export_matches.py > matches.json
```

## Common Tasks

### Manual Search
```bash
docker exec job-finder python run_job_search.py
```

### View Scheduler Logs
```bash
docker exec job-finder tail -f /app/logs/scheduler.log
```

### View Cron Logs
```bash
docker exec job-finder tail -f /var/log/cron.log
```

### Restart Container
```bash
docker restart job-finder
```

### Update to Latest Version
```bash
docker pull ghcr.io/jdubz/job-finder:latest
docker-compose up -d
```

## Troubleshooting

### Container won't start
```bash
docker logs job-finder
```

### No jobs being saved
```bash
# Check if cron is running
docker exec job-finder ps aux | grep cron

# Run manual search
docker exec job-finder python run_job_search.py
```

### Authentication errors
- Verify `serviceAccountKey.json` exists in `credentials/`
- Check `ANTHROPIC_API_KEY` is set in environment
- Ensure Firebase service account has Firestore permissions

## Next Steps

- Review full documentation: [DEPLOYMENT.md](DEPLOYMENT.md)
- Customize search criteria in `config/config.yaml`
- Add more job sources in Firestore `job-listings` collection
- Set up notifications (future feature)

## Support

- Full deployment guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- Issues: https://github.com/Jdubz/job-finder/issues
- Documentation: [README.md](README.md)
