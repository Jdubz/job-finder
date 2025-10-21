# Development Workflow with Firebase Emulators

This guide explains how to develop the Job Finder worker locally using Docker and Firebase Emulators.

## Overview

The development workflow uses:

- **Firebase Emulators** (from job-finder-BE) for Auth, Firestore, Functions, and Storage
- **Docker container** for the Python worker with mounted source code
- **Emulator connectivity** via `host.docker.internal` from container to host

## Architecture

```
┌─────────────────────────────────────────────┐
│ Host Machine                                │
│                                             │
│  ┌────────────────────────────────────┐    │
│  │ job-finder-BE/functions            │    │
│  │ Firebase Emulators                 │    │
│  │  - Auth (9099)                     │    │
│  │  - Firestore (8080)                │    │
│  │  - Functions (5001)                │    │
│  │  - Storage (9199)                  │    │
│  │  - UI (4000)                       │    │
│  └────────────────────────────────────┘    │
│         ▲                                   │
│         │ host.docker.internal              │
│         │                                   │
│  ┌──────┴──────────────────────────────┐   │
│  │ Docker Container                    │   │
│  │ job-finder-worker                   │   │
│  │  - Python worker                    │   │
│  │  - Mounted source code              │   │
│  │  - config.dev.yaml                  │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

1. **Docker** and **Docker Compose** installed
2. **job-finder-BE** repository cloned in the same parent directory
3. **API keys** set in environment:
   ```bash
   export ANTHROPIC_API_KEY="your-key-here"
   export OPENAI_API_KEY="your-key-here"  # optional
   ```

### Start Development Environment

Use the helper script to start everything:

```bash
./scripts/dev/start-dev.sh
```

This will:
1. Check if Firebase Emulators are running
2. Start emulators if needed (from ../job-finder-BE)
3. Start the worker Docker container
4. Connect container to emulators via `host.docker.internal`

### Manual Start (Alternative)

If you prefer manual control:

**Terminal 1 - Start Emulators:**
```bash
cd ../job-finder-BE/functions
npm run emulators:start
```

**Terminal 2 - Start Worker:**
```bash
docker-compose -f docker-compose.dev.yml up
```

## Development Workflow

### 1. Make Code Changes

Edit files in `src/`, `scripts/`, or `tests/` - they are mounted into the container.

### 2. Restart Worker

Changes to Python code require restarting:

```bash
docker-compose -f docker-compose.dev.yml restart
```

### 3. View Logs

```bash
docker-compose -f docker-compose.dev.yml logs -f
```

### 4. Enter Container Shell

```bash
./scripts/dev/dev-shell.sh

# Or manually:
docker-compose -f docker-compose.dev.yml exec job-finder bash
```

Inside the container, you can:

```bash
# Run tests
pytest

# Run specific test
pytest tests/test_firestore_storage.py -v

# Run the worker manually
python run_job_search.py

# Check emulator connectivity
curl http://host.docker.internal:8080
curl http://host.docker.internal:9099
```

### 5. View Emulator Data

Open the Emulator UI in your browser:

```
http://localhost:4000
```

You can:
- View Firestore documents in real-time
- Inspect queue items
- Check auth users
- View function logs
- Manually add test data

### 6. Stop Development Environment

```bash
./scripts/dev/stop-dev.sh
```

This stops:
- Worker container
- Firebase Emulators

**Note:** Emulator data persists in `.firebase/emulator-data/` (in job-finder-BE)

## Configuration

### config.dev.yaml

The development config (`config/config.dev.yaml`) is optimized for local development:

- **Database**: `(default)` - Emulator default database
- **AI thresholds**: Lower for easier testing
- **Scraping**: Disabled external sites (use mock data)
- **Logging**: Console only (no Cloud Logging)
- **Queue**: Enabled with faster polling

Key differences from production:

| Setting | Production | Development |
|---------|-----------|-------------|
| Database | `portfolio` | `(default)` |
| Min match score | 80 | 60 |
| External scraping | Enabled | Disabled |
| Mock data | No | Yes |
| Cloud logging | Yes | No |
| Poll interval | 30s | 5s |

### Environment Variables

Set in `docker-compose.dev.yml`:

```yaml
FIRESTORE_EMULATOR_HOST=host.docker.internal:8080
FIREBASE_AUTH_EMULATOR_HOST=host.docker.internal:9099
PROFILE_DATABASE_NAME=(default)
STORAGE_DATABASE_NAME=(default)
CONFIG_PATH=/app/config/config.dev.yaml
ENVIRONMENT=development
```

## Common Tasks

### Run Queue Worker

The container automatically starts the worker. To run manually:

```bash
./scripts/dev/dev-shell.sh

