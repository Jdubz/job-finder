# Environment Configuration Guide

Job Finder supports multiple environments with separate Firestore databases for staging and production.

## Overview

| Environment | Profile Database | Storage Database | Config File | Use Case |
|------------|------------------|------------------|-------------|----------|
| **Local Development** | `portfolio-staging` | `portfolio-staging` | `config.yaml` | Local testing, development |
| **Staging (Docker)** | `portfolio-staging` | `portfolio-staging` | `config.yaml` | Pre-production testing |
| **Production (Docker)** | `portfolio` | `portfolio` | `config.production.yaml` | Live job searches |

## Configuration Methods

There are **three ways** to configure which databases are used (in order of precedence):

### 1. Environment Variables (Highest Priority)
```bash
PROFILE_DATABASE_NAME=portfolio
STORAGE_DATABASE_NAME=portfolio
```

### 2. Config File
```yaml
profile:
  firestore:
    database_name: "portfolio-staging"

storage:
  database_name: "portfolio-staging"
```

### 3. Code Defaults (Fallback)
- Profile: `portfolio`
- Storage: `portfolio-staging`

## Local Development

### Setup

1. **Use staging config** (`config/config.yaml`):
   ```yaml
   profile:
     firestore:
       database_name: "portfolio-staging"

   storage:
     database_name: "portfolio-staging"
   ```

2. **Set environment variables** (optional):
   ```bash
   export PROFILE_DATABASE_NAME=portfolio-staging
   export STORAGE_DATABASE_NAME=portfolio-staging
   ```

3. **Run searches**:
   ```bash
   python run_job_search.py
   ```

### Why Staging?

- **Safe testing**: Won't pollute production data
- **Experimentation**: Try new configurations without risk
- **Debugging**: Easier to clear/reset data

## Docker Staging

Uses `docker-compose.yml` (default)

### Environment Variables

```yaml
environment:
  - ENVIRONMENT=staging
  - PROFILE_DATABASE_NAME=portfolio-staging
  - STORAGE_DATABASE_NAME=portfolio-staging
  - CONFIG_PATH=/app/config/config.yaml
```

### Deploy

```bash
docker-compose up -d
```

### Use Case

- Testing Docker deployment before production
- Validating configuration changes
- Testing auto-updates

## Docker Production

Uses `docker-compose.production.yml`

### Environment Variables

```yaml
environment:
  - ENVIRONMENT=production
  - PROFILE_DATABASE_NAME=portfolio
  - STORAGE_DATABASE_NAME=portfolio
  - CONFIG_PATH=/app/config/config.production.yaml
```

### Deploy

```bash
docker-compose -f docker-compose.production.yml up -d
```

### Use Case

- Live job searches
- Real job matches stored in production database
- Production-ready configuration

## Portainer Deployment

### Staging Stack

1. **Portainer → Stacks → Add Stack**
2. **Name**: `job-finder-staging`
3. **Build method**: Web editor
4. **Paste**: Contents of `docker-compose.yml`
5. **Environment variables**:
   ```
   ANTHROPIC_API_KEY=your-key
   PROFILE_DATABASE_NAME=portfolio-staging
   STORAGE_DATABASE_NAME=portfolio-staging
   ```
6. **Deploy**

### Production Stack

1. **Portainer → Stacks → Add Stack**
2. **Name**: `job-finder-production`
3. **Build method**: Web editor
4. **Paste**: Contents of `docker-compose.production.yml`
5. **Environment variables**:
   ```
   ANTHROPIC_API_KEY=your-key
   PROFILE_DATABASE_NAME=portfolio
   STORAGE_DATABASE_NAME=portfolio
   ```
6. **Deploy**

## Database Structure

### Firestore Databases

```
Project: static-sites-257923

├── portfolio-staging (STAGING)
│   ├── experience-entries (profile data)
│   ├── experience-blurbs (profile data)
│   ├── job-listings (job sources)
│   └── job-matches (found jobs)
│
└── portfolio (PRODUCTION)
    ├── experience-entries (profile data)
    ├── experience-blurbs (profile data)
    ├── job-listings (job sources)
    └── job-matches (found jobs)
```

### Collection Purposes

| Collection | Description | Shared/Separate |
|-----------|-------------|-----------------|
| `experience-entries` | Your work experience | Shared (read-only) |
| `experience-blurbs` | Your profile content | Shared (read-only) |
| `job-listings` | Job source configurations | **Separate per environment** |
| `job-matches` | Found job matches | **Separate per environment** |

## Environment Variable Reference

### Required

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-xxxxx
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/serviceAccountKey.json
```

### Environment Configuration

```bash
# Environment identifier (informational)
ENVIRONMENT=staging|production

# Database overrides (recommended)
PROFILE_DATABASE_NAME=portfolio-staging|portfolio
STORAGE_DATABASE_NAME=portfolio-staging|portfolio

# Paths (Docker)
CONFIG_PATH=/app/config/config.yaml
LOG_FILE=/app/logs/scheduler.log

# Timezone
TZ=America/Los_Angeles
```

### Optional

```bash
# Additional API keys
OPENAI_API_KEY=sk-xxxxx
ADZUNA_APP_ID=xxxxx
ADZUNA_API_KEY=xxxxx

