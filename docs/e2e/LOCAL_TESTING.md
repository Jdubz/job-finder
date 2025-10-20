# Local E2E Testing with Firebase Emulators

**Complete guide to running end-to-end tests locally without touching staging or production data**

---

## Overview

Local E2E testing uses Firebase emulators running in the portfolio project to provide a completely isolated test environment. This allows you to:

- **Test the complete pipeline** locally before pushing to staging
- **Iterate faster** without waiting for cloud deployments
- **Debug issues** with full visibility into emulator data
- **Avoid cloud costs** during development
- **Keep data isolated** from staging and production

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Local E2E Test                          │
│                                                             │
│  ┌─────────────┐       ┌──────────────┐                   │
│  │  Job-Finder │ ───── │   Firebase   │                   │
│  │  (Docker or │       │   Emulators  │                   │
│  │   Python)   │       │  (job-finder-FE) │                   │
│  └─────────────┘       └──────────────┘                   │
│         │                      │                            │
│         │                      ├─ Firestore: localhost:8080│
│         │                      ├─ Auth: localhost:9099     │
│         │                      └─ UI: localhost:4000       │
│         │                                                   │
│         └──────── FIRESTORE_EMULATOR_HOST ─────────────────┤
│                                                             │
│  No network calls to staging or production!                │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### 1. job-finder-FE Firebase Emulators Running

The portfolio project must have Firebase emulators running on your local machine.

**Start emulators (in portfolio directory):**
```bash
cd ~/Development/portfolio
make firebase-emulators
```

**Verify emulators are running:**
- Firestore UI: http://localhost:4000/firestore
- Auth UI: http://localhost:4000/auth
- Emulator Suite: http://localhost:4000

### 2. API Keys (Optional)

AI matching requires API keys. Tests will run without them but AI matching will be skipped.

**IMPORTANT:** Local E2E tests use **REAL AI APIs** (not stubs or mocks). This means:
- ✅ Tests validate actual AI integration
- ✅ You'll see real AI match scores and analysis
- ❌ Tests consume API credits/tokens (minimal cost ~$0.01-0.05 per test run)
- ❌ Tests will fail if API keys are invalid

```bash
# In job-finder/.env
ANTHROPIC_API_KEY=your_key_here
# or
OPENAI_API_KEY=your_key_here
```

**Cost Estimate:**
- Fast mode (4 jobs): ~$0.01-0.02
- Full mode (20+ jobs): ~$0.05-0.10

### 3. Docker (Optional)

Docker is optional. You can run tests with or without Docker:
- **With Docker**: Closer to production environment
- **Without Docker**: Faster, easier debugging

Check Docker availability:
```bash
docker --version
docker compose version
```

---

## Quick Start

### Option 1: Fast Test with Docker (Recommended)
```bash
make test-e2e-local
```

**What happens:**
1. Checks emulators are running
2. Builds Docker image
3. Runs fast E2E test (4 jobs)
4. Saves results to `test_results/e2e_local_*/`

**Duration:** ~2-3 minutes

### Option 2: Fast Test without Docker
```bash
make test-e2e-local-no-docker
```

**What happens:**
1. Checks emulators are running
2. Runs test directly with Python
3. Faster startup, easier debugging

**Duration:** ~2-3 minutes

### Option 3: Full Test (20+ jobs)
```bash
make test-e2e-local-full
```

**Duration:** ~10-15 minutes

### Option 4: Verbose Logging
```bash
make test-e2e-local-verbose
```

**Use when:** Debugging issues

---

## Test Modes

### Fast Mode (Default)
- **4 test jobs** (1 per type)
- **Quick validation** of core functionality
- **Best for:** Regular development, CI/CD
- **Duration:** 2-3 minutes

**Test jobs:**
- 1x Greenhouse job
- 1x Workday job
- 1x Lever job
- 1x RSS feed job

### Full Mode
- **20+ test jobs** (comprehensive coverage)
- **All job types** and edge cases
- **Best for:** Pre-release validation, regression testing
- **Duration:** 10-15 minutes

**Test jobs:**
- 5x Greenhouse jobs (different scenarios)
- 5x Workday jobs
- 5x Lever jobs
- 5x RSS feed jobs
- Edge cases (duplicates, invalid URLs, etc.)

---

## Execution Methods

### Method 1: Docker (Production-like)

**Pros:**
- ✅ Closer to production environment
- ✅ Isolated dependencies
- ✅ Consistent results

**Cons:**
- ❌ Slower startup (build time)
- ❌ Harder to debug

