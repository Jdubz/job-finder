# Local Development & Testing Guide

## Recommended: Use App-Monitor (Primary Method)

**For local development, use the dev-monitor tool to manage all services including the Python worker via Docker.**

The dev-monitor is a local development console that manages:
- Firebase Emulators (Firestore, Functions)
- Frontend development server
- Backend Firebase Functions
- **Python Worker (via Docker container)**

### Start App-Monitor

```bash
# From the job-finder-app-manager repository root
cd dev-monitor

# Start all services (including Python worker in Docker)
make dev-monitor

# Or start specific services
make start-worker  # Start Python worker container only
```

### View Worker Logs

```bash
# Worker logs are available at:
tail -f dev-monitor/logs/queue_worker.log

# Or via the dev-monitor web UI at http://localhost:5174
```

### Restart Worker After Code Changes

The Python worker runs in a Docker container managed by dev-monitor. After making code changes:

```bash
# Rebuild and restart the worker container
make restart-worker

# Or rebuild from scratch
make rebuild-worker
```

---

## Alternative: Manual Docker Testing

For testing specific Docker configurations without dev-monitor, use these docker-compose files.

### Prerequisites

```bash
# Ensure your credentials are in place
ls ~/.firebase/serviceAccountKey.json

# Ensure environment variables are set
echo $ANTHROPIC_API_KEY

# Create logs directory if it doesn't exist
mkdir -p logs data
```

## Option 1: Test Production Container (from ghcr.io)

Tests the exact same container that's deployed in Portainer.

```bash
# Pull and run the production container
docker-compose -f docker-compose.local-prod.yml up

# In another terminal, exec into the running container
docker exec -it job-finder-local-prod /bin/bash

# Inside the container, test manually:
python scripts/workers/scripts/workers/scheduler.py
# or
python run_job_search.py
```

### Run scheduler once and exit:
```bash
# Edit docker-compose.local-prod.yml and change the command to:
# command: python scripts/workers/scripts/workers/scheduler.py

docker-compose -f docker-compose.local-prod.yml up
```

### Test cron behavior:
```bash
# Edit docker-compose.local-prod.yml and change the command to:
# command: /bin/bash -c "printenv > /etc/environment && cron && tail -f /var/log/cron.log"

docker-compose -f docker-compose.local-prod.yml up
```

### View logs:
```bash
# Container logs
docker-compose -f docker-compose.local-prod.yml logs -f

# Scheduler logs (from mounted volume)
tail -f logs/scheduler.log

# Cron logs (inside container)
docker exec job-finder-local-prod tail -f /var/log/cron.log
```

### Cleanup:
```bash
docker-compose -f docker-compose.local-prod.yml down
```

---

## Option 2: Test Local Build

Builds from your local Dockerfile and source code. Use this to test changes before pushing.

```bash
# Build and run from local source
docker-compose -f docker-compose.local-build.yml up --build

# In another terminal, exec into the running container
docker exec -it job-finder-local-build /bin/bash

# Inside the container, test manually:
python scripts/workers/scripts/workers/scheduler.py
# or
python run_job_search.py
```

### Run scheduler once and exit:
```bash
# Edit docker-compose.local-build.yml and change the command to:
# command: python scripts/workers/scripts/workers/scheduler.py

docker-compose -f docker-compose.local-build.yml up --build
```

### Test cron behavior:
```bash
# Edit docker-compose.local-build.yml and change the command to:
# command: /bin/bash -c "printenv > /etc/environment && cron && tail -f /var/log/cron.log"

docker-compose -f docker-compose.local-build.yml up --build
```

### Rebuild after code changes:
```bash
docker-compose -f docker-compose.local-build.yml up --build --force-recreate
```

### Cleanup:
```bash
docker-compose -f docker-compose.local-build.yml down
docker rmi job-finder:local  # Remove local image
```

---

## Troubleshooting

### Check if environment variables are passed correctly:
```bash
docker exec job-finder-local-prod env | grep -E 'ANTHROPIC|GOOGLE'
```

### Check if credentials file is mounted:
```bash
docker exec job-finder-local-prod ls -la /app/credentials/
docker exec job-finder-local-prod cat /app/credentials/serviceAccountKey.json
```

### Check if config is mounted:
```bash
docker exec job-finder-local-prod cat /app/config/config.yaml
```

### Check if cron is running:
```bash
docker exec job-finder-local-prod ps aux | grep cron
```

### Check crontab is installed:
```bash
docker exec job-finder-local-prod crontab -l
```

### Manually trigger cron job:
```bash
docker exec job-finder-local-prod /bin/bash -c "cd /app && /usr/local/bin/python scripts/workers/scripts/workers/scheduler.py"
```

### Check Python path and imports:
```bash
docker exec job-finder-local-prod python -c "import sys; print(sys.path)"
docker exec job-finder-local-prod python -c "from job_finder.search_orchestrator import JobSearchOrchestrator; print('OK')"
```

---

## Common Issues

### "Permission denied" on docker commands
```bash
# Activate docker group in current shell
newgrp docker

# Or log out and back in
```

### "serviceAccountKey.json not found"
```bash
# Adjust the volume mount path in the docker-compose file
# Change: ~/.firebase:/app/credentials:ro
# To your actual credentials path
```

### Environment variables not set
```bash
# Export them in your shell before running docker-compose
export ANTHROPIC_API_KEY="your-key-here"

# Or create a .env file in the project root
cat > .env << 'EOF'
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
EOF
```

### Container exits immediately
```bash
# Check logs for errors
docker-compose -f docker-compose.local-prod.yml logs

# The default command keeps the container running for inspection
# If it exits, there's likely a startup error
```

---

## What's Different Between These Files?

### docker-compose.local-prod.yml
- Uses `image: ghcr.io/jdubz/job-finder:latest` (pulls from registry)
- Tests the production container
- Use this to debug Portainer deployment issues
- Faster startup (no build)

### docker-compose.local-build.yml
- Uses `build: .` (builds from local Dockerfile)
- Tests your local code changes
- Use this before pushing to main
- Slower startup (builds every time with --build)

### docker-compose.yml (staging deployment)
- Production-ready deployment file
- Includes Watchtower for auto-updates
- Resource limits configured
- Healthchecks enabled
- Use this in Portainer stacks