# Inside container:
python run_job_search.py
```

### Test Firestore Connection

```bash
./scripts/dev/dev-shell.sh

# Inside container:
python -c "
from google.cloud import firestore
import os
print(f'Emulator: {os.getenv(\"FIRESTORE_EMULATOR_HOST\")}')
db = firestore.Client(project='demo-project', database='(default)')
print(f'Connected to Firestore')
"
```

### Seed Test Data

Create test users and data in emulators:

```bash
# From job-finder-BE
cd ../job-finder-BE/functions
npm run emulators:seed
```

### Clear Emulator Data

Start fresh with empty database:

```bash
cd ../job-finder-BE
npm run emulators:clear
npm run emulators:start
```

### Run Tests

```bash
./scripts/dev/dev-shell.sh

# Inside container:
pytest
pytest --cov=src
pytest tests/queue/ -v
```

## Troubleshooting

### Worker can't connect to emulators

**Symptom:** Container logs show connection errors to Firestore/Auth

**Solution:**

1. Verify emulators are running:
   ```bash
   curl http://localhost:4000
   ```

2. Check `extra_hosts` in docker-compose.dev.yml:
   ```yaml
   extra_hosts:
     - "host.docker.internal:host-gateway"
   ```

3. Test from inside container:
   ```bash
   docker-compose -f docker-compose.dev.yml exec job-finder bash
   curl http://host.docker.internal:8080
   ```

### Emulators won't start

**Check logs:**
```bash
tail -f /tmp/firebase-emulators.log
```

**Common causes:**
- Ports already in use (kill existing emulators)
- Missing dependencies in job-finder-BE

### Source code changes not reflected

**Volumes not mounted correctly:**

```bash
# Rebuild container
docker-compose -f docker-compose.dev.yml up --build

# Verify mounts
docker-compose -f docker-compose.dev.yml exec job-finder ls -la /app/src
```

### Permission errors

**Fix file ownership:**

```bash
# On host
sudo chown -R $USER:$USER src/ tests/ scripts/

# Rebuild container
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up --build
```

### API keys not available

**Set in shell before starting:**

```bash
export ANTHROPIC_API_KEY="your-key"
docker-compose -f docker-compose.dev.yml up
```

**Or add to `.env` file** (gitignored):

```bash
# .env
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
```

## Best Practices

### 1. Always Use Emulators for Development

Never connect to production databases during development. Use emulators exclusively.

### 2. Keep Emulator Data Clean

Periodically clear emulator data to ensure tests are reproducible:

```bash
cd ../job-finder-BE
npm run emulators:clear
```

### 3. Use Mock Data

Enable `mock_scraping: true` in config.dev.yaml to avoid hitting real job sites.

### 4. Version Your Config

Keep `config.dev.yaml` in git so other developers have the same setup.

### 5. Test in Container

Always test in the Docker container, not on host, to ensure consistency.

### 6. Monitor Emulator UI

Keep the Emulator UI open at `localhost:4000` to watch data flow in real-time.

### 7. Commit Often

With mounted volumes, you're editing files directly. Commit frequently.

## Integration with Backend

### Calling Backend Functions

The worker can call backend Cloud Functions in the emulator:

```python
import requests

# Call a function in the emulator
response = requests.post(
    "http://host.docker.internal:5001/demo-project/us-central1/yourFunction",
    json={"data": {"key": "value"}}
)
```

### Sharing Data

Both worker and backend use the same Firestore emulator:

- Worker writes to `job-matches`
- Backend reads from `job-matches`
- Both use Auth emulator for users

### Testing Full Flow

1. **Backend creates job queue item** (via Emulator UI or function)
2. **Worker picks up item** from queue
3. **Worker processes job** and creates match
4. **Backend reads match** from Firestore
5. **Frontend displays match** (if running)

## Related Documentation

- [Firebase Emulators](../../job-finder-BE/docs/development/EMULATORS.md)
- [Docker Compose Reference](./DOCKER_COMPOSE.md)
- [Configuration Guide](./CONFIGURATION.md)
- [Testing Guide](./TESTING.md)

## Support

For issues:

1. Check container logs: `docker-compose -f docker-compose.dev.yml logs`
2. Check emulator logs: `tail -f /tmp/firebase-emulators.log`
3. Review Emulator UI: `http://localhost:4000`
4. Contact team in project Slack