**Command:**
```bash
# Fast test
make test-e2e-local

# Full test
make test-e2e-local-full

# With rebuild
python tests/e2e/run_local_e2e.py --build
```

### Method 2: Direct Python (Fast Development)

**Pros:**
- ✅ Faster startup (no Docker build)
- ✅ Easier debugging (breakpoints work)
- ✅ Direct access to logs

**Cons:**
- ❌ Depends on local Python environment
- ❌ May differ from production

**Command:**
```bash
# Fast test
make test-e2e-local-no-docker

# Full test
python tests/e2e/run_local_e2e.py --full --no-docker

# With verbose logging
python tests/e2e/run_local_e2e.py --no-docker --verbose
```

---

## Configuration

### Test Configuration File

**Location:** `config/config.local-e2e.yaml`

**Key settings:**
```yaml
# Profile Configuration
profile:
  source: "firestore"
  firestore:
    database_name: "(default)"  # Emulator default database

# Storage Configuration
storage:
  database_name: "(default)"

# Queue Configuration
queue:
  poll_interval: 30  # Faster polling for tests
  exit_when_empty: true  # Auto-exit when done

# E2E Test Settings
e2e:
  fast_mode: true
  test_jobs:
    jobs_per_type: 1
```

### Environment Variables

**Emulator connection:**
```bash
FIRESTORE_EMULATOR_HOST=localhost:8080
FIREBASE_AUTH_EMULATOR_HOST=localhost:9099
```

**Database selection:**
```bash
PROFILE_DATABASE_NAME=(default)
STORAGE_DATABASE_NAME=(default)
```

**Test mode:**
```bash
E2E_TEST_MODE=true
CONFIG_PATH=config/config.local-e2e.yaml
```

---

## Results & Output

### Output Directory Structure

```
test_results/e2e_local_YYYYMMDD_HHMMSS/
├── summary.txt                  # High-level test summary
├── test_run.log                 # Detailed execution log
├── backup/                      # Firestore backups (if any)
│   ├── job-listings.json
│   ├── job-matches.json
│   └── job-queue.json
├── submissions/                 # Job submission records
│   ├── job_001.json
│   ├── job_002.json
│   └── ...
└── analysis/                    # Results analysis
    ├── decision_tree_validation.txt
    ├── data_quality_report.json
    └── issues.txt
```

### Reading Results

**Quick summary:**
```bash
cat test_results/e2e_local_*/summary.txt
```

**Detailed logs:**
```bash
less test_results/e2e_local_*/test_run.log
```

**Check for errors:**
```bash
grep -i "error\|fail" test_results/e2e_local_*/test_run.log
```

**View submission records:**
```bash
ls test_results/e2e_local_*/submissions/
cat test_results/e2e_local_*/submissions/job_001.json
```

---

## Troubleshooting

### Emulators Not Running

**Symptom:**
```
✗ Firebase emulator not running on localhost:8080
```

**Solution:**
```bash
# Start emulators in portfolio project
cd ~/Development/portfolio
make firebase-emulators

# Verify in browser
open http://localhost:4000
```

### Connection Refused

**Symptom:**
```
Error: Connection refused to localhost:8080
```

**Possible causes:**
1. Emulators not running
2. Wrong port number
3. Firewall blocking

**Solution:**
```bash
# Check emulator status
curl http://localhost:8080

# Check if port is in use
lsof -i :8080

# Custom emulator host
python tests/e2e/run_local_e2e.py --emulator-host localhost:8888
```

### Docker Build Fails

**Symptom:**
```
Error: Docker build failed
```

**Solution:**
```bash
# Check Docker is running
docker ps

# Build manually to see errors
docker build -t job-finder:local-e2e .

# Use no-docker mode
make test-e2e-local-no-docker
```

### API Keys Not Found

**Symptom:**
```
⚠ No AI API keys found in environment
Tests will still run but AI matching will be skipped
```

**Solution:**
```bash
# Add to .env file
echo "ANTHROPIC_API_KEY=your_key_here" >> .env

# Or export directly
export ANTHROPIC_API_KEY=your_key_here
make test-e2e-local
```

### Tests Hang

**Symptom:**
Test runs indefinitely without completing

**Possible causes:**
1. Queue worker not processing
2. Emulator crashed
3. Network issues

**Solution:**
```bash
# Check emulator UI
open http://localhost:4000

# Check emulator logs (in portfolio terminal)

# Kill and restart
Ctrl+C
make test-e2e-local
```

### Permission Denied

**Symptom:**
```
Permission denied: tests/e2e/run_local_e2e.py
```

