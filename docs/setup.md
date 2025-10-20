# Complete Setup Guide

This guide covers everything you need to set up and configure Job Finder for local development, staging, and production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Environment Configuration](#environment-configuration)
- [Firebase/Firestore Setup](#firebasefirestore-setup)
- [Profile Setup](#profile-setup)
- [Docker Local Testing](#docker-local-testing)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

**Python 3.12+**
```bash
python --version  # Should be 3.12 or higher
```

**Git**
```bash
git --version
```

**Docker** (for containerized deployment)
```bash
docker --version
docker-compose --version
```

### Required Credentials

1. **AI Provider API Key** (at least one):
   - **Anthropic Claude** (recommended): https://console.anthropic.com/
   - **OpenAI GPT-4** (alternative): https://platform.openai.com/

2. **Firebase Service Account Key**:
   - Download from [Firebase Console](https://console.firebase.google.com/)
   - Project: `static-sites-257923`
   - Save to secure location: `~/.firebase/serviceAccountKey.json`

3. **Optional Job Board APIs**:
   - Adzuna: https://developer.adzuna.com/

---

## Local Development Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/Jdubz/job-finder.git
cd job-finder
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -e ".[dev]"
```

### Step 4: Install Pre-commit Hooks (Recommended)

```bash
pip install pre-commit
pre-commit install
```

This automatically runs on every commit:
- **black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **bandit**: Security checks

Run manually:
```bash
pre-commit run --all-files
```

### Step 5: Create Environment Variables

```bash
# Copy example
cp .env.example .env

# Edit .env
nano .env
```

**Minimum required in .env:**
```bash
# AI Provider (choose one)
ANTHROPIC_API_KEY=sk-ant-xxxxx
# OR
OPENAI_API_KEY=sk-xxxxx

# Firebase credentials path
GOOGLE_APPLICATION_CREDENTIALS=/home/user/.firebase/serviceAccountKey.json
```

---

## Environment Configuration

Job Finder supports multiple environments with separate Firestore databases.

### Environment Options

| Environment | Profile Database | Storage Database | Config File | Use Case |
|------------|------------------|------------------|-------------|----------|
| **Local Development** | `portfolio-staging` | `portfolio-staging` | `config.yaml` | Local testing |
| **Staging (Docker)** | `portfolio-staging` | `portfolio-staging` | `config.yaml` | Pre-production |
| **Production (Docker)** | `portfolio` | `portfolio` | `config.production.yaml` | Live searches |

### Configuration Methods (in order of precedence)

**1. Environment Variables (Highest Priority)**
```bash
export PROFILE_DATABASE_NAME=portfolio-staging
export STORAGE_DATABASE_NAME=portfolio-staging
```

**2. Config File**
```yaml
# config/config.yaml
profile:
  firestore:
    database_name: "portfolio-staging"

storage:
  database_name: "portfolio-staging"
```

**3. Code Defaults (Fallback)**
- Profile: `portfolio`
- Storage: `portfolio-staging`

### Local Development (Recommended)

Use staging database for safe testing:

```bash
# .env
PROFILE_DATABASE_NAME=portfolio-staging
STORAGE_DATABASE_NAME=portfolio-staging
```

```yaml
# config/config.yaml
profile:
  source: "firestore"
  firestore:
    database_name: "portfolio-staging"
    name: "Your Name"

storage:
  database_name: "portfolio-staging"
```

### Switching Environments

**Local: Staging → Production**

Option 1 - Environment variables:
```bash
export PROFILE_DATABASE_NAME=portfolio
export STORAGE_DATABASE_NAME=portfolio
python -m job_finder.main
```

Option 2 - Use production config:
```bash
python -m job_finder.main --config config/config.production.yaml
```

**Docker: Staging → Production**
```bash
# Stop staging
docker-compose down

# Start production
docker-compose -f docker-compose.production.yml up -d
```

---

## Firebase/Firestore Setup

### Step 1: Download Service Account Key

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select project: `static-sites-257923`
3. Project Settings → Service Accounts
4. Generate New Private Key
5. Save as `~/.firebase/serviceAccountKey.json`

### Step 2: Set Credentials Path

```bash
# In .env
GOOGLE_APPLICATION_CREDENTIALS=/home/user/.firebase/serviceAccountKey.json

# Or absolute path
GOOGLE_APPLICATION_CREDENTIALS=/Users/username/.firebase/serviceAccountKey.json
```

### Step 3: Verify Connection

```bash
python -c "
from job_finder.storage.firestore_client import FirestoreClient
client = FirestoreClient.get_client(database_name='portfolio-staging')
print('✓ Connected to Firestore successfully')
"
```

### Firestore Databases

```
Project: static-sites-257923

├── portfolio-staging (STAGING)
│   ├── content-items (profile data - new schema)
│   ├── experience-entries (profile data - old schema)
│   ├── experience-blurbs (profile data - old schema)
│   ├── job-listings (job sources)
│   ├── job-matches (found jobs)
│   ├── job-queue (queue system)
│   ├── job-finder-config (configuration)
│   └── companies (company cache)
│
└── portfolio (PRODUCTION)
    ├── content-items (profile data - new schema)
    ├── experience-entries (profile data - old schema)
    ├── experience-blurbs (profile data - old schema)
    ├── job-listings (job sources)
    ├── job-matches (found jobs)
    ├── job-queue (queue system)
    ├── job-finder-config (configuration)
    └── companies (company cache)
```

---

## Profile Setup

Choose **one** of these methods:

### Option A: Firestore Profile (Recommended)

Automatically syncs with job-finder-FE project database.

**1. Configure in config.yaml:**
```yaml
profile:
  source: "firestore"
  firestore:
    database_name: "portfolio-staging"
    name: "Josh Wentworth"
    email: "contact@joshwentworth.com"
```

**2. Verify profile loads:**
```bash
python -c "
from job_finder.profile.firestore_loader import FirestoreProfileLoader
loader = FirestoreProfileLoader(database_name='portfolio-staging')
profile = loader.load_profile(name='Josh Wentworth', email='contact@joshwentworth.com')
print(f'Loaded {len(profile.experience)} experiences')
print(f'Loaded {len(profile.skills)} skills')
"
```

**Profile Data Sources (in order):**
1. **content-items** collection (new schema) - Preferred
2. **experience-entries** + **experience-blurbs** (old schema) - Fallback

### Option B: JSON Profile

Manual profile creation for testing or standalone use.

**1. Create profile template:**
```bash
python -m job_finder.main --create-profile data/profile.json
```

**2. Edit profile.json with your data:**
```json
{
  "name": "Your Name",
  "email": "your.email@example.com",
  "experience": [
    {
      "title": "Software Engineer",
      "company": "Tech Corp",
      "start_date": "2020-01",
      "end_date": "2023-12",
      "responsibilities": ["Built APIs", "Led team"],
      "technologies": ["Python", "Django", "PostgreSQL"]
    }
  ],
  "skills": [
    {
      "name": "Python",
      "proficiency": "Expert",
      "years_experience": 8
    }
  ],
  "preferences": {
    "preferred_roles": ["Software Engineer", "Backend Developer"],
    "preferred_locations": ["Remote", "Portland, OR"],
    "min_salary": 120000
  }
}
```

**3. Configure in config.yaml:**
```yaml
profile:
  source: "json"
  profile_path: "data/profile.json"
```

---

## Configuration File Setup

### Step 1: Copy Example Config

```bash
cp config/config.example.yaml config/config.yaml
```

### Step 2: Configure Basic Settings

```yaml
# config/config.yaml

# Profile source (firestore or json)
profile:
  source: "firestore"
  firestore:
    database_name: "portfolio-staging"
    name: "Your Name"

# AI matching settings
ai:
  enabled: true
  provider: "claude"  # or "openai"
  model: "claude-3-5-haiku-20241022"
  min_match_score: 80
  generate_intake_data: true
  portland_office_bonus: 15
  user_timezone: -8  # Pacific Time
  prefer_large_companies: true

# Job storage
storage:
  type: "firestore"
  database_name: "portfolio-staging"
  collection_name: "job-matches"

# Scraping settings
scraping:
  user_agent: "Mozilla/5.0 (compatible; JobFinder/1.0)"
  delay_between_requests: 2
  max_retries: 3
  timeout: 30
```

### Step 3: Configure Job Sources

Job sources are stored in Firestore `job-listings` collection. See [Development Guide](development.md#managing-job-sources) for details.

---

## Docker Local Testing

Test the containerized application locally before deploying.

### Prerequisites

```bash
# Ensure credentials are in place
ls ~/.firebase/serviceAccountKey.json

# Ensure environment variables are set
echo $ANTHROPIC_API_KEY

# Create directories
mkdir -p logs data
```

### Option 1: Test Production Container (from Registry)

Tests the exact container deployed in Portainer.

```bash
# Pull and run production container
docker-compose -f docker-compose.local-prod.yml up

# In another terminal, exec into container
docker exec -it job-finder-local-prod /bin/bash

# Inside container, test manually:
python scripts/workers/scripts/workers/scheduler.py
```

### Option 2: Test Local Build

Build from your local Dockerfile and source code.

```bash
# Build and run from local source
docker-compose -f docker-compose.local-build.yml up --build

# Exec into container
docker exec -it job-finder-local-build /bin/bash

# Test
python scripts/workers/scripts/workers/scheduler.py
```

### Rebuild After Code Changes

```bash
docker-compose -f docker-compose.local-build.yml up --build --force-recreate
```

### Test Queue Mode

Enable queue mode in docker-compose file:
```yaml
environment:
  - ENABLE_QUEUE_MODE=true
```

Then:
```bash
docker-compose -f docker-compose.local-build.yml up --build
```

Check logs for queue worker startup:
```
✓ Queue worker started successfully (PID: XXXX)
```

### Cleanup

```bash
# Stop containers
docker-compose -f docker-compose.local-prod.yml down

# Remove local images
docker rmi job-finder:local
```

---

## Verification

### Step 1: Verify Dependencies

```bash
# Check Python version
python --version

# Verify imports
python -c "
import anthropic
import openai
import pydantic
import firebase_admin
from google.cloud import firestore
print('✓ All dependencies installed')
"
```

### Step 2: Verify Credentials

```bash
# Check API keys
echo $ANTHROPIC_API_KEY  # Should show key
echo $GOOGLE_APPLICATION_CREDENTIALS  # Should show path

# Verify Firebase credentials file exists
ls -la $GOOGLE_APPLICATION_CREDENTIALS
```

### Step 3: Verify Firestore Connection

```bash
python -c "
from job_finder.storage.firestore_client import FirestoreClient
client = FirestoreClient.get_client(database_name='portfolio-staging')
print('✓ Firestore connection successful')
"
```

### Step 4: Verify Profile Loading

```bash
# For Firestore profile
python -c "
from job_finder.profile.firestore_loader import FirestoreProfileLoader
loader = FirestoreProfileLoader(database_name='portfolio-staging')
profile = loader.load_profile(name='Your Name')
print(f'✓ Loaded profile: {len(profile.experience)} experiences, {len(profile.skills)} skills')
"

# For JSON profile
python -c "
from job_finder.profile.loader import ProfileLoader
profile = ProfileLoader.load_from_file('data/profile.json')
print(f'✓ Loaded profile: {profile.name}')
"
```

### Step 5: Run Test Search

```bash
# Test full pipeline (uses real AI API!)
python -m job_finder.main

# Or run tests
pytest tests/
```

---

## Troubleshooting

### Common Issues

#### "ModuleNotFoundError: No module named 'job_finder'"

**Cause**: Package not installed or wrong directory

**Fix**:
```bash
# Ensure you're in project root
pwd

# Install in editable mode
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

#### "Firebase credentials not found"

**Cause**: GOOGLE_APPLICATION_CREDENTIALS not set or file missing

**Fix**:
```bash
# Check environment variable
echo $GOOGLE_APPLICATION_CREDENTIALS

# Verify file exists
ls -la ~/.firebase/serviceAccountKey.json

# Set in .env
echo 'GOOGLE_APPLICATION_CREDENTIALS=/home/user/.firebase/serviceAccountKey.json' >> .env

# Reload environment
source .env
```

#### "Permission denied" on Docker commands

**Cause**: User not in docker group

**Fix**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Activate group (or log out/in)
newgrp docker

# Test
docker ps
```

#### "serviceAccountKey.json not found" in Docker

**Cause**: Volume mount path incorrect

**Fix**:
```yaml
# In docker-compose file, adjust path:
volumes:
  - ~/.firebase:/app/credentials:ro  # Adjust ~/.firebase to your actual path
```

#### Environment Variables Not Set in Docker

**Cause**: Variables not passed to container

**Fix**:
```bash
# Export before running docker-compose
export ANTHROPIC_API_KEY="your-key"

# Or create .env file in project root
cat > .env << 'EOF'
ANTHROPIC_API_KEY=your-key
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/serviceAccountKey.json
EOF
```

#### Container Exits Immediately

**Cause**: Startup error

**Fix**:
```bash
# Check logs for errors
docker-compose logs

# Or run with interactive shell
docker run -it job-finder:latest /bin/bash
```

### Verify Environment Setup

Run this comprehensive check:

```bash
python << 'EOF'
import os
import sys
from pathlib import Path

print("=== Environment Check ===\n")

# Python version
print(f"Python: {sys.version}")

# Environment variables
api_key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('OPENAI_API_KEY')
creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

print(f"API Key: {'✓ Set' if api_key else '✗ Missing'}")
print(f"Firebase Creds: {'✓ Set' if creds else '✗ Missing'}")

if creds:
    print(f"Creds Path: {creds}")
    print(f"Creds Exists: {'✓ Yes' if Path(creds).exists() else '✗ No'}")

# Imports
try:
    import anthropic
    import openai
    import pydantic
    import firebase_admin
    from google.cloud import firestore
    from job_finder.profile.firestore_loader import FirestoreProfileLoader
    print("\n✓ All imports successful")
except ImportError as e:
    print(f"\n✗ Import error: {e}")

print("\n=== Check Complete ===")
EOF
```

### Database Connection Issues

**Check which database is being used:**

```bash
# View environment variables in Docker
docker exec job-finder-staging env | grep DATABASE

# Expected output:
# PROFILE_DATABASE_NAME=portfolio-staging
# STORAGE_DATABASE_NAME=portfolio-staging
```

**Force specific database:**

```bash
docker exec job-finder-staging \
  env STORAGE_DATABASE_NAME=portfolio-staging \
  python -m job_finder.main
```

### Profile Loading from Wrong Database

```bash
docker exec job-finder-staging python -c "
from job_finder.profile.firestore_loader import FirestoreProfileLoader
loader = FirestoreProfileLoader(database_name='portfolio-staging')
profile = loader.load_profile(name='Josh Wentworth')
print(f'Database: {loader.database_name}')
print(f'Experiences: {len(profile.experience)}')
print(f'Skills: {len(profile.skills)}')
"
```

---

## Next Steps

After successful setup:

1. **Configure Job Sources**: See [Development Guide](development.md#managing-job-sources)
2. **Run Your First Search**: `python -m job_finder.main`
3. **Set Up Queue Mode**: See [Queue System Guide](queue-system.md)
4. **Deploy to Production**: See [Deployment Guide](deployment.md)

---

## Additional Resources

- **[Architecture](architecture.md)** - System design and components
- **[Development](development.md)** - Development workflow
- **[Queue System](queue-system.md)** - Queue-based processing
- **[Deployment](deployment.md)** - Production deployment

---

**Last Updated:** 2025-10-16
