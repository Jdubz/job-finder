# E2E Testing Documentation

**Complete end-to-end testing suite for Job-Finder**

---

## 📖 Quick Links

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[Getting Started](./GETTING_STARTED.md)** | Setup and run your first E2E test | New to E2E testing |
| **[Local Testing](./LOCAL_TESTING.md)** | Test with Firebase emulators (no cloud) | Daily development |
| **[User Guide](./USER_GUIDE.md)** | Running tests, interpreting results | Day-to-day testing |
| **[Architecture](./ARCHITECTURE.md)** | How E2E tests work internally | Understanding the system |
| **[Troubleshooting](./TROUBLESHOOTING.md)** | Common issues and solutions | When tests fail |
| **[Safety Guide](./SAFETY.md)** | Production protection measures | Security concerns |

---

## 🚀 Quick Start

### Run E2E Tests

```bash
# Fast test (2 jobs, ~90-120s)
make test-e2e

# Full test (all production data, comprehensive)
make test-e2e-full
```

### What It Tests

- ✅ Job submission and queue processing
- ✅ URL scraping and data extraction
- ✅ AI analysis and job matching
- ✅ Company discovery and tracking
- ✅ Filter application and scoring
- ✅ State-driven decision tree (loop prevention)

---

## 📋 Documentation Structure

### Core Documentation

1. **[GETTING_STARTED.md](./GETTING_STARTED.md)**
   - Prerequisites and setup
   - First test run
   - Understanding test output

2. **[USER_GUIDE.md](./USER_GUIDE.md)**
   - Running different test modes
   - Monitoring test execution
   - Analyzing results
   - Sequential job submission strategy

3. **[ARCHITECTURE.md](./ARCHITECTURE.md)**
   - System design and data flow
   - Database structure (staging vs production)
   - Component overview
   - Loop prevention implementation

4. **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)**
   - Common issues and solutions
   - Debugging techniques
   - Log analysis
   - Known limitations

5. **[SAFETY.md](./SAFETY.md)**
   - Production database protection
   - Safety checks and confirmations
   - Database script security
   - Incident response

### Reference Documentation

6. **[CHANGELOG.md](./CHANGELOG.md)**
   - Version history
   - Recent improvements
   - Breaking changes

7. **[CONTRIBUTING.md](./CONTRIBUTING.md)**
   - Adding new tests
   - Coding standards
   - Pull request process

---

## 🎯 Common Tasks

### Run Fast E2E Test
```bash
make test-e2e
```
- Tests 2 jobs sequentially
- Validates decision tree and loop prevention
- Takes ~90-120 seconds per job
- Best for: Daily development, quick validation

### Run Full E2E Test
```bash
make test-e2e-full
```
- Seeds ALL production data to staging
- Comprehensive quality assessment
- Monitors until all jobs complete
- Best for: Pre-release validation, quality reports

### Check Test Results
```bash
# View latest test summary
cat test_results/e2e_quick_*/summary.txt

# Check for issues
grep -i "error\|fail" test_results/e2e_quick_*/test_run.log

# Validate decision tree
python tests/e2e/validate_decision_tree.py \
    --database portfolio-staging \
    --results-dir test_results/e2e_quick_*
```

---

## 🏗️ System Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     E2E Test Flow                            │
└─────────────────────────────────────────────────────────────┘

1. Backup & Seed
   ├─ Read from: portfolio (production) - READ ONLY
   ├─ Write to: portfolio-staging (test environment)
   └─ Preserves: Original production data

2. Submit Jobs (Sequential)
   ├─ Job 1 → Queue → Process → Monitor until complete
   ├─ Job 2 → Queue → Process → Monitor until complete
   └─ Clear cause-and-effect (no batch confusion)

3. Monitor Queue
   ├─ Poll every 5s for pending/processing items
   ├─ Track: Status changes, errors, completion
   └─ Auto-exit when queue empty

4. Validate Results
   ├─ Decision tree validation (tracking_id, ancestry, depth)
   ├─ Loop detection
   ├─ Data quality checks
   └─ Success rate calculations

5. Generate Reports
   ├─ Summary statistics
   ├─ Collection snapshots
   ├─ Issue identification
   └─ Quality scores