**Solution:**
```bash
chmod +x tests/e2e/run_local_e2e.py
```

---

## Advanced Usage

### Custom Emulator Host

If emulators are running on a different machine or port:

```bash
python tests/e2e/run_local_e2e.py \
  --emulator-host 192.168.1.100:8080 \
  --auth-emulator-host 192.168.1.100:9099
```

### Custom Test Jobs

Edit `config/config.local-e2e.yaml`:

```yaml
e2e:
  test_jobs:
    jobs_per_type: 3  # More jobs per type
    types:
      - greenhouse
      - workday
      # Remove lever to skip lever tests
```

### Debugging with Breakpoints

**Without Docker:**
```bash
# Run directly with Python
python tests/e2e/run_local_e2e.py --no-docker

# Add breakpoint in code
import pdb; pdb.set_trace()
```

**With Docker:**
```bash
# Run container interactively
docker compose -f docker-compose.local-e2e.yml run \
  --rm job-finder-e2e bash

# Then run test manually inside container
python tests/e2e/data_collector.py --database "(default)" --fast-mode
```

### Parallel Tests

Run multiple test instances in parallel:

```bash
# Terminal 1
TEST_RUN_ID=run_1 make test-e2e-local

# Terminal 2
TEST_RUN_ID=run_2 make test-e2e-local
```

---

## Comparison: Local vs Staging vs Production

| Feature | Local E2E | Staging E2E | Production |
|---------|-----------|-------------|------------|
| **Data** | Emulator (ephemeral) | portfolio-staging | portfolio |
| **Speed** | Fast (~2-3 min) | Medium (~5-10 min) | N/A (read-only) |
| **Safety** | 100% safe | Safe (isolated) | READ ONLY |
| **Debugging** | Easy (local) | Medium (cloud logs) | Hard (limited access) |
| **Cost** | Free | Minimal | Production costs |
| **Network** | None (localhost) | Internet required | Internet required |
| **Use Case** | Development, debugging | Pre-release validation | Monitoring only |

**Recommendation:**
1. **Development:** Use local E2E tests
2. **Pre-release:** Use staging E2E tests
3. **Production:** Read-only monitoring only

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Local E2E Tests

on: [pull_request]

jobs:
  e2e-local:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Firebase Emulators
        run: |
          npm install -g firebase-tools
          firebase emulators:start --only firestore,auth &
          sleep 10
      
      - name: Run Local E2E Tests
        run: |
          make test-e2e-local-no-docker
      
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: e2e-results
          path: test_results/
```

---

## Best Practices

### ✅ Do

- **Use local E2E for regular development** - Fast feedback loop
- **Run before pushing** - Catch issues early
- **Check emulator UI** - View data in http://localhost:4000
- **Keep test jobs minimal** - Fast mode for regular runs
- **Use verbose mode for debugging** - Get detailed logs

### ❌ Don't

- **Don't skip emulator check** - Always verify emulators are running
- **Don't commit test results** - Results are in `.gitignore`
- **Don't rely solely on local tests** - Still need staging validation
- **Don't leave emulators running** - Clean up after testing
- **Don't modify emulator data manually** - Let tests manage data

---

## FAQ

**Q: Do I need Docker?**
A: No, use `--no-docker` flag to run directly with Python.

**Q: Can I run without portfolio emulators?**
A: No, emulators are required for local E2E tests.

**Q: How do I reset emulator data?**
A: Restart emulators - data is ephemeral.

**Q: Can I test with real staging data?**
A: Use `make test-e2e` for staging tests.

**Q: Are results saved permanently?**
A: Yes, in `test_results/` directory (not committed to git).

**Q: Can I run multiple tests simultaneously?**
A: Yes, use different `TEST_RUN_ID` values.

**Q: What if emulators crash during test?**
A: Tests will fail gracefully. Restart emulators and try again.

---

## Summary

**Quick Start:**
```bash
# 1. Start portfolio emulators
cd ~/Development/portfolio && make firebase-emulators

# 2. Run local E2E test
cd ~/Development/job-finder && make test-e2e-local

# 3. View results
cat test_results/e2e_local_*/summary.txt
```

**Key Benefits:**
- ✅ 100% safe (no prod/staging data)
- ✅ Fast (2-3 minutes)
- ✅ Easy debugging (local environment)
- ✅ Free (no cloud costs)
- ✅ Isolated (emulator data only)

**When to Use:**
- Daily development
- Before pushing code
- Debugging issues
- Rapid iteration

**When to Use Staging Instead:**
- Pre-release validation
- Integration testing with real data
- Performance testing
- Final QA before production
