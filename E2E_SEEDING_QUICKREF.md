# Production Seeding - Quick Summary

## What Changed

E2E tests now **seed staging from production** before each run.

## Why This Matters

✅ **Consistent starting state** - Always begin with real production data  
✅ **Recovery from failures** - Failed tests don't corrupt next run  
✅ **Production-safe** - Production is READ ONLY, never modified  
✅ **Real-world testing** - Tests validate against actual data

## How It Works

```
Production (READ) → Copy → Staging (CLEAR) → Restore → Test
```

1. Read collections from production
2. Clear staging collections
3. Copy production data to staging
4. Run tests on staging
5. Validate results

## Usage

```bash
# Standard usage (seeds from production)
make test-e2e-full

# Manual run
python tests/e2e/data_collector.py \
    --database portfolio-staging \
    --source-database portfolio
```

## Safety

- **Production**: READ ONLY ✓ Never modified
- **Staging**: READ + WRITE ⚠️ Cleared each run
- **Separate clients**: Different Firestore connections
- **Explicit logging**: Shows which DB is source vs test

## What Gets Saved

1. **`production_snapshot/`** - Copy of production at test start
2. **`staging_backup_before/`** - Staging before test (for rollback)
3. **`final_*.json`** - Staging after test (validation)

## Logs Show

```
Test Database:   portfolio-staging (where tests run)
Source Database: portfolio (where seed data comes from)

STEP 1: COPYING PRODUCTION DATA TO STAGING
Reading from: portfolio (production - READ ONLY)
Writing to:   portfolio-staging (staging - test environment)
```

## Before vs After

### Before (Unreliable)
```
Staging (unknown state) → Clear → Test
```
- ❌ Different every time
- ❌ Fails leave corruption
- ❌ Hard to reproduce

### After (Reliable)
```
Production → Copy → Staging (clear) → Restore → Test  
```
- ✅ Same every time
- ✅ Fresh start always
- ✅ Easy to reproduce

## Bottom Line

Tests now start from a **known-good, production-like state** every single time, while keeping production completely safe! 🎉
