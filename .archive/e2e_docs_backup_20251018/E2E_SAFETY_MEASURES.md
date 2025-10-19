# E2E Test Safety Measures

## Overview

The E2E test suite is **hardcoded to only run on `portfolio-staging`** with multiple safety measures to prevent accidental production usage.

## Safety Measures Implemented

### 1. ✅ Makefile Hardcoded to Staging

**File**: `Makefile` (line ~166)

```makefile
test-e2e-full: ## Run complete E2E suite (STAGING ONLY)
	@echo "⚠️  WARNING: This will CLEAR collections in portfolio-staging database"
	@echo "✓ Safe: Testing on portfolio-staging (not production)"
	...
	--database portfolio-staging \  # HARDCODED
```

**Protection**: The database parameter is explicitly set to `portfolio-staging` in the Makefile.

### 2. ✅ Default Database is Staging

**Files**: 
- `tests/e2e/data_collector.py` (line ~792)
- `tests/e2e/run_with_streaming.py` (line ~267)

```python
parser.add_argument(
    "--database",
    default="portfolio-staging",  # DEFAULT
    help="Firestore database name (default: portfolio-staging)",
)
```

**Protection**: If someone runs the script directly without specifying a database, it defaults to staging.

### 3. ✅ Production Database Blocker

**Files**: 
- `tests/e2e/data_collector.py` (line ~817)
- `tests/e2e/run_with_streaming.py` (line ~308)

```python
# SAFETY CHECK: Prevent accidental production usage
if args.database == "portfolio" and not args.allow_production:
    logger.error("🚨 PRODUCTION DATABASE BLOCKED 🚨")
    logger.error("This test would CLEAR and MODIFY the production database!")
    logger.error("Use --database portfolio-staging instead.")
    sys.exit(1)
```

**Protection**: Scripts will **refuse to run** on production database unless explicitly forced with `--allow-production` flag.

### 4. ✅ 10-Second Abort Window

If someone bypasses the blocker with `--allow-production`, there's a 10-second countdown:

```python
if args.database == "portfolio":
    logger.warning("⚠️  RUNNING ON PRODUCTION DATABASE ⚠️")
    logger.warning("Press Ctrl+C within 10 seconds to abort...")
    time.sleep(10)
```

**Protection**: Gives time to abort before any changes are made.

### 5. ✅ Clear Visual Warnings

The Makefile now shows:

```
⚠️  WARNING: This will CLEAR collections in portfolio-staging database
✓ Safe: Testing on portfolio-staging (not production)
Database: portfolio-staging
```

**Protection**: Makes it obvious which database is being used.

## How to Run Tests Safely

### ✅ Correct Usage (Staging)

```bash
# Run via Makefile (recommended)
make test-e2e-full

# Or run directly
python tests/e2e/data_collector.py --database portfolio-staging

# Database parameter not needed (defaults to staging)
python tests/e2e/data_collector.py
```

### ❌ What's Blocked

```bash
# This will be BLOCKED
python tests/e2e/data_collector.py --database portfolio

# Output:
# 🚨 PRODUCTION DATABASE BLOCKED 🚨
# This test would CLEAR and MODIFY the production database!
# Use --database portfolio-staging instead.
# Exit code: 1
```

### ⚠️ Override (Not Recommended)

```bash
# Only if you REALLY need to test on production (DANGEROUS!)
python tests/e2e/data_collector.py \
    --database portfolio \
    --allow-production

# Will show 10-second countdown before proceeding
```

## What the Test Does

### Destructive Actions (Why Production is Blocked)

1. **Clears collections**:
   - `job-listings` → Deletes all documents
   - `companies` → Deletes all documents
   - `job-sources` → Deletes all documents
   - `job-queue` → Deletes all documents

2. **Submits test jobs**:
   - Adds 4 test jobs to the queue
   - Worker processes them (creates new data)

3. **Modifies data**:
   - Creates new job-matches
   - Creates new companies
   - Creates new job-listings

### Staging vs Production

| Aspect | Staging | Production |
|--------|---------|------------|
| **Database** | `portfolio-staging` | `portfolio` |
| **Worker** | `job-finder-staging` container | `job-finder-production` container |
| **Data Impact** | ✅ Safe to clear/modify | ❌ Would lose real data |
| **User Impact** | ✅ No users affected | ❌ Would affect live users |
| **Test Allowed** | ✅ Yes (default) | ❌ Blocked by safety check |

## Verification Checklist

Before running E2E tests, verify:

- [ ] Makefile shows `--database portfolio-staging`
- [ ] No environment variables override database name
- [ ] Running via `make test-e2e-full` (not manual invocation with different DB)
- [ ] You see "Safe: Testing on portfolio-staging" message
- [ ] Test results go to `test_results/e2e_*/` directory

## Emergency: If Test Ran on Production

If the safety checks were somehow bypassed:

1. **Stop the test immediately**: Press Ctrl+C
2. **Check what was deleted**: Look in `test_results/*/backup_original/`
3. **Restore from backup**: The test creates backups before clearing
4. **Contact team**: Notify others of the incident

### Restore Command

```bash
# Check the backup
ls test_results/e2e_*/backup_original/

# Backups are in JSON format:
# - job-listings.json
# - companies.json
# - job-sources.json

# Use Firebase console or restoration script to restore
```

## Additional Protections

### Environment Isolation

- **Staging credentials**: Used via `GOOGLE_APPLICATION_CREDENTIALS`
- **Separate databases**: `portfolio-staging` vs `portfolio`
- **Separate workers**: Different containers processing different queues

### Code Review

- All E2E test changes should be reviewed
- Check for any `--database portfolio` in code
- Verify safety checks are not removed

### CI/CD

If running in CI/CD:

```yaml
# Example GitHub Actions
env:
  TEST_DATABASE: portfolio-staging  # Explicitly set
  
test:
  run: make test-e2e-full
  # Will use staging by default
```

## Summary

The E2E tests are **production-safe by design**:

1. ✅ **Hardcoded** to staging in Makefile
2. ✅ **Defaults** to staging in scripts
3. ✅ **Blocks** production database explicitly
4. ✅ **Warns** with 10-second abort window
5. ✅ **Shows** clear database name in output

To run on production, someone would need to:
1. Bypass the Makefile
2. Run the script directly with `--database portfolio`
3. Add the `--allow-production` flag
4. Wait through the 10-second warning

This makes accidental production usage **nearly impossible**.