# Watchtower notifications
WATCHTOWER_NOTIFICATION_URL=slack://xxxxx
```

## Switching Environments

### Local: Staging → Production

**Option 1**: Environment variables
```bash
export PROFILE_DATABASE_NAME=portfolio
export STORAGE_DATABASE_NAME=portfolio
python run_job_search.py
```

**Option 2**: Use production config
```bash
python run_job_search.py --config config/config.production.yaml
```

### Docker: Staging → Production

```bash
# Stop staging
docker-compose down

# Start production
docker-compose -f docker-compose.production.yml up -d
```

### Portainer: Deploy Both

You can run **both** staging and production simultaneously:

- Staging: `job-finder-staging` container
- Production: `job-finder-production` container

They use different:
- Container names
- Databases
- Volume mounts (if desired)

## Best Practices

### 1. **Always Test in Staging First**

```bash
# 1. Test locally with staging
python run_job_search.py

# 2. Test in Docker staging
docker-compose up -d

# 3. If successful, deploy to production
docker-compose -f docker-compose.production.yml up -d
```

### 2. **Use Environment Variables**

Don't edit config files for environment changes. Use environment variables:

```yaml
# docker-compose.production.yml
environment:
  - PROFILE_DATABASE_NAME=portfolio  # Override config
  - STORAGE_DATABASE_NAME=portfolio  # Override config
```

### 3. **Separate Job Listings**

Set up job sources separately for each environment:

**Staging**:
```bash
docker exec job-finder-staging python scripts/database/setup_job_listings.py
```

**Production**:
```bash
docker exec job-finder-production python scripts/database/setup_job_listings.py
```

### 4. **Monitor Both Environments**

**Staging logs**:
```bash
docker logs -f job-finder-staging
```

**Production logs**:
```bash
docker logs -f job-finder-production
```

### 5. **Clear Staging Data Regularly**

Staging is for testing - feel free to clear old data:

1. Firebase Console → `portfolio-staging`
2. Delete old documents from `job-matches`
3. Re-run searches to test with fresh data

## Troubleshooting

### Wrong Database Being Used

**Check which database is active**:

```bash
# View environment variables
docker exec job-finder-staging env | grep DATABASE

# Expected output:
# PROFILE_DATABASE_NAME=portfolio-staging
# STORAGE_DATABASE_NAME=portfolio-staging
```

### Jobs Appearing in Wrong Database

**Verify storage configuration**:

1. Check environment variables (highest priority)
2. Check config file
3. Check code defaults

**Force specific database**:
```bash
docker exec job-finder-staging \
  env STORAGE_DATABASE_NAME=portfolio-staging \
  python run_job_search.py
```

### Profile Loading from Wrong Database

**Check profile database**:
```bash
docker exec job-finder-staging \
  env PROFILE_DATABASE_NAME=portfolio-staging \
  python -c "
from job_finder.profile import FirestoreProfileLoader
loader = FirestoreProfileLoader(database_name='portfolio-staging')
profile = loader.load_profile(name='Josh Wentworth', email='Contact@joshwentworth.com')
print(f'Loaded from: {loader.database_name}')
print(f'Experiences: {len(profile.experience)}')
"
```

### Both Environments Writing to Same Database

**This happens if**:
- Environment variables not set correctly
- Using same config file for both
- Volume mounts pointing to same config

**Solution**:
- Use separate `docker-compose` files
- Set environment variables explicitly
- Verify with logs before running searches

## Migration Between Environments

### Promote Staging Job Listings to Production

```python
# Script to copy job-listings from staging to production
import os
from google.cloud import firestore

# Connect to both databases
staging = firestore.Client(project='static-sites-257923', database='portfolio-staging')
production = firestore.Client(project='static-sites-257923', database='portfolio')

# Copy active listings
for doc in staging.collection('job-listings').where('enabled', '==', True).stream():
    data = doc.to_dict()
    production.collection('job-listings').add(data)
    print(f"Copied: {data['name']}")
```

### Export Job Matches

```bash
# Export staging matches to JSON
docker exec job-finder-staging python -c "
import json
from google.cloud import firestore

db = firestore.Client(project='static-sites-257923', database='portfolio-staging')
matches = []

for doc in db.collection('job-matches').stream():
    data = doc.to_dict()
    matches.append(data)

print(json.dumps(matches, indent=2, default=str))
" > staging-matches.json
```

## Summary

- **Local Development**: Use `portfolio-staging` for both profile and storage
- **Docker Staging**: Use `docker-compose.yml` → `portfolio-staging`
- **Docker Production**: Use `docker-compose.production.yml` → `portfolio`
- **Override**: Use environment variables `PROFILE_DATABASE_NAME` and `STORAGE_DATABASE_NAME`
- **Best Practice**: Always test in staging before deploying to production

---

**Quick Reference**:

```bash
# Local staging
python run_job_search.py

# Docker staging
docker-compose up -d

# Docker production
docker-compose -f docker-compose.production.yml up -d

# Check current database
docker exec <container> env | grep DATABASE_NAME
```