```

### Databases

- **portfolio** (Production) - READ ONLY for seeding data
- **portfolio-staging** (Staging) - WHERE ALL TESTS RUN

### Safety Features

- ✅ Production blocked by default (requires `--allow-production`)
- ✅ 10-second warning before production operations
- ✅ Distinct database clients (staging vs production)
- ✅ All destructive operations target staging only
- ✅ Makefile hardcoded to staging

---

## 📊 Test Modes

### Fast Mode (`test-e2e`)

**Purpose:** Quick validation during development

**Characteristics:**
- Tests: 2 jobs (representative sample)
- Strategy: Sequential submission with per-job monitoring
- Duration: ~3-5 minutes total
- Validates: Decision tree, loop prevention, basic pipeline

**Use Cases:**
- Daily development workflow
- Pre-commit validation
- Quick smoke tests
- Debugging specific issues

### Full Mode (`test-e2e-full`)

**Purpose:** Comprehensive quality assessment

**Characteristics:**
- Tests: ALL production data
- Strategy: Seeds entire production dataset to staging
- Duration: 30-60 minutes (depends on queue size)
- Validates: Complete pipeline, data quality, scaling

**Use Cases:**
- Pre-release validation
- Quality reports for stakeholders
- Performance testing
- Comprehensive regression testing

---

## 🔧 Key Components

### 1. Data Collector (`tests/e2e/data_collector.py`)
- Orchestrates complete E2E test
- Backs up staging data
- Seeds production data
- Submits jobs sequentially
- Monitors queue completion
- Collects results and metrics

### 2. Queue Monitor (`tests/e2e/queue_monitor.py`)
- Standalone queue monitoring utility
- Polls every 5s for status changes
- Tracks pending/processing counts
- Auto-exits when queue empty

### 3. Decision Tree Validator (`tests/e2e/validate_decision_tree.py`)
- Validates loop prevention implementation
- Checks: tracking_id, ancestry_chain, spawn_depth
- Detects infinite loops
- Generates validation report

### 4. Test Job Submitter (in data_collector.py)
- Fetches real job URLs from production
- Submits jobs to staging queue
- Monitors each job until complete
- Sequential strategy: Job 1 → complete → Job 2

---

## 🛡️ Safety & Security

### Production Protection

**Multiple layers prevent accidental production modification:**

1. **CLI Safety Check** - Blocks `--database portfolio` by default
2. **Explicit Flag Required** - Must use `--allow-production` to override
3. **10-Second Warning** - Countdown before production operations
4. **Database Separation** - Distinct clients for staging vs production
5. **Makefile Defaults** - Hardcoded to `portfolio-staging`

**To modify production (NOT RECOMMENDED):**
```bash
python tests/e2e/data_collector.py \
    --database portfolio \
    --allow-production  # Explicit override required
```

See [SAFETY.md](./SAFETY.md) for complete safety documentation.

---

## 📈 Monitoring & Metrics

### Real-Time Monitoring

During test execution, monitor:

```bash
# Watch queue status
watch -n 5 'python tests/e2e/queue_monitor.py --database portfolio-staging --count-only'

# Stream logs
tail -f test_results/e2e_quick_*/test_run.log

# Check Firestore collections
# (Use Firebase Console or gcloud commands)
```

### Success Metrics

- **Job Success Rate:** % of jobs successfully processed
- **Queue Processing Time:** Average time per job
- **Data Quality Score:** 0-100 based on completeness
- **Loop Prevention:** 0 infinite loops detected

---

## 🐛 Common Issues

### No Jobs Fetched from Production

**Symptom:** "Found 0 real job URLs"

**Cause:** Query may need index or collection is empty

**Solution:**
```bash
# Check production has data
python scripts/database/check_job_sources.py

# Run with staging data instead
make test-e2e  # Uses staging data
```

### Queue Not Processing

**Symptom:** Jobs stuck in "pending" status

**Cause:** Queue worker not running or crashed

**Solution:**
```bash
# Check worker status
ps aux | grep queue_worker

# Restart worker
python scripts/workers/queue_worker.py --database portfolio-staging
```

### Duplicate Logging

**Symptom:** Every log message appears twice

**Status:** ✅ **FIXED** (Oct 18, 2025)

**Solution:** Handlers now cleared before adding new ones

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for more issues and solutions.

---

## 🔄 Recent Changes

### October 18, 2025

**Security Improvements:**
- ✅ Added production safety checks to all database scripts
- ✅ Required explicit `--database` flag for all cleanup scripts
- ✅ Added `--allow-production` flag requirement
- ✅ 10-second warning for production operations

**Bug Fixes:**
- ✅ Fixed duplicate logging (all messages appearing twice)
- ✅ Fixed query to fetch jobs without order_by index dependency
- ✅ Removed redundant 180s wait after sequential submission

**Architecture Changes:**
- ✅ Implemented sequential job submission strategy
- ✅ Per-job queue monitoring with auto-exit
- ✅ Removed batch submission (clearer cause-and-effect)

See [CHANGELOG.md](./CHANGELOG.md) for complete history.

---

## 📚 Additional Resources

### External Documentation

- [Firebase Firestore Docs](https://firebase.google.com/docs/firestore)
- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [Git Workflow Guide](../BRANCHING_STRATEGY.md)

### Related Documentation

- [Architecture Overview](../architecture.md)
- [Deployment Guide](../../DEPLOYMENT.md)
- [Data Quality Monitoring](../DATA_QUALITY_MONITORING.md)
- [Database Script Safety](../../DATABASE_SCRIPT_SAFETY.md)

---

## 🤝 Contributing

Want to improve E2E tests? See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### Quick Contribution Workflow

1. Create feature branch: `git checkout -b e2e/your-feature`
2. Make changes and test: `make test-e2e`
3. Document changes in this file
4. Submit PR to `staging` branch
5. Wait for CI/CD checks to pass

---

## 📞 Support

### Getting Help

- **Documentation Issues:** Open issue with `docs` label
- **Test Failures:** Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **Security Concerns:** See [SAFETY.md](./SAFETY.md)
- **Feature Requests:** Open issue with `enhancement` label

### Quick Checks

```bash
# Verify setup
make test  # Run unit tests first

# Check credentials
echo $GOOGLE_APPLICATION_CREDENTIALS

# Test database connection
python scripts/diagnose_production_queue.py --database portfolio-staging
```

---

## 📝 License

See [LICENSE](../../LICENSE) for details.

---

**Last Updated:** October 18, 2025  
**Maintainer:** Job-Finder Team  
**Version:** 2.0.0
